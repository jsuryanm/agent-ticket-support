# UDA-Hub — Architecture

UDA-Hub is a multi-agent customer-support orchestrator built on **LangGraph**.
This document explains the moving parts and the decisions behind them.

## 1. High-level flow

```
                 ┌──────────────┐
   START ───────▶│  supervisor  │  (entry: setup + long-term memory retrieval)
                 └──────┬───────┘
                        ▼
                 ┌──────────────┐
                 │  classifier  │  (LLM structured output: category/priority/conf)
                 └──────┬───────┘
                        ▼  route_after_classify
        ┌───────────────┼───────────────┬───────────────┐
        ▼               ▼               ▼               ▼
   ┌─────────┐    ┌───────────┐   ┌────────────┐   ┌─────────┐
   │ resolver│    │ tool_agent│   │ escalation │   │ memory  │
   │  (RAG)  │    │ (DB tools)│   │  (human)   │   │ (prefs) │
   └────┬────┘    └─────┬─────┘   └─────┬──────┘   └────┬────┘
        │ route         │ route         │               │
        ▼               ▼               │               │
   (escalation? ──▶ escalation)         │               │
        │               │               │               │
        └───────────────┴───────────────┴───────────────┘
                        ▼
                 ┌──────────────┐
                 │   finalize   │  (supervisor close: persist + learn + reply)
                 └──────┬───────┘
                        ▼
                       END
```

The **Supervisor** appears twice in the required design: once as the entry node
(`supervisor`) and once as the closing node (`finalize`). Splitting it into two
graph nodes keeps each node single-purpose and avoids a self-loop.

## 2. State

A single `TicketState` TypedDict (`agentic/state.py`) flows through the graph.
`messages` uses the `add_messages` reducer so every node appends to the
transcript instead of overwriting it. Other fields (`category`, `confidence`,
`route`, `retrieved_docs`, `memory_context`, `resolution`,
`escalation_required`) are working memory the agents read and write.

## 3. Agents (nodes)

| Node | Responsibility | LLM | Tools |
|------|----------------|-----|-------|
| `supervisor` (entry) | Normalise state, retrieve long-term memory for context | – | `memory_search` |
| `classifier` | Structured classification + routing signal | structured output | – |
| `resolver` | Answer from the knowledge base (RAG); escalate if unsure | structured output | `knowledge_search` |
| `tool_agent` | Account lookups/actions via the prebuilt ReAct agent | tool-calling | DB tools |
| `escalation` | Empathetic customer handoff + internal summary | structured output | – |
| `memory` | Distil and store a customer preference | yes | `memory_save` |
| `finalize` (close) | Persist outcome, write long-term memory, emit reply | – | `memory_save` |

The routing functions (`route_after_classify`, `route_after_resolver`,
`route_after_tools`) are **pure functions** — trivial to unit-test and easy to
reason about.

### Prebuilt where it helps, hand-built where it matters
The **orchestration graph** (nodes, edges, routing, the Supervisor split) is built
from scratch with `StateGraph` — that is the part the project asks us to own. The
Tool Agent's inner think→act→observe loop is delegated to the **prebuilt ReAct
agent** (`langchain.agents.create_agent`, the successor to LangGraph's deprecated
`langgraph.prebuilt.create_react_agent`). Reusing a well-tested tool loop is
simpler and more robust than hand-rolling one; we still own how its result feeds
routing (the node inspects the observed tool messages to decide escalation). The
loop is bounded via a `recursion_limit` derived from `MAX_TOOL_STEPS`.

## 4. Tools via MCP (FastMCP)

Tools are exposed by two **FastMCP** servers and consumed through
**langchain-mcp-adapters**:

- `agentic/tools/db_server.py` (`udahub-db`): `lookup_customer`,
  `get_subscription`, `list_reservations`, `cancel_reservation`,
  `process_refund`.
- `agentic/tools/rag_server.py` (`udahub-rag`): `knowledge_search`,
  `memory_save`, `memory_search`.

`agentic/tools/mcp_client.py` launches both servers over **stdio** using the
same Python interpreter and loads them as LangChain tools. Because stdio tools
are async, the compiled graph is driven with `ainvoke` (see the async chat loop
in `utils.py`).

**Testability split:** all real logic lives in plain modules (`db_ops.py`,
`rag_ops.py`); the MCP servers are thin wrappers. Tests exercise the logic
directly with temp SQLite DBs and an in-memory fake vector store — no
subprocesses, no network.

## 5. Memory

- **Short-term:** LangGraph checkpointer (`InMemorySaver`) keyed by `thread_id`
  (the ticket id). Each turn appends to the same thread's message history.
- **Long-term:** a Chroma collection (`udahub_memory_openai`). The Supervisor reads
  relevant notes at entry; `finalize` writes a compact outcome note and the
  Memory Agent stores explicit preferences. Notes are scoped per user via a
  metadata filter.

## 6. Safety

- The refund tool **never** auto-approves money (`needs_human=True`).
- Blocked accounts and refund-approval cases are routed to `escalation` (the
  Tool Agent detects `is_blocked`/`needs_human` in tool results).
- The Resolver only answers from retrieved context and escalates when it can't.
- Complaints and low-confidence classifications escalate automatically.

## 7. Dependency injection

`build_orchestrator(tools, llm=None, checkpointer=None)` injects the LLM and the
tool dict, so tests can pass fakes and notebooks can pass in-process tool
adapters over the same DB/RAG logic. This is the single seam that makes the
whole graph testable offline.

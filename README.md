# UDA-Hub — Multi-Agent Customer Support (CultPass)

A from-scratch **LangGraph** multi-agent system that triages and resolves
customer-support tickets for a fictional client, **CultPass**. It classifies an
incoming message, then routes it to a specialised agent: answer from the
knowledge base (RAG), act on the account via tools, capture a preference, or
hand off to a human — finishing by persisting the outcome and learning from it.

```
START → supervisor → classifier → {resolver | tool_agent | escalation | memory} → finalize → END
```

See `agentic/design/architecture.md` and `agentic/design/rag.md` for the design.

## Stack

- **Orchestration:** LangGraph `StateGraph` built by hand; the Tool Agent reuses the prebuilt ReAct loop (`langchain.agents.create_agent`)
- **LLM:** OpenAI `gpt-4o-mini` via `langchain-openai`
- **Tools:** two **FastMCP** servers consumed through `langchain-mcp-adapters`
- **RAG + long-term memory:** persistent **Chroma** + OpenAI embeddings
- **Short-term memory:** LangGraph checkpointer keyed by `thread_id`

## Project layout

```
solution/
├── 03_agentic_app.py          # entry point (async chat loop)
├── requirements.txt
├── .env.example
├── utils.py                   # db helpers + async chat interface
├── agentic/
│   ├── config.py              # paths, models, knobs (absolute paths)
│   ├── state.py               # TicketState
│   ├── llm.py                 # ChatOpenAI factory
│   ├── workflow.py            # builds the StateGraph from scratch
│   ├── agents/                # supervisor, classifier, resolver,
│   │                          #   tool_agent, escalation, memory
│   ├── tools/                 # db_ops/rag_ops (pure) + FastMCP servers + client
│   └── design/                # architecture.md, rag.md
├── data/
│   ├── models/                # SQLAlchemy models (cultpass, udahub)
│   ├── external/              # *.jsonl datasets (+ generated cultpass.db)
│   ├── core/                  # generated udahub.db
│   └── index/                 # generated Chroma store
├── scripts/
│   ├── 01_external_db_setup.py
│   ├── 02_core_db_setup.py
│   └── build_index.py
└── tests/                     # offline test suite (25 tests)
```

## Setup

```bash
cd solution
python -m venv .venv && source .venv/bin/activate      # Python 3.11+ (tested on 3.12)
pip install -r requirements.txt

cp .env.example .env            # then add your OPENAI_API_KEY
```

## Build the data

```bash
python scripts/01_external_db_setup.py   # -> data/external/cultpass.db
python scripts/02_core_db_setup.py       # -> data/core/udahub.db (>=14 KB articles)
python scripts/build_index.py            # -> data/index/ (needs OPENAI_API_KEY)
```

The first two scripts are offline; `build_index.py` calls the embeddings API.

## Run

```bash
python soltion/app.py          # optional: pass a ticket id, e.g. `python app.py`
```

You'll get an interactive prompt:

```
User: how do I reserve an event?
Assistant: You can reserve an experience by opening the CultPass app ...
User: q
```

The `ticket_id` is used as the LangGraph `thread_id`, so a session keeps
short-term memory across turns.

> **Why async?** MCP-over-stdio tools are asynchronous, so the graph is driven
> with `ainvoke` and the chat loop is async (`utils.async_chat_interface`). The
> starter's synchronous `chat_interface` cannot call async MCP tools.

## Tests

The suite runs fully offline (no API key, no network, no subprocesses) by
injecting fake LLMs/tools/vector stores into the same factories the app uses:

```bash
pytest -q          
```

Coverage: DB operations, RAG/memory operations, the classifier and its router,
the resolver (resolve vs. escalate), and end-to-end graph routing through the
resolver / tool / escalation paths plus short-term-memory persistence.

## Key decisions

- **MCP as recommended**, with all real logic kept in pure modules
  (`db_ops`, `rag_ops`) so the FastMCP servers stay thin and everything is
  testable without MCP.
- **Supervisor split** into `supervisor` (entry) + `finalize` (close) to keep
  nodes single-purpose and avoid self-loops.
- **Safety first:** refunds never auto-approve; blocked accounts, complaints,
  and low-confidence reads escalate to a human.
- **Dependency injection** in `build_orchestrator(...)` is the single seam that
  makes the graph testable and the provider swappable.

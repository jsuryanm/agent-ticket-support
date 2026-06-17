# UDA-Hub — RAG & Long-Term Memory

This document covers how retrieval-augmented generation (RAG) and long-term
memory are implemented.

## 1. Knowledge base ingestion

Source: `data/external/cultpass_articles.jsonl` (18 articles — the project
requires ≥14). `scripts/02_core_db_setup.py` loads them into the core
`knowledge` table; `scripts/build_index.py` then embeds them into Chroma.

- **No chunking.** Each KB article is short and self-contained (a single
  how-to/policy), so one article = one embedded document. This keeps retrieval
  results clean and citable; chunking would add complexity for no benefit here.
- **Embedded text** = `title + "\n\n" + content`. `title` and `tags` are also
  stored as metadata so retrieval results carry their source.

## 2. Embeddings & store

- **Embeddings:** OpenAI embeddings `text-embedding-small-3` (configurable via
  `OPENAI_EMBED_MODEL`).
- **Store:** persistent **Chroma** under `data/index/`, isolated in
  `agentic/tools/vectorstore.py` — the only module that imports chromadb. Two
  collections:
  - `cultpass_knowledge_openai` — the KB (RAG).
  - `udahub_memory_openai` — long-term memory.

## 3. Retrieval at query time

The Resolver calls the `knowledge_search` MCP tool with the customer's latest
message and `k = RAG_TOP_K` (default 3). The top-k articles are concatenated
into a context block and the LLM is instructed to answer **only** from that
context. If retrieval returns nothing, or the model sets `can_resolve=false`,
the ticket is escalated instead of risking a hallucinated answer.

```
question ─▶ knowledge_search(query, k=3) ─▶ [articles]
          ─▶ LLM(answer | can_resolve, grounded in articles)
          ─▶ resolve  (can_resolve=true)
          └▶ escalate (can_resolve=false or no docs)
```

## 4. Long-term memory

Long-term memory is also a Chroma collection, written and read through the same
RAG tools:

- **Write** (`memory_save`): the Memory Agent stores explicit customer
  preferences; `finalize` stores a compact note about each resolved/escalated
  outcome so the system "learns" from interactions.
- **Read** (`memory_search`): the Supervisor entry node fetches the most
  relevant notes for the current message and puts them in `memory_context`,
  which the Resolver folds into its prompt.
- **Scoping:** every note carries a `user_id` metadata field; `memory_search`
  filters on it so customers never see each other's notes. The key is the
  customer id when known, otherwise the ticket/thread id.

## 5. Tunable parameters (`agentic/config.py`)

| Setting | Default | Purpose |
|---------|---------|---------|
| `RAG_TOP_K` | 3 | KB articles retrieved per query |
| `MEMORY_TOP_K` | 3 | Memory notes retrieved per query |
| `CONFIDENCE_THRESHOLD` | 0.55 | Below this, escalate instead of resolve |
| `OPENAI_EMBED_MODEL` | text-embedding-3-small | Embedding model |

## 6. Limitations & next steps

- Similarity search is unfiltered by recency; a production system might decay or
  cap memory notes per user.
- The KB is small enough to skip re-ranking; larger corpora would benefit from a
  re-ranker or hybrid (keyword + vector) search.
- Embedding the KB requires an OpenAI key and network access, so the index is
  built by an explicit script rather than at app startup.

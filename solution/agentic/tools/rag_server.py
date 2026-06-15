import sys
from pathlib import Path

if __package__ in {None, ""}:
    PROJECT_ROOT = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(PROJECT_ROOT))

from fastmcp import FastMCP

from solution.config import settings

from solution.agentic.tools import rag_ops
from solution.agentic.tools.vector_store import get_vectorstore

config = settings()

mcp = FastMCP("udahub-rag")

@mcp.tool
def knowledge_search(query: str,k: int = config.RAG_TOP_K) -> list[dict]:
    """Search the CultPass knowledge base and return the top-k relevant articles.
    Use this to ground answers in official policy/help content before replying.
    """
    store = get_vectorstore(config.knowledge_base)
    return rag_ops.knowledge_search(store,query,k=k)

@mcp.tool
def memory_save(user_id: str, text: str) -> dict:
    """Save a long-term note about a customer (preference, prior resolution)."""
    store = get_vectorstore(config.memory_collection)
    return rag_ops.memory_save(store, user_id, text)


@mcp.tool
def memory_search(user_id: str, query: str, k: int = config.MEMORY_TOP_K) -> list[str]:
    """Recall a customer's past notes relevant to the current query."""
    store = get_vectorstore(config.memory_collection)
    return rag_ops.memory_search(store, user_id, query, k=k)


if __name__ == "__main__":
    mcp.run(transport="stdio")

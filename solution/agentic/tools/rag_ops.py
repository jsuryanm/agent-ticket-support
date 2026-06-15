from typing import Any, Protocol


class VectorStore(Protocol):
    """Minimal interface we rely on (satisfied by langchain_chroma.Chroma)."""

    def add_texts(self, texts: list[str], metadatas: list[dict] | None = None) -> Any: ...
    def similarity_search(self, query: str, k: int = 3, filter: dict | None = None) -> list: ...

def knowledge_search(store: VectorStore, query: str, k: int = 3) -> list[dict[str, Any]]:
    """Return the top-k knowledge snippets most similar to `query`."""
    docs = store.similarity_search(query, k=k)
    return [
        {
            "title": d.metadata.get("title", ""),
            "tags": d.metadata.get("tags", ""),
            "content": d.page_content,
        }
        for d in docs
    ]


def memory_save(store: VectorStore, user_id: str, text: str) -> dict[str, Any]:
    """Persist a single long-term memory note tied to a user."""
    store.add_texts([text], metadatas=[{"user_id": user_id}])
    return {"saved": True, "user_id": user_id, "text": text}


def memory_search(store: VectorStore, user_id: str, query: str, k: int = 3) -> list[str]:
    """Recall up to k of this user's past notes relevant to `query`."""
    docs = store.similarity_search(query, k=k, filter={"user_id": user_id})
    return [d.page_content for d in docs]

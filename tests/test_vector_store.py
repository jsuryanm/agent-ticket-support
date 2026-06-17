from solution.agentic.tools import vector_store
from solution.config import settings


def test_vector_store_uses_openai_embedding_model(monkeypatch):
    calls = {}

    class FakeEmbeddings:
        def __init__(self, model):
            calls["model"] = model

    monkeypatch.setattr(vector_store, "OpenAIEmbeddings", FakeEmbeddings)

    embedding = vector_store._embeddings()

    assert isinstance(embedding, FakeEmbeddings)
    assert calls["model"] == vector_store.config.openai_embed_model


def test_default_chroma_collections_are_openai_specific():
    config = settings()

    assert config.knowledge_base == "cultpass_knowledge_openai"
    assert config.memory_collection == "udahub_memory_openai"

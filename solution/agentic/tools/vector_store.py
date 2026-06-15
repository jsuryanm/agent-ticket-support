from solution.config import settings

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import OpenAIEmbeddings


config = settings()

def _embeddings() -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

def get_vectorstore(collection_name: str) -> Chroma: 
    return Chroma(collection_name=collection_name,
                  embedding_function=_embeddings(),
                  persist_directory=str(config.INDEX_DIR))

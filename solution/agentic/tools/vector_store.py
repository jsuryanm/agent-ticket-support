import logging

from solution.config import settings

from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings


config = settings()
logger = logging.getLogger("udahub.tools.vector_store")

def _embeddings() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(model=config.openai_embed_model)

def get_vectorstore(collection_name: str) -> Chroma: 
    logger.info("Opening Chroma collection '%s' at %s", collection_name, config.INDEX_DIR)
    return Chroma(collection_name=collection_name,
                  embedding_function=_embeddings(),
                  persist_directory=str(config.INDEX_DIR))

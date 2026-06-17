from functools import lru_cache

from solution.config import settings

from langchain_openai import ChatOpenAI 

config = settings()

@lru_cache(maxsize=1)
def get_llm() -> ChatOpenAI:
    """Returns cached ChatOpenAI instance"""
    return ChatOpenAI(model=config.openai_model,
                      api_key=config.openai_api_key,
                      temperature=config.llm_temp) 

from functools import lru_cache

from solution.config import settings

from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI 

config = settings()

@lru_cache(maxsize=1)
def get_llm() -> ChatGroq:
    """Returns cached ChatGroq instance"""
    return ChatGroq(model=config.groq_model,
                    api_key=config.groq_api_key,
                    temperature=config.llm_temp) 

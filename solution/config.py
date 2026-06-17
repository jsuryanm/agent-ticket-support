from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

from functools import lru_cache

PROJECT_ROOT: Path = Path(__file__).resolve().parents[1]
SOLUTION_ROOT: Path = Path(__file__).resolve().parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env",
                                      env_file_encoding="utf-8",
                                      case_sensitive=False,
                                      extra="ignore")

    PROJECT_ROOT: Path = PROJECT_ROOT
    SOLUTION_ROOT: Path = SOLUTION_ROOT
    
    openai_api_key: str = Field(...,description="openai api key")
    openai_model: str = Field(default="gpt-4o-mini",description="openai llm model")

    openai_embed_model: str = Field(default='text-embedding-3-small',description="openai embeddings model")

    llm_temp: float = Field(default=0.0)

    confidence_threshold: float = Field(default=0.55,description="minimum classifier confidence for escalation")
    max_tool_steps: int = Field(default=4,description="Maximum cap on tool calling")

    knowledge_base: str = "cultpass_knowledge_openai"
    memory_collection: str = "udahub_memory_openai"

    RAG_TOP_K: int = 3
    MEMORY_TOP_K: int = 3

    TOOLS_DIR: Path = SOLUTION_ROOT / "agentic" / "tools"
    DB_SERVER_PATH: Path = TOOLS_DIR / "db_server.py"
    RAG_SERVER_PATH: Path = TOOLS_DIR / "rag_server.py"

    ACCOUNT_ID: str = "cultpass"
    DATA_DIR: Path = SOLUTION_ROOT / "data"
    EXTERNAL_DIR: Path = DATA_DIR / "external"
    CORE_DIR: Path = DATA_DIR / "core"
    INDEX_DIR: Path = DATA_DIR / "index"  # Chroma persistent store lives here

    CULTPASS_DB: Path = EXTERNAL_DIR / "cultpass.db"
    UDAHUB_DB: Path = CORE_DIR / "udahub.db"


@lru_cache(maxsize=1)
def settings() -> Settings:
    """Stores result function call. 
    Future function calls with same args return cached result"""
    return Settings()
    

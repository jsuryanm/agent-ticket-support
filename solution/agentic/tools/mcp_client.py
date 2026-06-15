from langchain_mcp_adapters.client import MultiServerMCPClient

import json 
import os
import sys 
from typing import Any

from dotenv import dotenv_values
from langchain.tools import BaseTool

from solution.config import settings

config = settings()

DB_TOOL_NAMES = [
    "lookup_customer",
    "get_subscription",
    "list_reservations",
    "cancel_reservation",
    "process_refund",
]
RAG_TOOL_NAMES = ["knowledge_search", "memory_save", "memory_search"]

def _server_env() -> dict[str, str]:
    """Pass required app env vars to MCP subprocesses.

    The MCP stdio client intentionally inherits only a safe subset of the
    process environment by default, so API keys must be forwarded explicitly.
    """
    dotenv_env = {
        key: value
        for key, value in dotenv_values(config.PROJECT_ROOT / ".env").items()
        if value is not None
    }
    return {**os.environ, **dotenv_env}

def _connections() -> dict[str,dict]:
    """stdio connection spec for each server (absolute paths + same interpreter)."""
    common = {
        "transport": "stdio",
        "command": sys.executable,
        "cwd": str(config.PROJECT_ROOT),
        "env": _server_env(),
    }
    return {
        "udahub-db": {**common, "args": [str(config.DB_SERVER_PATH)]},
        "udahub-rag": {**common, "args": [str(config.RAG_SERVER_PATH)]},
    }

async def load_tools() -> dict[str,BaseTool]:
    """Connect to both MCP servers and return their tools keyed by name"""
    client = MultiServerMCPClient(_connections())
    tools = await client.get_tools()
    return {t.name:t for t in tools}

def coerce_json(result: Any) -> Any:
    """MCP text results may arrive as JSON strings; parse them when possible.

    Keeps agent code simple: it always gets back native dicts/lists.
    """
    if isinstance(result, str):
        try:
            return json.loads(result)
        except (ValueError, TypeError):
            return result
    return result

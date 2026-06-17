from __future__ import annotations

import logging
from typing import Any

from langchain_core.tools import StructuredTool

from solution.agentic.tools import db_ops, rag_ops
from solution.agentic.tools.mcp_client import DB_TOOL_NAMES, RAG_TOOL_NAMES
from solution.agentic.tools.vector_store import get_vectorstore
from solution.config import settings

config = settings()
logger = logging.getLogger("udahub.tools.local_tools")


async def _knowledge_search(query: str, k: int = 3) -> list[dict[str, Any]]:
    store = get_vectorstore(config.knowledge_base)
    return rag_ops.knowledge_search(store, query=query, k=k)


async def _memory_save(user_id: str, text: str) -> dict[str, Any]:
    store = get_vectorstore(config.memory_collection)
    return rag_ops.memory_save(store, user_id=user_id, text=text)


async def _memory_search(user_id: str, query: str, k: int = 3) -> list[str]:
    store = get_vectorstore(config.memory_collection)
    return rag_ops.memory_search(store, user_id=user_id, query=query, k=k)


async def _lookup_customer(identifier: str) -> dict[str, Any]:
    return db_ops.lookup_customer(identifier)


async def _get_subscription(user_id: str) -> dict[str, Any]:
    return db_ops.get_subscription(user_id)


async def _list_reservations(user_id: str) -> dict[str, Any]:
    return db_ops.list_reservations(user_id)


async def _cancel_reservation(reservation_id: str) -> dict[str, Any]:
    return db_ops.cancel_reservation(reservation_id)


async def _process_refund(user_id: str, reference: str = "") -> dict[str, Any]:
    return db_ops.process_refund(user_id=user_id, reference=reference)


def load_local_tools() -> dict[str, StructuredTool]:
    """Return in-process LangChain tools over the same logic exposed by MCP."""
    tools = [
        StructuredTool.from_function(
            coroutine=_knowledge_search,
            name="knowledge_search",
            description="Search CultPass knowledge-base articles.",
        ),
        StructuredTool.from_function(
            coroutine=_memory_save,
            name="memory_save",
            description="Save a compact memory note for a customer.",
        ),
        StructuredTool.from_function(
            coroutine=_memory_search,
            name="memory_search",
            description="Search prior customer memory notes.",
        ),
        StructuredTool.from_function(
            coroutine=_lookup_customer,
            name="lookup_customer",
            description="Look up a customer by id or email.",
        ),
        StructuredTool.from_function(
            coroutine=_get_subscription,
            name="get_subscription",
            description="Get subscription details for a customer id.",
        ),
        StructuredTool.from_function(
            coroutine=_list_reservations,
            name="list_reservations",
            description="List reservations for a customer id.",
        ),
        StructuredTool.from_function(
            coroutine=_cancel_reservation,
            name="cancel_reservation",
            description="Cancel a reservation by reservation id.",
        ),
        StructuredTool.from_function(
            coroutine=_process_refund,
            name="process_refund",
            description="Assess a refund request and flag whether human approval is needed.",
        ),
    ]
    loaded = {tool.name: tool for tool in tools}
    expected = {*DB_TOOL_NAMES, *RAG_TOOL_NAMES}
    missing = expected.difference(loaded)
    if missing:
        raise RuntimeError(f"Missing local tools: {sorted(missing)}")
    logger.info("Loaded local tools: %s", ", ".join(sorted(loaded)))
    return loaded

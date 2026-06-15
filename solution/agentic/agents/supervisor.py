import logging 

from typing import Callable 
from langchain_core.messages import AIMessage
from langchain_core.tools import BaseTool

from solution.config import settings
from solution.state import TicketState
from solution.agentic.tools.mcp_client import coerce_json
from solution.agentic.tools import db_ops

config = settings()
logger = logging.getLogger("udahub.supervisor")


def _memory_key(state: TicketState) -> str:
    return state.get("customer_id") or state.get("ticket_id") or "anonymous"

def _last_user_text(state: TicketState) -> str:
    for msg in reversed(state.get("messages",[])):
        if getattr(msg,'type',None) == "human":
            return msg.content 
    return ""

def make_supervisor_entry(memory_search):
    """seeds default and retrieves long term memory for context"""

    async def supervisor_entry(state: TicketState) -> dict:
        updates: dict = {}

        if not state.get("ticket_id"):
            updates['ticket_id'] = "adhoc"

        key = _memory_key(state)
        query = _last_user_text(state)
        try:
            raw = await memory_search.ainvoke(
                {"user_id": key, "query": query, "k": config.MEMORY_TOP_K}
            )
            memories = coerce_json(raw) or []
        except Exception as exc:  # memory store may be empty/unavailable -> degrade gracefully
            logger.warning("Memory retrieval failed: %s", exc)
            memories = []
        updates["memory_context"] = memories
        logger.info("Supervisor loaded %d memories for %s", len(memories), key)
        return updates

    return supervisor_entry

def make_finalize(memory_save: BaseTool) -> Callable:
    """Finalize node: persist outcome + long-term memory, emit the reply."""

    async def finalize(state: TicketState) -> dict:
        resolution = state.get("resolution") or "Thanks for reaching out — is there anything else I can help with?"
        escalated = bool(state.get("escalation_required"))

        # 1) Persist ticket status in the core DB (internal bookkeeping; direct
        #    in-process call is simpler than MCP for this private write).
        db_ops.record_resolution(
            ticket_id=state.get("ticket_id", "adhoc"),
            status="escalated" if escalated else "resolved",
            resolution=resolution,
        )

        # 2) Learn: store a compact note so future tickets recall this outcome.
        try:
            note = f"[{state.get('category','General')}] {resolution[:200]}"
            await memory_save.ainvoke({"user_id": _memory_key(state), "text": note})
        except Exception as exc:
            logger.warning("Memory write failed: %s", exc)

        # 3) The single customer-facing message for this turn.
        return {"messages": [AIMessage(content=resolution)], "escalation_required": escalated}

    return finalize

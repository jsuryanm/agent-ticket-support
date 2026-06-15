import logging
from typing import Callable

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import BaseTool

from solution.state import TicketState

logger = logging.getLogger("udahub.memory")

_SYSTEM = (
    "Extract the single durable preference the customer wants remembered, as a short "
    "third-person note (e.g. 'Prefers morning events'). Reply with the note text only."
)


def _last_user_text(state: TicketState) -> str:
    for msg in reversed(state.get("messages", [])):
        if getattr(msg, "type", None) == "human":
            return msg.content
    return ""


def _memory_key(state: TicketState) -> str:
    # Prefer a real customer id; fall back to the thread so memory still works.
    return state.get("customer_id") or state.get("ticket_id") or "anonymous"


def make_memory(llm: BaseChatModel, memory_save: BaseTool) -> Callable:
    """Return an async memory node bound to the LLM and memory_save tool."""

    async def memory_node(state: TicketState) -> dict:
        text = _last_user_text(state)
        note_msg = await llm.ainvoke([SystemMessage(content=_SYSTEM), HumanMessage(content=text)])
        note = (note_msg.content or text).strip()
        key = _memory_key(state)
        await memory_save.ainvoke({"user_id": key, "text": note})
        logger.info("Saved memory for %s: %s", key, note)
        return {"resolution": f"Got it — I'll remember that ({note})."}

    return memory_node

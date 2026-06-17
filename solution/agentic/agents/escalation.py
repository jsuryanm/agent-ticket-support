from __future__ import annotations

import logging
from typing import Callable

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from solution.state import TicketState
from solution.logging_config import log_event

logger = logging.getLogger("udahub.escalation")


class Escalation(BaseModel):
    customer_message: str = Field(description="Brief, empathetic message telling the customer it's being escalated.")
    internal_summary: str = Field(description="2-3 sentence summary for the human agent: issue, context, suggested action.")


_SYSTEM = (
    "You are the Escalation Agent for CultPass support. The ticket needs a human. "
    "Write a brief, warm customer_message that acknowledges the issue and says a teammate "
    "will follow up, and a crisp internal_summary for that teammate."
)


def _transcript(state: TicketState) -> str:
    parts = []
    for m in state.get("messages", []):
        role = getattr(m, "type", "?")
        parts.append(f"{role}: {m.content}")
    return "\n".join(parts)


def make_escalation(llm: BaseChatModel) -> Callable:
    """Return an async escalation node bound to the LLM."""
    structured = llm.with_structured_output(Escalation)

    async def escalation_node(state: TicketState) -> dict:
        context = (
            f"Category: {state.get('category','?')} | Priority: {state.get('priority','?')}\n"
            f"Transcript:\n{_transcript(state)}"
        )
        result: Escalation = await structured.ainvoke(
            [SystemMessage(content=_SYSTEM), HumanMessage(content=context)]
        )
        # Internal summary is for humans only - log it, don't show the customer.
        logger.info("ESCALATION SUMMARY: %s", result.internal_summary)
        log_event(
            logger,
            "escalated",
            ticket_id=state.get("ticket_id"),
            agent="escalation",
            route=state.get("route"),
            escalation_required=True,
            escalation_reason=state.get("escalation_reason") or "human_handoff",
        )
        return {
            "resolution": result.customer_message,
            "escalation_required": True,
        }

    return escalation_node

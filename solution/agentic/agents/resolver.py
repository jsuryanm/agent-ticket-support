from __future__ import annotations

import logging
from typing import Callable

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from solution.config import settings
from solution.state import TicketState
from solution.agentic.tools.mcp_client import coerce_json

config = settings()
logger = logging.getLogger("udahub.resolver")


class ResolverAnswer(BaseModel):
    can_resolve: bool = Field(description="True only if the context fully answers the question.")
    answer: str = Field(description="The customer-facing reply grounded in the context.")


_SYSTEM = (
    "You are the Resolver for CultPass support. Answer the customer using ONLY the "
    "knowledge-base context provided. Be concise, friendly and accurate. If the context "
    "does not contain enough information to answer confidently, set can_resolve=false and "
    "briefly say the issue will be passed to a human."
)


def _last_user_text(state: TicketState) -> str:
    for msg in reversed(state.get("messages", [])):
        if getattr(msg, "type", None) == "human":
            return msg.content
    return ""


def make_resolver(llm: BaseChatModel, knowledge_search: BaseTool) -> Callable:
    """Return an async resolver node bound to an LLM and the knowledge_search tool."""
    structured = llm.with_structured_output(ResolverAnswer)

    async def resolver_node(state: TicketState) -> dict:
        question = _last_user_text(state)

        # --- Retrieval -----------------------------------------------------
        raw = await knowledge_search.ainvoke({"query": question, "k": config.RAG_TOP_K})
        docs = coerce_json(raw) or []
        logger.info("Retrieved %d KB docs", len(docs))

        if not docs:
            # No grounding material -> don't hallucinate, escalate.
            return {
                "retrieved_docs": [],
                "resolution": "I couldn't find this in our help content, so I'm passing it to a human teammate.",
                "escalation_required": True,
            }

        context = "\n\n".join(f"# {d.get('title','')}\n{d.get('content','')}" for d in docs)
        memory = state.get("memory_context") or []
        memory_block = ("\nKnown about this customer:\n- " + "\n- ".join(memory)) if memory else ""

        result: ResolverAnswer = await structured.ainvoke(
            [
                SystemMessage(content=_SYSTEM + memory_block),
                HumanMessage(content=f"Context:\n{context}\n\nCustomer question: {question}"),
            ]
        )
        return {
            "retrieved_docs": docs,
            "resolution": result.answer,
            "escalation_required": not result.can_resolve,
        }

    return resolver_node


def route_after_resolver(state: TicketState) -> str:
    """Escalate if the resolver wasn't confident, otherwise finish."""
    return "escalation" if state.get("escalation_required") else "finalize"

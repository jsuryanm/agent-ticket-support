
import logging
from typing import Callable, Literal, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from solution.config import settings
from solution.state import TicketState

config = settings()

logger = logging.getLogger("udahub.classifier")

Category = Literal[
    "Refund",
    "Membership",
    "Billing",
    "Technical Support",
    "Account Access",
    "Complaint",
    "Preference",
    "General",
]
Priority = Literal["low", "medium", "high", "urgent"]


class Classification(BaseModel):
    """Structured classifier output."""

    category: Category = Field(description="The single best category for the ticket.")
    priority: Priority = Field(description="How urgent the ticket is.")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in the category, 0..1.")
    escalation_required: bool = Field(
        description="True if a human is clearly needed (safety, legal, abuse, or unresolved risk)."
    )
    customer_id: Optional[str] = Field(
        default=None, description="A user id or email mentioned by the customer, if any."
    )


_SYSTEM = SystemMessage(
    content=(
        "You are the Classifier for CultPass customer support.\n"
        "Classify the latest customer message into exactly one category:\n"
        "- Refund: wants money back / refund eligibility.\n"
        "- Membership: subscription plan, quota, credits, tiers.\n"
        "- Billing: payment methods, charges, invoices.\n"
        "- Technical Support: app bugs, login, password, notifications.\n"
        "- Account Access: blocked/suspended account, can't sign in due to account state.\n"
        "- Complaint: angry, dissatisfied, reporting bad experience.\n"
        "- Preference: stating a personal preference they want remembered.\n"
        "- General: anything else, greetings, how-to questions.\n"
        "Set escalation_required=true for complaints involving safety/discrimination, "
        "legal threats, or anything you cannot safely resolve. Extract a customer id or "
        "email only if the customer actually provides one."
    )
)


def _last_user_text(state: TicketState) -> str:
    for msg in reversed(state.get("messages", [])):
        if getattr(msg, "type", None) == "human":
            return msg.content
    return ""


def make_classifier(llm: BaseChatModel) -> Callable:
    """Return an async classifier node bound to the given LLM."""
    structured = llm.with_structured_output(Classification)

    async def classifier_node(state: TicketState) -> dict:
        text = _last_user_text(state)
        result: Classification = await structured.ainvoke([_SYSTEM, HumanMessage(content=text)])
        logger.info("Classified as %s (p=%s, conf=%.2f)", result.category, result.priority, result.confidence)
        update = {
            "category": result.category,
            "priority": result.priority,
            "confidence": result.confidence,
            "escalation_required": result.escalation_required,
        }
        if result.customer_id:
            update["customer_id"] = result.customer_id
        return update

    return classifier_node


def route_after_classify(state: TicketState) -> str:
    """Pure routing decision based on the classifier output."""
    category = state.get("category", "General")
    confidence = state.get("confidence", 1.0)

    # Anything explicitly flagged, a complaint, or a low-confidence read -> human.
    if state.get("escalation_required") or category == "Complaint" or confidence < config.confidence_threshold:
        return "escalation"
    if category == "Preference":
        return "memory"
    if category in {"Refund", "Membership", "Billing", "Account Access"}:
        return "tool_agent"
    return "resolver"

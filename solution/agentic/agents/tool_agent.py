from __future__ import annotations

import json
import logging
from typing import Callable

from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage
from langchain_core.tools import BaseTool

from solution.config import settings
from solution.state import TicketState

config = settings()

logger = logging.getLogger("udahub.tool_agent")

_SYSTEM = (
    "You are the Tool Agent for CultPass support. Use the available tools to look up "
    "the customer's account and take safe actions (e.g. cancel a reservation). "
    "Never promise a refund or unblock an account yourself — if a refund needs approval "
    "or the account is blocked, explain that you are escalating to a human. "
    "When you have enough information, reply directly to the customer with a clear, friendly answer."
)


def _input_messages(state: TicketState) -> list:
    """Pass the conversation turns; create_agent prepends the system prompt."""
    msgs: list = []
    if state.get("customer_id"):
        msgs.append(SystemMessage(content=f"Known customer id/email: {state['customer_id']}"))
    msgs.extend(m for m in state.get("messages", []) if getattr(m, "type", None) in {"human", "ai"})
    return msgs


def _needs_human(tool_message) -> bool:
    """True if an observed tool result requires a human (blocked / refund approval)."""
    content = getattr(tool_message, "content", "") or ""
    try:
        data = json.loads(content)
        if isinstance(data, dict):
            return bool(data.get("needs_human")) or bool(data.get("is_blocked"))
    except (ValueError, TypeError):
        pass
    low = content.lower()
    return '"needs_human": true' in low or '"is_blocked": true' in low


def make_tool_agent(llm: BaseChatModel, db_tools: list[BaseTool]) -> Callable:
    """Return an async tool-agent node backed by a prebuilt ReAct agent."""
    agent = create_agent(llm, db_tools, system_prompt=_SYSTEM)
    # Bound the inner loop: ~2 supersteps per tool round-trip, plus a margin.
    run_config = {"recursion_limit": 2 * config.max_tool_steps + 2}

    async def tool_agent_node(state: TicketState) -> dict:
        result = await agent.ainvoke({"messages": _input_messages(state)}, config=run_config)
        out_msgs = result["messages"]
        resolution = (out_msgs[-1].content if out_msgs else "") or "I've looked into your account."
        escalate = any(
            _needs_human(m) for m in out_msgs if getattr(m, "type", None) == "tool"
        )
        logger.info("Tool agent finished (escalate=%s)", escalate)
        return {"resolution": resolution, "escalation_required": escalate}

    return tool_agent_node


def route_after_tools(state: TicketState) -> str:
    """Escalate blocked/refund-approval cases, otherwise finish."""
    return "escalation" if state.get("escalation_required") else "finalize"

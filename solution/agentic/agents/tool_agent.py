from __future__ import annotations

import json
import logging
from typing import Any, Callable

from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage
from langchain_core.tools import BaseTool

from solution.config import settings
from solution.state import TicketState
from solution.logging_config import log_event

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


def _content_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and "text" in item:
                parts.append(str(item["text"]))
            else:
                parts.append(str(item))
        return "\n".join(parts)
    return str(content)


def _parse_tool_content(content: Any) -> Any:
    text = _content_text(content)
    try:
        return json.loads(text)
    except (ValueError, TypeError):
        return text


def _needs_human(tool_message) -> bool:
    """True if an observed tool result requires a human (blocked / refund approval)."""
    content = getattr(tool_message, "content", "") or ""
    data = _parse_tool_content(content)
    if isinstance(data, dict):
        return bool(data.get("needs_human")) or bool(data.get("is_blocked"))
    low = str(data).lower()
    return '"needs_human": true' in low or '"is_blocked": true' in low


def _tool_results(messages: list) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for message in messages:
        if getattr(message, "type", None) != "tool":
            continue
        parsed = _parse_tool_content(getattr(message, "content", "") or "")
        results.append(
            {
                "tool": getattr(message, "name", None) or "tool",
                "result": parsed,
            }
        )
    return results


def _tool_success(result: Any) -> bool:
    if isinstance(result, dict):
        if "success" in result:
            return bool(result["success"])
        if "error" in result:
            return False
        if "found" in result:
            return bool(result["found"])
    return True


def log_tool_result_events(
    state: TicketState,
    tool_results: list[dict[str, Any]],
    escalation_required: bool,
) -> None:
    for item in tool_results:
        log_event(
            logger,
            "tool_result",
            ticket_id=state.get("ticket_id"),
            agent="tool_agent",
            tool_name=item.get("tool"),
            tool_success=_tool_success(item.get("result")),
            escalation_required=escalation_required,
        )
    log_event(
        logger,
        "tool_agent_finished",
        ticket_id=state.get("ticket_id"),
        agent="tool_agent",
        tool_count=len(tool_results),
        escalation_required=escalation_required,
        escalation_reason="tool_requires_human" if escalation_required else None,
    )


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
        tool_results = _tool_results(out_msgs)
        logger.info("Tool agent finished (tools=%d, escalate=%s)", len(tool_results), escalate)
        log_tool_result_events(state, tool_results, escalate)
        return {
            "resolution": resolution,
            "tool_results": tool_results,
            "escalation_required": escalate,
        }

    return tool_agent_node


def route_after_tools(state: TicketState) -> str:
    """Escalate blocked/refund-approval cases, otherwise finish."""
    return "escalation" if state.get("escalation_required") else "finalize"

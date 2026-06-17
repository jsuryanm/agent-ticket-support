import asyncio

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import StructuredTool

from solution.agentic.workflow import build_orchestrator
from solution.agentic.agents.tool_agent import _needs_human, _tool_results


class FakeStructured:
    def __init__(self, schema):
        self.schema = schema

    async def ainvoke(self, messages):
        name = self.schema.__name__
        text = ""
        for message in reversed(messages):
            if getattr(message, "type", None) == "human":
                text = getattr(message, "content", "").lower()
                break

        if name == "Classification":
            if "subscription" in text:
                return self.schema(
                    category="Membership",
                    priority="medium",
                    confidence=0.93,
                    escalation_required=False,
                    customer_id="f556c0",
                )
            if "refund" in text:
                return self.schema(
                    category="Refund",
                    priority="high",
                    confidence=0.91,
                    escalation_required=False,
                    customer_id="a4ab87",
                )
            return self.schema(
                category="General",
                priority="low",
                confidence=0.95,
                escalation_required=False,
                customer_id=None,
            )

        if name == "ResolverAnswer":
            return self.schema(
                can_resolve=True,
                answer="Open the CultPass app, choose an experience, and tap Reserve.",
            )

        if name == "Escalation":
            return self.schema(
                customer_message="I'm sending this to a human teammate for review.",
                internal_summary="Refund approval requires human review for customer a4ab87.",
            )

        raise AssertionError(f"Unexpected schema: {name}")


class FakeLLM:
    def with_structured_output(self, schema):
        return FakeStructured(schema)


async def fake_memory_search(user_id: str, query: str, k: int = 3):
    """Return one prior memory in MCP-like structured form."""
    return [{"text": "Customer prefers concise instructions."}]


async def fake_memory_save(user_id: str, text: str):
    """Capture memory writes."""
    return {"saved": True, "user_id": user_id, "text": text}


async def fake_knowledge_search(query: str, k: int = 3):
    """Return one KB article."""
    return [
        {
            "title": "How to Reserve a Spot for an Event",
            "tags": "reservation, booking",
            "content": "Open the app, pick an experience, and tap Reserve.",
        }
    ]


async def fake_get_subscription(user_id: str):
    """Return subscription details for a fake user."""
    return {
        "found": True,
        "user_id": user_id,
        "status": "active",
        "tier": "premium",
        "monthly_quota": 5,
    }


async def fake_process_refund(user_id: str, reference: str = ""):
    """Return a refund result that requires human approval."""
    return {
        "success": True,
        "user_id": user_id,
        "reference": reference,
        "auto_approved": False,
        "needs_human": True,
    }


def make_tool(name, coroutine):
    return StructuredTool.from_function(
        coroutine=coroutine,
        name=name,
        description=f"Fake {name} tool",
    )


def fake_tool_agent_factory(_llm, db_tools):
    async def tool_agent_node(state):
        if state["category"] == "Refund":
            tool = next(tool for tool in db_tools if tool.name == "process_refund")
            result = await tool.ainvoke({"user_id": state["customer_id"], "reference": "demo"})
            return {
                "resolution": "Refund approval requires a human support lead.",
                "tool_results": [{"tool": tool.name, "result": result}],
                "escalation_required": True,
            }

        tool = next(tool for tool in db_tools if tool.name == "get_subscription")
        result = await tool.ainvoke({"user_id": state["customer_id"]})
        return {
            "resolution": (
                f"Your subscription is {result['status']} on the "
                f"{result['tier']} tier with {result['monthly_quota']} monthly reservations."
            ),
            "tool_results": [{"tool": tool.name, "result": result}],
            "escalation_required": False,
        }

    return tool_agent_node


class FakeToolMessage:
    type = "tool"
    name = "process_refund"

    def __init__(self, content):
        self.content = content


def test_tool_result_helpers_accept_mcp_content_blocks():
    message = FakeToolMessage(
        [
            {
                "type": "text",
                "text": (
                    '{"success": true, "auto_approved": false, '
                    '"needs_human": true}'
                ),
            }
        ]
    )

    assert _needs_human(message) is True
    assert _tool_results([message]) == [
        {
            "tool": "process_refund",
            "result": {
                "success": True,
                "auto_approved": False,
                "needs_human": True,
            },
        }
    ]


@pytest.fixture
def fake_tools():
    return {
        "knowledge_search": make_tool("knowledge_search", fake_knowledge_search),
        "memory_search": make_tool("memory_search", fake_memory_search),
        "memory_save": make_tool("memory_save", fake_memory_save),
        "get_subscription": make_tool("get_subscription", fake_get_subscription),
        "process_refund": make_tool("process_refund", fake_process_refund),
    }


async def invoke_graph(fake_tools, message, ticket_id):
    graph = build_orchestrator(
        fake_tools,
        llm=FakeLLM(),
        tool_agent_factory=fake_tool_agent_factory,
    )
    config = {"configurable": {"thread_id": ticket_id}}
    return await graph.ainvoke(
        {"ticket_id": ticket_id, "messages": [HumanMessage(content=message)]},
        config=config,
    )


def test_compiled_graph_resolves_knowledge_base_ticket(fake_tools):
    state = asyncio.run(invoke_graph(fake_tools, "How do I reserve an event?", "it-kb"))

    assert state["category"] == "General"
    assert state["route"] == "resolver"
    assert state["retrieved_docs"][0]["title"] == "How to Reserve a Spot for an Event"
    assert state["escalation_required"] is False
    assert "tap Reserve" in state["messages"][-1].content


def test_compiled_graph_uses_tool_agent_for_membership_ticket(fake_tools):
    state = asyncio.run(
        invoke_graph(
            fake_tools,
            "What subscription do I have? My id is f556c0.",
            "it-tool",
        )
    )

    assert state["category"] == "Membership"
    assert state["route"] == "tool_agent"
    assert state["tool_results"][0]["tool"] == "get_subscription"
    assert state["tool_results"][0]["result"]["tier"] == "premium"
    assert state["escalation_required"] is False
    assert "premium tier" in state["messages"][-1].content


def test_compiled_graph_escalates_refund_ticket(fake_tools):
    state = asyncio.run(
        invoke_graph(
            fake_tools,
            "I need a refund approval for customer a4ab87.",
            "it-escalation",
        )
    )

    assert state["category"] == "Refund"
    assert state["route"] == "tool_agent"
    assert state["escalation_required"] is True
    assert "human teammate" in state["messages"][-1].content

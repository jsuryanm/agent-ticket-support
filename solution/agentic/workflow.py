from __future__ import annotations

import logging
from typing import Callable, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from solution.agentic.agents.classifier import make_classifier, route_after_classify
from solution.agentic.agents.escalation import make_escalation
from solution.agentic.agents.memory import make_memory
from solution.agentic.agents.resolver import make_resolver, route_after_resolver
from solution.agentic.agents.supervisor import make_finalize, make_supervisor_entry
from solution.agentic.agents.tool_agent import make_tool_agent, route_after_tools
from solution.llm import get_llm
from solution.state import TicketState
from solution.agentic.tools.mcp_client import DB_TOOL_NAMES, load_tools

logger = logging.getLogger("udahub.workflow")


def build_orchestrator(
    tools: dict[str, BaseTool],
    *,
    llm: Optional[BaseChatModel] = None,
    checkpointer=None,
    tool_agent_factory: Callable[[BaseChatModel, list[BaseTool]], Callable] = make_tool_agent,
) -> CompiledStateGraph:
    """Assemble and compile the orchestrator graph.

    `tools` is a {name: tool} dict (from mcp_client.load_tools or a test double).
    `checkpointer` defaults to an in-memory saver -> short-term memory per thread_id.
    """
    llm = llm or get_llm()
    checkpointer = checkpointer or InMemorySaver()

    # Split tools per agent responsibility.
    knowledge_search = tools["knowledge_search"]
    memory_save = tools["memory_save"]
    memory_search = tools["memory_search"]
    db_tools = [tools[n] for n in DB_TOOL_NAMES if n in tools]
    logger.info(
        "Building orchestrator with %d total tools (%d DB tools)",
        len(tools),
        len(db_tools),
    )

    graph = StateGraph(TicketState)

    # --- Nodes (each small + single-responsibility) ------------------------
    graph.add_node("supervisor", make_supervisor_entry(memory_search))
    graph.add_node("classifier", make_classifier(llm))
    graph.add_node("resolver", make_resolver(llm, knowledge_search))
    graph.add_node("tool_agent", tool_agent_factory(llm, db_tools))
    graph.add_node("escalation", make_escalation(llm))
    graph.add_node("memory", make_memory(llm, memory_save))
    graph.add_node("finalize", make_finalize(memory_save))

    # --- Edges (routing kept explicit) -------------------------------------
    graph.add_edge(START, "supervisor")
    graph.add_edge("supervisor", "classifier")
    graph.add_conditional_edges(
        "classifier",
        route_after_classify,
        {
            "resolver": "resolver",
            "tool_agent": "tool_agent",
            "escalation": "escalation",
            "memory": "memory",
        },
    )
    graph.add_conditional_edges(
        "resolver",
        route_after_resolver,
        {"escalation": "escalation", "finalize": "finalize"},
    )
    graph.add_conditional_edges(
        "tool_agent",
        route_after_tools,
        {"escalation": "escalation", "finalize": "finalize"},
    )
    graph.add_edge("memory", "finalize")
    graph.add_edge("escalation", "finalize")
    graph.add_edge("finalize", END)

    return graph.compile(checkpointer=checkpointer)


async def get_orchestrator(*, checkpointer=None) -> CompiledStateGraph:
    """Convenience async builder: loads MCP tools then compiles the graph."""
    tools = await load_tools()
    logger.info("Loaded %d MCP tools", len(tools))
    return build_orchestrator(tools, checkpointer=checkpointer)

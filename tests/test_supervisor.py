import asyncio

from langchain_core.messages import HumanMessage

from solution.agentic.agents import supervisor


class HangingMemorySearch:
    async def ainvoke(self, _input):
        await asyncio.sleep(10)


def test_supervisor_degrades_when_memory_search_times_out(monkeypatch):
    monkeypatch.setattr(supervisor, "MEMORY_TOOL_TIMEOUT_SECONDS", 0.01)
    node = supervisor.make_supervisor_entry(HangingMemorySearch())

    result = asyncio.run(
        node(
            {
                "ticket_id": "timeout-ticket",
                "messages": [HumanMessage(content="How do I reserve an event?")],
            }
        )
    )

    assert result["memory_context"] == []

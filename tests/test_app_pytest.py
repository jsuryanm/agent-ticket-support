import asyncio
import importlib

from solution.utils import async_chat_interface


class NeverCalledAgent:
    async def ainvoke(self, _input, config=None):
        raise AssertionError("agent should not be called when the user quits")


class HangingAgent:
    async def ainvoke(self, _input, config=None):
        await asyncio.sleep(10)


def test_app_module_imports_cleanly():
    module = importlib.import_module("solution.app")

    assert hasattr(module, "main")


def test_chat_loop_exits_on_q(monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda _prompt: "q")

    asyncio.run(async_chat_interface(NeverCalledAgent(), "test-ticket"))

    output = capsys.readouterr().out
    assert "UDA-Hub ready" in output
    assert "Assistant: Goodbye!" in output


def test_chat_loop_uses_local_kb_fallback_on_timeout(monkeypatch, capsys):
    inputs = iter(["How do I reserve an event?", "q"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(inputs))
    monkeypatch.setattr("solution.utils.CHAT_TURN_TIMEOUT_SECONDS", 0.01)

    asyncio.run(async_chat_interface(HangingAgent(), "test-ticket"))

    output = capsys.readouterr().out
    assert "Assistant:" in output
    assert "How to Reserve a Spot for an Event" in output
    assert "Assistant: Goodbye!" in output

import asyncio
import contextlib
import io
import unittest
from unittest.mock import patch

from solution.utils import async_chat_interface


class HangingAgent:
    async def ainvoke(self, _input, config=None):
        await asyncio.sleep(10)


class ChatInterfaceTests(unittest.TestCase):
    def test_async_chat_interface_returns_local_fallback_on_timeout(self):
        output = io.StringIO()

        async def run_chat():
            with patch("solution.utils.CHAT_TURN_TIMEOUT_SECONDS", 0.01):
                with patch("builtins.input", side_effect=["How do I reserve an event?", "q"]):
                    with contextlib.redirect_stdout(output):
                        await async_chat_interface(HangingAgent(), "ticket-1")

        asyncio.run(run_chat())

        text = output.getvalue()
        self.assertIn("Assistant:", text)
        self.assertIn("How to Reserve a Spot for an Event", text)
        self.assertIn("Goodbye", text)


if __name__ == "__main__":
    unittest.main()

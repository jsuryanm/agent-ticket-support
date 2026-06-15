import asyncio
import logging
import sys
from pathlib import Path

if __package__ in {None, ""}:
    PROJECT_ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

from solution.agentic.workflow import get_orchestrator
from solution.utils import async_chat_interface


async def main(ticket_id: str = "1") -> None:
    load_dotenv()
    orchestrator = await get_orchestrator()
    await async_chat_interface(orchestrator, ticket_id)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    tid = sys.argv[1] if len(sys.argv) > 1 else "1"
    asyncio.run(main(tid))

import asyncio
import logging
import sys
from pathlib import Path

if __package__ in {None, ""}:
    PROJECT_ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

from solution.agentic.workflow import get_orchestrator
from solution.logging_config import configure_logging
from solution.utils import async_chat_interface

logger = logging.getLogger("udahub.app")


async def main(ticket_id: str = "1") -> None:
    load_dotenv()
    logger.info("Starting UDA-Hub chat for ticket_id=%s", ticket_id)
    orchestrator = await get_orchestrator()
    logger.info("Orchestrator ready for ticket_id=%s", ticket_id)
    await async_chat_interface(orchestrator, ticket_id)


if __name__ == "__main__":
    configure_logging()
    tid = sys.argv[1] if len(sys.argv) > 1 else "1"
    asyncio.run(main(tid))

import sys 
from pathlib import Path 

if __package__ in {None, ""}:
    PROJECT_ROOT = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(PROJECT_ROOT))

from fastmcp import FastMCP

from solution.agentic.tools import db_ops

mcp = FastMCP("udahub-db")

@mcp.tool
def lookup_customer(identifier: str) -> dict:
    """Look up a CultPass customer by user id OR email.

    Returns their name, email, whether the account is blocked, and a
    subscription summary. Use this first to ground any account question.
    """
    return db_ops.lookup_customer(identifier)

@mcp.tool 
def get_subscription(user_id: str) -> dict:
    """Get a customer's subscription status, tier and monthly quota."""
    return db_ops.get_subscription(user_id)

@mcp.tool
def list_reservations(user_id: str) -> dict:
    """List a customer's reservations with experience title, date and premium flag."""
    return db_ops.list_reservations(user_id)


@mcp.tool
def cancel_reservation(reservation_id: str) -> dict:
    """Cancel a specific reservation by its id. Sets its status to 'cancelled'."""
    return db_ops.cancel_reservation(reservation_id)


@mcp.tool
def process_refund(user_id: str, reference: str = "") -> dict:
    """Assess a refund request. Never auto-approves money; flags needs_human=True."""
    return db_ops.process_refund(user_id, reference)


if __name__ == "__main__":
    mcp.run(transport="stdio")

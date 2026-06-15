import sys 
from pathlib import Path 

from typing import Optional, Any 
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from solution.config import settings
from solution.data.models import cultpass, udahub

config = settings()

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

def _session(db_path: str | Path):
    engine = create_engine(f"sqlite:///{db_path}",echo=False)
    return sessionmaker(bind=engine)()

def lookup_customer(identifier: str,cultpass_db: Optional[str] = None) -> dict:
    """Find a customer by user_id or email and summarise their account.

    Returns {"found": False} when no match, otherwise account + subscription
    summary including the important `is_blocked` flag.
    """
    db = str(cultpass_db or config.CULTPASS_DB)
    session = _session(db)

    try:
        user = (session.query(cultpass.User)
                .filter((cultpass.User.user_id == identifier)
                        | (cultpass.User.email == identifier))
                        .first()) # first() returns the first row that matches the filter conditions

        if not user: 
            return {"found":False,"identifier":identifier}
        
        sub = user.subscription
        return {"found":True,
                "user_id":user.full_name,
                "email":user.email,
                "is_blocked":bool(user.is_blocked),
                "subscription":None
                
                if sub is None
                
                else {
                    "status":sub.status,
                    "tier":sub.tier,
                    "monthly_quota":sub.monthly_quota,
                }}
    finally:
        session.close()

def get_subscription(user_id: str, cultpass_db: Optional[str] = None) -> dict[str,Any]:
    """Return subscription details for a user, or {"found": False}."""
    db = str(cultpass_db or config.CULTPASS_DB)
    session = _session(db)
    try:
        sub = (session.query(cultpass.Subscription)
               .filter(cultpass.Subscription.user_id == user_id)
               .first())
        
        if not sub:
            return {"found":False,"user_id":user_id}
        
        return {"found":True,
                "user_id":user_id,
                "status":sub.status,
                "tier":sub.tier,
                "monthly_quota":sub.monthly_quota}
    finally:
        session.close()

def list_reservations(user_id: str,cultpass_db: Optional[str] = None) -> dict[str,str]:
    """List a user's reservations with the experience title and date."""
    db = str(cultpass_db or config.CULTPASS_DB)
    session = _session(db)

    try:
        rows = (session.query(cultpass.Reservation)
                .filter(cultpass.Reservation.user_id == user_id)
                .all())

        reservations = [
            {
                'reservation_id':r.reservation_id,
                'status':r.status,
                'experience_title':r.experience.title if r.experience else None,
                'when':r.experience.when.isoformat() if r.experience else None,
                'is_premium':bool(r.experience.is_premium) if r.experience  else None
            } for r in rows
        ]        
        return {'user_id':user_id,'count':len(reservations),'reservation':reservations}
    finally:
        session.close()

list_reservation = list_reservations

def cancel_reservation(reservation_id: str, 
                       cultpass_db: Optional[str] = None) -> dict[str,Any]:
    """Cancel a reservation by id. Returns the new status or an error."""
    db = str(cultpass_db or config.CULTPASS_DB)
    session = _session(db)
    try:
        r = (
            session.query(cultpass.Reservation)
            .filter(cultpass.Reservation.status == reservation_id)
            .first()
        )

        if not r:
            return {"success":False,
                    "error":"reservation_not_found",
                    "reservation_id":reservation_id}
        r.status = "cancelled"

        session.commit()
        return {"success":True,
                "reservation_id":reservation_id,
                "status":"cancelled"}
    
    except Exception:
        session.rollback()
        raise 

    finally:
        session.close()

def process_refund(user_id: str,
                   reference: str = "",
                   cultpass_db: Optional[str] = None) -> dict[str, Any]:
    """Evaluate a refund request against policy.

    Policy intentionally never auto-approves money movement: the tool returns an
    eligibility assessment and flags `needs_human=True`, so the agent explains the
    rules but routing always sends the final approval to a human. This mirrors the
    KB articles ("Do NOT offer refunds unless approved by support lead").
    """
    customer = lookup_customer(user_id, cultpass_db=cultpass_db)
    if not customer.get("found"):
        return {"success": False, "error": "customer_not_found", "needs_human": True}
    return {
        "success": True,
        "user_id": user_id,
        "reference": reference,
        "auto_approved": False,
        "needs_human": True,
        "reason": (
            "Refund eligibility depends on policy (subscription refundable within "
            "14 days; premium experience fees generally non-refundable). Approval "
            "must be confirmed by a human support lead."
        ),
    }

def record_resolution(
    ticket_id: str,
    status: str,
    resolution: str,
    udahub_db: Optional[str] = None,
) -> dict[str, Any]:
    """Update a ticket's status in the core DB if the ticket exists.

    Tolerant by design: unknown ticket ids (e.g. ad-hoc chat threads) are a
    no-op rather than an error, so the workflow never crashes on logging.
    """
    db = str(udahub_db or config.UDAHUB_DB)
    if not Path(db).exists():
        return {"recorded": False, "reason": "core_db_missing"}
    session = _session(db)
    try:
        meta = (
            session.query(udahub.TicketMetadata)
            .filter(udahub.TicketMetadata.ticket_id == ticket_id)
            .first()
        )
        if not meta:
            return {"recorded": False, "reason": "ticket_not_found", "ticket_id": ticket_id}
        meta.status = status
        session.commit()
        return {"recorded": True, "ticket_id": ticket_id, "status": status}
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

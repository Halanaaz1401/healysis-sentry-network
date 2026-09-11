from typing import List, Optional, Any, Dict
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict

from app.database import get_db
from app.models import AuditEvent, User, Facility, EventType
from app.security import require_cdmo

router = APIRouter(prefix="/api/v1/audit", tags=["SHA-256 Audit Ledger"])


class AuditEventResponse(BaseModel):
    id: int
    event_id: str
    timestamp: datetime
    actor_user_id: Optional[int] = None
    actor_name: Optional[str] = None
    actor_email: Optional[str] = None
    action: str
    event_type: str
    facility_id: Optional[int] = None
    facility_name: Optional[str] = None
    facility_code: Optional[str] = None
    payload_json: Optional[Dict[str, Any]] = None
    previous_hash: str
    current_hash: str
    is_tampered: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


@router.get("/events", response_model=List[AuditEventResponse])
def get_audit_events(
    limit: int = Query(default=100, ge=1, le=500, description="Max number of events to return"),
    offset: int = Query(default=0, ge=0, description="Pagination offset"),
    event_type: Optional[str] = Query(default=None, description="Filter by event_type (TRANSACTION, RULE_ALERT, REQUISITION, SYSTEM)"),
    current_user: User = Depends(require_cdmo),
    db: Session = Depends(get_db),
):
    """
    Returns tamper-evident SHA-256 audit ledger events.
    Requires CDMO or ADMIN role.
    Optionally filter by event_type.
    Ordered newest-first.
    """
    query = db.query(AuditEvent)

    if event_type:
        # Validate against known EventType values; silently ignore unknown values
        known_types = {e.value for e in EventType}
        if event_type.upper() in known_types:
            query = query.filter(AuditEvent.event_type == event_type.upper())

    events = (
        query.order_by(AuditEvent.timestamp.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    results: List[AuditEventResponse] = []
    for evt in events:
        actor_name = None
        actor_email = None
        if evt.actor_user_id is not None:
            actor = db.query(User).filter(User.id == evt.actor_user_id).first()
            if actor:
                actor_name = actor.full_name
                actor_email = actor.email

        facility_name = None
        facility_code = None
        if evt.facility_id is not None:
            facility = db.query(Facility).filter(Facility.id == evt.facility_id).first()
            if facility:
                facility_name = facility.name
                facility_code = facility.facility_code

        results.append(
            AuditEventResponse(
                id=evt.id,
                event_id=evt.event_id,
                timestamp=evt.timestamp,
                actor_user_id=evt.actor_user_id,
                actor_name=actor_name,
                actor_email=actor_email,
                action=evt.action,
                event_type=evt.event_type.value if hasattr(evt.event_type, "value") else str(evt.event_type),
                facility_id=evt.facility_id,
                facility_name=facility_name,
                facility_code=facility_code,
                payload_json=evt.payload_json,
                previous_hash=evt.previous_hash,
                current_hash=evt.current_hash,
                is_tampered=evt.is_tampered,
                created_at=evt.created_at,
            )
        )

    return results

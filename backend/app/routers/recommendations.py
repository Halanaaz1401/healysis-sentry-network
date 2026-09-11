import hashlib
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    Recommendation, User, UserRole, RecommendationStatus, 
    Inventory, Medicine, AuditEvent, EventType
)
from app.schemas import RecommendationResponse
from app.security import (
    get_current_user, require_facility_officer, require_cdmo, 
    verify_facility_access
)
from app.algorithms import generate_and_persist_redistribution_recommendations, run_forecast_and_alert_engine

router = APIRouter(prefix="/api/v1", tags=["Cross-District Stock Redistribution"])

class RecommendationActionRequest(BaseModel):
    action: str = Field(..., description="Action: 'APPROVE' or 'REJECT'")

def _enrich_recommendation(rec: Recommendation, db: Session) -> RecommendationResponse:
    med = getattr(rec, "medicine", None) or db.query(Medicine).filter(Medicine.id == rec.medicine_id).first()
    donor_inv = db.query(Inventory).filter(
        Inventory.facility_id == rec.donor_facility_id,
        Inventory.medicine_id == rec.medicine_id
    ).first()
    recip_inv = db.query(Inventory).filter(
        Inventory.facility_id == rec.recipient_facility_id,
        Inventory.medicine_id == rec.medicine_id
    ).first()

    return RecommendationResponse(
        id=rec.id,
        recommendation_code=rec.recommendation_code,
        donor_facility_id=rec.donor_facility_id,
        recipient_facility_id=rec.recipient_facility_id,
        medicine_id=rec.medicine_id,
        item_code=rec.item_code,
        recommended_quantity=rec.recommended_quantity,
        urgency_level=rec.urgency_level,
        haversine_distance_km=rec.haversine_distance_km,
        expected_days_cover_gained=rec.expected_days_cover_gained,
        confidence_score=rec.confidence_score,
        reason=rec.reason,
        status=rec.status,
        created_at=rec.created_at,
        donor_facility_name=rec.donor_facility.name if rec.donor_facility else None,
        donor_district=rec.donor_facility.district if rec.donor_facility else None,
        donor_state=rec.donor_facility.state if rec.donor_facility else None,
        recipient_facility_name=rec.recipient_facility.name if rec.recipient_facility else None,
        recipient_district=rec.recipient_facility.district if rec.recipient_facility else None,
        recipient_state=rec.recipient_facility.state if rec.recipient_facility else None,
        item_name=med.name if med else None,
        donor_current_stock=donor_inv.quantity if donor_inv else 0,
        donor_safety_stock=donor_inv.safety_stock if donor_inv else 40,
        recipient_current_stock=recip_inv.quantity if recip_inv else 0,
        recipient_safety_stock=recip_inv.safety_stock if recip_inv else 40
    )

@router.get("/recommendations", response_model=List[RecommendationResponse])
def get_all_recommendations(
    current_user: User = Depends(require_facility_officer),
    db: Session = Depends(get_db)
):
    """
    Returns list of cross-district stock redistribution recommendations.
    FACILITY_OFFICER sees recommendations involving their assigned facility (as donor or recipient).
    CDMO and ADMIN see all recommendations across facilities.
    """
    query = db.query(Recommendation)
    if current_user.role == UserRole.FACILITY_OFFICER:
        if current_user.facility_id is None:
            return []
        query = query.filter(
            (Recommendation.donor_facility_id == current_user.facility_id) |
            (Recommendation.recipient_facility_id == current_user.facility_id)
        )

    recs = query.order_by(Recommendation.urgency_level.desc(), Recommendation.created_at.desc()).all()
    return [_enrich_recommendation(r, db) for r in recs]

@router.get("/recommendations/{recommendation_id}", response_model=RecommendationResponse)
def get_recommendation_by_id(
    recommendation_id: int,
    current_user: User = Depends(require_facility_officer),
    db: Session = Depends(get_db)
):
    """
    Returns a single redistribution recommendation by ID.
    Enforces facility-scoped access if user is FACILITY_OFFICER.
    """
    rec = db.query(Recommendation).filter(Recommendation.id == recommendation_id).first()
    if not rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recommendation with id={recommendation_id} not found."
        )

    if current_user.role == UserRole.FACILITY_OFFICER:
        if current_user.facility_id not in [rec.donor_facility_id, rec.recipient_facility_id]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden. User is restricted to facility_id={current_user.facility_id}."
            )

    return _enrich_recommendation(rec, db)

@router.get("/facilities/{facility_id}/recommendations", response_model=List[RecommendationResponse])
def get_facility_recommendations(
    facility_id: int,
    current_user: User = Depends(require_facility_officer),
    db: Session = Depends(get_db)
):
    """
    Returns redistribution recommendations where specified facility is donor or recipient.
    Enforces facility-scoped access.
    """
    verify_facility_access(facility_id, current_user)
    recs = db.query(Recommendation).filter(
        (Recommendation.donor_facility_id == facility_id) |
        (Recommendation.recipient_facility_id == facility_id)
    ).order_by(Recommendation.created_at.desc()).all()
    return [_enrich_recommendation(r, db) for r in recs]

@router.post("/recommendations/generate", response_model=List[RecommendationResponse])
def generate_recommendations(
    current_user: User = Depends(require_cdmo),
    db: Session = Depends(get_db)
):
    """
    Triggers deterministic redistribution engine execution, ranks candidate donors, and persists recommendations.
    Requires CDMO or ADMIN role. FACILITY_OFFICER is restricted.
    """
    recommendations = generate_and_persist_redistribution_recommendations(db)
    return [_enrich_recommendation(r, db) for r in recommendations]

@router.post("/recommendations/{recommendation_id}/action", response_model=RecommendationResponse)
def action_recommendation(
    recommendation_id: int,
    req: RecommendationActionRequest,
    current_user: User = Depends(require_cdmo),
    db: Session = Depends(get_db)
):
    """
    Submits human operational decision (APPROVE or REJECT) on candidate redistribution transfer.
    Requires CDMO or ADMIN role.
    On APPROVE:
    1. Validates recommendation status is PENDING_HUMAN_APPROVAL.
    2. Validates donor has sufficient stock.
    3. Decreases donor stock and increases recipient stock.
    4. Records approval actor and timestamp.
    5. Emits tamper-evident AuditEvent.
    6. Recalculates forecast & risk engine across affected nodes.
    """
    rec = db.query(Recommendation).filter(Recommendation.id == recommendation_id).first()
    if not rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recommendation with id={recommendation_id} not found."
        )

    action_upper = req.action.upper().strip()
    if action_upper not in ["APPROVE", "REJECT"]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid action '{req.action}'. Expected 'APPROVE' or 'REJECT'."
        )

    if rec.status != RecommendationStatus.PENDING_HUMAN_APPROVAL:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Recommendation #{recommendation_id} is no longer pending (Current status: {rec.status.value})."
        )

    if action_upper == "APPROVE":
        donor_inv = db.query(Inventory).filter(
            Inventory.facility_id == rec.donor_facility_id,
            Inventory.medicine_id == rec.medicine_id
        ).first()

        if not donor_inv or donor_inv.quantity < rec.recommended_quantity:
            available_qty = donor_inv.quantity if donor_inv else 0
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Donor facility lacks sufficient stock for transfer (Available: {available_qty}, Required: {rec.recommended_quantity})."
            )

        recip_inv = db.query(Inventory).filter(
            Inventory.facility_id == rec.recipient_facility_id,
            Inventory.medicine_id == rec.medicine_id
        ).first()

        if not recip_inv:
            med = db.query(Medicine).filter(Medicine.id == rec.medicine_id).first()
            recip_inv = Inventory(
                facility_id=rec.recipient_facility_id,
                medicine_id=rec.medicine_id,
                item_code=rec.item_code,
                item_name=med.name if med else rec.item_code,
                quantity=0,
                safety_stock=40,
                unit=med.unit if med else "units"
            )
            db.add(recip_inv)

        # Atomic Stock Transfer
        donor_inv.quantity -= rec.recommended_quantity
        recip_inv.quantity += rec.recommended_quantity

        rec.status = RecommendationStatus.APPROVED
        rec.reviewed_by_user_id = current_user.id
        rec.reviewed_at = datetime.now(timezone.utc)

        # Audit Event Logging
        last_event = db.query(AuditEvent).order_by(AuditEvent.id.desc()).first()
        prev_hash = last_event.current_hash if last_event else "GENESIS_ROOT_HEALYSIS_000"

        payload = {
            "recommendation_id": rec.id,
            "donor_facility_id": rec.donor_facility_id,
            "recipient_facility_id": rec.recipient_facility_id,
            "item_code": rec.item_code,
            "quantity": rec.recommended_quantity,
            "action": "REDISTRIBUTION_TRANSFER_APPROVED",
            "reviewed_by_user_id": current_user.id
        }
        event_str = f"{prev_hash}|{rec.donor_facility_id}|{rec.recipient_facility_id}|{rec.item_code}|{rec.recommended_quantity}"
        curr_hash = hashlib.sha256(event_str.encode("utf-8")).hexdigest()

        audit_evt = AuditEvent(
            event_id=f"EVT-TRANSFER-{uuid.uuid4().hex[:8].upper()}",
            timestamp=datetime.now(timezone.utc),
            actor_user_id=current_user.id,
            action="REDISTRIBUTION_TRANSFER_APPROVED",
            facility_id=rec.recipient_facility_id,
            payload_json=payload,
            previous_hash=prev_hash,
            current_hash=curr_hash,
            event_type=EventType.TRANSACTION
        )
        db.add(audit_evt)

        # Recalculate Forecast & Risk Engine for both facilities
        run_forecast_and_alert_engine(db)

    elif action_upper == "REJECT":
        rec.status = RecommendationStatus.REJECTED
        rec.reviewed_by_user_id = current_user.id
        rec.reviewed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(rec)
    return _enrich_recommendation(rec, db)

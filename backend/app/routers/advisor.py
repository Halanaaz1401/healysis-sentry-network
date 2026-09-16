import uuid
import hashlib
import logging
from datetime import datetime, timezone, date, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from typing import List, Optional
from app.database import get_db
from app.models import User, UserRole, Facility, Inventory, Forecast, AuditEvent, EventType, Conversation, Message, utc_now
from app.schemas import (
    AdvisorChatRequest, AdvisorChatResponse,
    InventoryUpdateConfirmationRequest, InventoryUpdateConfirmationResponse,
    ConversationCreate, ConversationSummary, ConversationDetail, MessageSchema
)
from app.security import (
    get_current_user, require_facility_officer, verify_facility_access
)
from app.advisor_service import run_grounded_ai_advisor, verify_update_token, generate_conversation_title
from app.algorithms import classify_risk_severity, run_forecast_and_alert_engine

logger = logging.getLogger("healysis.advisor")

router = APIRouter(prefix="/api/v1/advisor", tags=["Healysis AI Advisor & Operational Intelligence"])

# ==========================================
# Conversation Endpoints
# ==========================================

@router.post("/conversations", response_model=ConversationSummary, status_code=status.HTTP_201_CREATED)
def create_conversation_endpoint(
    req: Optional[ConversationCreate] = None,
    current_user: User = Depends(require_facility_officer),
    db: Session = Depends(get_db)
):
    """
    Creates a new conversation session bound strictly to the authenticated user.
    """
    title = (req.title.strip() if req and req.title and req.title.strip() else "New Chat")
    convo = Conversation(
        user_id=current_user.id,
        title=title,
        created_at=utc_now(),
        updated_at=utc_now()
    )
    db.add(convo)
    db.commit()
    db.refresh(convo)
    return convo


@router.get("/conversations", response_model=List[ConversationSummary])
def list_conversations_endpoint(
    current_user: User = Depends(require_facility_officer),
    db: Session = Depends(get_db)
):
    """
    Lists lightweight metadata for conversations owned by the authenticated user,
    ordered by most recently updated first.
    Enforces strict server-side ownership.
    """
    convos = (
        db.query(Conversation)
        .filter(Conversation.user_id == current_user.id)
        .order_by(Conversation.updated_at.desc())
        .all()
    )
    return convos


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
def get_conversation_endpoint(
    conversation_id: int,
    current_user: User = Depends(require_facility_officer),
    db: Session = Depends(get_db)
):
    """
    Retrieves full details and message history for a specific conversation.
    Enforces strict ownership: returns 404 if not found or owned by another user.
    """
    convo = (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id, Conversation.user_id == current_user.id)
        .first()
    )
    if not convo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found."
        )

    # Order messages chronologically
    messages = (
        db.query(Message)
        .filter(Message.conversation_id == convo.id)
        .order_by(Message.created_at.asc())
        .all()
    )

    return ConversationDetail(
        id=convo.id,
        title=convo.title,
        created_at=convo.created_at,
        updated_at=convo.updated_at,
        messages=messages
    )


@router.post("/conversations/{conversation_id}/messages", response_model=AdvisorChatResponse)
def post_conversation_message_endpoint(
    conversation_id: int,
    request: AdvisorChatRequest,
    current_user: User = Depends(require_facility_officer),
    db: Session = Depends(get_db)
):
    """
    Appends a user message to an existing conversation, invokes the grounded AI Advisor,
    persists both user and advisor messages to the database, and updates conversation metadata.
    Enforces strict ownership: returns 404 if conversation is not owned by current user.
    """
    convo = (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id, Conversation.user_id == current_user.id)
        .first()
    )
    if not convo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found."
        )

    # Facility scoping check
    if current_user.role == UserRole.FACILITY_OFFICER:
        if request.facility_id and request.facility_id != current_user.facility_id:
            verify_facility_access(request.facility_id, current_user)

    now = utc_now()

    # 1. Persist user message
    user_msg = Message(
        conversation_id=convo.id,
        sender="user",
        text=request.message,
        meta_json=None,
        created_at=now
    )
    db.add(user_msg)

    # Auto-generate title if currently default
    if convo.title == "New Chat":
        convo.title = generate_conversation_title(request.message)

    # 2. Run grounded AI Advisor
    response = run_grounded_ai_advisor(request, current_user, db)

    # 3. Persist advisor response
    meta = {
        "summary": response.summary,
        "severity": response.severity,
        "evidence": response.evidence,
        "data_sources": response.data_sources,
        "recommended_actions": response.recommended_actions,
        "limitations": response.limitations,
        "pending_update": response.pending_update.model_dump() if response.pending_update else None
    }
    advisor_msg = Message(
        conversation_id=convo.id,
        sender="advisor",
        text=response.answer,
        meta_json=meta,
        created_at=utc_now()
    )
    db.add(advisor_msg)

    convo.updated_at = utc_now()
    db.commit()

    response.conversation_id = convo.id
    return response


@router.delete("/conversations/{conversation_id}")
def delete_conversation_endpoint(
    conversation_id: int,
    current_user: User = Depends(require_facility_officer),
    db: Session = Depends(get_db)
):
    """
    Deletes a conversation and its messages.
    Enforces strict ownership: returns 404 if not found or owned by another user.
    """
    convo = (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id, Conversation.user_id == current_user.id)
        .first()
    )
    if not convo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found."
        )

    db.delete(convo)
    db.commit()
    return {"status": "SUCCESS", "message": "Conversation deleted successfully."}


# ==========================================
# Chat & Confirmation Endpoints
# ==========================================

@router.post("/chat", response_model=AdvisorChatResponse)
def advisor_chat_endpoint(
    request: AdvisorChatRequest,
    current_user: User = Depends(require_facility_officer),
    db: Session = Depends(get_db)
):
    """
    Grounded AI Advisor endpoint.
    Processes natural language operational queries against verified backend tools.
    Enforces server-side RBAC and facility-scoped access control.
    Automatically persists to conversation history in database.
    """
    # Enforce facility scope if user is FACILITY_OFFICER
    if current_user.role == UserRole.FACILITY_OFFICER:
        if request.facility_id and request.facility_id != current_user.facility_id:
            verify_facility_access(request.facility_id, current_user)

    # Route through conversation persistence
    convo = None
    if request.conversation_id:
        convo = (
            db.query(Conversation)
            .filter(Conversation.id == request.conversation_id, Conversation.user_id == current_user.id)
            .first()
        )
        if not convo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found."
            )
    else:
        title = generate_conversation_title(request.message)
        convo = Conversation(
            user_id=current_user.id,
            title=title,
            created_at=utc_now(),
            updated_at=utc_now()
        )
        db.add(convo)
        db.commit()
        db.refresh(convo)

    now = utc_now()
    user_msg = Message(
        conversation_id=convo.id,
        sender="user",
        text=request.message,
        meta_json=None,
        created_at=now
    )
    db.add(user_msg)

    response = run_grounded_ai_advisor(request, current_user, db)

    meta = {
        "summary": response.summary,
        "severity": response.severity,
        "evidence": response.evidence,
        "data_sources": response.data_sources,
        "recommended_actions": response.recommended_actions,
        "limitations": response.limitations,
        "pending_update": response.pending_update.model_dump() if response.pending_update else None
    }
    advisor_msg = Message(
        conversation_id=convo.id,
        sender="advisor",
        text=response.answer,
        meta_json=meta,
        created_at=utc_now()
    )
    db.add(advisor_msg)
    convo.updated_at = utc_now()
    db.commit()

    response.conversation_id = convo.id
    return response

@router.post("/confirm-update", response_model=InventoryUpdateConfirmationResponse)
def confirm_inventory_update_endpoint(
    req: InventoryUpdateConfirmationRequest,
    current_user: User = Depends(require_facility_officer),
    db: Session = Depends(get_db)
):
    """
    Commits an AI Advisor frontline inventory update following explicit human confirmation.
    Enforces server-side RBAC, performs atomic DB mutation, recalculates Days of Cover
    and risk severity, refreshes alerts, and creates a SHA-256 chained audit block.
    """
    # 1. Enforce RBAC facility scope
    verify_facility_access(req.facility_id, current_user)

    # 2. Verify cryptographic confirmation token
    if not verify_update_token(
        token=req.confirmation_token,
        user_id=current_user.id,
        facility_id=req.facility_id,
        item_code=req.item_code,
        quantity=req.quantity,
        demand=req.daily_demand
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or tampered confirmation token."
        )

    # 3. Fetch target facility and inventory
    fac = db.query(Facility).filter(Facility.id == req.facility_id).first()
    if not fac:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Facility with id={req.facility_id} not found."
        )

    inv = db.query(Inventory).filter(
        Inventory.facility_id == req.facility_id,
        Inventory.item_code == req.item_code
    ).first()
    if not inv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resource {req.item_code} not found in facility {fac.name}."
        )

    old_qty = inv.quantity

    # 4. Atomic Mutation
    inv.quantity = req.quantity

    # Fetch and update Forecast
    forecast = db.query(Forecast).filter(
        Forecast.facility_id == req.facility_id,
        Forecast.item_code == req.item_code
    ).first()

    old_demand = forecast.expected_daily_demand if forecast else 10.0
    new_demand = req.daily_demand if req.daily_demand is not None else old_demand

    doc = round(req.quantity / new_demand, 1) if new_demand > 0 else 99.0
    stockout_days = int(doc) if doc < 365 else 365
    stockout_date = date.today() + timedelta(days=stockout_days)

    now_utc = datetime.now(timezone.utc)
    if forecast:
        forecast.expected_daily_demand = new_demand
        forecast.days_of_cover = doc
        forecast.projected_stockout_date = stockout_date
        forecast.calculated_at = now_utc
    else:
        forecast = Forecast(
            facility_id=req.facility_id,
            medicine_id=inv.medicine_id,
            item_code=req.item_code,
            forecast_date=date.today(),
            expected_daily_demand=new_demand,
            days_of_cover=doc,
            projected_stockout_date=stockout_date,
            confidence_score=0.92,
            calculated_at=now_utc
        )
        db.add(forecast)

    # Recompute risk severity
    severity = classify_risk_severity(doc, inv.quantity, inv.safety_stock)
    severity_str = severity.value if hasattr(severity, 'value') else str(severity)

    # 5. SHA-256 Tamper-evident Audit Ledger Entry
    prev_event = db.query(AuditEvent).order_by(AuditEvent.id.desc()).first()
    prev_hash = prev_event.current_hash if prev_event else "GENESIS_HASH_0000000000000000000000000000000000000000000000000000000000000000"
    event_id = f"EVT-UPD-{uuid.uuid4().hex[:8].upper()}"

    payload = {
        "action": "FRONTLINE_INVENTORY_UPDATE",
        "facility_id": req.facility_id,
        "facility_name": fac.name,
        "item_code": req.item_code,
        "item_name": inv.item_name,
        "previous_quantity": old_qty,
        "new_quantity": req.quantity,
        "previous_daily_demand": old_demand,
        "new_daily_demand": new_demand,
        "days_of_cover": doc,
        "severity": severity_str,
        "updated_by_user_id": current_user.id,
        "updated_by_role": current_user.role.value,
        "source": "AI_ADVISOR_FRONTLINE_INPUT"
    }

    event_str = f"{prev_hash}|{req.facility_id}|{req.item_code}|{old_qty}|{req.quantity}|{current_user.id}"
    curr_hash = hashlib.sha256(event_str.encode("utf-8")).hexdigest()

    audit_evt = AuditEvent(
        event_id=event_id,
        timestamp=now_utc,
        actor_user_id=current_user.id,
        action="FRONTLINE_INVENTORY_UPDATE",
        facility_id=req.facility_id,
        payload_json=payload,
        previous_hash=prev_hash,
        current_hash=curr_hash,
        event_type=EventType.TRANSACTION,
        is_tampered=False
    )
    db.add(audit_evt)
    db.commit()

    # 6. Post-update Forecast & Alert Refresh
    try:
        run_forecast_and_alert_engine(db)
        refreshed_fc = db.query(Forecast).filter(
            Forecast.facility_id == req.facility_id,
            Forecast.item_code == req.item_code
        ).first()
        if refreshed_fc:
            doc = refreshed_fc.days_of_cover
            if hasattr(refreshed_fc, "risk_level") and refreshed_fc.risk_level:
                severity_str = refreshed_fc.risk_level
            new_demand = refreshed_fc.expected_daily_demand
    except Exception as e:
        logger.warning(f"Post-update alert refresh note: {e}")

    return InventoryUpdateConfirmationResponse(
        status="SUCCESS",
        message=f"Updated successfully. {inv.item_name} stock at {fac.name} is now {req.quantity} {inv.unit} (Coverage: {doc} days, Risk: {severity_str}).",
        facility_id=fac.id,
        facility_name=fac.name,
        item_code=inv.item_code,
        item_name=inv.item_name,
        previous_quantity=old_qty,
        new_quantity=req.quantity,
        daily_demand=new_demand,
        days_of_cover=doc,
        severity=severity_str,
        audit_event_id=event_id
    )

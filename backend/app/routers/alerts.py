from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Alert, AlertStatus, User, UserRole, Facility, Medicine, Notification
from app.schemas import AlertResponse, RiskExplanationResponse, AlertActionRequest
from app.security import (
    get_current_user, require_facility_officer, require_cdmo, 
    verify_facility_access
)
from app.explainability import build_risk_explanation_for_alert
from app.notification_service import (
    acknowledge_alert_and_notifications,
    monitor_alert_and_notifications,
    resolve_alert_and_notifications,
    escalate_single_alert
)

router = APIRouter(prefix="/api/v1", tags=["Early Warning Alerts"])

def _enrich_alert(alt: Alert, db: Session) -> AlertResponse:
    fac = alt.facility or db.query(Facility).filter(Facility.id == alt.facility_id).first()
    med = db.query(Medicine).filter(Medicine.code == alt.resource_id).first() if alt.resource_id else None
    explanation = build_risk_explanation_for_alert(alt, db)

    # Resolve notification lifecycle timeline
    latest_notif = db.query(Notification).filter(
        Notification.alert_id == alt.id
    ).order_by(Notification.escalation_level.desc(), Notification.created_at.desc()).first()

    first_notif = db.query(Notification).filter(
        Notification.alert_id == alt.id,
        Notification.escalation_level == 0
    ).first()

    ack_user = None
    if latest_notif and latest_notif.acknowledged_by_user_id:
        ack_user = db.query(User).filter(User.id == latest_notif.acknowledged_by_user_id).first()

    notification_lifecycle = {
        "notification_created_at": first_notif.created_at.isoformat() if first_notif else alt.created_at.isoformat(),
        "is_escalated": alt.status == AlertStatus.ESCALATED or (latest_notif.is_escalated if latest_notif else False),
        "escalated_at": latest_notif.escalated_at.isoformat() if (latest_notif and latest_notif.escalated_at) else None,
        "escalation_reason": latest_notif.escalation_reason if (latest_notif and latest_notif.escalation_reason) else None,
        "is_acknowledged": alt.status in [AlertStatus.ACKNOWLEDGED, AlertStatus.MONITORED, AlertStatus.RESOLVED],
        "acknowledged_at": latest_notif.acknowledged_at.isoformat() if (latest_notif and latest_notif.acknowledged_at) else None,
        "acknowledged_by_name": ack_user.full_name if ack_user else None,
    }

    return AlertResponse(
        id=alt.id,
        alert_code=alt.alert_code,
        facility_id=alt.facility_id,
        resource_id=alt.resource_id or "",
        severity=alt.severity,
        alert_type=alt.alert_type,
        title=alt.title,
        evidence_json=alt.evidence_json,
        projected_impact_date=alt.projected_impact_date,
        status=alt.status,
        created_at=alt.created_at,
        updated_at=alt.updated_at,
        facility_name=fac.name if fac else None,
        item_name=med.name if med else alt.resource_id,
        explanation=explanation,
        notification_lifecycle=notification_lifecycle
    )

@router.get("/alerts", response_model=List[AlertResponse])
def get_all_alerts(
    current_user: User = Depends(require_facility_officer),
    db: Session = Depends(get_db)
):
    """
    Returns active early warning alerts.
    FACILITY_OFFICER sees only their assigned facility alerts.
    CDMO and ADMIN see all facilities.
    """
    query = db.query(Alert)
    if current_user.role == UserRole.FACILITY_OFFICER:
        if current_user.facility_id is None:
            return []
        query = query.filter(Alert.facility_id == current_user.facility_id)

    alerts = query.order_by(Alert.severity.desc(), Alert.created_at.desc()).all()
    return [_enrich_alert(a, db) for a in alerts]

@router.get("/alerts/{alert_id}", response_model=AlertResponse)
def get_alert_by_id(
    alert_id: int,
    current_user: User = Depends(require_facility_officer),
    db: Session = Depends(get_db)
):
    """
    Returns a single early warning alert by ID.
    Enforces facility-scoped access.
    """
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert with id={alert_id} not found."
        )

    verify_facility_access(alert.facility_id, current_user)
    return _enrich_alert(alert, db)

@router.get("/alerts/{alert_id}/explanation", response_model=RiskExplanationResponse)
def get_alert_explanation(
    alert_id: int,
    current_user: User = Depends(require_facility_officer),
    db: Session = Depends(get_db)
):
    """
    Returns an authoritative, deterministic explanation of why this risk alert was triggered,
    grounded in real database inventory and forecast calculations.
    Enforces facility-scoped access control.
    """
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert with id={alert_id} not found."
        )

    verify_facility_access(alert.facility_id, current_user)
    explanation = build_risk_explanation_for_alert(alert, db)
    return RiskExplanationResponse(**explanation)

@router.get("/facilities/{facility_id}/alerts", response_model=List[AlertResponse])
def get_facility_alerts(
    facility_id: int,
    current_user: User = Depends(require_facility_officer),
    db: Session = Depends(get_db)
):
    """
    Returns early warning alerts for a specific facility_id.
    Enforces facility-scoped access.
    """
    verify_facility_access(facility_id, current_user)
    alerts = db.query(Alert).filter(Alert.facility_id == facility_id).order_by(Alert.severity.desc()).all()
    return [_enrich_alert(a, db) for a in alerts]

@router.post("/alerts/{alert_id}/acknowledge", response_model=AlertResponse)
def acknowledge_alert(
    alert_id: int,
    req: Optional[AlertActionRequest] = None,
    current_user: User = Depends(require_facility_officer),
    db: Session = Depends(get_db)
):
    """
    Acknowledges an active or escalated early warning alert.
    RBAC:
    - FACILITY_OFFICER: Can acknowledge alerts for their assigned facility.
    - CDMO / ADMIN: Can acknowledge alerts across any facility.
    Emits an ALERT_ACKNOWLEDGED block to the tamper-evident SHA-256 audit ledger.
    """
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert with id={alert_id} not found."
        )

    verify_facility_access(alert.facility_id, current_user)
    reason = req.reason if req else None
    updated_alert = acknowledge_alert_and_notifications(db, alert, current_user, reason)
    return _enrich_alert(updated_alert, db)

@router.post("/alerts/{alert_id}/escalate", response_model=AlertResponse)
def escalate_alert(
    alert_id: int,
    req: Optional[AlertActionRequest] = None,
    current_user: User = Depends(require_facility_officer),
    db: Session = Depends(get_db)
):
    """
    Escalates an active or acknowledged alert to the CDMO supervisory authority.
    RBAC:
    - FACILITY_OFFICER: Can escalate alerts for their assigned facility.
    - CDMO / ADMIN: Can escalate alerts across any facility.
    Emits an ALERT_ESCALATED block to the tamper-evident SHA-256 audit ledger.
    """
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert with id={alert_id} not found."
        )

    verify_facility_access(alert.facility_id, current_user)
    reason = req.reason if req else None
    updated_alert = escalate_single_alert(db, alert, current_user, reason)
    return _enrich_alert(updated_alert, db)

@router.post("/alerts/{alert_id}/monitor", response_model=AlertResponse)
def monitor_alert(
    alert_id: int,
    req: Optional[AlertActionRequest] = None,
    current_user: User = Depends(require_facility_officer),
    db: Session = Depends(get_db)
):
    """
    Places an acknowledged alert under active clinical and inventory monitoring.
    RBAC:
    - FACILITY_OFFICER: Can monitor alerts for their assigned facility.
    - CDMO / ADMIN: Can monitor alerts across any facility.
    Emits an ALERT_MONITORED block to the SHA-256 audit ledger.
    """
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert with id={alert_id} not found."
        )

    verify_facility_access(alert.facility_id, current_user)
    reason = req.reason if req else None
    updated_alert = monitor_alert_and_notifications(db, alert, current_user, reason)
    return _enrich_alert(updated_alert, db)

@router.post("/alerts/{alert_id}/resolve", response_model=AlertResponse)
def resolve_alert(
    alert_id: int,
    req: Optional[AlertActionRequest] = None,
    current_user: User = Depends(require_facility_officer),
    db: Session = Depends(get_db)
):
    """
    Resolves an alert when safe buffer coverage has been restored.
    RBAC:
    - FACILITY_OFFICER: Can resolve alerts for their assigned facility.
    - CDMO / ADMIN: Can resolve alerts across any facility.
    Emits an ALERT_RESOLVED block to the SHA-256 audit ledger.
    """
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert with id={alert_id} not found."
        )

    verify_facility_access(alert.facility_id, current_user)
    reason = req.reason if req else None
    updated_alert = resolve_alert_and_notifications(db, alert, current_user, reason)
    return _enrich_alert(updated_alert, db)


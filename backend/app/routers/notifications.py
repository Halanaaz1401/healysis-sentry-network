from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    Notification, NotificationStatus, Alert, AlertStatus, User, UserRole, Facility, Medicine
)
from app.schemas import (
    NotificationResponse, UnreadNotificationsResponse,
    NotificationAcknowledgeRequest, EscalationProcessRequest
)
from app.security import (
    get_current_user, require_facility_officer, require_cdmo,
    verify_facility_access
)
from app.notification_service import (
    acknowledge_alert_and_notifications,
    escalate_unacknowledged_alerts,
    sync_notifications_for_alerts
)

router = APIRouter(prefix="/api/v1", tags=["Alert Notifications & Escalation"])

def _enrich_notification(notif: Notification, db: Session) -> NotificationResponse:
    fac = notif.facility or db.query(Facility).filter(Facility.id == notif.facility_id).first()
    med = db.query(Medicine).filter(Medicine.code == notif.resource_id).first() if notif.resource_id else None
    
    ack_user = None
    if notif.acknowledged_by_user_id:
        ack_user = db.query(User).filter(User.id == notif.acknowledged_by_user_id).first()

    alert_obj = notif.alert or db.query(Alert).filter(Alert.id == notif.alert_id).first()
    alert_details = None
    if alert_obj:
        alert_details = {
            "alert_code": alert_obj.alert_code,
            "status": alert_obj.status.value,
            "severity": alert_obj.severity.value,
            "alert_type": alert_obj.alert_type.value,
            "projected_impact_date": str(alert_obj.projected_impact_date) if alert_obj.projected_impact_date else None,
            "evidence": alert_obj.evidence_json
        }

    return NotificationResponse(
        id=notif.id,
        notification_code=notif.notification_code,
        alert_id=notif.alert_id,
        facility_id=notif.facility_id,
        facility_name=fac.name if fac else None,
        resource_id=notif.resource_id,
        item_name=med.name if med else notif.resource_id,
        severity=notif.severity.value if hasattr(notif.severity, "value") else str(notif.severity),
        channel=notif.channel.value if hasattr(notif.channel, "value") else str(notif.channel),
        recipient_role=notif.recipient_role.value if hasattr(notif.recipient_role, "value") else str(notif.recipient_role),
        recipient_user_id=notif.recipient_user_id,
        title=notif.title,
        message=notif.message,
        status=notif.status.value if hasattr(notif.status, "value") else str(notif.status),
        escalation_level=notif.escalation_level,
        escalation_reason=notif.escalation_reason,
        is_escalated=notif.is_escalated,
        escalated_at=notif.escalated_at,
        acknowledged_at=notif.acknowledged_at,
        acknowledged_by_user_id=notif.acknowledged_by_user_id,
        acknowledged_by_name=ack_user.full_name if ack_user else None,
        created_at=notif.created_at,
        updated_at=notif.updated_at,
        alert_details=alert_details
    )

@router.get("/notifications", response_model=List[NotificationResponse])
def get_notifications(
    unread_only: bool = Query(default=False, description="Filter for unread notifications only"),
    escalated_only: bool = Query(default=False, description="Filter for escalated notifications only"),
    limit: int = Query(default=50, ge=1, le=200, description="Max notifications to retrieve"),
    current_user: User = Depends(require_facility_officer),
    db: Session = Depends(get_db)
):
    """
    Returns in-app notifications for active early warning alerts.
    RBAC:
    - FACILITY_OFFICER: Scoped to notifications for their assigned facility.
    - CDMO / ADMIN: Access cross-facility notifications, including supervisory escalations.
    """
    # Ensure all active alerts have corresponding notification records
    sync_notifications_for_alerts(db)

    query = db.query(Notification)

    if current_user.role == UserRole.FACILITY_OFFICER:
        if current_user.facility_id is None:
            return []
        query = query.filter(Notification.facility_id == current_user.facility_id)

    if unread_only:
        query = query.filter(Notification.status == NotificationStatus.UNREAD)

    if escalated_only:
        query = query.filter(Notification.is_escalated == True)

    notifications = query.order_by(Notification.created_at.desc()).limit(limit).all()
    return [_enrich_notification(n, db) for n in notifications]

@router.get("/notifications/unread", response_model=UnreadNotificationsResponse)
def get_unread_notifications(
    current_user: User = Depends(require_facility_officer),
    db: Session = Depends(get_db)
):
    """
    Returns unread counts and recent unread notifications for navigation indicator/badge.
    Enforces facility-scoped access for FACILITY_OFFICER.
    """
    sync_notifications_for_alerts(db)

    query = db.query(Notification).filter(Notification.status == NotificationStatus.UNREAD)
    if current_user.role == UserRole.FACILITY_OFFICER:
        if current_user.facility_id is None:
            return UnreadNotificationsResponse(unread_count=0, escalated_count=0, notifications=[])
        query = query.filter(Notification.facility_id == current_user.facility_id)

    unread_notifs = query.order_by(Notification.created_at.desc()).all()
    escalated_count = sum(1 for n in unread_notifs if n.is_escalated)

    return UnreadNotificationsResponse(
        unread_count=len(unread_notifs),
        escalated_count=escalated_count,
        notifications=[_enrich_notification(n, db) for n in unread_notifs[:20]]
    )

@router.post("/notifications/{notification_id}/acknowledge", response_model=NotificationResponse)
def acknowledge_notification(
    notification_id: int,
    req: Optional[NotificationAcknowledgeRequest] = None,
    current_user: User = Depends(require_facility_officer),
    db: Session = Depends(get_db)
):
    """
    Acknowledges an alert notification.
    - FACILITY_OFFICER can acknowledge alerts for their assigned facility.
    - CDMO / ADMIN can acknowledge alerts across all facilities.
    Transitions alert and notification state, commits to SHA-256 audit ledger.
    """
    notif = db.query(Notification).filter(Notification.id == notification_id).first()
    if not notif:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Notification #{notification_id} not found."
        )

    # Enforce facility-scoped RBAC
    if current_user.role == UserRole.FACILITY_OFFICER:
        if current_user.facility_id is None or current_user.facility_id != notif.facility_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden. User is assigned to facility_id={current_user.facility_id} and cannot acknowledge notifications for facility_id={notif.facility_id}."
            )

    alert = db.query(Alert).filter(Alert.id == notif.alert_id).first()
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Associated alert #{notif.alert_id} not found."
        )

    reason = req.reason if req else None
    acknowledge_alert_and_notifications(db, alert, current_user, reason)
    db.refresh(notif)
    return _enrich_notification(notif, db)

@router.post("/notifications/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_as_read(
    notification_id: int,
    current_user: User = Depends(require_facility_officer),
    db: Session = Depends(get_db)
):
    """
    Marks an unread notification as READ (without acknowledging the clinical risk).
    Enforces facility-scoped access.
    """
    notif = db.query(Notification).filter(Notification.id == notification_id).first()
    if not notif:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Notification #{notification_id} not found."
        )

    if current_user.role == UserRole.FACILITY_OFFICER:
        if current_user.facility_id is None or current_user.facility_id != notif.facility_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden. Cannot view notification belonging to another facility."
            )

    if notif.status == NotificationStatus.UNREAD:
        notif.status = NotificationStatus.READ
        db.commit()
        db.refresh(notif)

    return _enrich_notification(notif, db)

@router.post("/notifications/process-escalations", response_model=List[NotificationResponse])
def process_escalations(
    req: Optional[EscalationProcessRequest] = None,
    current_user: User = Depends(require_cdmo),
    db: Session = Depends(get_db)
):
    """
    Deterministic escalation engine trigger.
    Evaluates unacknowledged alerts against configured SLA response thresholds.
    Requires CDMO or ADMIN role.
    """
    timeout_override = req.force_timeout_minutes if req else None
    escalated = escalate_unacknowledged_alerts(db, timeout_override, current_user.id)
    return [_enrich_notification(n, db) for n in escalated]

@router.get("/alerts/{alert_id}/notifications", response_model=List[NotificationResponse])
def get_alert_notifications(
    alert_id: int,
    current_user: User = Depends(require_facility_officer),
    db: Session = Depends(get_db)
):
    """
    Returns notification lifecycle history for a specific early warning alert.
    Enforces facility-scoped access.
    """
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert #{alert_id} not found."
        )

    verify_facility_access(alert.facility_id, current_user)
    notifications = db.query(Notification).filter(Notification.alert_id == alert_id).order_by(Notification.created_at.asc()).all()
    return [_enrich_notification(n, db) for n in notifications]

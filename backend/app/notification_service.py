import uuid
import hashlib
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.config import settings
from app.models import (
    Alert, AlertStatus, AlertSeverity, Notification, NotificationChannel,
    NotificationStatus, User, UserRole, Facility, AuditEvent, EventType
)

def emit_audit_event(
    db: Session,
    action: str,
    facility_id: Optional[int],
    actor_user_id: Optional[int],
    payload: dict,
    event_type: EventType = EventType.RULE_ALERT
) -> AuditEvent:
    """
    Appends a cryptographically linked SHA-256 block to the tamper-evident audit ledger.
    """
    now_utc = datetime.now(timezone.utc)
    last_event = db.query(AuditEvent).order_by(AuditEvent.id.desc()).first()
    prev_hash = last_event.current_hash if last_event else "GENESIS_ROOT_HEALYSIS_000"

    event_str = f"{prev_hash}|{action}|{facility_id}|{actor_user_id}|{now_utc.isoformat()}|{payload}"
    curr_hash = hashlib.sha256(event_str.encode("utf-8")).hexdigest()

    audit_evt = AuditEvent(
        event_id=f"EVT-{action[:8]}-{uuid.uuid4().hex[:8].upper()}",
        timestamp=now_utc,
        actor_user_id=actor_user_id,
        action=action,
        facility_id=facility_id,
        payload_json=payload,
        previous_hash=prev_hash,
        current_hash=curr_hash,
        event_type=event_type,
        is_tampered=False,
    )
    db.add(audit_evt)
    return audit_evt

# ==========================================
# Extensible Notification Channel Interface
# ==========================================
class BaseNotificationChannelHandler:
    """Abstract interface for extensible notification delivery (in_app, email, SMS, push)."""
    def send(self, notification: Notification) -> bool:
        raise NotImplementedError

class InAppNotificationHandler(BaseNotificationChannelHandler):
    """Primary in-app notification provider delivering real-time telemetry to the UI."""
    def send(self, notification: Notification) -> bool:
        # Delivered via relational database record queried by frontend AppShell & Alerts UI
        return True

class EmailNotificationHandler(BaseNotificationChannelHandler):
    """Pluggable email provider (e.g. SMTP / SendGrid / Amazon SES) for supervisory alerts."""
    def send(self, notification: Notification) -> bool:
        # Prototype: Ready for provider plug-in without modifying the early warning alert engine
        return True

class SMSNotificationHandler(BaseNotificationChannelHandler):
    """Pluggable SMS gateway (e.g. NIC SMS / CDAC / Twilio) for critical frontline escalations."""
    def send(self, notification: Notification) -> bool:
        return True

class PushNotificationHandler(BaseNotificationChannelHandler):
    """Pluggable mobile/web push provider (e.g. Firebase Cloud Messaging / WebPush)."""
    def send(self, notification: Notification) -> bool:
        return True

CHANNEL_HANDLERS: Dict[NotificationChannel, BaseNotificationChannelHandler] = {
    NotificationChannel.IN_APP: InAppNotificationHandler(),
    NotificationChannel.EMAIL: EmailNotificationHandler(),
    NotificationChannel.SMS: SMSNotificationHandler(),
    NotificationChannel.PUSH: PushNotificationHandler(),
}

def dispatch_notification_channel(notification: Notification) -> bool:
    handler = CHANNEL_HANDLERS.get(notification.channel, CHANNEL_HANDLERS[NotificationChannel.IN_APP])
    return handler.send(notification)

def create_alert_notification(
    db: Session,
    alert: Alert,
    target_role: UserRole = UserRole.FACILITY_OFFICER,
    target_user: Optional[User] = None,
    channel: NotificationChannel = NotificationChannel.IN_APP,
    actor_id: Optional[int] = None
) -> Notification:
    """
    Creates an initial frontline notification record for an active alert if not already notified.
    Dispatches to the configured channel handler and emits an ALERT_NOTIFICATION_CREATED audit event.
    """
    # Check if a non-escalated notification already exists for this alert
    existing = db.query(Notification).filter(
        Notification.alert_id == alert.id,
        Notification.escalation_level == 0
    ).first()
    if existing:
        return existing

    fac = alert.facility or db.query(Facility).filter(Facility.id == alert.facility_id).first()
    fac_name = fac.name if fac else f"Facility #{alert.facility_id}"

    notif_code = f"NOTIF-{alert.alert_code}-{uuid.uuid4().hex[:6].upper()}"
    impact_str = f"projected impact by {alert.projected_impact_date}" if alert.projected_impact_date else "immediate operational impact"
    
    title = f"{alert.severity.value}: {alert.title}"
    message = (
        f"Early warning alert triggered at {fac_name} for {alert.resource_id or 'inventory resource'} "
        f"({impact_str}). Action required: review stock telemetry and acknowledge or initiate replenishment."
    )

    now_utc = datetime.now(timezone.utc)
    notif = Notification(
        notification_code=notif_code,
        alert_id=alert.id,
        facility_id=alert.facility_id,
        resource_id=alert.resource_id,
        severity=alert.severity,
        channel=channel,
        recipient_role=target_role,
        recipient_user_id=target_user.id if target_user else None,
        title=title,
        message=message,
        status=NotificationStatus.UNREAD,
        escalation_level=0,
        is_escalated=False,
        created_at=now_utc,
        updated_at=now_utc
    )
    db.add(notif)
    db.flush()

    # Dispatch to channel handler
    dispatch_notification_channel(notif)

    # Actor resolution for audit ledger
    actor_user = db.query(User).filter(User.id == actor_id).first() if actor_id else None
    actor_role_str = actor_user.role.value if actor_user else "SYSTEM"
    actor_name_str = actor_user.full_name if actor_user else "SYSTEM_AUTOMATION"

    # Emit audit ledger record
    payload = {
        "notification_id": notif.id,
        "notification_code": notif.notification_code,
        "alert_id": alert.id,
        "alert_code": alert.alert_code,
        "facility_id": alert.facility_id,
        "resource_id": alert.resource_id,
        "severity": alert.severity.value,
        "channel": channel.value,
        "recipient_role": target_role.value,
        "status": "UNREAD",
        "actor": actor_name_str,
        "actor_role": actor_role_str,
        "previous_status": "NONE",
        "new_status": "UNREAD"
    }
    emit_audit_event(db, "ALERT_NOTIFICATION_CREATED", alert.facility_id, actor_id, payload, EventType.RULE_ALERT)
    db.commit()
    db.refresh(notif)
    return notif

def acknowledge_alert_and_notifications(
    db: Session,
    alert: Alert,
    current_user: User,
    reason: Optional[str] = None
) -> Alert:
    """
    Submits human operational decision acknowledging an active or escalated alert.
    RBAC Rules:
    - FACILITY_OFFICER can only acknowledge alerts belonging to their assigned facility.
    - CDMO and ADMIN can acknowledge alerts across facilities.
    Transitions:
    - Alert: ACTIVE/ESCALATED -> ACKNOWLEDGED
    - Associated notifications: UNREAD/READ/ESCALATED -> ACKNOWLEDGED
    Emits ALERT_ACKNOWLEDGED to SHA-256 audit ledger.
    """
    # Strict server-side RBAC enforcement
    if current_user.role == UserRole.FACILITY_OFFICER:
        if current_user.facility_id is None or current_user.facility_id != alert.facility_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Forbidden. User '{current_user.full_name}' is assigned to facility_id={current_user.facility_id} "
                    f"and cannot acknowledge alerts for facility_id={alert.facility_id}."
                )
            )

    # State validation: Resolved alerts cannot be acknowledged
    if alert.status == AlertStatus.RESOLVED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Invalid state transition: Alert #{alert.id} ({alert.alert_code}) is already RESOLVED and cannot be acknowledged."
        )

    prev_status = alert.status
    if prev_status == AlertStatus.ACKNOWLEDGED:
        # Idempotent acknowledgment
        return alert

    now_utc = datetime.now(timezone.utc)
    alert.status = AlertStatus.ACKNOWLEDGED
    alert.updated_at = now_utc

    # Update all associated unacknowledged notifications
    notifs = db.query(Notification).filter(
        Notification.alert_id == alert.id,
        Notification.status != NotificationStatus.ACKNOWLEDGED
    ).all()

    for n in notifs:
        n.status = NotificationStatus.ACKNOWLEDGED
        n.acknowledged_at = now_utc
        n.acknowledged_by_user_id = current_user.id
        n.updated_at = now_utc

    # Emit audit block
    payload = {
        "alert_id": alert.id,
        "alert_code": alert.alert_code,
        "facility_id": alert.facility_id,
        "resource_id": alert.resource_id,
        "previous_status": prev_status.value if hasattr(prev_status, "value") else str(prev_status),
        "new_status": "ACKNOWLEDGED",
        "actor_id": current_user.id,
        "actor": current_user.full_name,
        "actor_name": current_user.full_name,
        "actor_role": current_user.role.value,
        "reason": reason or "Operator human confirmation of alert acknowledgment."
    }
    emit_audit_event(db, "ALERT_ACKNOWLEDGED", alert.facility_id, current_user.id, payload, EventType.RULE_ALERT)

    db.commit()
    db.refresh(alert)
    return alert

def monitor_alert_and_notifications(
    db: Session,
    alert: Alert,
    current_user: User,
    reason: Optional[str] = None
) -> Alert:
    """
    Transitions an acknowledged alert into MONITORED state.
    Enforces RBAC:
    - FACILITY_OFFICER: Only assigned facility.
    - CDMO / ADMIN: Any facility.
    Emits ALERT_MONITORED to SHA-256 audit ledger.
    """
    if current_user.role == UserRole.FACILITY_OFFICER:
        if current_user.facility_id is None or current_user.facility_id != alert.facility_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden. Cannot monitor alert belonging to another facility."
            )

    if alert.status == AlertStatus.RESOLVED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Invalid state transition: Alert #{alert.id} is already RESOLVED and cannot transition to MONITORED."
        )

    prev_status = alert.status
    if prev_status == AlertStatus.MONITORED:
        return alert

    now_utc = datetime.now(timezone.utc)
    alert.status = AlertStatus.MONITORED
    alert.updated_at = now_utc

    payload = {
        "alert_id": alert.id,
        "alert_code": alert.alert_code,
        "facility_id": alert.facility_id,
        "resource_id": alert.resource_id,
        "previous_status": prev_status.value if hasattr(prev_status, "value") else str(prev_status),
        "new_status": "MONITORED",
        "actor_id": current_user.id,
        "actor": current_user.full_name,
        "actor_name": current_user.full_name,
        "actor_role": current_user.role.value,
        "reason": reason or "Alert placed under active clinical and inventory monitoring."
    }
    emit_audit_event(db, "ALERT_MONITORED", alert.facility_id, current_user.id, payload, EventType.RULE_ALERT)

    db.commit()
    db.refresh(alert)
    return alert

def resolve_alert_and_notifications(
    db: Session,
    alert: Alert,
    current_user: User,
    reason: Optional[str] = None
) -> Alert:
    """
    Transitions an alert into RESOLVED state (e.g. after successful local procurement or replenishment).
    Dismisses all active notifications associated with this alert.
    Enforces RBAC:
    - FACILITY_OFFICER: Only assigned facility.
    - CDMO / ADMIN: Any facility.
    Emits ALERT_RESOLVED to SHA-256 audit ledger.
    """
    if current_user.role == UserRole.FACILITY_OFFICER:
        if current_user.facility_id is None or current_user.facility_id != alert.facility_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden. Cannot resolve alert belonging to another facility."
            )

    prev_status = alert.status
    if prev_status == AlertStatus.RESOLVED:
        return alert

    now_utc = datetime.now(timezone.utc)
    alert.status = AlertStatus.RESOLVED
    alert.updated_at = now_utc

    # Update associated notifications to ACKNOWLEDGED
    notifs = db.query(Notification).filter(
        Notification.alert_id == alert.id,
        Notification.status.in_([NotificationStatus.UNREAD, NotificationStatus.READ, NotificationStatus.ESCALATED])
    ).all()
    for n in notifs:
        n.status = NotificationStatus.ACKNOWLEDGED
        n.acknowledged_at = now_utc
        n.acknowledged_by_user_id = current_user.id
        n.updated_at = now_utc

    payload = {
        "alert_id": alert.id,
        "alert_code": alert.alert_code,
        "facility_id": alert.facility_id,
        "resource_id": alert.resource_id,
        "previous_status": prev_status.value if hasattr(prev_status, "value") else str(prev_status),
        "new_status": "RESOLVED",
        "actor_id": current_user.id,
        "actor": current_user.full_name,
        "actor_name": current_user.full_name,
        "actor_role": current_user.role.value,
        "reason": reason or "Alert resolved following inventory replenishment / safe stock verification."
    }
    emit_audit_event(db, "ALERT_RESOLVED", alert.facility_id, current_user.id, payload, EventType.RULE_ALERT)

    db.commit()
    db.refresh(alert)
    return alert


def escalate_unacknowledged_alerts(
    db: Session,
    force_timeout_minutes: Optional[int] = None,
    actor_id: Optional[int] = None
) -> List[Notification]:
    """
    Deterministic Escalation Engine:
    Evaluates ACTIVE alerts that have not been acknowledged within the configured SLA.
    If timeout elapsed:
    1. Updates alert.status -> ESCALATED.
    2. Marks frontline notification as ESCALATED.
    3. Creates a new supervisory notification with recipient_role=CDMO and escalation_level=1.
    4. Emits ALERT_ESCALATED to SHA-256 audit ledger.
    """
    now_utc = datetime.now(timezone.utc)
    
    active_alerts = db.query(Alert).filter(
        Alert.status.in_([AlertStatus.ACTIVE]),
        Alert.severity.in_([AlertSeverity.CRITICAL, AlertSeverity.WARNING])
    ).all()

    escalated_notifications: List[Notification] = []

    for alert in active_alerts:
        # Check if already escalated
        already_escalated = db.query(Notification).filter(
            Notification.alert_id == alert.id,
            Notification.is_escalated == True,
            Notification.escalation_level >= 1
        ).first()
        if already_escalated:
            continue

        # Determine threshold
        if force_timeout_minutes is not None:
            timeout_min = force_timeout_minutes
        elif alert.severity == AlertSeverity.CRITICAL:
            timeout_min = settings.ESCALATION_CRITICAL_TIMEOUT_MINUTES
        else:
            timeout_min = settings.ESCALATION_WARNING_TIMEOUT_MINUTES

        alert_time = alert.created_at
        if alert_time.tzinfo is None:
            alert_time = alert_time.replace(tzinfo=timezone.utc)
            
        elapsed_minutes = (now_utc - alert_time).total_seconds() / 60.0

        if elapsed_minutes >= timeout_min:
            prev_status = alert.status
            alert.status = AlertStatus.ESCALATED
            alert.updated_at = now_utc

            # Mark existing frontline notifications
            frontline_notifs = db.query(Notification).filter(
                Notification.alert_id == alert.id,
                Notification.is_escalated == False
            ).all()

            for fn in frontline_notifs:
                fn.status = NotificationStatus.ESCALATED
                fn.is_escalated = True
                fn.escalated_at = now_utc
                fn.escalation_reason = f"Unacknowledged {alert.severity.value} alert exceeded {timeout_min}m response SLA"
                fn.updated_at = now_utc

            fac = alert.facility or db.query(Facility).filter(Facility.id == alert.facility_id).first()
            fac_name = fac.name if fac else f"Facility #{alert.facility_id}"

            esc_notif_code = f"NOTIF-ESC-{alert.id}-{uuid.uuid4().hex[:6].upper()}"
            esc_notif = Notification(
                notification_code=esc_notif_code,
                alert_id=alert.id,
                facility_id=alert.facility_id,
                resource_id=alert.resource_id,
                severity=alert.severity,
                channel=NotificationChannel.IN_APP,
                recipient_role=UserRole.CDMO,
                recipient_user_id=None,
                title=f"ESCALATED: {alert.severity.value} Stockout at {fac_name}",
                message=(
                    f"Frontline facility officer did not acknowledge {alert.severity.value} alert for {alert.resource_id} "
                    f"within the {timeout_min}-minute SLA threshold (elapsed: {round(elapsed_minutes, 1)}m). "
                    f"Escalated to CDMO Director for inter-facility redistribution and supervisory review."
                ),
                status=NotificationStatus.UNREAD,
                escalation_level=1,
                escalation_reason=f"Unacknowledged {alert.severity.value} alert exceeded {timeout_min}m response SLA",
                is_escalated=True,
                escalated_at=now_utc,
                created_at=now_utc,
                updated_at=now_utc
            )
            db.add(esc_notif)
            db.flush()

            # Record in SHA-256 audit ledger
            actor_user = db.query(User).filter(User.id == actor_id).first() if actor_id else None
            actor_role_str = actor_user.role.value if actor_user else "SYSTEM"
            actor_name_str = actor_user.full_name if actor_user else "SYSTEM_SLA_ENGINE"

            payload = {
                "notification_id": esc_notif.id,
                "notification_code": esc_notif.notification_code,
                "alert_id": alert.id,
                "alert_code": alert.alert_code,
                "facility_id": alert.facility_id,
                "resource_id": alert.resource_id,
                "severity": alert.severity.value,
                "escalation_level": 1,
                "recipient_role": "CDMO",
                "actor": actor_name_str,
                "actor_role": actor_role_str,
                "reason": esc_notif.escalation_reason,
                "previous_status": prev_status.value if hasattr(prev_status, "value") else str(prev_status),
                "new_status": "ESCALATED",
                "elapsed_minutes": round(elapsed_minutes, 1),
                "threshold_minutes": timeout_min
            }
            emit_audit_event(db, "ALERT_ESCALATED", alert.facility_id, actor_id, payload, EventType.RULE_ALERT)
            escalated_notifications.append(esc_notif)

    db.commit()
    for en in escalated_notifications:
        db.refresh(en)

    return escalated_notifications

def escalate_single_alert(
    db: Session,
    alert: Alert,
    current_user: User,
    reason: Optional[str] = None
) -> Alert:
    """
    Operator-initiated escalation of an active or acknowledged alert to the CDMO supervisory tier.
    RBAC:
    - FACILITY_OFFICER: Can escalate alerts for their assigned facility.
    - CDMO / ADMIN: Can escalate alerts across any facility.
    Emits an ALERT_ESCALATED block to the tamper-evident SHA-256 audit ledger.
    """
    if current_user.role == UserRole.FACILITY_OFFICER:
        if current_user.facility_id is None or current_user.facility_id != alert.facility_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden. User is restricted to facility_id={current_user.facility_id} and cannot escalate alert belonging to facility_id={alert.facility_id}."
            )

    if alert.status == AlertStatus.RESOLVED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot escalate an alert that is already RESOLVED."
        )

    prev_status = alert.status
    now_utc = datetime.now(timezone.utc)
    alert.status = AlertStatus.ESCALATED
    alert.updated_at = now_utc

    esc_reason = reason or f"Operator {current_user.full_name} ({current_user.role.value}) escalated risk to CDMO"

    # Mark existing frontline notifications as escalated
    frontline_notifs = db.query(Notification).filter(
        Notification.alert_id == alert.id,
        Notification.is_escalated == False
    ).all()
    for fn in frontline_notifs:
        fn.status = NotificationStatus.ESCALATED
        fn.is_escalated = True
        fn.escalated_at = now_utc
        fn.escalation_reason = esc_reason
        fn.updated_at = now_utc

    # Check if a CDMO notification already exists
    cdmo_notif = db.query(Notification).filter(
        Notification.alert_id == alert.id,
        Notification.is_escalated == True,
        Notification.recipient_role == UserRole.CDMO
    ).first()

    if not cdmo_notif:
        fac = alert.facility or db.query(Facility).filter(Facility.id == alert.facility_id).first()
        fac_name = fac.name if fac else f"Facility #{alert.facility_id}"
        esc_notif_code = f"NOTIF-ESC-{alert.id}-{uuid.uuid4().hex[:6].upper()}"
        cdmo_notif = Notification(
            notification_code=esc_notif_code,
            alert_id=alert.id,
            facility_id=alert.facility_id,
            resource_id=alert.resource_id,
            severity=alert.severity,
            channel=NotificationChannel.IN_APP,
            recipient_role=UserRole.CDMO,
            recipient_user_id=None,
            title=f"ESCALATED: {alert.severity.value} Stockout at {fac_name}",
            message=(
                f"{fac_name} operator {current_user.full_name} escalated {alert.severity.value} alert for {alert.resource_id}. "
                f"Escalation note: {esc_reason}. Requires CDMO review and inter-facility stock redistribution."
            ),
            status=NotificationStatus.UNREAD,
            escalation_level=1,
            escalation_reason=esc_reason,
            is_escalated=True,
            escalated_at=now_utc,
            created_at=now_utc,
            updated_at=now_utc
        )
        db.add(cdmo_notif)
        db.flush()

    # Emit SHA-256 tamper-evident audit event
    payload = {
        "notification_id": cdmo_notif.id if cdmo_notif else None,
        "alert_id": alert.id,
        "alert_code": alert.alert_code,
        "facility_id": alert.facility_id,
        "resource_id": alert.resource_id,
        "severity": alert.severity.value,
        "escalation_level": 1,
        "recipient_role": "CDMO",
        "actor": current_user.full_name,
        "actor_id": current_user.id,
        "actor_role": current_user.role.value,
        "reason": esc_reason,
        "previous_status": prev_status.value if hasattr(prev_status, "value") else str(prev_status),
        "new_status": "ESCALATED"
    }
    emit_audit_event(db, "ALERT_ESCALATED", alert.facility_id, current_user.id, payload, EventType.RULE_ALERT)

    db.commit()
    db.refresh(alert)
    return alert

def sync_notifications_for_alerts(db: Session) -> None:
    """
    Ensures active alerts have corresponding in-app notification records,
    and resolves/dismisses notifications for resolved alerts.
    """
    active_alerts = db.query(Alert).filter(
        Alert.status.in_([AlertStatus.ACTIVE, AlertStatus.ESCALATED]),
        Alert.severity.in_([AlertSeverity.CRITICAL, AlertSeverity.WARNING])
    ).all()

    for alt in active_alerts:
        existing = db.query(Notification).filter(Notification.alert_id == alt.id).first()
        if not existing:
            create_alert_notification(db, alt, target_role=UserRole.FACILITY_OFFICER)

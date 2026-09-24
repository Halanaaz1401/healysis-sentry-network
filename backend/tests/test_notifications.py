"""
test_notifications.py
Comprehensive test suite for the P1 NOTIFY -> ACKNOWLEDGE -> ESCALATE workflow.

Covers:
  1. Notification Lifecycle:
     - Notification creation from active alerts
     - List and unread queries
     - Scoped facility access for FACILITY_OFFICER
     - Cross-facility access for CDMO/ADMIN
  2. Acknowledgement:
     - FACILITY_OFFICER can acknowledge own facility's alert and notification
     - FACILITY_OFFICER cannot acknowledge another facility's alert or notification (HTTP 403)
     - CDMO and ADMIN can acknowledge alerts across facilities
     - Acknowledgment creates ALERT_ACKNOWLEDGED audit block
     - Acknowledgment does not mark an alert as RESOLVED (clinical stockout requires replenishment)
     - Acknowledged alerts do not escalate
  3. Escalation:
     - Deterministic timeout triggers escalation for unacknowledged alerts
     - Frontline notification marked ESCALATED
     - Supervisory notification created for CDMO (escalation_level=1)
     - ALERT_ESCALATED audit block emitted with SLA metadata
     - FACILITY_OFFICER cannot trigger escalation processing directly (HTTP 403)
"""
import os
import sys
from datetime import datetime, timezone, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ["TESTING"] = "true"

from app.config import settings
from app.database import Base, get_db, engine as db_engine
from app.models import (
    Facility, Medicine, Inventory, Alert, Notification, User, AuditEvent,
    FacilityType, UserRole, MedicineCategory, AlertSeverity, AlertType, AlertStatus,
    NotificationChannel, NotificationStatus, EventType,
)
from main import app
from app.notification_service import (
    create_alert_notification,
    acknowledge_alert_and_notifications,
    escalate_unacknowledged_alerts
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

ADMIN_TOKEN   = "Bearer TEST-TOKEN-UID-ADMIN-99"
CDMO_TOKEN    = "Bearer TEST-TOKEN-UID-CDMO-88"
OFFICER_JATNI = "Bearer TEST-TOKEN-UID-OFFICER-JATNI"   # Assigned to Jatni CHC
OFFICER_CUTTACK = "Bearer TEST-TOKEN-UID-OFFICER-MSDAS" # Assigned to UPHC MS Das

@pytest.fixture()
def db_session():
    settings.TESTING = True
    Base.metadata.create_all(bind=db_engine)
    db = TestingSessionLocal()
    yield db
    db.close()

@pytest.fixture(autouse=True)
def clean_tables():
    settings.TESTING = True
    Base.metadata.create_all(bind=db_engine)
    db = TestingSessionLocal()

    db.query(Notification).delete()
    db.query(AuditEvent).delete()
    db.query(Alert).delete()
    db.query(Inventory).delete()
    db.query(User).delete()
    db.query(Facility).delete()
    db.query(Medicine).delete()
    db.commit()
    db.close()
    yield
    db = TestingSessionLocal()
    from seed_db import ensure_facilities_seeded, ensure_demo_users_seeded
    ensure_facilities_seeded(db)
    ensure_demo_users_seeded(db)
    db.close()

def _seed_environment(db):
    """
    Seeds two facilities, two officers, CDMO, Admin, medicine, and alerts.
    """
    fac1 = Facility(
        facility_code="CHC-OD-KHU-001",
        name="Jatni CHC (Khordha)",
        facility_type=FacilityType.CHC,
        state="OD", district="Khordha",
        latitude=20.165, longitude=85.705,
    )
    fac2 = Facility(
        facility_code="UPHC-OD-CTC-002",
        name="UPHC MS Das (Kafla Bazar)",
        facility_type=FacilityType.UPHC,
        state="OD", district="Cuttack",
        latitude=20.462, longitude=85.882,
    )
    db.add_all([fac1, fac2])
    db.commit()

    med = Medicine(
        code="MED-ORS-SACHET",
        name="Oral Rehydration Salts (ORS)",
        category=MedicineCategory.ESSENTIAL_MEDICINE,
        unit="sachets",
    )
    db.add(med)
    db.commit()

    admin = User(firebase_uid="UID-ADMIN-99", email="admin@healysis.gov.in",
                 full_name="System Admin", role=UserRole.ADMIN)
    cdmo = User(firebase_uid="UID-CDMO-88", email="cdmo@healysis.gov.in",
                full_name="CDMO Director", role=UserRole.CDMO)
    officer1 = User(firebase_uid="UID-OFFICER-JATNI", email="officer.jatni@healysis.gov.in",
                    full_name="Jatni Officer", role=UserRole.FACILITY_OFFICER,
                    facility_id=fac1.id)
    officer2 = User(firebase_uid="UID-OFFICER-MSDAS", email="pharmacist.cuttack@healysis.gov.in",
                    full_name="Cuttack Officer", role=UserRole.FACILITY_OFFICER,
                    facility_id=fac2.id)
    db.add_all([admin, cdmo, officer1, officer2])
    db.commit()

    # Active Critical Alert at Jatni CHC
    alert1 = Alert(
        alert_code=f"ALT-{fac1.facility_code}-{med.code}",
        facility_id=fac1.id,
        resource_id=med.code,
        severity=AlertSeverity.CRITICAL,
        alert_type=AlertType.STOCKOUT_PROJECTED,
        title="Critical Stockout Projected for ORS",
        evidence_json={"current_quantity": 10, "safety_stock": 40, "days_of_cover": 1.0},
        projected_impact_date=datetime.now(timezone.utc).date() + timedelta(days=1),
        status=AlertStatus.ACTIVE,
        created_at=datetime.now(timezone.utc) - timedelta(minutes=30)  # Created 30 mins ago
    )
    # Active Warning Alert at UPHC MS Das
    alert2 = Alert(
        alert_code=f"ALT-{fac2.facility_code}-{med.code}",
        facility_id=fac2.id,
        resource_id=med.code,
        severity=AlertSeverity.WARNING,
        alert_type=AlertType.GHOST_DRAWDOWN,
        title="Stock Warning: ORS Below Buffer",
        evidence_json={"current_quantity": 25, "safety_stock": 40, "days_of_cover": 3.0},
        projected_impact_date=datetime.now(timezone.utc).date() + timedelta(days=3),
        status=AlertStatus.ACTIVE,
        created_at=datetime.now(timezone.utc) - timedelta(minutes=5)
    )
    db.add_all([alert1, alert2])
    db.commit()

    # Inventory for fac1 and fac2
    inv1 = Inventory(
        facility_id=fac1.id,
        medicine_id=med.id,
        item_code=med.code,
        item_name=med.name,
        quantity=10,
        safety_stock=40,
        unit="sachets",
    )
    inv2 = Inventory(
        facility_id=fac2.id,
        medicine_id=med.id,
        item_code=med.code,
        item_name=med.name,
        quantity=25,
        safety_stock=40,
        unit="sachets",
    )
    db.add_all([inv1, inv2])
    db.commit()

    db.refresh(fac1)
    db.refresh(fac2)
    db.refresh(alert1)
    db.refresh(alert2)
    db.refresh(inv1)
    db.refresh(inv2)

    return {
        "fac1": fac1, "fac2": fac2, "med": med,
        "admin": admin, "cdmo": cdmo, "officer1": officer1, "officer2": officer2,
        "alert1": alert1, "alert2": alert2,
        "inv1": inv1, "inv2": inv2
    }


# ==============================================================================
# 1. NOTIFICATION LIFECYCLE TESTS
# ==============================================================================

class TestNotificationLifecycle:

    def test_notification_automatically_created_for_active_alert(self, db_session):
        s = _seed_environment(db_session)
        
        # Query notifications endpoint
        res = client.get("/api/v1/notifications", headers={"Authorization": CDMO_TOKEN})
        assert res.status_code == 200
        data = res.json()
        assert len(data) >= 2

        # Check alert1 notification properties
        notif1 = next((n for n in data if n["alert_id"] == s["alert1"].id), None)
        assert notif1 is not None
        assert notif1["facility_id"] == s["fac1"].id
        assert notif1["severity"] == "CRITICAL"
        assert notif1["channel"] == "IN_APP"
        assert notif1["status"] == "UNREAD"
        assert notif1["is_escalated"] is False
        assert "Critical" in notif1["title"]

    def test_facility_officer_sees_only_assigned_facility_notifications(self, db_session):
        s = _seed_environment(db_session)

        # Officer 1 (Jatni) queries notifications
        res = client.get("/api/v1/notifications", headers={"Authorization": OFFICER_JATNI})
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 1
        assert data[0]["facility_id"] == s["fac1"].id
        assert data[0]["alert_id"] == s["alert1"].id

        # Officer 2 (Cuttack) queries notifications
        res2 = client.get("/api/v1/notifications", headers={"Authorization": OFFICER_CUTTACK})
        assert res2.status_code == 200
        data2 = res2.json()
        assert len(data2) == 1
        assert data2[0]["facility_id"] == s["fac2"].id
        assert data2[0]["alert_id"] == s["alert2"].id

    def test_unread_notifications_count_endpoint(self, db_session):
        s = _seed_environment(db_session)

        res = client.get("/api/v1/notifications/unread", headers={"Authorization": CDMO_TOKEN})
        assert res.status_code == 200
        data = res.json()
        assert data["unread_count"] == 2
        assert len(data["notifications"]) == 2

    def test_mark_notification_as_read(self, db_session):
        s = _seed_environment(db_session)
        notif = create_alert_notification(db_session, s["alert1"])

        res = client.post(
            f"/api/v1/notifications/{notif.id}/read",
            headers={"Authorization": OFFICER_JATNI}
        )
        assert res.status_code == 200
        assert res.json()["status"] == "READ"

        # Reading does NOT acknowledge the clinical alert
        db_session.expire_all()
        alert = db_session.query(Alert).filter(Alert.id == s["alert1"].id).first()
        assert alert.status == AlertStatus.ACTIVE


# ==============================================================================
# 2. ACKNOWLEDGEMENT TESTS & RBAC
# ==============================================================================

class TestAlertAcknowledgement:

    def test_facility_officer_can_acknowledge_own_facility_alert(self, db_session):
        s = _seed_environment(db_session)
        notif = create_alert_notification(db_session, s["alert1"])
        audit_before = db_session.query(AuditEvent).count()

        res = client.post(
            f"/api/v1/alerts/{s['alert1'].id}/acknowledge",
            headers={"Authorization": OFFICER_JATNI}
        )
        assert res.status_code == 200
        assert res.json()["status"] == "ACKNOWLEDGED"

        db_session.expire_all()
        # Verify alert updated in DB
        alert_after = db_session.query(Alert).filter(Alert.id == s["alert1"].id).first()
        assert alert_after.status == AlertStatus.ACKNOWLEDGED

        # Verify notification status updated
        notif_after = db_session.query(Notification).filter(Notification.id == notif.id).first()
        assert notif_after.status == NotificationStatus.ACKNOWLEDGED
        assert notif_after.acknowledged_by_user_id == s["officer1"].id
        assert notif_after.acknowledged_at is not None

        # Verify audit ledger entry
        audit_after = db_session.query(AuditEvent).count()
        assert audit_after == audit_before + 1

        last_evt = db_session.query(AuditEvent).order_by(AuditEvent.id.desc()).first()
        assert last_evt.action == "ALERT_ACKNOWLEDGED"
        assert last_evt.facility_id == s["fac1"].id
        assert last_evt.actor_user_id == s["officer1"].id
        assert last_evt.payload_json["alert_id"] == s["alert1"].id
        assert last_evt.payload_json["new_status"] == "ACKNOWLEDGED"

    def test_facility_officer_cannot_acknowledge_other_facility_alert(self, db_session):
        """Cross-facility IDOR attempt: Officer 1 attempts to acknowledge Officer 2's alert."""
        s = _seed_environment(db_session)
        audit_before = db_session.query(AuditEvent).count()

        res = client.post(
            f"/api/v1/alerts/{s['alert2'].id}/acknowledge",
            headers={"Authorization": OFFICER_JATNI}
        )
        assert res.status_code == 403
        assert "forbidden" in res.json()["detail"].lower()

        # Alert status and audit events must be completely untouched
        db_session.expire_all()
        alert2 = db_session.query(Alert).filter(Alert.id == s["alert2"].id).first()
        assert alert2.status == AlertStatus.ACTIVE
        assert db_session.query(AuditEvent).count() == audit_before

    def test_facility_officer_cannot_acknowledge_other_facility_notification(self, db_session):
        """Cross-facility IDOR attempt via notification endpoint."""
        s = _seed_environment(db_session)
        notif2 = create_alert_notification(db_session, s["alert2"])

        res = client.post(
            f"/api/v1/notifications/{notif2.id}/acknowledge",
            json={"reason": "Unauthorized attempt"},
            headers={"Authorization": OFFICER_JATNI}
        )
        assert res.status_code == 403

        db_session.expire_all()
        notif_after = db_session.query(Notification).filter(Notification.id == notif2.id).first()
        assert notif_after.status == NotificationStatus.UNREAD

    def test_cdmo_can_acknowledge_alert_across_facilities(self, db_session):
        s = _seed_environment(db_session)

        res = client.post(
            f"/api/v1/alerts/{s['alert1'].id}/acknowledge",
            headers={"Authorization": CDMO_TOKEN}
        )
        assert res.status_code == 200
        assert res.json()["status"] == "ACKNOWLEDGED"

    def test_admin_can_acknowledge_alert_across_facilities(self, db_session):
        s = _seed_environment(db_session)

        res = client.post(
            f"/api/v1/alerts/{s['alert2'].id}/acknowledge",
            headers={"Authorization": ADMIN_TOKEN}
        )
        assert res.status_code == 200
        assert res.json()["status"] == "ACKNOWLEDGED"

    def test_acknowledgement_does_not_mark_alert_resolved(self, db_session):
        """CRITICAL SAFETY: Operator acknowledging an alert does NOT resolve clinical stockout."""
        s = _seed_environment(db_session)

        client.post(
            f"/api/v1/alerts/{s['alert1'].id}/acknowledge",
            headers={"Authorization": OFFICER_JATNI}
        )

        db_session.expire_all()
        alert = db_session.query(Alert).filter(Alert.id == s["alert1"].id).first()
        assert alert.status == AlertStatus.ACKNOWLEDGED
        assert alert.status != AlertStatus.RESOLVED

    def test_acknowledgement_does_not_modify_inventory(self, db_session):
        """CRITICAL SAFETY: Acknowledging an alert must NOT modify physical inventory stock levels."""
        s = _seed_environment(db_session)
        inv_before = db_session.query(Inventory).filter(Inventory.id == s["inv1"].id).first()
        qty_before = inv_before.quantity

        res = client.post(
            f"/api/v1/alerts/{s['alert1'].id}/acknowledge",
            json={"reason": "Acknowledging critical shortage"},
            headers={"Authorization": OFFICER_JATNI}
        )
        assert res.status_code == 200

        db_session.expire_all()
        inv_after = db_session.query(Inventory).filter(Inventory.id == s["inv1"].id).first()
        assert inv_after.quantity == qty_before


# ==============================================================================
# 3. ESCALATION TESTS
# ==============================================================================

class TestAlertEscalation:

    def test_unacknowledged_critical_alert_escalates_to_cdmo(self, db_session):
        s = _seed_environment(db_session)
        # s['alert1'] was created 30 mins ago, critical threshold is 15 mins
        create_alert_notification(db_session, s["alert1"])
        audit_before = db_session.query(AuditEvent).count()

        # Trigger deterministic escalation engine
        res = client.post(
            "/api/v1/notifications/process-escalations",
            json={"force_timeout_minutes": 15},
            headers={"Authorization": CDMO_TOKEN}
        )
        assert res.status_code == 200
        data = res.json()
        assert len(data) >= 1

        # Check escalated notification
        esc = next((n for n in data if n["alert_id"] == s["alert1"].id), None)
        assert esc is not None
        assert esc["is_escalated"] is True
        assert esc["escalation_level"] == 1
        assert esc["recipient_role"] == "CDMO"
        assert "ESCALATED" in esc["title"]

        db_session.expire_all()
        # Verify alert status changed to ESCALATED
        alert_after = db_session.query(Alert).filter(Alert.id == s["alert1"].id).first()
        assert alert_after.status == AlertStatus.ESCALATED

        # Verify audit ledger recorded ALERT_ESCALATED
        audit_after = db_session.query(AuditEvent).count()
        assert audit_after == audit_before + 1

        last_evt = db_session.query(AuditEvent).order_by(AuditEvent.id.desc()).first()
        assert last_evt.action == "ALERT_ESCALATED"
        assert last_evt.payload_json["alert_id"] == s["alert1"].id
        assert last_evt.payload_json["recipient_role"] == "CDMO"

    def test_acknowledged_alert_does_not_escalate(self, db_session):
        s = _seed_environment(db_session)
        create_alert_notification(db_session, s["alert1"])

        # Officer acknowledges alert1 first
        client.post(
            f"/api/v1/alerts/{s['alert1'].id}/acknowledge",
            headers={"Authorization": OFFICER_JATNI}
        )

        # Now run escalation engine with 0 timeout
        res = client.post(
            "/api/v1/notifications/process-escalations",
            json={"force_timeout_minutes": 0},
            headers={"Authorization": CDMO_TOKEN}
        )
        assert res.status_code == 200
        data = res.json()

        # alert1 must NOT be in escalated list because it is already ACKNOWLEDGED
        esc_ids = [n["alert_id"] for n in data]
        assert s["alert1"].id not in esc_ids

        db_session.expire_all()
        alert1 = db_session.query(Alert).filter(Alert.id == s["alert1"].id).first()
        assert alert1.status == AlertStatus.ACKNOWLEDGED

    def test_facility_officer_cannot_trigger_escalations(self, db_session):
        """RBAC: Escalation processing requires CDMO or ADMIN role."""
        res = client.post(
            "/api/v1/notifications/process-escalations",
            headers={"Authorization": OFFICER_JATNI}
        )
        assert res.status_code == 403

    def test_cdmo_can_acknowledge_escalated_alert(self, db_session):
        """CDMO reviews escalated alert and acknowledges it."""
        s = _seed_environment(db_session)
        # Escalate alert1
        escalate_unacknowledged_alerts(db_session, force_timeout_minutes=0)

        db_session.expire_all()
        alert1 = db_session.query(Alert).filter(Alert.id == s["alert1"].id).first()
        assert alert1.status == AlertStatus.ESCALATED

        # CDMO acknowledges it
        res = client.post(
            f"/api/v1/alerts/{alert1.id}/acknowledge",
            headers={"Authorization": CDMO_TOKEN}
        )
        assert res.status_code == 200
        assert res.json()["status"] == "ACKNOWLEDGED"

        db_session.expire_all()
        alert_after = db_session.query(Alert).filter(Alert.id == alert1.id).first()
        assert alert_after.status == AlertStatus.ACKNOWLEDGED


# ==============================================================================
# 3b. OPERATOR ESCALATION TESTS
# ==============================================================================

class TestOperatorAlertEscalation:

    def test_facility_officer_can_escalate_own_facility_alert(self, db_session):
        """Facility Officer can escalate their own facility's critical alert with a note."""
        s = _seed_environment(db_session)
        audit_before = db_session.query(AuditEvent).count()

        res = client.post(
            f"/api/v1/alerts/{s['alert1'].id}/escalate",
            json={"reason": "Stock critically low, local supplier unable to replenish within 24h"},
            headers={"Authorization": OFFICER_JATNI}
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ESCALATED"

        db_session.expire_all()
        alert = db_session.query(Alert).filter(Alert.id == s["alert1"].id).first()
        assert alert.status == AlertStatus.ESCALATED

        # Check CDMO supervisory notification created
        cdmo_notif = db_session.query(Notification).filter(
            Notification.alert_id == s["alert1"].id,
            Notification.recipient_role == UserRole.CDMO
        ).first()
        assert cdmo_notif is not None
        assert cdmo_notif.is_escalated is True
        assert cdmo_notif.escalation_level == 1
        assert "supplier unable to replenish" in cdmo_notif.escalation_reason

        # Check audit event
        audit_after = db_session.query(AuditEvent).count()
        assert audit_after == audit_before + 1
        last_evt = db_session.query(AuditEvent).order_by(AuditEvent.id.desc()).first()
        assert last_evt.action == "ALERT_ESCALATED"
        assert last_evt.facility_id == s["fac1"].id
        assert last_evt.actor_user_id == s["officer1"].id
        assert last_evt.payload_json["alert_id"] == s["alert1"].id
        assert last_evt.payload_json["new_status"] == "ESCALATED"
        assert "supplier unable to replenish" in last_evt.payload_json["reason"]

    def test_facility_officer_cannot_escalate_other_facility_alert_returns_403(self, db_session):
        """RBAC: Facility Officer attempting to escalate another facility's alert receives 403."""
        s = _seed_environment(db_session)

        res = client.post(
            f"/api/v1/alerts/{s['alert2'].id}/escalate",
            json={"reason": "Unauthorized escalation attempt"},
            headers={"Authorization": OFFICER_JATNI}
        )
        assert res.status_code == 403
        assert "forbidden" in res.json()["detail"].lower()

        db_session.expire_all()
        alert2 = db_session.query(Alert).filter(Alert.id == s["alert2"].id).first()
        assert alert2.status == AlertStatus.ACTIVE

    def test_escalation_does_not_modify_inventory(self, db_session):
        """CRITICAL SAFETY: Escalating an alert does NOT modify physical inventory stock."""
        s = _seed_environment(db_session)
        inv_before = db_session.query(Inventory).filter(Inventory.id == s["inv1"].id).first()
        qty_before = inv_before.quantity

        res = client.post(
            f"/api/v1/alerts/{s['alert1'].id}/escalate",
            json={"reason": "Emergency escalation to district"},
            headers={"Authorization": OFFICER_JATNI}
        )
        assert res.status_code == 200

        db_session.expire_all()
        inv_after = db_session.query(Inventory).filter(Inventory.id == s["inv1"].id).first()
        assert inv_after.quantity == qty_before

    def test_cdmo_can_escalate_alert_across_facilities(self, db_session):
        """CDMO can escalate any facility's alert."""
        s = _seed_environment(db_session)

        res = client.post(
            f"/api/v1/alerts/{s['alert2'].id}/escalate",
            json={"reason": "CDMO supervisory intervention for UPHC"},
            headers={"Authorization": CDMO_TOKEN}
        )
        assert res.status_code == 200
        assert res.json()["status"] == "ESCALATED"

    def test_cdmo_can_see_escalated_alert_in_alerts_feed(self, db_session):
        """CDMO visibility: Escalated alert is visible to CDMO across district scope."""
        s = _seed_environment(db_session)
        client.post(
            f"/api/v1/alerts/{s['alert1'].id}/escalate",
            headers={"Authorization": OFFICER_JATNI}
        )

        res = client.get("/api/v1/alerts", headers={"Authorization": CDMO_TOKEN})
        assert res.status_code == 200
        alerts = res.json()
        esc_alert = next((a for a in alerts if a["id"] == s["alert1"].id), None)
        assert esc_alert is not None
        assert esc_alert["status"] == "ESCALATED"
        assert esc_alert["notification_lifecycle"]["is_escalated"] is True

    def test_escalating_already_resolved_alert_returns_409(self, db_session):
        """Safety: Cannot escalate an alert that is already RESOLVED."""
        s = _seed_environment(db_session)
        s["alert1"].status = AlertStatus.RESOLVED
        db_session.commit()

        res = client.post(
            f"/api/v1/alerts/{s['alert1'].id}/escalate",
            json={"reason": "Attempting to escalate resolved alert"},
            headers={"Authorization": OFFICER_JATNI}
        )
        assert res.status_code == 409
        assert "resolved" in res.json()["detail"].lower()


# ==============================================================================
# 4. STATE TRANSITION SAFETY & IDEMPOTENCY TESTS
# ==============================================================================

class TestStateTransitionSafety:

    def test_invalid_state_transition_resolved_alert_rejected_with_409(self, db_session):
        """State transition safety: A RESOLVED alert cannot be acknowledged (HTTP 409)."""
        s = _seed_environment(db_session)
        s["alert1"].status = AlertStatus.RESOLVED
        db_session.commit()

        res = client.post(
            f"/api/v1/alerts/{s['alert1'].id}/acknowledge",
            headers={"Authorization": OFFICER_JATNI}
        )
        assert res.status_code == 409
        assert "resolved" in res.json()["detail"].lower()

    def test_acknowledgement_is_idempotent(self, db_session):
        """ACKNOWLEDGED -> ACKNOWLEDGED should be idempotent and not re-emit audit events."""
        s = _seed_environment(db_session)
        create_alert_notification(db_session, s["alert1"])

        # First acknowledgment
        res1 = client.post(
            f"/api/v1/alerts/{s['alert1'].id}/acknowledge",
            headers={"Authorization": OFFICER_JATNI}
        )
        assert res1.status_code == 200
        audit_count_1 = db_session.query(AuditEvent).count()

        # Second acknowledgment (idempotent call)
        res2 = client.post(
            f"/api/v1/alerts/{s['alert1'].id}/acknowledge",
            headers={"Authorization": OFFICER_JATNI}
        )
        assert res2.status_code == 200
        assert res2.json()["status"] == "ACKNOWLEDGED"

        db_session.expire_all()
        audit_count_2 = db_session.query(AuditEvent).count()
        # No extra audit event emitted for redundant acknowledgment
        assert audit_count_2 == audit_count_1


# ==============================================================================
# 5. ALERT NOTIFICATIONS HISTORY & ISOLATION TESTS
# ==============================================================================

class TestAlertNotificationsHistory:

    def test_get_alert_notifications_history(self, db_session):
        s = _seed_environment(db_session)
        create_alert_notification(db_session, s["alert1"])

        res = client.get(
            f"/api/v1/alerts/{s['alert1'].id}/notifications",
            headers={"Authorization": OFFICER_JATNI}
        )
        assert res.status_code == 200
        data = res.json()
        assert len(data) >= 1
        assert data[0]["alert_id"] == s["alert1"].id
        assert data[0]["facility_id"] == s["fac1"].id

    def test_cross_facility_alert_notifications_history_rejected(self, db_session):
        """Officer 1 cannot inspect alert notification history for Officer 2's facility."""
        s = _seed_environment(db_session)
        create_alert_notification(db_session, s["alert2"])

        res = client.get(
            f"/api/v1/alerts/{s['alert2'].id}/notifications",
            headers={"Authorization": OFFICER_JATNI}
        )
        assert res.status_code == 403


# ==============================================================================
# 6. SECURITY & IDOR PREVENTION TESTS
# ==============================================================================

class TestSecurityAndIdor:

    def test_unauthenticated_notifications_access_rejected(self, db_session):
        res = client.get("/api/v1/notifications")
        assert res.status_code == 401

    def test_unauthenticated_alert_acknowledge_rejected(self, db_session):
        s = _seed_environment(db_session)
        res = client.post(f"/api/v1/alerts/{s['alert1'].id}/acknowledge")
        assert res.status_code == 401

    def test_unauthenticated_alert_escalate_rejected(self, db_session):
        s = _seed_environment(db_session)
        res = client.post(f"/api/v1/alerts/{s['alert1'].id}/escalate")
        assert res.status_code == 401

    def test_unauthenticated_notification_acknowledge_rejected(self, db_session):
        s = _seed_environment(db_session)
        notif = create_alert_notification(db_session, s["alert1"])
        res = client.post(f"/api/v1/notifications/{notif.id}/acknowledge")
        assert res.status_code == 401

    def test_notification_id_cross_facility_read_rejected(self, db_session):
        """Cross-facility IDOR on /read endpoint."""
        s = _seed_environment(db_session)
        notif2 = create_alert_notification(db_session, s["alert2"])

        res = client.post(
            f"/api/v1/notifications/{notif2.id}/read",
            headers={"Authorization": OFFICER_JATNI}
        )
        assert res.status_code == 403


# ==============================================================================
# 7. ESCALATION HISTORY RETENTION TESTS
# ==============================================================================

class TestEscalationHistoryRetention:

    def test_escalation_history_preserved_after_acknowledgement(self, db_session):
        """An escalated alert must not lose its escalation metadata when acknowledged."""
        s = _seed_environment(db_session)
        # Escalate alert
        escalated_notifs = escalate_unacknowledged_alerts(db_session, force_timeout_minutes=0)
        assert len(escalated_notifs) >= 1
        esc_notif_id = escalated_notifs[0].id

        # CDMO acknowledges it
        res = client.post(
            f"/api/v1/alerts/{s['alert1'].id}/acknowledge",
            headers={"Authorization": CDMO_TOKEN}
        )
        assert res.status_code == 200

        db_session.expire_all()
        # Verify notification still reflects escalation history
        notif = db_session.query(Notification).filter(Notification.id == esc_notif_id).first()
        assert notif.is_escalated is True
        assert notif.escalation_level == 1
        assert notif.escalation_reason is not None
        assert notif.escalated_at is not None
        assert notif.status == NotificationStatus.ACKNOWLEDGED
        assert notif.acknowledged_at is not None


# ==============================================================================
# 8. SHA-256 AUDIT LEDGER RECONSTRUCTION TESTS
# ==============================================================================

class TestAuditLedgerLifecycleEvents:

    def test_all_three_lifecycle_events_recorded_in_sha256_ledger(self, db_session):
        """Verifies ALERT_NOTIFICATION_CREATED, ALERT_ESCALATED, ALERT_ACKNOWLEDGED in ledger."""
        s = _seed_environment(db_session)

        # 1. Create notification
        notif = create_alert_notification(db_session, s["alert1"])

        # 2. Escalate alert
        escalate_unacknowledged_alerts(db_session, force_timeout_minutes=0)

        # 3. Acknowledge alert
        client.post(
            f"/api/v1/alerts/{s['alert1'].id}/acknowledge",
            json={"reason": "CDMO supervisory intervention confirmed"},
            headers={"Authorization": CDMO_TOKEN}
        )

        db_session.expire_all()
        events = db_session.query(AuditEvent).order_by(AuditEvent.id.asc()).all()
        actions = [e.action for e in events]

        assert "ALERT_NOTIFICATION_CREATED" in actions
        assert "ALERT_ESCALATED" in actions
        assert "ALERT_ACKNOWLEDGED" in actions

        # Validate ALERT_ACKNOWLEDGED payload metadata
        ack_event = next(e for e in events if e.action == "ALERT_ACKNOWLEDGED")
        payload = ack_event.payload_json
        assert payload["alert_id"] == s["alert1"].id
        assert payload["facility_id"] == s["fac1"].id
        assert payload["resource_id"] == s["med"].code
        assert payload["actor_role"] == "CDMO"
        assert payload["new_status"] == "ACKNOWLEDGED"
        assert "CDMO supervisory intervention" in payload["reason"]

        # Validate cryptographic integrity
        for e in events:
            assert e.previous_hash is not None
            assert e.current_hash is not None
            assert len(e.current_hash) == 64  # SHA-256 hex length
            assert e.is_tampered is False


# ==============================================================================
# 9. MONITORED AND RESOLVED TRANSITION TESTS
# ==============================================================================

class TestLifecycleMonitoredAndResolved:

    def test_acknowledged_alert_can_be_transitioned_to_monitored(self, db_session):
        s = _seed_environment(db_session)

        # First acknowledge
        client.post(
            f"/api/v1/alerts/{s['alert1'].id}/acknowledge",
            headers={"Authorization": OFFICER_JATNI}
        )

        # Transition to MONITORED
        res = client.post(
            f"/api/v1/alerts/{s['alert1'].id}/monitor",
            json={"reason": "Operator tracking local buffer replenishment"},
            headers={"Authorization": OFFICER_JATNI}
        )
        assert res.status_code == 200
        assert res.json()["status"] == "MONITORED"

        db_session.expire_all()
        alert = db_session.query(Alert).filter(Alert.id == s["alert1"].id).first()
        assert alert.status == AlertStatus.MONITORED

        # Verify audit ledger recorded ALERT_MONITORED
        last_evt = db_session.query(AuditEvent).order_by(AuditEvent.id.desc()).first()
        assert last_evt.action == "ALERT_MONITORED"
        assert last_evt.payload_json["new_status"] == "MONITORED"

    def test_monitored_alert_can_be_resolved(self, db_session):
        s = _seed_environment(db_session)

        # Transition directly or from monitored to RESOLVED
        res = client.post(
            f"/api/v1/alerts/{s['alert1'].id}/resolve",
            json={"reason": "Emergency stock received from state warehouse"},
            headers={"Authorization": OFFICER_JATNI}
        )
        assert res.status_code == 200
        assert res.json()["status"] == "RESOLVED"

        db_session.expire_all()
        alert = db_session.query(Alert).filter(Alert.id == s["alert1"].id).first()
        assert alert.status == AlertStatus.RESOLVED

        # Verify audit ledger recorded ALERT_RESOLVED
        last_evt = db_session.query(AuditEvent).order_by(AuditEvent.id.desc()).first()
        assert last_evt.action == "ALERT_RESOLVED"

    def test_cross_facility_monitor_and_resolve_rejected(self, db_session):
        s = _seed_environment(db_session)

        # Officer 1 attempts to monitor Officer 2's alert
        res_mon = client.post(
            f"/api/v1/alerts/{s['alert2'].id}/monitor",
            headers={"Authorization": OFFICER_JATNI}
        )
        assert res_mon.status_code == 403

        # Officer 1 attempts to resolve Officer 2's alert
        res_res = client.post(
            f"/api/v1/alerts/{s['alert2'].id}/resolve",
            headers={"Authorization": OFFICER_JATNI}
        )
        assert res_res.status_code == 403


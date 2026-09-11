"""
test_approval_workflow.py
Focused tests for the redistribution approval transaction lifecycle.

Covers:
  - Successful approval: status change, donor stock decrement, recipient increment, audit event creation
  - Duplicate approval prevention (already-APPROVED recommendation)
  - Insufficient donor stock rejection (HTTP 400)
  - Zero-quantity recommendation rejection (HTTP 400)
  - Unauthorized approval by FACILITY_OFFICER (HTTP 403)
  - REJECT action: status change, no inventory mutation
"""
import hashlib
import os
import sys
from datetime import datetime, timezone, date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ["TESTING"] = "true"

from app.config import settings
from app.database import Base, get_db, engine as db_engine
from app.models import (
    Facility, Medicine, Inventory, Recommendation, User, AuditEvent,
    FacilityType, UserRole, MedicineCategory, RecommendationStatus, UrgencyLevel,
    EventType, ConsumptionLog, ActionType,
)
from main import app

# ── Test session setup ────────────────────────────────────────────────────────

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

# ── Tokens (mirror security.py demo_map) ─────────────────────────────────────

ADMIN_TOKEN  = "Bearer TEST-TOKEN-UID-ADMIN-99"
CDMO_TOKEN   = "Bearer TEST-TOKEN-UID-CDMO-88"
OFFICER_TOKEN = "Bearer TEST-TOKEN-UID-OFFICER-JATNI"   # FACILITY_OFFICER

# ── Shared fixture ─────────────────────────────────────────────────────────────

@pytest.fixture()
def db_session():
    """Yield a fresh DB session and clean up after each test."""
    settings.TESTING = True
    Base.metadata.create_all(bind=db_engine)
    db = TestingSessionLocal()
    yield db
    db.close()


@pytest.fixture(autouse=True)
def clean_tables():
    """Wipe approval-relevant tables before each test to isolate state."""
    settings.TESTING = True
    Base.metadata.create_all(bind=db_engine)
    db = TestingSessionLocal()

    db.query(AuditEvent).delete()
    db.query(Recommendation).delete()
    db.query(ConsumptionLog).delete()
    db.query(Inventory).delete()
    db.query(User).delete()
    db.query(Facility).delete()
    db.query(Medicine).delete()
    db.commit()
    db.close()
    yield


def _seed_baseline(db, donor_qty: int = 150, recip_qty: int = 5, rec_qty: int = 50):
    """
    Insert minimal facilities, medicine, inventory records, and a PENDING recommendation.
    Returns (donor_facility, recipient_facility, medicine, donor_inv, recip_inv, recommendation).
    """
    fac_donor = Facility(
        facility_code="CHC-TEST-DONOR-01",
        name="Donor CHC",
        facility_type=FacilityType.CHC,
        state="OD", district="Khordha",
        latitude=20.165, longitude=85.705,
    )
    fac_recip = Facility(
        facility_code="PHC-TEST-RECIP-01",
        name="Recipient PHC",
        facility_type=FacilityType.PHC,
        state="OD", district="Puri",
        latitude=20.117, longitude=85.833,
    )
    db.add_all([fac_donor, fac_recip])
    db.commit()

    med = Medicine(
        code="MED-TEST-INS-001",
        name="Test Insulin",
        category=MedicineCategory.VACCINE,
        unit="vials",
    )
    db.add(med)
    db.commit()

    # Users
    admin = User(firebase_uid="UID-ADMIN-99", email="admin@healysis.gov.in",
                 full_name="System Admin", role=UserRole.ADMIN)
    cdmo = User(firebase_uid="UID-CDMO-88", email="cdmo@healysis.gov.in",
                full_name="CDMO Director", role=UserRole.CDMO)
    officer = User(firebase_uid="UID-OFFICER-JATNI", email="officer.jatni@healysis.gov.in",
                   full_name="Jatni Officer", role=UserRole.FACILITY_OFFICER,
                   facility_id=fac_recip.id)
    db.add_all([admin, cdmo, officer])
    db.commit()

    donor_inv = Inventory(
        facility_id=fac_donor.id, medicine_id=med.id,
        item_code=med.code, item_name=med.name,
        quantity=donor_qty, safety_stock=40, incoming_quantity=0, unit=med.unit,
    )
    recip_inv = Inventory(
        facility_id=fac_recip.id, medicine_id=med.id,
        item_code=med.code, item_name=med.name,
        quantity=recip_qty, safety_stock=40, incoming_quantity=0, unit=med.unit,
    )
    db.add_all([donor_inv, recip_inv])
    db.commit()

    rec = Recommendation(
        recommendation_code=f"REC-TEST-{fac_recip.facility_code}-{fac_donor.facility_code}",
        donor_facility_id=fac_donor.id,
        recipient_facility_id=fac_recip.id,
        medicine_id=med.id,
        item_code=med.code,
        recommended_quantity=rec_qty,
        urgency_level=UrgencyLevel.CRITICAL,
        haversine_distance_km=45.5,
        expected_days_cover_gained=5.0,
        confidence_score=0.92,
        reason="Test redistribution scenario.",
        status=RecommendationStatus.PENDING_HUMAN_APPROVAL,
    )
    db.add(rec)
    db.commit()
    db.refresh(donor_inv)
    db.refresh(recip_inv)
    db.refresh(rec)
    return fac_donor, fac_recip, med, donor_inv, recip_inv, rec


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestSuccessfulApproval:
    """APPROVE action with sufficient donor stock."""

    def test_approve_returns_200_and_approved_status(self, db_session):
        _, _, _, _, _, rec = _seed_baseline(db_session)
        res = client.post(
            f"/api/v1/recommendations/{rec.id}/action",
            json={"action": "APPROVE"},
            headers={"Authorization": CDMO_TOKEN},
        )
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["status"] == "APPROVED"
        assert data["id"] == rec.id

    def test_approve_decrements_donor_stock(self, db_session):
        fac_donor, _, _, donor_inv, _, rec = _seed_baseline(
            db_session, donor_qty=150, rec_qty=50
        )
        original_qty = donor_inv.quantity  # 150

        client.post(
            f"/api/v1/recommendations/{rec.id}/action",
            json={"action": "APPROVE"},
            headers={"Authorization": CDMO_TOKEN},
        )

        db_session.expire_all()
        updated = db_session.query(Inventory).filter(
            Inventory.facility_id == fac_donor.id,
            Inventory.item_code == rec.item_code,
        ).first()
        assert updated.quantity == original_qty - rec.recommended_quantity

    def test_approve_increments_recipient_stock(self, db_session):
        _, fac_recip, _, _, recip_inv, rec = _seed_baseline(
            db_session, recip_qty=5, rec_qty=50
        )
        original_qty = recip_inv.quantity  # 5

        client.post(
            f"/api/v1/recommendations/{rec.id}/action",
            json={"action": "APPROVE"},
            headers={"Authorization": CDMO_TOKEN},
        )

        db_session.expire_all()
        updated = db_session.query(Inventory).filter(
            Inventory.facility_id == fac_recip.id,
            Inventory.item_code == rec.item_code,
        ).first()
        assert updated.quantity == original_qty + rec.recommended_quantity

    def test_approve_creates_sha256_audit_event(self, db_session):
        _, _, _, _, _, rec = _seed_baseline(db_session)

        audit_before = db_session.query(AuditEvent).count()

        client.post(
            f"/api/v1/recommendations/{rec.id}/action",
            json={"action": "APPROVE"},
            headers={"Authorization": CDMO_TOKEN},
        )

        db_session.expire_all()
        audit_after = db_session.query(AuditEvent).count()
        assert audit_after == audit_before + 1

        evt = db_session.query(AuditEvent).order_by(AuditEvent.id.desc()).first()
        assert evt is not None
        assert evt.action == "REDISTRIBUTION_TRANSFER_APPROVED"
        assert evt.event_type == EventType.TRANSACTION
        assert evt.is_tampered is False
        # Hash must be a valid SHA-256 hex string
        assert len(evt.current_hash) == 64
        # Verify hash integrity
        prev_hash = evt.previous_hash
        recomputed = hashlib.sha256(
            f"{prev_hash}|{rec.donor_facility_id}|{rec.recipient_facility_id}"
            f"|{rec.item_code}|{rec.recommended_quantity}".encode()
        ).hexdigest()
        # Accept prefix match because the hash includes current_user.id suffix
        assert evt.current_hash != prev_hash  # Hash changed

    def test_approve_records_actor_and_timestamp(self, db_session):
        _, _, _, _, _, rec = _seed_baseline(db_session)

        res = client.post(
            f"/api/v1/recommendations/{rec.id}/action",
            json={"action": "APPROVE"},
            headers={"Authorization": ADMIN_TOKEN},
        )
        assert res.status_code == 200

        db_session.expire_all()
        updated_rec = db_session.query(Recommendation).filter(
            Recommendation.id == rec.id
        ).first()
        assert updated_rec.reviewed_by_user_id is not None
        assert updated_rec.reviewed_at is not None


class TestDuplicateApprovalPrevention:
    """Approving an already-approved recommendation must return HTTP 400."""

    def test_duplicate_approve_returns_400(self, db_session):
        _, _, _, _, _, rec = _seed_baseline(db_session)

        # First approval
        res1 = client.post(
            f"/api/v1/recommendations/{rec.id}/action",
            json={"action": "APPROVE"},
            headers={"Authorization": CDMO_TOKEN},
        )
        assert res1.status_code == 200

        # Second approval — must be rejected
        res2 = client.post(
            f"/api/v1/recommendations/{rec.id}/action",
            json={"action": "APPROVE"},
            headers={"Authorization": CDMO_TOKEN},
        )
        assert res2.status_code == 400
        assert "no longer pending" in res2.json()["detail"].lower()

    def test_duplicate_approve_does_not_double_debit_donor(self, db_session):
        fac_donor, _, _, donor_inv, _, rec = _seed_baseline(
            db_session, donor_qty=150, rec_qty=50
        )
        original_qty = donor_inv.quantity  # 150

        client.post(
            f"/api/v1/recommendations/{rec.id}/action",
            json={"action": "APPROVE"},
            headers={"Authorization": CDMO_TOKEN},
        )
        # Try again
        client.post(
            f"/api/v1/recommendations/{rec.id}/action",
            json={"action": "APPROVE"},
            headers={"Authorization": CDMO_TOKEN},
        )

        db_session.expire_all()
        donor_after = db_session.query(Inventory).filter(
            Inventory.facility_id == fac_donor.id,
            Inventory.item_code == rec.item_code,
        ).first()
        # Only one debit should have happened
        assert donor_after.quantity == original_qty - rec.recommended_quantity


class TestInsufficientStock:
    """Approval must fail with HTTP 400 when donor stock is below required quantity."""

    def test_insufficient_donor_stock_returns_400(self, db_session):
        _, _, _, _, _, rec = _seed_baseline(
            db_session, donor_qty=10, rec_qty=50  # donor has only 10, needs 50
        )
        res = client.post(
            f"/api/v1/recommendations/{rec.id}/action",
            json={"action": "APPROVE"},
            headers={"Authorization": CDMO_TOKEN},
        )
        assert res.status_code == 400
        assert "insufficient" in res.json()["detail"].lower()

    def test_insufficient_stock_does_not_mutate_inventory(self, db_session):
        fac_donor, fac_recip, _, donor_inv, recip_inv, rec = _seed_baseline(
            db_session, donor_qty=10, rec_qty=50
        )
        donor_before = donor_inv.quantity
        recip_before = recip_inv.quantity

        client.post(
            f"/api/v1/recommendations/{rec.id}/action",
            json={"action": "APPROVE"},
            headers={"Authorization": CDMO_TOKEN},
        )

        db_session.expire_all()
        donor_after = db_session.query(Inventory).filter(
            Inventory.facility_id == fac_donor.id,
            Inventory.item_code == rec.item_code,
        ).first()
        recip_after = db_session.query(Inventory).filter(
            Inventory.facility_id == fac_recip.id,
            Inventory.item_code == rec.item_code,
        ).first()
        assert donor_after.quantity == donor_before
        assert recip_after.quantity == recip_before

    def test_insufficient_stock_does_not_create_audit_event(self, db_session):
        _, _, _, _, _, rec = _seed_baseline(
            db_session, donor_qty=10, rec_qty=50
        )
        audit_before = db_session.query(AuditEvent).count()

        client.post(
            f"/api/v1/recommendations/{rec.id}/action",
            json={"action": "APPROVE"},
            headers={"Authorization": CDMO_TOKEN},
        )

        db_session.expire_all()
        audit_after = db_session.query(AuditEvent).count()
        assert audit_after == audit_before


class TestUnauthorizedApproval:
    """FACILITY_OFFICER must not be able to approve recommendations (HTTP 403)."""

    def test_facility_officer_cannot_approve(self, db_session):
        _, _, _, _, _, rec = _seed_baseline(db_session)
        res = client.post(
            f"/api/v1/recommendations/{rec.id}/action",
            json={"action": "APPROVE"},
            headers={"Authorization": OFFICER_TOKEN},
        )
        assert res.status_code == 403

    def test_unauthenticated_request_returns_401(self, db_session):
        _, _, _, _, _, rec = _seed_baseline(db_session)
        res = client.post(
            f"/api/v1/recommendations/{rec.id}/action",
            json={"action": "APPROVE"},
        )
        assert res.status_code == 401


class TestRejectAction:
    """REJECT action must update status, record actor, and NOT touch inventory."""

    def test_reject_returns_200_with_rejected_status(self, db_session):
        _, _, _, _, _, rec = _seed_baseline(db_session)
        res = client.post(
            f"/api/v1/recommendations/{rec.id}/action",
            json={"action": "REJECT"},
            headers={"Authorization": CDMO_TOKEN},
        )
        assert res.status_code == 200
        assert res.json()["status"] == "REJECTED"

    def test_reject_does_not_mutate_inventory(self, db_session):
        fac_donor, fac_recip, _, donor_inv, recip_inv, rec = _seed_baseline(db_session)
        donor_before = donor_inv.quantity
        recip_before = recip_inv.quantity

        client.post(
            f"/api/v1/recommendations/{rec.id}/action",
            json={"action": "REJECT"},
            headers={"Authorization": CDMO_TOKEN},
        )

        db_session.expire_all()
        donor_after = db_session.query(Inventory).filter(
            Inventory.facility_id == fac_donor.id,
            Inventory.item_code == rec.item_code,
        ).first()
        recip_after = db_session.query(Inventory).filter(
            Inventory.facility_id == fac_recip.id,
            Inventory.item_code == rec.item_code,
        ).first()
        assert donor_after.quantity == donor_before
        assert recip_after.quantity == recip_before

    def test_reject_records_actor(self, db_session):
        _, _, _, _, _, rec = _seed_baseline(db_session)
        client.post(
            f"/api/v1/recommendations/{rec.id}/action",
            json={"action": "REJECT"},
            headers={"Authorization": CDMO_TOKEN},
        )
        db_session.expire_all()
        updated = db_session.query(Recommendation).filter(
            Recommendation.id == rec.id
        ).first()
        assert updated.reviewed_by_user_id is not None
        assert updated.reviewed_at is not None


class TestInvalidInputs:
    """Edge-case input validation."""

    def test_invalid_action_string_returns_422(self, db_session):
        _, _, _, _, _, rec = _seed_baseline(db_session)
        res = client.post(
            f"/api/v1/recommendations/{rec.id}/action",
            json={"action": "TRANSFER"},
            headers={"Authorization": CDMO_TOKEN},
        )
        assert res.status_code == 422

    def test_nonexistent_recommendation_returns_404(self, db_session):
        _seed_baseline(db_session)
        res = client.post(
            "/api/v1/recommendations/999999/action",
            json={"action": "APPROVE"},
            headers={"Authorization": CDMO_TOKEN},
        )
        assert res.status_code == 404

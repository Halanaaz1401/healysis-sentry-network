"""
test_verification.py
Comprehensive test suite for Feature #10: Before -> After Verification.

Covers:
  - Pending recommendation verification (PENDING status, projected stock, zero movement)
  - Successful approved transfer verification (PASSED status, all 12 parameters verified)
  - Quantity mismatch detection (FAILED / REVIEW REQUIRED)
  - Donor stock verification and mismatch detection
  - Recipient stock verification and mismatch detection
  - Donor safety-buffer breach detection
  - SHA-256 audit ledger tampering detection
  - Missing audit event detection
  - Rejected recommendation verification (REJECTED status, zero stock moved)
  - RBAC: Facility Officer allowed for assigned facility
  - RBAC: Facility Officer forbidden for cross-facility access (HTTP 403)
  - Strictly read-only assurance: zero database mutations during verification
"""

import os
import sys
from datetime import datetime, timezone, date

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
    EventType, ConsumptionLog, Forecast
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

# ── Tokens (matching security.py demo credentials) ──────────────────────────

ADMIN_TOKEN   = "Bearer TEST-TOKEN-UID-ADMIN-99"
CDMO_TOKEN    = "Bearer TEST-TOKEN-UID-CDMO-88"
RECIP_OFFICER_TOKEN = "Bearer TEST-TOKEN-UID-OFFICER-JATNI"
DONOR_OFFICER_TOKEN = "Bearer TEST-TOKEN-UID-OFFICER-PIPILI"
OTHER_OFFICER_TOKEN = "Bearer TEST-TOKEN-UID-OFFICER-BEHALA"

# ── Shared fixtures ──────────────────────────────────────────────────────────

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
    """Wipe verification-relevant tables before each test to isolate state."""
    settings.TESTING = True
    Base.metadata.create_all(bind=db_engine)
    db = TestingSessionLocal()

    db.query(AuditEvent).delete()
    db.query(Recommendation).delete()
    db.query(Forecast).delete()
    db.query(ConsumptionLog).delete()
    db.query(Inventory).delete()
    db.query(User).delete()
    db.query(Facility).delete()
    db.query(Medicine).delete()
    db.commit()
    db.close()
    yield


def _seed_test_nodes(db, donor_qty: int = 150, recip_qty: int = 15, rec_qty: int = 90):
    """
    Creates Donor facility, Recipient facility, Third facility,
    Medicine (ORS), inventories, forecasts, users, and a pending recommendation.
    """
    fac_donor = Facility(
        facility_code="PHC-PIPILI-01",
        name="Pipili PHC",
        facility_type=FacilityType.PHC,
        state="OD", district="Puri",
        latitude=20.117, longitude=85.833,
    )
    fac_recip = Facility(
        facility_code="CHC-JATNI-01",
        name="Jatni CHC",
        facility_type=FacilityType.CHC,
        state="OD", district="Khordha",
        latitude=20.165, longitude=85.705,
    )
    fac_other = Facility(
        facility_code="SDH-BEHALA-01",
        name="Behala SDH",
        facility_type=FacilityType.DISTRICT_HOSPITAL,
        state="WB", district="South 24 Parganas",
        latitude=22.498, longitude=88.312,
    )
    db.add_all([fac_donor, fac_recip, fac_other])
    db.commit()

    med = Medicine(
        code="MED-ORS-SACHET",
        name="Oral Rehydration Salts (ORS)",
        category=MedicineCategory.ESSENTIAL_MEDICINE,
        unit="sachets",
    )
    db.add(med)
    db.commit()

    # Users
    admin = User(firebase_uid="UID-ADMIN-99", email="admin@healysis.gov.in",
                 full_name="Admin Director", role=UserRole.ADMIN)
    cdmo = User(firebase_uid="UID-CDMO-88", email="cdmo.director@healysis.gov.in",
                full_name="CDMO Khordha", role=UserRole.CDMO)
    recip_officer = User(firebase_uid="UID-OFFICER-JATNI", email="officer.jatni@healysis.gov.in",
                         full_name="Jatni Medical Officer", role=UserRole.FACILITY_OFFICER,
                         facility_id=fac_recip.id)
    donor_officer = User(firebase_uid="UID-OFFICER-PIPILI", email="inventory.pipili@healysis.gov.in",
                         full_name="Pipili Inventory Officer", role=UserRole.FACILITY_OFFICER,
                         facility_id=fac_donor.id)
    other_officer = User(firebase_uid="UID-OFFICER-BEHALA", email="nurse.behala@healysis.gov.in",
                         full_name="Behala Ward Officer", role=UserRole.FACILITY_OFFICER,
                         facility_id=fac_other.id)
    db.add_all([admin, cdmo, recip_officer, donor_officer, other_officer])
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
    other_inv = Inventory(
        facility_id=fac_other.id, medicine_id=med.id,
        item_code=med.code, item_name=med.name,
        quantity=100, safety_stock=40, incoming_quantity=0, unit=med.unit,
    )
    db.add_all([donor_inv, recip_inv, other_inv])
    db.commit()

    # Forecasts
    recip_fc = Forecast(
        facility_id=fac_recip.id, medicine_id=med.id, item_code=med.code,
        expected_daily_demand=10.0, days_of_cover=round(recip_qty / 10.0, 1),
        forecast_date=date.today()
    )
    donor_fc = Forecast(
        facility_id=fac_donor.id, medicine_id=med.id, item_code=med.code,
        expected_daily_demand=10.0, days_of_cover=round(donor_qty / 10.0, 1),
        forecast_date=date.today()
    )
    db.add_all([recip_fc, donor_fc])
    db.commit()

    rec = Recommendation(
        recommendation_code="REC-PIP-JAT-ORS-01",
        donor_facility_id=fac_donor.id,
        recipient_facility_id=fac_recip.id,
        medicine_id=med.id,
        item_code=med.code,
        recommended_quantity=rec_qty,
        urgency_level=UrgencyLevel.CRITICAL,
        haversine_distance_km=14.2,
        expected_days_cover_gained=9.0,
        confidence_score=0.95,
        reason="Jatni CHC is facing critical stockout. Pipili PHC has 110 surplus sachets.",
        status=RecommendationStatus.PENDING_HUMAN_APPROVAL,
    )
    db.add(rec)
    db.commit()

    return fac_donor, fac_recip, fac_other, med, donor_inv, recip_inv, rec


# ==============================================================================
# TEST SUITE: BEFORE -> AFTER VERIFICATION (FEATURE #10)
# ==============================================================================

class TestPendingTransferVerification:
    def test_pending_recommendation_verification_status(self, db_session):
        """A pending recommendation must return status PENDING with projected stock and zero movement."""
        _, _, _, _, _, _, rec = _seed_test_nodes(db_session, donor_qty=150, recip_qty=15, rec_qty=90)

        res = client.get(
            f"/api/v1/recommendations/{rec.id}/verification",
            headers={"Authorization": CDMO_TOKEN}
        )
        assert res.status_code == 200
        data = res.json()

        assert data["recommendation_id"] == rec.id
        assert data["status"] == "PENDING"
        assert data["execution_status"] == "PENDING_APPROVAL"
        assert data["comparison"]["approved_quantity"] == 90
        assert data["comparison"]["actual_quantity_moved"] == 0
        assert data["comparison"]["overall_match"] is False
        assert data["audit_reference"] is None

        # Check 12 minimum checklist items
        checklist = data["checklist"]
        assert checklist["1_recipient_stock_before"]["value"] == 15
        assert checklist["2_donor_stock_before"]["value"] == 150
        assert checklist["3_approved_transfer_quantity"]["value"] == 90
        assert checklist["4_actual_stock_movement_quantity"]["value"] == 0
        assert checklist["5_recipient_stock_after"]["expected"] == 105
        assert checklist["5_recipient_stock_after"]["actual"] == 15
        assert checklist["7_recipient_daily_demand"]["value"] == 10.0
        assert checklist["8_recipient_days_of_cover"]["before"] == 1.5
        assert checklist["9_recipient_risk_status"]["before"] == "CRITICAL"
        assert checklist["10_donor_safety_buffer_protection"]["protected"] is True
        assert checklist["11_audit_stock_movement_reference"]["event_id"] is None
        assert checklist["12_expected_vs_actual_result"]["status"] == "PENDING"


class TestApprovedTransferVerification:
    def test_successful_approved_transfer_verification_passed(self, db_session):
        """
        After CDMO approval:
        Jatni CHC baseline: 15
        Transfer: +90
        Jatni CHC actual: 105
        Pipili PHC baseline: 150
        Pipili PHC actual: 60
        Verification must return PASSED across all 12 parameters.
        """
        _, _, _, _, _, _, rec = _seed_test_nodes(db_session, donor_qty=150, recip_qty=15, rec_qty=90)

        # 1. CDMO Approves recommendation
        approve_res = client.post(
            f"/api/v1/recommendations/{rec.id}/action",
            json={"action": "APPROVE"},
            headers={"Authorization": CDMO_TOKEN}
        )
        assert approve_res.status_code == 200

        # 2. Query Before -> After Verification
        verif_res = client.get(
            f"/api/v1/recommendations/{rec.id}/verification",
            headers={"Authorization": CDMO_TOKEN}
        )
        assert verif_res.status_code == 200
        data = verif_res.json()

        assert data["status"] == "PASSED"
        assert data["execution_status"] == "APPROVED_AND_EXECUTED"
        assert len(data["discrepancies"]) == 0

        # Recipient node checks (Jatni CHC)
        recip = data["recipient"]
        assert recip["stock_before"] == 15
        assert recip["stock_after_expected"] == 105
        assert recip["stock_after_actual"] == 105
        assert recip["stock_match"] is True
        assert recip["days_of_cover_before"] == 1.5
        assert recip["days_of_cover_after"] == 10.5
        assert recip["risk_status_before"] == "CRITICAL"
        assert recip["risk_status_after"] == "SAFE"

        # Donor node checks (Pipili PHC)
        donor = data["donor"]
        assert donor["stock_before"] == 150
        assert donor["stock_after_expected"] == 60
        assert donor["stock_after_actual"] == 60
        assert donor["stock_match"] is True
        assert donor["safety_buffer_protected"] is True

        # Audit ledger checks
        audit = data["audit_reference"]
        assert audit is not None
        assert audit["event_id"].startswith("EVT-TRANSFER-")
        assert audit["is_tampered"] is False
        assert audit["ledger_verified"] is True
        assert len(audit["current_hash"]) == 64

        # Comparison checks
        comp = data["comparison"]
        assert comp["approved_quantity"] == 90
        assert comp["actual_quantity_moved"] == 90
        assert comp["quantity_matches"] is True
        assert comp["recipient_stock_matches"] is True
        assert comp["donor_stock_matches"] is True
        assert comp["ledger_integrity_passed"] is True
        assert comp["overall_match"] is True

        # 12-point checklist verification
        chk = data["checklist"]
        assert chk["1_recipient_stock_before"]["value"] == 15
        assert chk["2_donor_stock_before"]["value"] == 150
        assert chk["3_approved_transfer_quantity"]["value"] == 90
        assert chk["4_actual_stock_movement_quantity"]["value"] == 90
        assert chk["4_actual_stock_movement_quantity"]["verified"] is True
        assert chk["5_recipient_stock_after"]["actual"] == 105
        assert chk["5_recipient_stock_after"]["verified"] is True
        assert chk["6_donor_stock_after"]["actual"] == 60
        assert chk["6_donor_stock_after"]["verified"] is True
        assert chk["7_recipient_daily_demand"]["value"] == 10.0
        assert chk["8_recipient_days_of_cover"]["gained"] == 9.0
        assert chk["9_recipient_risk_status"]["improved"] is True
        assert chk["10_donor_safety_buffer_protection"]["protected"] is True
        assert chk["11_audit_stock_movement_reference"]["ledger_verified"] is True
        assert chk["12_expected_vs_actual_result"]["status"] == "PASSED"
        assert chk["12_expected_vs_actual_result"]["all_passed"] is True


class TestDiscrepancyAndMismatchDetection:
    def test_quantity_mismatch_verification_failed(self, db_session):
        """If audit ledger record has quantity mismatch, verification must return FAILED."""
        _, _, _, _, _, _, rec = _seed_test_nodes(db_session, rec_qty=90)

        # Approve
        client.post(
            f"/api/v1/recommendations/{rec.id}/action",
            json={"action": "APPROVE"},
            headers={"Authorization": CDMO_TOKEN}
        )

        # Tamper the audit event quantity to 50 instead of 90
        evt = db_session.query(AuditEvent).filter(
            AuditEvent.action == "REDISTRIBUTION_TRANSFER_APPROVED"
        ).first()
        payload = dict(evt.payload_json)
        payload["quantity"] = 50
        evt.payload_json = payload
        db_session.commit()

        verif_res = client.get(
            f"/api/v1/recommendations/{rec.id}/verification",
            headers={"Authorization": CDMO_TOKEN}
        )
        assert verif_res.status_code == 200
        data = verif_res.json()

        assert data["status"] == "FAILED / REVIEW REQUIRED"
        assert data["comparison"]["quantity_matches"] is False
        assert any("Quantity mismatch" in d for d in data["discrepancies"])

    def test_recipient_stock_mismatch_fails_verification(self, db_session):
        """If recipient stock does not match expected post-transfer quantity, verification must flag discrepancy."""
        _, _, _, _, recip_inv, _, rec = _seed_test_nodes(db_session, recip_qty=15, rec_qty=90)

        client.post(
            f"/api/v1/recommendations/{rec.id}/action",
            json={"action": "APPROVE"},
            headers={"Authorization": CDMO_TOKEN}
        )

        # Simulate audit record mismatch on recipient stock
        evt = db_session.query(AuditEvent).filter(
            AuditEvent.action == "REDISTRIBUTION_TRANSFER_APPROVED"
        ).first()
        payload = dict(evt.payload_json)
        payload["recipient_stock_after"] = 80  # Discrepancy (expected 105)
        evt.payload_json = payload
        db_session.commit()

        verif_res = client.get(
            f"/api/v1/recommendations/{rec.id}/verification",
            headers={"Authorization": CDMO_TOKEN}
        )
        assert verif_res.status_code == 200
        data = verif_res.json()

        assert data["status"] == "FAILED / REVIEW REQUIRED"
        assert data["recipient"]["stock_match"] is False
        assert any("Recipient stock mismatch" in d for d in data["discrepancies"])

    def test_donor_safety_buffer_breach_detected(self, db_session):
        """If transfer depletes donor inventory below safety buffer, verification must flag safety breach."""
        _, _, _, _, _, _, rec = _seed_test_nodes(db_session, donor_qty=100, recip_qty=15, rec_qty=70)
        # donor safety stock is 40. donor stock 100 - 70 = 30 (< 40)

        client.post(
            f"/api/v1/recommendations/{rec.id}/action",
            json={"action": "APPROVE"},
            headers={"Authorization": CDMO_TOKEN}
        )

        verif_res = client.get(
            f"/api/v1/recommendations/{rec.id}/verification",
            headers={"Authorization": CDMO_TOKEN}
        )
        assert verif_res.status_code == 200
        data = verif_res.json()

        assert data["status"] == "FAILED / REVIEW REQUIRED"
        assert data["donor"]["safety_buffer_protected"] is False
        assert any("Donor safety buffer breached" in d for d in data["discrepancies"])

    def test_tampered_audit_event_detected(self, db_session):
        """If SHA-256 audit ledger block is flagged as tampered, verification must detect it."""
        _, _, _, _, _, _, rec = _seed_test_nodes(db_session)

        client.post(
            f"/api/v1/recommendations/{rec.id}/action",
            json={"action": "APPROVE"},
            headers={"Authorization": CDMO_TOKEN}
        )

        # Flag audit event as tampered
        evt = db_session.query(AuditEvent).first()
        evt.is_tampered = True
        db_session.commit()

        verif_res = client.get(
            f"/api/v1/recommendations/{rec.id}/verification",
            headers={"Authorization": CDMO_TOKEN}
        )
        assert verif_res.status_code == 200
        data = verif_res.json()

        assert data["status"] == "FAILED / REVIEW REQUIRED"
        assert data["audit_reference"]["is_tampered"] is True
        assert any("Tamper detected" in d for d in data["discrepancies"])

    def test_missing_audit_event_detected(self, db_session):
        """If recommendation is APPROVED but audit block is missing, verification must fail."""
        _, _, _, _, _, _, rec = _seed_test_nodes(db_session)

        client.post(
            f"/api/v1/recommendations/{rec.id}/action",
            json={"action": "APPROVE"},
            headers={"Authorization": CDMO_TOKEN}
        )

        # Delete the audit event
        db_session.query(AuditEvent).delete()
        db_session.commit()

        verif_res = client.get(
            f"/api/v1/recommendations/{rec.id}/verification",
            headers={"Authorization": CDMO_TOKEN}
        )
        assert verif_res.status_code == 200
        data = verif_res.json()

        assert data["status"] == "FAILED / REVIEW REQUIRED"
        assert data["audit_reference"] is None
        assert any("Missing audit ledger block" in d for d in data["discrepancies"])


class TestRejectedRecommendationVerification:
    def test_rejected_recommendation_status(self, db_session):
        """A rejected recommendation must report REJECTED verification with zero stock moved."""
        _, _, _, _, _, _, rec = _seed_test_nodes(db_session)

        client.post(
            f"/api/v1/recommendations/{rec.id}/action",
            json={"action": "REJECT"},
            headers={"Authorization": CDMO_TOKEN}
        )

        verif_res = client.get(
            f"/api/v1/recommendations/{rec.id}/verification",
            headers={"Authorization": CDMO_TOKEN}
        )
        assert verif_res.status_code == 200
        data = verif_res.json()

        assert data["status"] == "REJECTED"
        assert data["execution_status"] == "REJECTED"
        assert data["comparison"]["approved_quantity"] == 0
        assert data["comparison"]["actual_quantity_moved"] == 0


class TestRBACSecurityVerification:
    def test_facility_officer_allowed_for_own_facility(self, db_session):
        """Facility Officer assigned to recipient or donor can view verification."""
        _, _, _, _, _, _, rec = _seed_test_nodes(db_session)

        # Recipient officer access
        res_recip = client.get(
            f"/api/v1/recommendations/{rec.id}/verification",
            headers={"Authorization": RECIP_OFFICER_TOKEN}
        )
        assert res_recip.status_code == 200

        # Donor officer access
        res_donor = client.get(
            f"/api/v1/recommendations/{rec.id}/verification",
            headers={"Authorization": DONOR_OFFICER_TOKEN}
        )
        assert res_donor.status_code == 200

    def test_facility_officer_forbidden_for_other_facility(self, db_session):
        """Facility Officer from an unrelated facility receives HTTP 403 Forbidden."""
        _, _, _, _, _, _, rec = _seed_test_nodes(db_session)

        # Behala officer has facility_id = fac_other.id (not donor, not recip)
        res = client.get(
            f"/api/v1/recommendations/{rec.id}/verification",
            headers={"Authorization": OTHER_OFFICER_TOKEN}
        )
        assert res.status_code == 403
        assert "Forbidden" in res.json()["detail"]

    def test_cdmo_and_admin_have_global_verification_access(self, db_session):
        """CDMO and ADMIN have network-wide read access."""
        _, _, _, _, _, _, rec = _seed_test_nodes(db_session)

        res_cdmo = client.get(
            f"/api/v1/recommendations/{rec.id}/verification",
            headers={"Authorization": CDMO_TOKEN}
        )
        assert res_cdmo.status_code == 200

        res_admin = client.get(
            f"/api/v1/recommendations/{rec.id}/verification",
            headers={"Authorization": ADMIN_TOKEN}
        )
        assert res_admin.status_code == 200


class TestReadOnlySafety:
    def test_verification_does_not_mutate_database(self, db_session):
        """Verification must be strictly read-only. Database state must remain 100% identical."""
        _, _, _, _, donor_inv, recip_inv, rec = _seed_test_nodes(db_session)

        # Approve transfer first
        client.post(
            f"/api/v1/recommendations/{rec.id}/action",
            json={"action": "APPROVE"},
            headers={"Authorization": CDMO_TOKEN}
        )

        db_session.expire_all()
        donor_qty_before = db_session.query(Inventory).filter(Inventory.id == donor_inv.id).first().quantity
        recip_qty_before = db_session.query(Inventory).filter(Inventory.id == recip_inv.id).first().quantity
        audit_count_before = db_session.query(AuditEvent).count()
        rec_count_before = db_session.query(Recommendation).count()

        # Call verification endpoint multiple times
        for _ in range(5):
            res = client.get(
                f"/api/v1/recommendations/{rec.id}/verification",
                headers={"Authorization": CDMO_TOKEN}
            )
            assert res.status_code == 200

        db_session.expire_all()
        donor_qty_after = db_session.query(Inventory).filter(Inventory.id == donor_inv.id).first().quantity
        recip_qty_after = db_session.query(Inventory).filter(Inventory.id == recip_inv.id).first().quantity
        audit_count_after = db_session.query(AuditEvent).count()
        rec_count_after = db_session.query(Recommendation).count()

        assert donor_qty_after == donor_qty_before
        assert recip_qty_after == recip_qty_before
        assert audit_count_after == audit_count_before
        assert rec_count_after == rec_count_before

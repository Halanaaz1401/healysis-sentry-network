"""
Feature 2.2 — Voice Frontline Input Integration Tests

Voice is purely a frontend input method: browser speech recognition produces a transcript
which enters the SAME backend pipeline as typed text. The backend cannot distinguish voice
from typed input — the text arrives at the same endpoint.

These tests verify that:
1. Voice-style transcripts (Hinglish, English, Hindi) are processed correctly by the
   existing Feature 2.1 advisor pipeline.
2. Unauthenticated voice transcript requests are rejected (401).
3. Facility Officer RBAC still blocks cross-facility voice-transcribed updates.
4. Voice transcripts cannot bypass the human confirmation step — pending_update
   is always returned; inventory is NOT mutated until POST /confirm-update.
5. Voice-transcribed operational queries (non-update) work correctly.
6. The full end-to-end voice update flow succeeds: transcript → chat → confirm → audit.
"""
import os
import sys
import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

os.environ["TESTING"] = "true"

from app.config import settings
from app.database import Base, get_db, engine as db_engine
from app.models import (
    Facility, Medicine, Inventory, Forecast, User,
    FacilityType, UserRole, MedicineCategory,
    AuditEvent, EventType, ConsumptionLog, ActionType
)
from main import app

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_voice_test_data():
    """Sets up standard test data: Jatni CHC, Behala PHC, ORS and Paracetamol inventory."""
    settings.TESTING = True
    Base.metadata.create_all(bind=db_engine)
    db = TestingSessionLocal()

    db.query(AuditEvent).delete()
    db.query(ConsumptionLog).delete()
    db.query(Forecast).delete()
    db.query(Inventory).delete()
    db.query(User).delete()
    db.query(Facility).delete()
    db.query(Medicine).delete()
    db.commit()

    fac_jatni = Facility(
        id=1, facility_code="CHC-OD-KHU-001", name="Jatni CHC (Khordha)",
        facility_type=FacilityType.CHC, state="OD", district="Khordha",
        latitude=20.165, longitude=85.705
    )
    fac_behala = Facility(
        id=4, facility_code="PHC-WB-KOL-004", name="Behala Urban PHC (Kolkata)",
        facility_type=FacilityType.UPHC, state="WB", district="Kolkata",
        latitude=22.498, longitude=88.318
    )
    db.add_all([fac_jatni, fac_behala])
    db.commit()

    med_ors = Medicine(
        id=1, code="MED-ORS-SACHET", name="ORS",
        category=MedicineCategory.ESSENTIAL_MEDICINE, unit="sachets"
    )
    med_pcm = Medicine(
        id=2, code="MED-PARACET-500MG", name="Paracetamol",
        category=MedicineCategory.ESSENTIAL_MEDICINE, unit="tablets"
    )
    db.add_all([med_ors, med_pcm])
    db.commit()

    inv_ors = Inventory(
        id=1, facility_id=1, medicine_id=1, item_code="MED-ORS-SACHET",
        item_name="ORS", quantity=100, safety_stock=50,
        incoming_quantity=0, unit="sachets"
    )
    inv_pcm = Inventory(
        id=2, facility_id=1, medicine_id=2, item_code="MED-PARACET-500MG",
        item_name="Paracetamol", quantity=200, safety_stock=100,
        incoming_quantity=0, unit="tablets"
    )
    inv_behala_ors = Inventory(
        id=3, facility_id=4, medicine_id=1, item_code="MED-ORS-SACHET",
        item_name="ORS", quantity=80, safety_stock=40,
        incoming_quantity=0, unit="sachets"
    )
    db.add_all([inv_ors, inv_pcm, inv_behala_ors])
    db.commit()

    fc_ors = Forecast(
        facility_id=1, medicine_id=1, item_code="MED-ORS-SACHET",
        forecast_date=date.today(), expected_daily_demand=10.0,
        days_of_cover=10.0, confidence_score=0.95
    )
    fc_pcm = Forecast(
        facility_id=1, medicine_id=2, item_code="MED-PARACET-500MG",
        forecast_date=date.today(), expected_daily_demand=20.0,
        days_of_cover=10.0, confidence_score=0.95
    )
    db.add_all([fc_ors, fc_pcm])
    db.commit()

    today = date.today()
    for d in range(7, 0, -1):
        db.add(ConsumptionLog(
            facility_id=1, medicine_id=1, item_code="MED-ORS-SACHET",
            date=today - timedelta(days=d),
            quantity_dispensed=10, patient_footfall=25, action_type=ActionType.DISPENSE
        ))
    db.commit()

    user_jatni = User(
        id=1, firebase_uid="UID-OFFICER-JATNI",
        email="officer.jatni@healysis.gov.in", full_name="Dr. A. Nayak",
        role=UserRole.FACILITY_OFFICER, facility_id=1
    )
    user_behala = User(
        id=2, firebase_uid="UID-OFFICER-BEHALA",
        email="officer.behala@healysis.gov.in", full_name="T. Banerjee",
        role=UserRole.FACILITY_OFFICER, facility_id=4
    )
    user_cdmo = User(
        id=3, firebase_uid="UID-CDMO-88",
        email="cdmo.director@healysis.gov.in", full_name="Dr. S. Mohanty (CDMO)",
        role=UserRole.CDMO, facility_id=None
    )
    db.add_all([user_jatni, user_behala, user_cdmo])
    db.commit()
    db.close()


# ==========================================
# Test 1: Unauthenticated voice transcript rejected (401)
# ==========================================

def test_voice_transcript_unauthenticated_rejected():
    """
    Voice transcript reaching the backend without a valid auth token must be rejected.
    This applies equally to voice-transcribed and typed text.
    """
    resp = client.post(
        "/api/v1/advisor/chat",
        json={"message": "Aaj ORS ka stock 200 hai."},
        headers={}  # No Authorization header
    )
    assert resp.status_code == 401, (
        f"Unauthenticated voice transcript must return 401, got {resp.status_code}"
    )


# ==========================================
# Test 2: Hinglish voice transcript parsed correctly
# ==========================================

def test_voice_hinglish_transcript_parsed_correctly():
    """
    Voice transcript 'Aaj ORS ka stock 200 hai.' (Hinglish, typical voice input)
    must be recognised as a frontline inventory update intent.
    """
    headers = {"Authorization": "Bearer TEST-TOKEN-UID-OFFICER-JATNI"}
    resp = client.post(
        "/api/v1/advisor/chat",
        json={"message": "Aaj ORS ka stock 200 hai."},
        headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["pending_update"] is not None, "Hinglish voice transcript must produce pending_update"
    assert data["pending_update"]["new_quantity"] == 200
    assert data["pending_update"]["item_code"] == "MED-ORS-SACHET"
    assert data["pending_update"]["facility_id"] == 1
    assert data["requires_human_approval"] is True


# ==========================================
# Test 3: English voice transcript parsed correctly
# ==========================================

def test_voice_english_transcript_parsed_correctly():
    """
    Voice transcript in English 'ORS stock is 180 sachets' must be parsed correctly.
    """
    headers = {"Authorization": "Bearer TEST-TOKEN-UID-OFFICER-JATNI"}
    resp = client.post(
        "/api/v1/advisor/chat",
        json={"message": "ORS stock is 180 sachets."},
        headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["pending_update"] is not None
    assert data["pending_update"]["new_quantity"] == 180
    assert data["pending_update"]["item_code"] == "MED-ORS-SACHET"
    assert data["requires_human_approval"] is True


# ==========================================
# Test 4: Hindi command voice transcript parsed correctly
# ==========================================

def test_voice_hinglish_command_kardo_parsed():
    """
    Voice transcript 'ORS ka stock 180 kar do.' (command form) must be recognized as
    an inventory update intent.
    """
    headers = {"Authorization": "Bearer TEST-TOKEN-UID-OFFICER-JATNI"}
    resp = client.post(
        "/api/v1/advisor/chat",
        json={"message": "ORS ka stock 180 kar do."},
        headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["pending_update"] is not None
    assert data["pending_update"]["new_quantity"] == 180
    assert data["pending_update"]["item_code"] == "MED-ORS-SACHET"


# ==========================================
# Test 5: Voice transcript cannot bypass confirmation
# ==========================================

def test_voice_transcript_cannot_bypass_confirmation():
    """
    A voice transcript that contains an update intent MUST result in pending_update
    requiring confirmation. It must NOT directly mutate inventory.
    """
    headers = {"Authorization": "Bearer TEST-TOKEN-UID-OFFICER-JATNI"}
    db = TestingSessionLocal()
    inv_before = db.query(Inventory).filter(
        Inventory.facility_id == 1, Inventory.item_code == "MED-ORS-SACHET"
    ).first()
    qty_before = inv_before.quantity
    db.close()

    # Submit a voice-like transcript
    resp = client.post(
        "/api/v1/advisor/chat",
        json={"message": "Aaj ORS ka stock 250 hai."},
        headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["pending_update"] is not None
    assert data["requires_human_approval"] is True

    # Verify database was NOT mutated — confirmation was never called
    db = TestingSessionLocal()
    inv_after = db.query(Inventory).filter(
        Inventory.facility_id == 1, Inventory.item_code == "MED-ORS-SACHET"
    ).first()
    assert inv_after.quantity == qty_before, (
        f"Voice transcript must NOT mutate inventory before confirmation. "
        f"Expected {qty_before}, got {inv_after.quantity}"
    )
    db.close()


# ==========================================
# Test 6: Voice RBAC — cross-facility blocked
# ==========================================

def test_voice_transcript_cross_facility_rbac_blocked():
    """
    Behala officer (facility_id=4) speaks a message referencing Jatni CHC (facility_id=1).
    The backend must reject the cross-facility update via RBAC — same as typed input.
    """
    headers = {"Authorization": "Bearer TEST-TOKEN-UID-OFFICER-BEHALA"}
    resp = client.post(
        "/api/v1/advisor/chat",
        json={"message": "Jatni mein ORS 250 hai."},
        headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    # Must not produce a pending_update for Jatni (facility 1) from Behala officer
    if data["pending_update"] is not None:
        assert data["pending_update"]["facility_id"] != 1, (
            "RBAC must block Behala officer from updating Jatni CHC via voice transcript"
        )


# ==========================================
# Test 7: Voice operational query (non-update)
# ==========================================

def test_voice_operational_query_works():
    """
    A voice transcript asking an operational question (not an update) must be
    processed as a standard operational query with no pending_update.
    """
    headers = {"Authorization": "Bearer TEST-TOKEN-UID-OFFICER-JATNI"}
    resp = client.post(
        "/api/v1/advisor/chat",
        json={"message": "ORS ka kitna stock bacha hai Jatni mein?"},
        headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["pending_update"] is None
    assert data["answer"] is not None
    assert len(data["answer"]) > 0


# ==========================================
# Test 8: Voice with daily demand transcript
# ==========================================

def test_voice_transcript_with_daily_demand_parsed():
    """
    Voice transcript 'Paracetamol ka stock 320 hai aur daily demand 35 hai.'
    must parse both quantity and daily demand correctly.
    """
    headers = {"Authorization": "Bearer TEST-TOKEN-UID-OFFICER-JATNI"}
    resp = client.post(
        "/api/v1/advisor/chat",
        json={"message": "Paracetamol ka stock 320 hai aur daily demand 35 hai."},
        headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["pending_update"] is not None
    assert data["pending_update"]["new_quantity"] == 320
    assert data["pending_update"]["item_code"] == "MED-PARACET-500MG"
    assert data["pending_update"]["new_daily_demand"] == 35.0


# ==========================================
# Test 9: Full end-to-end voice update — transcript → confirm → audit
# ==========================================

def test_voice_end_to_end_transcript_confirm_audit():
    """
    Full voice pipeline:
    1. Voice transcript produces pending_update (chat endpoint)
    2. Human confirms via confirm-update endpoint
    3. Inventory is mutated
    4. Audit event is recorded with SHA-256 hash
    5. Forecast/risk is recalculated
    """
    jatni_headers = {"Authorization": "Bearer TEST-TOKEN-UID-OFFICER-JATNI"}

    # Step 1: Voice transcript → advisor returns pending_update
    chat_resp = client.post(
        "/api/v1/advisor/chat",
        json={"message": "Aaj ORS ka stock 200 hai."},
        headers=jatni_headers
    )
    assert chat_resp.status_code == 200
    chat_data = chat_resp.json()
    assert chat_data["pending_update"] is not None
    pending = chat_data["pending_update"]
    assert pending["new_quantity"] == 200
    assert pending["item_code"] == "MED-ORS-SACHET"
    assert pending["facility_id"] == 1
    token = pending["confirmation_token"]
    assert token.startswith("TOK-UPD-")

    # Step 2: Human explicitly confirms (just as they would in UI)
    confirm_resp = client.post(
        "/api/v1/advisor/confirm-update",
        json={
            "facility_id": 1,
            "item_code": "MED-ORS-SACHET",
            "quantity": 200,
            "daily_demand": None,
            "confirmation_token": token
        },
        headers=jatni_headers
    )
    assert confirm_resp.status_code == 200
    confirm_data = confirm_resp.json()
    assert confirm_data["status"] == "SUCCESS"
    assert confirm_data["new_quantity"] == 200
    assert confirm_data["previous_quantity"] == 100
    assert confirm_data["audit_event_id"].startswith("EVT-UPD-")
    assert confirm_data["days_of_cover"] > 0

    # Step 3: Verify database was mutated
    db = TestingSessionLocal()
    inv = db.query(Inventory).filter(
        Inventory.facility_id == 1, Inventory.item_code == "MED-ORS-SACHET"
    ).first()
    assert inv.quantity == 200, f"Inventory must be 200 after confirmation, got {inv.quantity}"

    # Step 4: Verify SHA-256 audit entry
    evt = db.query(AuditEvent).filter(
        AuditEvent.event_id == confirm_data["audit_event_id"]
    ).first()
    assert evt is not None
    assert evt.payload_json["previous_quantity"] == 100
    assert evt.payload_json["new_quantity"] == 200
    assert evt.payload_json["source"] == "AI_ADVISOR_FRONTLINE_INPUT"
    assert evt.current_hash is not None
    assert len(evt.current_hash) == 64  # SHA-256 hex digest
    db.close()


# ==========================================
# Test 10: Voice no-op when stock already matches
# ==========================================

def test_voice_noop_when_stock_already_matches():
    """
    If a voice transcript reports the same stock quantity already in the database,
    the backend must return a no-op response (no pending_update, no mutation).
    """
    jatni_headers = {"Authorization": "Bearer TEST-TOKEN-UID-OFFICER-JATNI"}

    # Inventory starts at 100 sachets
    resp = client.post(
        "/api/v1/advisor/chat",
        json={"message": "Aaj ORS ka stock 100 hai."},
        headers=jatni_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["pending_update"] is None
    assert data["requires_human_approval"] is False
    assert "already recorded as" in data["answer"]
    assert "100" in data["answer"]


# ==========================================
# Test 11: Voice with invalid/tampered token rejected
# ==========================================

def test_voice_confirm_tampered_token_rejected():
    """
    Attempting to confirm with a tampered token (even with correct voice transcription)
    must be rejected with HTTP 400.
    """
    jatni_headers = {"Authorization": "Bearer TEST-TOKEN-UID-OFFICER-JATNI"}
    confirm_resp = client.post(
        "/api/v1/advisor/confirm-update",
        json={
            "facility_id": 1,
            "item_code": "MED-ORS-SACHET",
            "quantity": 200,
            "daily_demand": None,
            "confirmation_token": "TOK-UPD-VOICE-TAMPERED-INVALID"
        },
        headers=jatni_headers
    )
    assert confirm_resp.status_code == 400
    assert "Invalid or tampered confirmation token" in confirm_resp.json()["detail"]


# ==========================================
# Test 12: CDMO voice transcript (operational query allowed)
# ==========================================

def test_cdmo_voice_operational_query_allowed():
    """
    CDMO role can ask operational queries via voice transcript (no facility restriction).
    """
    cdmo_headers = {"Authorization": "Bearer TEST-TOKEN-UID-CDMO-88"}
    resp = client.post(
        "/api/v1/advisor/chat",
        json={"message": "Which facility has the highest stockout risk?"},
        headers=cdmo_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["answer"] is not None
    assert data["pending_update"] is None  # Operational query, not an update

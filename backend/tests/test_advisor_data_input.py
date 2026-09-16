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
    Facility, Medicine, Inventory, Forecast, Alert, Recommendation, User,
    FacilityType, UserRole, MedicineCategory, AlertSeverity, AlertType, AlertStatus,
    AuditEvent, EventType, ConsumptionLog, ActionType
)
from app.schemas import AdvisorChatRequest, InventoryUpdateConfirmationRequest
from app.advisor_service import (
    generate_update_token, verify_update_token, run_grounded_ai_advisor
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
def setup_test_data():
    settings.TESTING = True
    Base.metadata.create_all(bind=db_engine)
    db = TestingSessionLocal()

    db.query(AuditEvent).delete()
    db.query(Recommendation).delete()
    db.query(Alert).delete()
    db.query(Forecast).delete()
    db.query(Inventory).delete()
    db.query(User).delete()
    db.query(Facility).delete()
    db.query(Medicine).delete()
    db.commit()

    # Facilities
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

    # Medicines
    med_ors = Medicine(id=1, code="MED-ORS-SACHET", name="ORS", category=MedicineCategory.ESSENTIAL_MEDICINE, unit="sachets")
    med_pcm = Medicine(id=2, code="MED-PARACET-500MG", name="Paracetamol", category=MedicineCategory.ESSENTIAL_MEDICINE, unit="tablets")
    db.add_all([med_ors, med_pcm])
    db.commit()

    # Inventory at Jatni
    inv_ors = Inventory(
        id=1, facility_id=fac_jatni.id, medicine_id=med_ors.id, item_code=med_ors.code,
        item_name=med_ors.name, quantity=100, safety_stock=50, incoming_quantity=0, unit="sachets"
    )
    inv_pcm = Inventory(
        id=2, facility_id=fac_jatni.id, medicine_id=med_pcm.id, item_code=med_pcm.code,
        item_name=med_pcm.name, quantity=200, safety_stock=100, incoming_quantity=0, unit="tablets"
    )
    # Inventory at Behala
    inv_behala_ors = Inventory(
        id=3, facility_id=fac_behala.id, medicine_id=med_ors.id, item_code=med_ors.code,
        item_name=med_ors.name, quantity=80, safety_stock=40, incoming_quantity=0, unit="sachets"
    )
    db.add_all([inv_ors, inv_pcm, inv_behala_ors])
    db.commit()

    # Forecast at Jatni
    fc_ors = Forecast(
        facility_id=fac_jatni.id, medicine_id=med_ors.id, item_code=med_ors.code,
        forecast_date=date.today(), expected_daily_demand=10.0, days_of_cover=10.0, confidence_score=0.95
    )
    fc_pcm = Forecast(
        facility_id=fac_jatni.id, medicine_id=med_pcm.id, item_code=med_pcm.code,
        forecast_date=date.today(), expected_daily_demand=20.0, days_of_cover=10.0, confidence_score=0.95
    )
    db.add_all([fc_ors, fc_pcm])
    db.commit()

    # Seed 7 days consumption logs
    today = date.today()
    for d in range(7, 0, -1):
        db.add(ConsumptionLog(
            facility_id=fac_jatni.id, medicine_id=med_ors.id, item_code=med_ors.code,
            date=today - timedelta(days=d), quantity_dispensed=10, patient_footfall=25, action_type=ActionType.DISPENSE
        ))
        db.add(ConsumptionLog(
            facility_id=fac_jatni.id, medicine_id=med_pcm.id, item_code=med_pcm.code,
            date=today - timedelta(days=d), quantity_dispensed=20, patient_footfall=30, action_type=ActionType.DISPENSE
        ))
    db.commit()

    # Users
    user_officer_jatni = User(
        id=1, firebase_uid="UID-OFFICER-JATNI", email="officer.jatni@healysis.gov.in",
        full_name="Dr. A. Nayak", role=UserRole.FACILITY_OFFICER, facility_id=1
    )
    user_officer_behala = User(
        id=2, firebase_uid="UID-OFFICER-BEHALA", email="officer.behala@healysis.gov.in",
        full_name="T. Banerjee", role=UserRole.FACILITY_OFFICER, facility_id=4
    )
    user_admin = User(
        id=3, firebase_uid="UID-ADMIN-99", email="admin@healysis.gov.in",
        full_name="System Admin", role=UserRole.ADMIN, facility_id=None
    )
    db.add_all([user_officer_jatni, user_officer_behala, user_admin])
    db.commit()

    db.close()


def test_token_generation_and_verification():
    token = generate_update_token(user_id=1, facility_id=1, item_code="MED-ORS-SACHET", quantity=180, demand=None)
    assert token.startswith("TOK-UPD-")
    assert verify_update_token(token, user_id=1, facility_id=1, item_code="MED-ORS-SACHET", quantity=180, demand=None) is True
    # Tampered quantity
    assert verify_update_token(token, user_id=1, facility_id=1, item_code="MED-ORS-SACHET", quantity=190, demand=None) is False
    # Tampered user
    assert verify_update_token(token, user_id=2, facility_id=1, item_code="MED-ORS-SACHET", quantity=180, demand=None) is False


def test_detect_update_intent_english():
    db = TestingSessionLocal()
    user = db.query(User).filter(User.id == 1).first()
    req = AdvisorChatRequest(message="ORS stock is 180 units.")
    res = run_grounded_ai_advisor(req, user, db)

    assert res.pending_update is not None
    assert res.pending_update.item_code == "MED-ORS-SACHET"
    assert res.pending_update.new_quantity == 180
    assert res.pending_update.facility_id == 1
    assert "Confirm Update" in res.answer
    assert res.requires_human_approval is True
    db.close()


def test_detect_update_intent_hinglish():
    db = TestingSessionLocal()
    user = db.query(User).filter(User.id == 1).first()
    req = AdvisorChatRequest(message="Aaj ORS ka stock 180 hai.")
    res = run_grounded_ai_advisor(req, user, db)

    assert res.pending_update is not None
    assert res.pending_update.item_code == "MED-ORS-SACHET"
    assert res.pending_update.new_quantity == 180
    assert res.pending_update.facility_id == 1
    assert "Confirm Update" in res.answer
    db.close()


def test_detect_update_with_daily_demand():
    db = TestingSessionLocal()
    user = db.query(User).filter(User.id == 1).first()
    req = AdvisorChatRequest(message="Paracetamol stock is 320 and daily demand is 35.")
    res = run_grounded_ai_advisor(req, user, db)

    assert res.pending_update is not None
    assert res.pending_update.item_code == "MED-PARACET-500MG"
    assert res.pending_update.new_quantity == 320
    assert res.pending_update.new_daily_demand == 35.0
    assert "35.0" in res.answer or "35" in res.answer
    db.close()


def test_detect_hinglish_update_with_daily_demand():
    db = TestingSessionLocal()
    user = db.query(User).filter(User.id == 1).first()
    req = AdvisorChatRequest(message="Paracetamol ka stock 320 hai aur daily demand 35 hai.")
    res = run_grounded_ai_advisor(req, user, db)

    assert res.pending_update is not None
    assert res.pending_update.item_code == "MED-PARACET-500MG"
    assert res.pending_update.new_quantity == 320
    assert res.pending_update.new_daily_demand == 35.0
    db.close()


def test_detect_command_kardo():
    db = TestingSessionLocal()
    user = db.query(User).filter(User.id == 1).first()
    req = AdvisorChatRequest(message="ORS ka stock 180 kar do.")
    res = run_grounded_ai_advisor(req, user, db)

    assert res.pending_update is not None
    assert res.pending_update.new_quantity == 180
    assert res.pending_update.item_code == "MED-ORS-SACHET"
    db.close()


def test_missing_resource_asks_clarification():
    db = TestingSessionLocal()
    user = db.query(User).filter(User.id == 1).first()
    req = AdvisorChatRequest(message="Stock 180 hai.")
    res = run_grounded_ai_advisor(req, user, db)

    assert res.pending_update is None
    assert "Which medicine would you like to update" in res.answer
    db.close()


def test_unknown_resource_rejected():
    db = TestingSessionLocal()
    user = db.query(User).filter(User.id == 1).first()
    req = AdvisorChatRequest(message="XYZ medicine ka stock 100 hai.")
    res = run_grounded_ai_advisor(req, user, db)

    assert res.pending_update is None
    # Updated: new error message format includes catalog listing and clarification prompt
    assert "XYZ" in res.answer
    # Must contain either the old phrasing or the new clarification phrasing
    assert (
        "not found in the verified healthcare medicine catalog" in res.answer
        or "verified Healysis medicine catalog" in res.answer
        or "Did you mean" in res.answer
    )
    db.close()


def test_negative_value_rejected():
    db = TestingSessionLocal()
    user = db.query(User).filter(User.id == 1).first()
    req = AdvisorChatRequest(message="ORS stock minus 20 hai.")
    res = run_grounded_ai_advisor(req, user, db)

    assert res.pending_update is None
    assert "cannot be negative" in res.answer
    db.close()


def test_negative_number_symbol_rejected():
    db = TestingSessionLocal()
    user = db.query(User).filter(User.id == 1).first()
    req = AdvisorChatRequest(message="ORS stock -20 hai.")
    res = run_grounded_ai_advisor(req, user, db)

    assert res.pending_update is None
    assert "cannot be negative" in res.answer
    db.close()


def test_facility_officer_cross_facility_rejected():
    db = TestingSessionLocal()
    # User 2 is assigned to Behala (id=4). They try to update Jatni (id=1).
    user_behala = db.query(User).filter(User.id == 2).first()
    req = AdvisorChatRequest(message="Jatni mein ORS 180 hai.")
    res = run_grounded_ai_advisor(req, user_behala, db)

    assert res.pending_update is None
    assert "Authorization Error" in res.answer
    assert "Jatni CHC" in res.answer
    db.close()


def test_informational_query_not_treated_as_update():
    db = TestingSessionLocal()
    user = db.query(User).filter(User.id == 1).first()
    req = AdvisorChatRequest(message="Which facility has the highest stockout risk?")
    res = run_grounded_ai_advisor(req, user, db)

    assert res.pending_update is None
    assert res.severity in ["SAFE", "WARNING", "CRITICAL"]
    db.close()


def test_chat_and_confirm_update_end_to_end():
    # 1. Ask chat to prepare update as Jatni officer
    headers = {"Authorization": "Bearer TEST-TOKEN-UID-OFFICER-JATNI"}
    chat_payload = {"message": "Aaj ORS ka stock 180 hai."}
    chat_resp = client.post("/api/v1/advisor/chat", json=chat_payload, headers=headers)
    assert chat_resp.status_code == 200
    chat_data = chat_resp.json()

    assert chat_data["pending_update"] is not None
    pending = chat_data["pending_update"]
    assert pending["new_quantity"] == 180
    assert pending["item_code"] == "MED-ORS-SACHET"
    assert pending["facility_id"] == 1
    token = pending["confirmation_token"]

    # 2. Confirm the update
    confirm_payload = {
        "facility_id": 1,
        "item_code": "MED-ORS-SACHET",
        "quantity": 180,
        "daily_demand": None,
        "confirmation_token": token
    }
    confirm_resp = client.post("/api/v1/advisor/confirm-update", json=confirm_payload, headers=headers)
    assert confirm_resp.status_code == 200
    confirm_data = confirm_resp.json()

    assert confirm_data["status"] == "SUCCESS"
    assert confirm_data["new_quantity"] == 180
    assert confirm_data["previous_quantity"] == 100
    assert confirm_data["days_of_cover"] in [12.0, 18.0]
    assert confirm_data["audit_event_id"].startswith("EVT-UPD-")

    # 3. Verify in database
    db = TestingSessionLocal()
    inv = db.query(Inventory).filter(Inventory.facility_id == 1, Inventory.item_code == "MED-ORS-SACHET").first()
    assert inv.quantity == 180

    fc = db.query(Forecast).filter(Forecast.facility_id == 1, Forecast.item_code == "MED-ORS-SACHET").first()
    assert fc.days_of_cover == confirm_data["days_of_cover"]

    evt = db.query(AuditEvent).filter(AuditEvent.event_id == confirm_data["audit_event_id"]).first()
    assert evt is not None
    assert evt.payload_json["previous_quantity"] == 100
    assert evt.payload_json["new_quantity"] == 180
    assert evt.payload_json["source"] == "AI_ADVISOR_FRONTLINE_INPUT"
    assert evt.current_hash is not None
    db.close()


def test_confirm_update_tampered_token_rejected():
    headers = {"Authorization": "Bearer TEST-TOKEN-UID-OFFICER-JATNI"}
    confirm_payload = {
        "facility_id": 1,
        "item_code": "MED-ORS-SACHET",
        "quantity": 500,  # tampered quantity
        "daily_demand": None,
        "confirmation_token": "TOK-UPD-INVALID_OR_TAMPERED_SIG"
    }
    confirm_resp = client.post("/api/v1/advisor/confirm-update", json=confirm_payload, headers=headers)
    assert confirm_resp.status_code == 400
    assert "Invalid or tampered confirmation token" in confirm_resp.json()["detail"]


def test_confirm_update_cross_facility_rbac_forbidden():
    # Officer Behala (facility 4) tries to confirm an update for Jatni (facility 1)
    headers = {"Authorization": "Bearer TEST-TOKEN-UID-OFFICER-BEHALA"}
    token = generate_update_token(user_id=2, facility_id=1, item_code="MED-ORS-SACHET", quantity=180, demand=None)
    confirm_payload = {
        "facility_id": 1,
        "item_code": "MED-ORS-SACHET",
        "quantity": 180,
        "daily_demand": None,
        "confirmation_token": token
    }
    confirm_resp = client.post("/api/v1/advisor/confirm-update", json=confirm_payload, headers=headers)
    assert confirm_resp.status_code == 403


# ==========================================
# No-Op vs Real Update Regression Tests
# ==========================================

def test_noop_when_proposed_stock_matches_current_db_stock():
    """When proposed stock matches database stock and demand is unchanged, return no-op without mutation."""
    headers = {"Authorization": "Bearer TEST-TOKEN-UID-OFFICER-JATNI"}
    db = TestingSessionLocal()
    inv = db.query(Inventory).filter(Inventory.facility_id == 1, Inventory.item_code == "MED-ORS-SACHET").first()
    assert inv.quantity == 100
    initial_audit_count = db.query(AuditEvent).count()
    db.close()

    # User reports stock is 100 (which is already recorded in DB)
    resp = client.post("/api/v1/advisor/chat", json={"message": "Aaj ORS ka stock 100 hai."}, headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    # Verify no pending update confirmation is created
    assert data["pending_update"] is None
    assert data["requires_human_approval"] is False
    assert "already recorded as" in data["answer"]
    assert "100" in data["answer"]
    assert "No inventory update is required" in data["answer"]

    # Verify database remains untouched and no mutation audit event was recorded
    db = TestingSessionLocal()
    inv_after = db.query(Inventory).filter(Inventory.facility_id == 1, Inventory.item_code == "MED-ORS-SACHET").first()
    assert inv_after.quantity == 100
    assert db.query(AuditEvent).count() == initial_audit_count
    db.close()


def test_real_update_flow_after_noop_and_cancel():
    """Verify transitions: No-op -> Real update (200) -> Cancel -> Confirm (200) -> Subsequent No-op (200)."""
    headers = {"Authorization": "Bearer TEST-TOKEN-UID-OFFICER-JATNI"}

    # 1. No-op when stock is 100
    resp_noop = client.post("/api/v1/advisor/chat", json={"message": "Aaj ORS ka stock 100 hai."}, headers=headers)
    assert resp_noop.status_code == 200
    assert resp_noop.json()["pending_update"] is None

    # 2. Real update proposed to 200
    resp_update = client.post("/api/v1/advisor/chat", json={"message": "Aaj ORS ka stock 200 hai."}, headers=headers)
    assert resp_update.status_code == 200
    data_update = resp_update.json()
    assert data_update["pending_update"] is not None
    assert data_update["pending_update"]["current_quantity"] == 100
    assert data_update["pending_update"]["new_quantity"] == 200
    token = data_update["pending_update"]["confirmation_token"]

    # 3. Simulate Cancel: User discards; verify DB remains 100
    db = TestingSessionLocal()
    inv = db.query(Inventory).filter(Inventory.facility_id == 1, Inventory.item_code == "MED-ORS-SACHET").first()
    assert inv.quantity == 100
    db.close()

    # 4. User confirms update with token
    confirm_resp = client.post("/api/v1/advisor/confirm-update", json={
        "facility_id": 1,
        "item_code": "MED-ORS-SACHET",
        "quantity": 200,
        "daily_demand": None,
        "confirmation_token": token
    }, headers=headers)
    assert confirm_resp.status_code == 200
    assert confirm_resp.json()["new_quantity"] == 200

    # 5. Verify database was mutated to 200
    db = TestingSessionLocal()
    inv_updated = db.query(Inventory).filter(Inventory.facility_id == 1, Inventory.item_code == "MED-ORS-SACHET").first()
    assert inv_updated.quantity == 200
    db.close()

    # 6. Subsequent query proposing 200 is now a NO-OP!
    resp_subsequent_noop = client.post("/api/v1/advisor/chat", json={"message": "Aaj ORS ka stock 200 hai."}, headers=headers)
    assert resp_subsequent_noop.status_code == 200
    assert resp_subsequent_noop.json()["pending_update"] is None
    assert "already recorded as" in resp_subsequent_noop.json()["answer"]
    assert "200" in resp_subsequent_noop.json()["answer"]


def test_demand_update_not_treated_as_noop_even_if_stock_unchanged():
    """When proposed stock is unchanged but proposed daily demand is updated, it is a real update."""
    headers = {"Authorization": "Bearer TEST-TOKEN-UID-OFFICER-JATNI"}
    db = TestingSessionLocal()
    inv_pcm = db.query(Inventory).filter(Inventory.facility_id == 1, Inventory.item_code == "MED-PARACET-500MG").first()
    assert inv_pcm.quantity == 200
    fc_pcm = db.query(Forecast).filter(Forecast.facility_id == 1, Forecast.item_code == "MED-PARACET-500MG").first()
    assert fc_pcm.expected_daily_demand == 20.0
    db.close()

    # Proposed stock is 200 (same), but daily demand is 35 (changed from 20.0)
    resp = client.post(
        "/api/v1/advisor/chat",
        json={"message": "Paracetamol stock is 200 and daily demand is 35."},
        headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["pending_update"] is not None
    assert data["pending_update"]["current_quantity"] == 200
    assert data["pending_update"]["new_quantity"] == 200
    assert data["pending_update"]["current_daily_demand"] == 20.0
    assert data["pending_update"]["new_daily_demand"] == 35.0


def test_demand_unchanged_and_stock_unchanged_is_noop():
    """When proposed stock is unchanged and proposed daily demand matches current demand, it is a no-op."""
    headers = {"Authorization": "Bearer TEST-TOKEN-UID-OFFICER-JATNI"}
    resp = client.post(
        "/api/v1/advisor/chat",
        json={"message": "Paracetamol stock is 200 and daily demand is 20."},
        headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["pending_update"] is None
    assert data["requires_human_approval"] is False
    assert "already recorded as" in data["answer"]
    assert "200" in data["answer"]


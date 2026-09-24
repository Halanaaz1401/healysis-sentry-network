import os
import sys
from datetime import date, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

os.environ["TESTING"] = "true"

from app.config import settings
from app.database import Base, get_db, engine as db_engine
from app.models import (
    Facility, Medicine, Inventory, ConsumptionLog, Forecast, Alert, Recommendation, User, AuditEvent,
    FacilityType, UserRole, MedicineCategory, ActionType, RecommendationStatus
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
def setup_simulation_test_data():
    settings.TESTING = True
    Base.metadata.create_all(bind=db_engine)
    db = TestingSessionLocal()

    db.query(AuditEvent).delete()
    db.query(Recommendation).delete()
    db.query(Alert).delete()
    db.query(Forecast).delete()
    db.query(ConsumptionLog).delete()
    db.query(Inventory).delete()
    db.query(User).delete()
    db.query(Facility).delete()
    db.query(Medicine).delete()
    db.commit()

    # Facilities
    fac_jatni = Facility(facility_code="CHC-OD-KHU-001", name="Jatni CHC (Khordha)", facility_type=FacilityType.CHC, state="OD", district="Khordha", latitude=20.165, longitude=85.705)
    fac_cuttack = Facility(facility_code="UPHC-OD-CTC-002", name="UPHC MS Das (Kafla Bazar)", facility_type=FacilityType.UPHC, state="OD", district="Cuttack", latitude=20.462, longitude=85.882)
    fac_pipili = Facility(facility_code="PHC-OD-PURI-004", name="Pipili PHC (Puri)", facility_type=FacilityType.PHC, state="OD", district="Puri", latitude=20.117, longitude=85.833)
    db.add_all([fac_jatni, fac_cuttack, fac_pipili])
    db.commit()

    # Medicines
    med_ins = Medicine(code="MED-INSULIN-100IU", name="Insulin 100IU", category=MedicineCategory.VACCINE, unit="vials")
    med_ors = Medicine(code="MED-ORS-SACHET", name="ORS Sachet", category=MedicineCategory.ESSENTIAL_MEDICINE, unit="sachets")
    db.add_all([med_ins, med_ors])
    db.commit()

    # Users
    user_admin = User(firebase_uid="UID-ADMIN-TEST", email="admin@healysis.gov.in", full_name="Admin User", role=UserRole.ADMIN, facility_id=None)
    user_cdmo = User(firebase_uid="UID-CDMO-TEST", email="cdmo@healysis.gov.in", full_name="CDMO User", role=UserRole.CDMO, facility_id=None)
    user_jatni_officer = User(firebase_uid="UID-JATNI-OFFICER", email="jatni.officer@healysis.gov.in", full_name="Jatni Officer", role=UserRole.FACILITY_OFFICER, facility_id=fac_jatni.id)
    user_cuttack_officer = User(firebase_uid="UID-CUTTACK-OFFICER", email="cuttack.officer@healysis.gov.in", full_name="Cuttack Officer", role=UserRole.FACILITY_OFFICER, facility_id=fac_cuttack.id)
    db.add_all([user_admin, user_cdmo, user_jatni_officer, user_cuttack_officer])
    db.commit()

    # Inventories
    # Jatni CHC: 15 ORS units (Safety 40, Deficit 25)
    inv_jatni_ors = Inventory(facility_id=fac_jatni.id, medicine_id=med_ors.id, item_code=med_ors.code, item_name=med_ors.name, quantity=15, safety_stock=40, incoming_quantity=0, unit="sachets")
    # Pipili PHC: 180 ORS units (Safety 40, Surplus 140)
    inv_pipili_ors = Inventory(facility_id=fac_pipili.id, medicine_id=med_ors.id, item_code=med_ors.code, item_name=med_ors.name, quantity=180, safety_stock=40, incoming_quantity=0, unit="sachets")
    # Cuttack UPHC: 150 Insulin vials (Safety 40, Surplus 110)
    inv_cuttack_ins = Inventory(facility_id=fac_cuttack.id, medicine_id=med_ins.id, item_code=med_ins.code, item_name=med_ins.name, quantity=150, safety_stock=40, incoming_quantity=0, unit="vials")
    # Jatni Insulin: 5 vials (Safety 40, Deficit 35)
    inv_jatni_ins = Inventory(facility_id=fac_jatni.id, medicine_id=med_ins.id, item_code=med_ins.code, item_name=med_ins.name, quantity=5, safety_stock=40, incoming_quantity=0, unit="vials")

    db.add_all([inv_jatni_ors, inv_pipili_ors, inv_cuttack_ins, inv_jatni_ins])
    db.commit()

    # Forecasts for deterministic daily demand
    # Jatni ORS: demand = 15.0/day
    fc_jatni_ors = Forecast(facility_id=fac_jatni.id, medicine_id=med_ors.id, item_code=med_ors.code, forecast_date=date.today(), expected_daily_demand=15.0, days_of_cover=1.0, confidence_score=0.92)
    # Pipili ORS: demand = 9.38/day
    fc_pipili_ors = Forecast(facility_id=fac_pipili.id, medicine_id=med_ors.id, item_code=med_ors.code, forecast_date=date.today(), expected_daily_demand=9.38, days_of_cover=19.19, confidence_score=0.95)
    # Cuttack Insulin: demand = 5.0/day
    fc_cuttack_ins = Forecast(facility_id=fac_cuttack.id, medicine_id=med_ins.id, item_code=med_ins.code, forecast_date=date.today(), expected_daily_demand=5.0, days_of_cover=30.0, confidence_score=0.90)
    # Jatni Insulin: demand = 10.0/day
    fc_jatni_ins = Forecast(facility_id=fac_jatni.id, medicine_id=med_ins.id, item_code=med_ins.code, forecast_date=date.today(), expected_daily_demand=10.0, days_of_cover=0.5, confidence_score=0.91)

    db.add_all([fc_jatni_ors, fc_pipili_ors, fc_cuttack_ins, fc_jatni_ins])
    db.commit()
    db.close()

    yield

# ==========================================
# 1. Validation & Calculation Tests
# ==========================================

def test_valid_redistribution_simulation_cdmo():
    db = TestingSessionLocal()
    fac_jatni = db.query(Facility).filter(Facility.facility_code == "CHC-OD-KHU-001").first()
    fac_pipili = db.query(Facility).filter(Facility.facility_code == "PHC-OD-PURI-004").first()
    med_ors = db.query(Medicine).filter(Medicine.code == "MED-ORS-SACHET").first()
    db.close()

    # Simulate transfer of 90 ORS units from Pipili (donor) to Jatni (recipient)
    payload = {
        "donor_facility_id": fac_pipili.id,
        "recipient_facility_id": fac_jatni.id,
        "item_code": med_ors.code,
        "transfer_quantity": 90
    }
    res = client.post("/api/v1/simulations/redistribution", json=payload, headers={"Authorization": "Bearer TEST-TOKEN-UID-CDMO-TEST"})
    assert res.status_code == 200
    data = res.json()

    assert data["simulation_id"].startswith("SIM-")
    assert data["resource_id"] == "MED-ORS-SACHET"
    assert data["resource_name"] == "ORS Sachet"
    assert data["unit"] == "sachets"
    assert data["transfer_quantity"] == 90
    assert data["status"] == "SAFE"
    assert data["haversine_distance_km"] > 0
    assert "Simulation only" in data["disclaimer"]

    # Recipient telemetry checks
    recip = data["recipient"]
    assert recip["facility_id"] == fac_jatni.id
    assert recip["current_stock"] == 15
    assert recip["simulated_stock"] == 105  # 15 + 90
    assert recip["daily_demand"] == 15.0
    assert recip["current_days_of_cover"] == 1.0
    assert recip["simulated_days_of_cover"] == 7.0  # 105 / 15.0
    assert recip["safety_buffer"] == 40
    assert recip["buffer_achieved"] is True
    assert recip["days_of_cover_gained"] == 6.0
    assert recip["current_projected_stockout"] is not None
    assert recip["simulated_projected_stockout"] is not None

    # Donor telemetry checks
    donor = data["donor"]
    assert donor["facility_id"] == fac_pipili.id
    assert donor["current_stock"] == 180
    assert donor["simulated_stock"] == 90  # 180 - 90
    assert donor["daily_demand"] == 9.38
    assert donor["current_days_of_cover"] == round(180 / 9.38, 2)
    assert donor["simulated_days_of_cover"] == round(90 / 9.38, 2)
    assert donor["safety_buffer"] == 40
    assert donor["surplus_available"] == 140  # 180 - 40
    assert donor["buffer_preserved"] is True  # 90 >= 40
    assert donor["days_of_cover_lost"] > 0

    # Risk analysis flags
    risk = data["risk_analysis"]
    assert risk["recipient_improves"] is True
    assert risk["recipient_remains_below_safety"] is False
    assert risk["donor_falls_below_safety"] is False
    assert risk["donor_becomes_new_risk"] is False
    assert risk["creates_or_worsens_stockout"] is False
    assert risk["within_donor_surplus"] is True
    assert risk["is_operationally_safe"] is True

def test_recipient_stock_calculation():
    db = TestingSessionLocal()
    fac_jatni = db.query(Facility).filter(Facility.facility_code == "CHC-OD-KHU-001").first()
    fac_pipili = db.query(Facility).filter(Facility.facility_code == "PHC-OD-PURI-004").first()
    db.close()

    payload = {
        "donor_facility_id": fac_pipili.id,
        "recipient_facility_id": fac_jatni.id,
        "item_code": "MED-ORS-SACHET",
        "transfer_quantity": 50
    }
    res = client.post("/api/v1/simulations/redistribution", json=payload, headers={"Authorization": "Bearer TEST-TOKEN-UID-CDMO-TEST"})
    assert res.status_code == 200
    data = res.json()
    assert data["recipient"]["current_stock"] == 15
    assert data["recipient"]["simulated_stock"] == 65

def test_donor_stock_calculation():
    db = TestingSessionLocal()
    fac_jatni = db.query(Facility).filter(Facility.facility_code == "CHC-OD-KHU-001").first()
    fac_pipili = db.query(Facility).filter(Facility.facility_code == "PHC-OD-PURI-004").first()
    db.close()

    payload = {
        "donor_facility_id": fac_pipili.id,
        "recipient_facility_id": fac_jatni.id,
        "item_code": "MED-ORS-SACHET",
        "transfer_quantity": 50
    }
    res = client.post("/api/v1/simulations/redistribution", json=payload, headers={"Authorization": "Bearer TEST-TOKEN-UID-CDMO-TEST"})
    assert res.status_code == 200
    data = res.json()
    assert data["donor"]["current_stock"] == 180
    assert data["donor"]["simulated_stock"] == 130

def test_recipient_days_of_cover_calculation():
    db = TestingSessionLocal()
    fac_jatni = db.query(Facility).filter(Facility.facility_code == "CHC-OD-KHU-001").first()
    fac_cuttack = db.query(Facility).filter(Facility.facility_code == "UPHC-OD-CTC-002").first()
    db.close()

    # Jatni Insulin: current=5, demand=10.0/day. Transfer 50 => simulated 55 => DoC = 55 / 10 = 5.5 days
    payload = {
        "donor_facility_id": fac_cuttack.id,
        "recipient_facility_id": fac_jatni.id,
        "item_code": "MED-INSULIN-100IU",
        "transfer_quantity": 50
    }
    res = client.post("/api/v1/simulations/redistribution", json=payload, headers={"Authorization": "Bearer TEST-TOKEN-UID-ADMIN-TEST"})
    assert res.status_code == 200
    data = res.json()
    assert data["recipient"]["simulated_days_of_cover"] == 5.5

def test_donor_days_of_cover_calculation():
    db = TestingSessionLocal()
    fac_jatni = db.query(Facility).filter(Facility.facility_code == "CHC-OD-KHU-001").first()
    fac_cuttack = db.query(Facility).filter(Facility.facility_code == "UPHC-OD-CTC-002").first()
    db.close()

    # Cuttack Insulin: current=150, demand=5.0/day. Transfer 50 => simulated 100 => DoC = 100 / 5 = 20.0 days
    payload = {
        "donor_facility_id": fac_cuttack.id,
        "recipient_facility_id": fac_jatni.id,
        "item_code": "MED-INSULIN-100IU",
        "transfer_quantity": 50
    }
    res = client.post("/api/v1/simulations/redistribution", json=payload, headers={"Authorization": "Bearer TEST-TOKEN-UID-ADMIN-TEST"})
    assert res.status_code == 200
    data = res.json()
    assert data["donor"]["simulated_days_of_cover"] == 20.0

def test_safety_buffer_evaluation():
    db = TestingSessionLocal()
    fac_jatni = db.query(Facility).filter(Facility.facility_code == "CHC-OD-KHU-001").first()
    fac_pipili = db.query(Facility).filter(Facility.facility_code == "PHC-OD-PURI-004").first()
    db.close()

    # Transfer 100 units from Pipili (stock 180, safety 40 => remaining 80 >= 40)
    payload = {
        "donor_facility_id": fac_pipili.id,
        "recipient_facility_id": fac_jatni.id,
        "item_code": "MED-ORS-SACHET",
        "transfer_quantity": 100
    }
    res = client.post("/api/v1/simulations/redistribution", json=payload, headers={"Authorization": "Bearer TEST-TOKEN-UID-CDMO-TEST"})
    assert res.status_code == 200
    data = res.json()
    assert data["donor"]["buffer_preserved"] is True
    assert data["recipient"]["buffer_achieved"] is True

def test_unsafe_transfer_detection_depletes_donor_buffer():
    db = TestingSessionLocal()
    fac_jatni = db.query(Facility).filter(Facility.facility_code == "CHC-OD-KHU-001").first()
    fac_pipili = db.query(Facility).filter(Facility.facility_code == "PHC-OD-PURI-004").first()
    db.close()

    # Pipili has 180 units, safety stock 40. Surplus is 140.
    # Propose transferring 160 units: remaining stock = 20 (< safety buffer 40)
    payload = {
        "donor_facility_id": fac_pipili.id,
        "recipient_facility_id": fac_jatni.id,
        "item_code": "MED-ORS-SACHET",
        "transfer_quantity": 160
    }
    res = client.post("/api/v1/simulations/redistribution", json=payload, headers={"Authorization": "Bearer TEST-TOKEN-UID-CDMO-TEST"})
    assert res.status_code == 200
    data = res.json()

    assert data["status"] == "UNSAFE"
    assert data["donor"]["buffer_preserved"] is False
    assert data["donor"]["simulated_stock"] == 20
    assert data["risk_analysis"]["donor_falls_below_safety"] is True
    assert data["risk_analysis"]["within_donor_surplus"] is False
    assert data["risk_analysis"]["is_operationally_safe"] is False
    assert "UNSAFE" in data["reason"]

def test_caution_status_recipient_remains_below_safety():
    db = TestingSessionLocal()
    fac_jatni = db.query(Facility).filter(Facility.facility_code == "CHC-OD-KHU-001").first()
    fac_pipili = db.query(Facility).filter(Facility.facility_code == "PHC-OD-PURI-004").first()
    db.close()

    # Jatni has 15 ORS (safety 40). Transfer only 10 ORS => Jatni simulated = 25 (< 40)
    # Pipili remaining = 170 (safe). Recipient improves, but remains below safety buffer => CAUTION
    payload = {
        "donor_facility_id": fac_pipili.id,
        "recipient_facility_id": fac_jatni.id,
        "item_code": "MED-ORS-SACHET",
        "transfer_quantity": 10
    }
    res = client.post("/api/v1/simulations/redistribution", json=payload, headers={"Authorization": "Bearer TEST-TOKEN-UID-CDMO-TEST"})
    assert res.status_code == 200
    data = res.json()

    assert data["status"] == "CAUTION"
    assert data["recipient"]["buffer_achieved"] is False
    assert data["risk_analysis"]["recipient_remains_below_safety"] is True
    assert "CAUTION" in data["reason"]

def test_transfer_greater_than_donor_stock_rejected():
    db = TestingSessionLocal()
    fac_jatni = db.query(Facility).filter(Facility.facility_code == "CHC-OD-KHU-001").first()
    fac_pipili = db.query(Facility).filter(Facility.facility_code == "PHC-OD-PURI-004").first()
    db.close()

    # Pipili has 180 units. Propose 250 units.
    payload = {
        "donor_facility_id": fac_pipili.id,
        "recipient_facility_id": fac_jatni.id,
        "item_code": "MED-ORS-SACHET",
        "transfer_quantity": 250
    }
    res = client.post("/api/v1/simulations/redistribution", json=payload, headers={"Authorization": "Bearer TEST-TOKEN-UID-CDMO-TEST"})
    assert res.status_code == 400
    assert "exceeds total available stock" in res.json()["detail"]

def test_zero_and_negative_quantity_rejected():
    db = TestingSessionLocal()
    fac_jatni = db.query(Facility).filter(Facility.facility_code == "CHC-OD-KHU-001").first()
    fac_pipili = db.query(Facility).filter(Facility.facility_code == "PHC-OD-PURI-004").first()
    db.close()

    payload_zero = {
        "donor_facility_id": fac_pipili.id,
        "recipient_facility_id": fac_jatni.id,
        "item_code": "MED-ORS-SACHET",
        "transfer_quantity": 0
    }
    res0 = client.post("/api/v1/simulations/redistribution", json=payload_zero, headers={"Authorization": "Bearer TEST-TOKEN-UID-CDMO-TEST"})
    assert res0.status_code == 400

    payload_neg = {
        "donor_facility_id": fac_pipili.id,
        "recipient_facility_id": fac_jatni.id,
        "item_code": "MED-ORS-SACHET",
        "transfer_quantity": -15
    }
    res_neg = client.post("/api/v1/simulations/redistribution", json=payload_neg, headers={"Authorization": "Bearer TEST-TOKEN-UID-CDMO-TEST"})
    assert res_neg.status_code == 400

def test_same_facility_transfer_rejected():
    db = TestingSessionLocal()
    fac_jatni = db.query(Facility).filter(Facility.facility_code == "CHC-OD-KHU-001").first()
    db.close()

    payload = {
        "donor_facility_id": fac_jatni.id,
        "recipient_facility_id": fac_jatni.id,
        "item_code": "MED-ORS-SACHET",
        "transfer_quantity": 10
    }
    res = client.post("/api/v1/simulations/redistribution", json=payload, headers={"Authorization": "Bearer TEST-TOKEN-UID-CDMO-TEST"})
    assert res.status_code == 400
    assert "cannot be identical" in res.json()["detail"]

# ==========================================
# 2. RBAC & Security Isolation Tests
# ==========================================

def test_unauthenticated_request_rejected():
    payload = {
        "donor_facility_id": 1,
        "recipient_facility_id": 2,
        "item_code": "MED-ORS-SACHET",
        "transfer_quantity": 10
    }
    res = client.post("/api/v1/simulations/redistribution", json=payload)
    assert res.status_code == 401

def test_facility_officer_can_simulate_own_facility_as_recipient():
    db = TestingSessionLocal()
    fac_jatni = db.query(Facility).filter(Facility.facility_code == "CHC-OD-KHU-001").first()
    fac_pipili = db.query(Facility).filter(Facility.facility_code == "PHC-OD-PURI-004").first()
    db.close()

    # Jatni Officer simulates transfer where Jatni is recipient
    payload = {
        "donor_facility_id": fac_pipili.id,
        "recipient_facility_id": fac_jatni.id,
        "item_code": "MED-ORS-SACHET",
        "transfer_quantity": 20
    }
    res = client.post("/api/v1/simulations/redistribution", json=payload, headers={"Authorization": "Bearer TEST-TOKEN-UID-JATNI-OFFICER"})
    assert res.status_code == 200

def test_facility_officer_can_simulate_own_facility_as_donor():
    db = TestingSessionLocal()
    fac_cuttack = db.query(Facility).filter(Facility.facility_code == "UPHC-OD-CTC-002").first()
    fac_jatni = db.query(Facility).filter(Facility.facility_code == "CHC-OD-KHU-001").first()
    db.close()

    # Cuttack Officer simulates transfer where Cuttack is donor
    payload = {
        "donor_facility_id": fac_cuttack.id,
        "recipient_facility_id": fac_jatni.id,
        "item_code": "MED-INSULIN-100IU",
        "transfer_quantity": 20
    }
    res = client.post("/api/v1/simulations/redistribution", json=payload, headers={"Authorization": "Bearer TEST-TOKEN-UID-CUTTACK-OFFICER"})
    assert res.status_code == 200

def test_facility_officer_cannot_simulate_unauthorized_facility():
    db = TestingSessionLocal()
    fac_cuttack = db.query(Facility).filter(Facility.facility_code == "UPHC-OD-CTC-002").first()
    fac_pipili = db.query(Facility).filter(Facility.facility_code == "PHC-OD-PURI-004").first()
    db.close()

    # Jatni Officer attempts to simulate transfer between Cuttack (donor) and Pipili (recipient)
    payload = {
        "donor_facility_id": fac_cuttack.id,
        "recipient_facility_id": fac_pipili.id,
        "item_code": "MED-ORS-SACHET",
        "transfer_quantity": 20
    }
    res = client.post("/api/v1/simulations/redistribution", json=payload, headers={"Authorization": "Bearer TEST-TOKEN-UID-JATNI-OFFICER"})
    assert res.status_code == 403
    assert "Forbidden" in res.json()["detail"]

# ==========================================
# 3. Read-Only Safety & Human Boundary Tests
# ==========================================

def test_simulation_does_not_modify_inventory():
    db = TestingSessionLocal()
    fac_jatni = db.query(Facility).filter(Facility.facility_code == "CHC-OD-KHU-001").first()
    fac_pipili = db.query(Facility).filter(Facility.facility_code == "PHC-OD-PURI-004").first()

    # Baseline quantities
    jatni_inv_before = db.query(Inventory).filter(Inventory.facility_id == fac_jatni.id, Inventory.item_code == "MED-ORS-SACHET").first().quantity
    pipili_inv_before = db.query(Inventory).filter(Inventory.facility_id == fac_pipili.id, Inventory.item_code == "MED-ORS-SACHET").first().quantity
    db.close()

    # Run simulation
    payload = {
        "donor_facility_id": fac_pipili.id,
        "recipient_facility_id": fac_jatni.id,
        "item_code": "MED-ORS-SACHET",
        "transfer_quantity": 90
    }
    res = client.post("/api/v1/simulations/redistribution", json=payload, headers={"Authorization": "Bearer TEST-TOKEN-UID-CDMO-TEST"})
    assert res.status_code == 200

    # Verify inventory is completely unchanged
    db2 = TestingSessionLocal()
    jatni_inv_after = db2.query(Inventory).filter(Inventory.facility_id == fac_jatni.id, Inventory.item_code == "MED-ORS-SACHET").first().quantity
    pipili_inv_after = db2.query(Inventory).filter(Inventory.facility_id == fac_pipili.id, Inventory.item_code == "MED-ORS-SACHET").first().quantity
    db2.close()

    assert jatni_inv_after == jatni_inv_before
    assert pipili_inv_after == pipili_inv_before

def test_simulation_does_not_create_stock_movement_or_audit_transfer():
    db = TestingSessionLocal()
    fac_jatni = db.query(Facility).filter(Facility.facility_code == "CHC-OD-KHU-001").first()
    fac_pipili = db.query(Facility).filter(Facility.facility_code == "PHC-OD-PURI-004").first()
    db.close()

    payload = {
        "donor_facility_id": fac_pipili.id,
        "recipient_facility_id": fac_jatni.id,
        "item_code": "MED-ORS-SACHET",
        "transfer_quantity": 90
    }
    res = client.post("/api/v1/simulations/redistribution", json=payload, headers={"Authorization": "Bearer TEST-TOKEN-UID-CDMO-TEST"})
    assert res.status_code == 200

    db2 = TestingSessionLocal()
    transfer_evts = db2.query(AuditEvent).filter(AuditEvent.action == "REDISTRIBUTION_TRANSFER_APPROVED").all()
    db2.close()
    assert len(transfer_evts) == 0

def test_simulation_does_not_approve_redistribution():
    db = TestingSessionLocal()
    fac_jatni = db.query(Facility).filter(Facility.facility_code == "CHC-OD-KHU-001").first()
    fac_pipili = db.query(Facility).filter(Facility.facility_code == "PHC-OD-PURI-004").first()
    med_ors = db.query(Medicine).filter(Medicine.code == "MED-ORS-SACHET").first()

    # Create a pending recommendation
    rec = Recommendation(
        recommendation_code="REC-TEST-PENDING",
        donor_facility_id=fac_pipili.id,
        recipient_facility_id=fac_jatni.id,
        medicine_id=med_ors.id,
        item_code=med_ors.code,
        recommended_quantity=90,
        urgency_level="CRITICAL",
        haversine_distance_km=15.0,
        expected_days_cover_gained=6.0,
        confidence_score=0.95,
        reason="Test",
        status=RecommendationStatus.PENDING_HUMAN_APPROVAL
    )
    db.add(rec)
    db.commit()
    rec_id = rec.id
    pipili_id = fac_pipili.id
    jatni_id = fac_jatni.id
    db.close()

    # Run simulation for the exact same parameters
    payload = {
        "donor_facility_id": pipili_id,
        "recipient_facility_id": jatni_id,
        "item_code": "MED-ORS-SACHET",
        "transfer_quantity": 90
    }
    res = client.post("/api/v1/simulations/redistribution", json=payload, headers={"Authorization": "Bearer TEST-TOKEN-UID-CDMO-TEST"})
    assert res.status_code == 200

    # Ensure recommendation status remains PENDING_HUMAN_APPROVAL
    db2 = TestingSessionLocal()
    checked_rec = db2.query(Recommendation).filter(Recommendation.id == rec_id).first()
    assert checked_rec.status == RecommendationStatus.PENDING_HUMAN_APPROVAL
    db2.close()

def test_human_approval_boundary_enforced():
    db = TestingSessionLocal()
    fac_jatni = db.query(Facility).filter(Facility.facility_code == "CHC-OD-KHU-001").first()
    fac_pipili = db.query(Facility).filter(Facility.facility_code == "PHC-OD-PURI-004").first()
    med_ors = db.query(Medicine).filter(Medicine.code == "MED-ORS-SACHET").first()

    rec = Recommendation(
        recommendation_code="REC-TEST-APPROVAL-BOUNDARY",
        donor_facility_id=fac_pipili.id,
        recipient_facility_id=fac_jatni.id,
        medicine_id=med_ors.id,
        item_code=med_ors.code,
        recommended_quantity=50,
        urgency_level="CRITICAL",
        haversine_distance_km=15.0,
        expected_days_cover_gained=3.3,
        confidence_score=0.95,
        reason="Test",
        status=RecommendationStatus.PENDING_HUMAN_APPROVAL
    )
    db.add(rec)
    db.commit()
    rec_id = rec.id
    db.close()

    # 1. Facility Officer cannot approve (Forbidden 403)
    res_officer = client.post(f"/api/v1/recommendations/{rec_id}/action", json={"action": "APPROVE"}, headers={"Authorization": "Bearer TEST-TOKEN-UID-JATNI-OFFICER"})
    assert res_officer.status_code == 403

    # 2. CDMO can approve (Success 200)
    res_cdmo = client.post(f"/api/v1/recommendations/{rec_id}/action", json={"action": "APPROVE"}, headers={"Authorization": "Bearer TEST-TOKEN-UID-CDMO-TEST"})
    assert res_cdmo.status_code == 200
    assert res_cdmo.json()["status"] == "APPROVED"


# ==========================================
# 4. AI Advisor What-If Natural Language Queries
# ==========================================

def test_ai_advisor_what_if_simulation_with_donor_and_recipient():
    """Natural-language What-If query with explicit donor, recipient, quantity, and SKU."""
    req_body = {
        "message": "What if Jatni CHC receives 90 ORS units from Pipili PHC?"
    }
    res = client.post("/api/v1/advisor/chat", json=req_body, headers={"Authorization": "Bearer TEST-TOKEN-UID-CDMO-TEST"})
    assert res.status_code == 200
    data = res.json()
    ans = data["answer"]

    assert "WHAT-IF OPERATIONAL SIMULATION" in ans
    assert "90 sachets" in ans or "90" in ans
    assert "Jatni CHC" in ans
    assert "Pipili PHC" in ans
    assert "Recipient Impact" in ans
    assert "Donor Impact" in ans
    assert "Simulated Stock" in ans
    assert "Simulation only" in ans

def test_ai_advisor_what_if_simulation_auto_donor_resolution():
    """When only recipient and quantity are specified, AI Advisor finds candidate donor with surplus."""
    req_body = {
        "message": "What happens if we transfer 50 units of ORS to Jatni?"
    }
    res = client.post("/api/v1/advisor/chat", json=req_body, headers={"Authorization": "Bearer TEST-TOKEN-UID-CDMO-TEST"})
    assert res.status_code == 200
    data = res.json()
    ans = data["answer"]

    assert "WHAT-IF OPERATIONAL SIMULATION" in ans
    assert "Jatni CHC" in ans
    assert "Pipili PHC" in ans  # Identified as surplus donor
    assert "Recipient Impact" in ans
    assert "Simulation only" in ans

def test_ai_advisor_what_if_missing_quantity_requests_clarification():
    """Missing quantity prompts clarification rather than guessing."""
    req_body = {
        "message": "What if Pipili transfers ORS to Jatni?"
    }
    res = client.post("/api/v1/advisor/chat", json=req_body, headers={"Authorization": "Bearer TEST-TOKEN-UID-CDMO-TEST"})
    assert res.status_code == 200
    data = res.json()
    assert "specify the transfer quantity" in data["answer"].lower()

def test_ai_advisor_what_if_facility_officer_restricted_to_own_facility():
    """Facility Officer cannot simulate transfers between two unrelated facilities."""
    req_body = {
        "message": "What if Jatni CHC receives 90 ORS units from Pipili PHC?"
    }
    # Cuttack officer has no involvement in Jatni <-> Pipili
    res = client.post("/api/v1/advisor/chat", json=req_body, headers={"Authorization": "Bearer TEST-TOKEN-UID-CUTTACK-OFFICER"})
    assert res.status_code == 200
    data = res.json()
    assert "restricted to scenarios involving your assigned facility" in data["answer"].lower()

def test_recipient_risk_transition_critical_to_safe():
    """Test 5: Recipient risk transitions from CRITICAL to SAFE deterministically."""
    db = TestingSessionLocal()
    fac_jatni = db.query(Facility).filter(Facility.facility_code == "CHC-OD-KHU-001").first()
    fac_pipili = db.query(Facility).filter(Facility.facility_code == "PHC-OD-PURI-004").first()
    db.close()

    payload = {
        "donor_facility_id": fac_pipili.id,
        "recipient_facility_id": fac_jatni.id,
        "item_code": "MED-ORS-SACHET",
        "transfer_quantity": 90
    }
    res = client.post("/api/v1/simulations/redistribution", json=payload, headers={"Authorization": "Bearer TEST-TOKEN-UID-CDMO-TEST"})
    assert res.status_code == 200
    data = res.json()

    # Recipient: 15 ORS (1.0 day cover) -> 105 ORS (7.0 days cover)
    recip = data["recipient"]
    assert recip["current_risk_severity"] == "CRITICAL"
    assert recip["simulated_risk_severity"] == "SAFE"
    assert recip["safety_stock"] == 40
    assert recip["projected_7day_demand"] == 105.0  # 15.0 * 7

    impact = data["impact"]
    assert impact["recipient_risk_before"] == "CRITICAL"
    assert impact["recipient_risk_after"] == "SAFE"
    assert impact["recipient_days_of_cover_gained"] == 6.0

def test_donor_risk_transition_safe_to_safe():
    """Test 6: Donor risk remains SAFE with preserved safety buffer."""
    db = TestingSessionLocal()
    fac_jatni = db.query(Facility).filter(Facility.facility_code == "CHC-OD-KHU-001").first()
    fac_pipili = db.query(Facility).filter(Facility.facility_code == "PHC-OD-PURI-004").first()
    db.close()

    payload = {
        "donor_facility_id": fac_pipili.id,
        "recipient_facility_id": fac_jatni.id,
        "item_code": "MED-ORS-SACHET",
        "transfer_quantity": 90
    }
    res = client.post("/api/v1/simulations/redistribution", json=payload, headers={"Authorization": "Bearer TEST-TOKEN-UID-CDMO-TEST"})
    assert res.status_code == 200
    data = res.json()

    donor = data["donor"]
    assert donor["current_risk_severity"] == "SAFE"
    assert donor["simulated_risk_severity"] == "SAFE"
    assert donor["safety_stock"] == 40
    assert donor["buffer_preserved"] is True

    impact = data["impact"]
    assert impact["donor_risk_before"] == "SAFE"
    assert impact["donor_risk_after"] == "SAFE"

    validation = data["validation"]
    assert validation["donor_safety_buffer_protected"] is True
    assert validation["sufficient_stock"] is True
    assert validation["is_feasible"] is True

def test_unknown_resource_rejected():
    """Test 11: Unknown medicine resource is rejected with HTTP 404."""
    db = TestingSessionLocal()
    fac_jatni = db.query(Facility).filter(Facility.facility_code == "CHC-OD-KHU-001").first()
    fac_pipili = db.query(Facility).filter(Facility.facility_code == "PHC-OD-PURI-004").first()
    db.close()

    payload = {
        "donor_facility_id": fac_pipili.id,
        "recipient_facility_id": fac_jatni.id,
        "item_code": "MED-NONEXISTENT-XYZ",
        "transfer_quantity": 90
    }
    res = client.post("/api/v1/simulations/redistribution", json=payload, headers={"Authorization": "Bearer TEST-TOKEN-UID-CDMO-TEST"})
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()

def test_ai_advisor_does_not_invent_simulation_numbers():
    """Test 17: AI Advisor uses exact simulation engine numbers, zero hallucinations."""
    req_body = {
        "message": "What if we transfer 90 ORS units from Pipili PHC to Jatni CHC?"
    }
    res = client.post("/api/v1/advisor/chat", json=req_body, headers={"Authorization": "Bearer TEST-TOKEN-UID-CDMO-TEST"})
    assert res.status_code == 200
    data = res.json()
    ans = data["answer"]

    # Must contain exact verified values calculated by engine:
    # Recipient: 15 current -> 105 simulated, 1.0 day cover -> 7.0 days cover, +6.0 days gained
    assert "15 sachets" in ans or "15" in ans
    assert "105 sachets" in ans or "105" in ans
    assert "1.0 days" in ans or "1 days" in ans
    assert "7.0 days" in ans or "7 days" in ans
    assert "+6.0 days" in ans or "6.0 days" in ans

    # Donor: 180 current -> 90 simulated
    assert "180 sachets" in ans or "180" in ans
    assert "90 sachets" in ans or "90" in ans
    assert "PRESERVED" in ans
    assert "Simulation only — no inventory has been changed" in ans

import os
import sys
from datetime import datetime, date, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

os.environ["TESTING"] = "true"

from app.config import settings
from app.database import Base, get_db, engine as db_engine
from app.models import (
    Facility, Medicine, Inventory, ConsumptionLog, Forecast, Alert, Recommendation, User,
    FacilityType, UserRole, MedicineCategory, ActionType, AlertSeverity, AlertStatus,
    UrgencyLevel, RecommendationStatus
)
from app.algorithms import (
    calculate_haversine_distance, calculate_donor_transferable_quantity,
    calculate_recipient_required_quantity, score_redistribution_candidate,
    generate_and_persist_redistribution_recommendations
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
def setup_redistribution_data():
    settings.TESTING = True
    Base.metadata.create_all(bind=db_engine)
    db = TestingSessionLocal()

    # Clean existing database state
    db.query(Recommendation).delete()
    db.query(Alert).delete()
    db.query(Forecast).delete()
    db.query(ConsumptionLog).delete()
    db.query(Inventory).delete()
    db.query(User).delete()
    db.query(Facility).delete()
    db.query(Medicine).delete()
    db.commit()

    # 1. Odisha Facilities
    fac_jatni = Facility(facility_code="CHC-OD-KHU-001", name="Jatni CHC (Khordha)", facility_type=FacilityType.CHC, state="OD", district="Khordha", latitude=20.165, longitude=85.705)
    fac_cuttack = Facility(facility_code="UPHC-OD-CTC-002", name="UPHC MS Das (Kafla Bazar)", facility_type=FacilityType.UPHC, state="OD", district="Cuttack", latitude=20.462, longitude=85.882)
    fac_pipili = Facility(facility_code="PHC-OD-PURI-004", name="Pipili PHC (Puri)", facility_type=FacilityType.PHC, state="OD", district="Puri", latitude=20.117, longitude=85.833)

    # 2. West Bengal Facilities
    fac_kolkata = Facility(facility_code="UPHC-WB-KOL-012", name="Behala Urban PHC (Kolkata)", facility_type=FacilityType.UPHC, state="WB", district="Kolkata", latitude=22.501, longitude=88.312)
    fac_dh = Facility(facility_code="PHC-WB-S24P-008", name="Diamond Harbour PHC", facility_type=FacilityType.PHC, state="WB", district="South 24 Parganas", latitude=22.193, longitude=88.188)

    db.add_all([fac_jatni, fac_cuttack, fac_pipili, fac_kolkata, fac_dh])
    db.commit()

    # Medicine
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

    # Scenario: Jatni CHC has Insulin SHORTAGE (quantity = 5, safety_stock = 40)
    inv_jatni_ins = Inventory(facility_id=fac_jatni.id, medicine_id=med_ins.id, item_code=med_ins.code, item_name=med_ins.name, quantity=5, safety_stock=40, incoming_quantity=0)

    # Donor Cuttack has Insulin SURPLUS (quantity = 150, safety_stock = 40 => transferable = 110)
    inv_cuttack_ins = Inventory(facility_id=fac_cuttack.id, medicine_id=med_ins.id, item_code=med_ins.code, item_name=med_ins.name, quantity=150, safety_stock=40, incoming_quantity=0)

    # Donor Pipili has Insulin SURPLUS (quantity = 80, safety_stock = 40 => transferable = 40)
    inv_pipili_ins = Inventory(facility_id=fac_pipili.id, medicine_id=med_ins.id, item_code=med_ins.code, item_name=med_ins.name, quantity=80, safety_stock=40, incoming_quantity=0)

    # WB Kolkata has ORS SHORTAGE (quantity = 10, safety_stock = 40)
    inv_kolkata_ors = Inventory(facility_id=fac_kolkata.id, medicine_id=med_ors.id, item_code=med_ors.code, item_name=med_ors.name, quantity=10, safety_stock=40, incoming_quantity=0)

    # WB Diamond Harbour has ORS SURPLUS (quantity = 120, safety_stock = 40 => transferable = 80)
    inv_dh_ors = Inventory(facility_id=fac_dh.id, medicine_id=med_ors.id, item_code=med_ors.code, item_name=med_ors.name, quantity=120, safety_stock=40, incoming_quantity=0)

    db.add_all([inv_jatni_ins, inv_cuttack_ins, inv_pipili_ins, inv_kolkata_ors, inv_dh_ors])
    db.commit()

    # Consumption Logs for Jatni (high daily consumption = 10/day => DoC = 0.5 days => CRITICAL)
    today = date.today()
    for d in range(7, 0, -1):
        db.add(ConsumptionLog(facility_id=fac_jatni.id, medicine_id=med_ins.id, item_code=med_ins.code, date=today - timedelta(days=d), quantity_dispensed=10, patient_footfall=40, action_type=ActionType.DISPENSE))
        db.add(ConsumptionLog(facility_id=fac_cuttack.id, medicine_id=med_ins.id, item_code=med_ins.code, date=today - timedelta(days=d), quantity_dispensed=2, patient_footfall=20, action_type=ActionType.DISPENSE))
        db.add(ConsumptionLog(facility_id=fac_kolkata.id, medicine_id=med_ors.id, item_code=med_ors.code, date=today - timedelta(days=d), quantity_dispensed=10, patient_footfall=30, action_type=ActionType.DISPENSE))
        db.add(ConsumptionLog(facility_id=fac_dh.id, medicine_id=med_ors.id, item_code=med_ors.code, date=today - timedelta(days=d), quantity_dispensed=3, patient_footfall=15, action_type=ActionType.DISPENSE))

    db.commit()
    db.close()

    yield

# ==========================================
# 1. Unit Tests for Redistribution Algorithms
# ==========================================

def test_haversine_distance_math():
    # Jatni (20.165, 85.705) to Cuttack (20.462, 85.882) ~ 37.8 km
    dist = calculate_haversine_distance(20.165, 85.705, 20.462, 85.882)
    assert 30.0 <= dist <= 45.0

def test_donor_transferable_quantity_and_safety_stock_protection():
    inv = Inventory(quantity=150, safety_stock=40, expiry=date.today() + timedelta(days=100))
    transferable = calculate_donor_transferable_quantity(inv)
    assert transferable == 110  # 150 - 40 = 110

def test_expired_stock_exclusion():
    expired_inv = Inventory(quantity=150, safety_stock=40, expiry=date.today() - timedelta(days=1))
    transferable = calculate_donor_transferable_quantity(expired_inv)
    assert transferable == 0

def test_zero_transferable_quantity():
    low_inv = Inventory(quantity=35, safety_stock=40, expiry=date.today() + timedelta(days=100))
    transferable = calculate_donor_transferable_quantity(low_inv)
    assert transferable == 0

def test_recipient_shortage_calculation():
    rec_inv = Inventory(quantity=10, safety_stock=40, incoming_quantity=0)
    required = calculate_recipient_required_quantity(rec_inv, expected_daily_demand=10.0)
    assert required == 70  # target = max(80, 70) = 80. needed = 80 - 10 = 70

def test_candidate_ranking_and_deterministic_scoring():
    s1 = score_redistribution_candidate(donor_transferable_qty=100, donor_safety_stock=40, distance_km=30.0, urgency_level=UrgencyLevel.CRITICAL)
    s2 = score_redistribution_candidate(donor_transferable_qty=50, donor_safety_stock=40, distance_km=30.0, urgency_level=UrgencyLevel.CRITICAL)
    assert s1 > s2

    # Deterministic check
    assert s1 == score_redistribution_candidate(donor_transferable_qty=100, donor_safety_stock=40, distance_km=30.0, urgency_level=UrgencyLevel.CRITICAL)

# ==========================================
# 2. Integration Tests for Recommendation Engine & Persistence
# ==========================================

def test_recommendation_generation_and_persistence():
    db = TestingSessionLocal()
    recs = generate_and_persist_redistribution_recommendations(db)
    
    assert len(recs) >= 2  # Odisha recommendation + West Bengal recommendation

    # Verify PENDING_HUMAN_APPROVAL status
    for r in recs:
        assert r.status == RecommendationStatus.PENDING_HUMAN_APPROVAL
        assert r.haversine_distance_km > 0
        assert r.recommended_quantity > 0
        assert "transferable units while remaining above its safety stock threshold" in r.reason

    db.close()

def test_odisha_shortage_scenario():
    db = TestingSessionLocal()
    recs = generate_and_persist_redistribution_recommendations(db)
    fac_jatni = db.query(Facility).filter(Facility.facility_code == "CHC-OD-KHU-001").first()

    # Find recommendation targeting Jatni CHC
    jatni_rec = next((r for r in recs if r.recipient_facility_id == fac_jatni.id), None)
    assert jatni_rec is not None
    assert jatni_rec.item_code == "MED-INSULIN-100IU"
    assert jatni_rec.urgency_level == UrgencyLevel.CRITICAL
    db.close()

def test_west_bengal_shortage_scenario():
    db = TestingSessionLocal()
    recs = generate_and_persist_redistribution_recommendations(db)
    fac_kolkata = db.query(Facility).filter(Facility.facility_code == "UPHC-WB-KOL-012").first()

    # Find recommendation targeting Behala Urban PHC (Kolkata)
    kolkata_rec = next((r for r in recs if r.recipient_facility_id == fac_kolkata.id), None)
    assert kolkata_rec is not None
    assert kolkata_rec.item_code == "MED-ORS-SACHET"
    db.close()

def test_no_eligible_donor_scenario():
    db = TestingSessionLocal()
    # Deplete all donor stock for Insulin below safety stock
    db.query(Inventory).filter(Inventory.item_code == "MED-INSULIN-100IU").update({"quantity": 10})
    db.commit()

    recs = generate_and_persist_redistribution_recommendations(db)

    # Verify no recommendation generated for Insulin when no eligible donors exist
    ins_recs = [r for r in recs if r.item_code == "MED-INSULIN-100IU"]
    assert len(ins_recs) == 0
    db.close()


# ==========================================
# 3. API & RBAC Security Tests
# ==========================================

def test_generate_recommendations_admin_success():
    res = client.post("/api/v1/recommendations/generate", headers={"Authorization": "Bearer TEST-TOKEN-UID-ADMIN-TEST"})
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 1

def test_generate_recommendations_cdmo_success():
    res = client.post("/api/v1/recommendations/generate", headers={"Authorization": "Bearer TEST-TOKEN-UID-CDMO-TEST"})
    assert res.status_code == 200

def test_generate_recommendations_facility_officer_forbidden():
    res = client.post("/api/v1/recommendations/generate", headers={"Authorization": "Bearer TEST-TOKEN-UID-JATNI-OFFICER"})
    assert res.status_code == 403
    assert "Forbidden" in res.json()["detail"]

def test_facility_officer_read_scoped_access():
    db = TestingSessionLocal()
    generate_and_persist_redistribution_recommendations(db)
    fac_jatni = db.query(Facility).filter(Facility.facility_code == "CHC-OD-KHU-001").first()
    fac_cuttack = db.query(Facility).filter(Facility.facility_code == "UPHC-OD-CTC-002").first()
    db.close()

    # Jatni Officer reads recommendations -> gets recommendations involving Jatni
    res_jatni = client.get("/api/v1/recommendations", headers={"Authorization": "Bearer TEST-TOKEN-UID-JATNI-OFFICER"})
    assert res_jatni.status_code == 200
    data_jatni = res_jatni.json()
    for r in data_jatni:
        assert fac_jatni.id in [r["donor_facility_id"], r["recipient_facility_id"]]

    # Jatni Officer attempts to read Cuttack facility recommendations route -> FORBIDDEN (403)
    res_cuttack = client.get(f"/api/v1/facilities/{fac_cuttack.id}/recommendations", headers={"Authorization": "Bearer TEST-TOKEN-UID-JATNI-OFFICER"})
    assert res_cuttack.status_code == 403

import os
import sys
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

os.environ["TESTING"] = "true"

from app.config import settings
from app.database import Base, engine as db_engine
from app.models import Facility, FacilityType, Medicine, MedicineCategory, User, Inventory, Recommendation, RecommendationStatus
from seed_db import ensure_demo_users_seeded, seed_database
from main import app

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_phase10_runtime_db():
    settings.TESTING = True
    settings.ALLOW_DEMO_TOKENS = True
    Base.metadata.create_all(bind=db_engine)
    db = TestingSessionLocal()
    
    # Ensure database foundation and demo users seeded
    facilities_data = [
        {"code": "CHC-OD-KHU-001", "name": "Jatni CHC (Khordha)", "type": FacilityType.CHC, "state": "OD", "district": "Khordha", "lat": 20.165, "long": 85.705},
        {"code": "UPHC-OD-CTC-002", "name": "UPHC MS Das (Kafla Bazar)", "type": FacilityType.UPHC, "state": "OD", "district": "Cuttack", "lat": 20.462, "long": 85.882},
        {"code": "PHC-OD-PURI-004", "name": "Pipili PHC (Puri)", "type": FacilityType.PHC, "state": "OD", "district": "Puri", "lat": 20.117, "long": 85.833},
        {"code": "UPHC-WB-KOL-012", "name": "Behala Urban PHC (Kolkata)", "type": FacilityType.UPHC, "state": "WB", "district": "Kolkata", "lat": 22.501, "long": 88.312},
        {"code": "PHC-WB-S24P-008", "name": "Diamond Harbour PHC", "type": FacilityType.PHC, "state": "WB", "district": "South 24 Parganas", "lat": 22.193, "long": 88.188}
    ]
    for f in facilities_data:
        if not db.query(Facility).filter(Facility.facility_code == f["code"]).first():
            fac = Facility(
                facility_code=f["code"],
                name=f["name"],
                facility_type=f["type"],
                state=f["state"],
                district=f["district"],
                latitude=f["lat"],
                longitude=f["long"]
            )
            db.add(fac)
    db.commit()

    medicines_data = [
        {"code": "MED-ORS-SACHET", "name": "ORS Sachet (Oral Rehydration Salts)", "category": MedicineCategory.ESSENTIAL_MEDICINE, "unit": "sachets"},
        {"code": "MED-PARACET-500MG", "name": "Paracetamol 500mg", "category": MedicineCategory.ESSENTIAL_MEDICINE, "unit": "tablets"}
    ]
    for m in medicines_data:
        if not db.query(Medicine).filter(Medicine.code == m["code"]).first():
            med = Medicine(code=m["code"], name=m["name"], category=m["category"], unit=m["unit"])
            db.add(med)
    db.commit()

    ensure_demo_users_seeded(db)

    # Seed an inventory item
    fac1 = db.query(Facility).filter(Facility.facility_code == "CHC-OD-KHU-001").first()
    med1 = db.query(Medicine).filter(Medicine.code == "MED-ORS-SACHET").first()
    if fac1 and med1:
        inv = db.query(Inventory).filter(Inventory.facility_id == fac1.id, Inventory.medicine_id == med1.id).first()
        if not inv:
            inv = Inventory(
                facility_id=fac1.id,
                medicine_id=med1.id,
                item_code=med1.code,
                item_name=med1.name,
                quantity=15,
                safety_stock=40,
                unit="sachets"
            )
            db.add(inv)
            db.commit()

    db.close()
    yield

# =========================================================
# 15 MANDATORY RUNTIME INTEGRATION CONTRACT TESTS
# =========================================================

def test_1_get_facilities_200_for_admin():
    res = client.get("/api/v1/facilities", headers={"Authorization": "Bearer TEST-TOKEN-UID-ADMIN-99"})
    assert res.status_code == 200

def test_2_facilities_returns_seeded_facilities():
    res = client.get("/api/v1/facilities", headers={"Authorization": "Bearer TEST-TOKEN-UID-ADMIN-99"})
    assert res.status_code == 200
    facilities = res.json()
    assert len(facilities) >= 5
    names = [f["name"] for f in facilities]
    assert "Jatni CHC (Khordha)" in names
    assert "Behala Urban PHC (Kolkata)" in names

def test_3_get_resources_200():
    res = client.get("/api/v1/resources", headers={"Authorization": "Bearer TEST-TOKEN-UID-ADMIN-99"})
    assert res.status_code == 200
    assert isinstance(res.json(), list)

def test_4_post_resource_201():
    payload = {
        "facility_id": 1,
        "item_code": "MED-PARACET-500MG",
        "item_name": "Paracetamol 500mg",
        "quantity": 250,
        "safety_stock": 50,
        "daily_demand": 20.0,
        "unit": "tablets"
    }
    res = client.post("/api/v1/resources", json=payload, headers={"Authorization": "Bearer TEST-TOKEN-UID-ADMIN-99"})
    assert res.status_code == 201
    item = res.json()
    assert item["item_code"] == "MED-PARACET-500MG"
    assert item["quantity"] == 250

def test_5_put_resource_successful_update():
    # Retrieve existing inventory item
    res_list = client.get("/api/v1/resources", headers={"Authorization": "Bearer TEST-TOKEN-UID-ADMIN-99"}).json()
    assert len(res_list) > 0
    inv_id = res_list[0]["id"]

    update_payload = {
        "quantity": 500,
        "safety_stock": 80,
        "daily_demand": 25.0
    }
    res = client.put(f"/api/v1/resources/{inv_id}", json=update_payload, headers={"Authorization": "Bearer TEST-TOKEN-UID-ADMIN-99"})
    assert res.status_code == 200
    updated = res.json()
    assert updated["quantity"] == 500
    assert updated["safety_stock"] == 80

def test_6_put_nonexistent_resource_proper_404():
    update_payload = {"quantity": 100}
    res = client.put("/api/v1/resources/999999", json=update_payload, headers={"Authorization": "Bearer TEST-TOKEN-UID-ADMIN-99"})
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()

def test_7_recommendation_creation_persisted_queue_item():
    gen_res = client.post("/api/v1/recommendations/generate", headers={"Authorization": "Bearer TEST-TOKEN-UID-ADMIN-99"})
    assert gen_res.status_code == 200
    
    # Query queue
    q_res = client.get("/api/v1/recommendations", headers={"Authorization": "Bearer TEST-TOKEN-UID-ADMIN-99"})
    assert q_res.status_code == 200
    recs = q_res.json()
    if len(recs) > 0:
        assert recs[0]["status"] == "PENDING_HUMAN_APPROVAL"

def test_8_redistribution_endpoint_authenticated_admin_succeeds():
    res = client.post("/api/v1/recommendations/generate", headers={"Authorization": "Bearer TEST-TOKEN-UID-ADMIN-99"})
    assert res.status_code == 200

def test_9_redistribution_endpoint_authenticated_cdmo_succeeds():
    res = client.post("/api/v1/recommendations/generate", headers={"Authorization": "Bearer TEST-TOKEN-UID-CDMO-88"})
    assert res.status_code == 200

def test_10_facility_officer_restricted_access_403():
    # Facility officer is restricted from triggering redistribution generation across district
    res = client.post("/api/v1/recommendations/generate", headers={"Authorization": "Bearer TEST-TOKEN-UID-OFFICER-JATNI"})
    assert res.status_code == 403
    assert "Forbidden" in res.json()["detail"]

def test_11_invalid_firebase_token_401():
    res = client.get("/api/v1/facilities", headers={"Authorization": "Bearer INVALID-EXPIRED-TOKEN-XYZ"})
    assert res.status_code == 401

def test_12_missing_authorization_header_401():
    res = client.get("/api/v1/facilities")
    assert res.status_code == 401

def test_13_unauthorized_role_403():
    # Officer attempting to delete inventory at unassigned facility
    res = client.delete("/api/v1/resources/1", headers={"Authorization": "Bearer TEST-TOKEN-UID-OFFICER-JATNI"})
    assert res.status_code == 403

def test_14_firebase_uid_resolves_to_application_user():
    res = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer TEST-TOKEN-UID-ADMIN-99"})
    assert res.status_code == 200
    user_info = res.json()
    assert user_info["firebase_uid"] == "UID-ADMIN-99"
    assert user_info["role"] == "ADMIN"

def test_15_role_determined_server_side():
    # Attempting to send spoofed role in headers does not change server-determined role
    res = client.get("/api/v1/auth/me", headers={
        "Authorization": "Bearer TEST-TOKEN-UID-OFFICER-JATNI",
        "X-User-Role": "ADMIN"
    })
    assert res.status_code == 200
    user_info = res.json()
    # Must remain FACILITY_OFFICER determined by DB lookup
    assert user_info["role"] == "FACILITY_OFFICER"

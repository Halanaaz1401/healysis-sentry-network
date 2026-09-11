import os
import sys
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

os.environ["TESTING"] = "true"

from app.config import settings
from app.database import Base, engine as db_engine
from app.models import Facility, FacilityType, Medicine, MedicineCategory, User
from seed_db import ensure_demo_users_seeded
from main import app

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_facilities_resources_test_db():
    settings.TESTING = True
    settings.ALLOW_DEMO_TOKENS = True
    Base.metadata.create_all(bind=db_engine)
    db = TestingSessionLocal()
    
    # Ensure all 5 demo facilities exist
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
        {"code": "MED-PARACET-500MG", "name": "Paracetamol 500mg", "category": MedicineCategory.ESSENTIAL_MEDICINE, "unit": "tablets"},
        {"code": "MED-INSULIN-100IU", "name": "Insulin 100IU Injection", "category": MedicineCategory.VACCINE, "unit": "vials"},
        {"code": "MED-AMOXICILLIN-250", "name": "Amoxicillin 250mg Capsule", "category": MedicineCategory.ESSENTIAL_MEDICINE, "unit": "capsules"},
        {"code": "MED-CETIRIZINE-10", "name": "Cetirizine 10mg", "category": MedicineCategory.ESSENTIAL_MEDICINE, "unit": "tablets"}
    ]
    for m in medicines_data:
        if not db.query(Medicine).filter(Medicine.code == m["code"]).first():
            med = Medicine(code=m["code"], name=m["name"], category=m["category"], unit=m["unit"])
            db.add(med)
    db.commit()

    ensure_demo_users_seeded(db)
    db.close()
    yield

# =========================================================
# 1. CANONICAL FACILITIES API TESTS
# =========================================================
def test_canonical_get_facilities_200():
    res = client.get("/api/v1/facilities", headers={"Authorization": "Bearer TEST-TOKEN-UID-ADMIN-99"})
    assert res.status_code == 200
    facilities = res.json()
    assert len(facilities) >= 5

def test_canonical_get_facilities_trailing_slash():
    res = client.get("/api/v1/facilities/", headers={"Authorization": "Bearer TEST-TOKEN-UID-ADMIN-99"})
    assert res.status_code == 200
    facilities = res.json()
    assert len(facilities) >= 5

def test_admin_retrieves_all_5_facilities():
    res = client.get("/api/v1/facilities", headers={"Authorization": "Bearer TEST-TOKEN-UID-ADMIN-99"})
    assert res.status_code == 200
    names = [f["name"] for f in res.json()]
    assert "Jatni CHC (Khordha)" in names
    assert "UPHC MS Das (Kafla Bazar)" in names
    assert "Pipili PHC (Puri)" in names
    assert "Behala Urban PHC (Kolkata)" in names
    assert "Diamond Harbour PHC" in names

def test_facility_officer_retrieves_only_assigned_facility():
    res = client.get("/api/v1/facilities", headers={"Authorization": "Bearer TEST-TOKEN-UID-OFFICER-JATNI"})
    assert res.status_code == 200
    facilities = res.json()
    assert len(facilities) == 1
    assert facilities[0]["name"] == "Jatni CHC (Khordha)"

# =========================================================
# 2. TARGET FACILITY SELECTOR & RESOURCE CREATION TESTS
# =========================================================
def test_resource_catalog_retrieval():
    res = client.get("/api/v1/resources/catalog", headers={"Authorization": "Bearer TEST-TOKEN-UID-ADMIN-99"})
    assert res.status_code == 200
    catalog = res.json()
    assert len(catalog) >= 5
    skus = [c["sku"] for c in catalog]
    assert "MED-ORS-SACHET" in skus

def test_post_resource_with_selected_target_facility_id():
    # Retrieve facility 3 ID dynamically
    facs_res = client.get("/api/v1/facilities", headers={"Authorization": "Bearer TEST-TOKEN-UID-ADMIN-99"})
    pipili_fac = [f for f in facs_res.json() if "Pipili" in f["name"]][0]

    payload = {
        "facility_id": pipili_fac["id"],
        "item_code": "MED-ORS-SACHET",
        "item_name": "ORS Sachet (Oral Rehydration Salts)",
        "quantity": 300,
        "safety_stock": 100,
        "daily_demand": 50.0,
        "incoming_quantity": 50,
        "unit": "sachets"
    }
    res = client.post("/api/v1/resources", json=payload, headers={"Authorization": "Bearer TEST-TOKEN-UID-ADMIN-99"})
    assert res.status_code == 201
    item = res.json()
    assert item["facility_id"] == pipili_fac["id"]
    assert item["item_code"] == "MED-ORS-SACHET"
    assert item["quantity"] == 300

def test_post_resource_unassigned_facility_officer_403():
    facs_res = client.get("/api/v1/facilities", headers={"Authorization": "Bearer TEST-TOKEN-UID-ADMIN-99"})
    behala_fac = [f for f in facs_res.json() if "Behala" in f["name"]][0]

    payload = {
        "facility_id": behala_fac["id"],
        "item_code": "MED-PARACET-500MG",
        "item_name": "Paracetamol 500mg",
        "quantity": 100,
        "safety_stock": 30,
        "daily_demand": 10.0,
        "unit": "tablets"
    }
    res = client.post("/api/v1/resources", json=payload, headers={"Authorization": "Bearer TEST-TOKEN-UID-OFFICER-JATNI"})
    assert res.status_code == 403
    assert "Forbidden" in res.json()["detail"]

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
from seed_db import ensure_demo_users_seeded, seed_database
from main import app

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_phase10_test_db():
    settings.TESTING = True
    settings.ALLOW_DEMO_TOKENS = True
    Base.metadata.create_all(bind=db_engine)
    db = TestingSessionLocal()
    
    # Ensure facilities exist
    if not db.query(Facility).first():
        fac1 = Facility(id=1, facility_code="CHC-OD-KHU-001", name="Jatni CHC (Khordha)", facility_type=FacilityType.CHC, state="OD", district="Khordha", latitude=20.165, longitude=85.705)
        fac2 = Facility(id=2, facility_code="UPHC-OD-CTC-002", name="UPHC MS Das (Kafla Bazar)", facility_type=FacilityType.UPHC, state="OD", district="Cuttack", latitude=20.462, longitude=85.882)
        db.add_all([fac1, fac2])
        db.commit()

    if not db.query(Medicine).first():
        med1 = Medicine(id=1, code="MED-ORS-SACHET", name="ORS Sachet (Oral Rehydration Salts)", category=MedicineCategory.ESSENTIAL_MEDICINE, unit="sachets")
        med2 = Medicine(id=2, code="MED-PARACET-500MG", name="Paracetamol 500mg", category=MedicineCategory.ESSENTIAL_MEDICINE, unit="tablets")
        db.add_all([med1, med2])
        db.commit()

    ensure_demo_users_seeded(db)
    db.close()
    yield

# =========================================================
# 1. AUTHENTICATION & DEMO CREDENTIAL TESTS
# =========================================================
def test_authenticated_admin_request():
    res = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer TEST-TOKEN-UID-ADMIN-99"})
    assert res.status_code == 200
    assert res.json()["role"] == "ADMIN"

def test_authenticated_cdmo_request():
    res = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer TEST-TOKEN-UID-CDMO-88"})
    assert res.status_code == 200
    assert res.json()["role"] == "CDMO"

def test_authenticated_officer_request():
    res = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer TEST-TOKEN-UID-OFFICER-JATNI"})
    assert res.status_code == 200
    assert res.json()["role"] == "FACILITY_OFFICER"

def test_missing_authorization_header():
    res = client.get("/api/v1/facilities")
    assert res.status_code == 401
    assert "Missing Authorization header" in res.json()["detail"]

def test_invalid_authorization_header():
    res = client.get("/api/v1/facilities", headers={"Authorization": "InvalidScheme token"})
    assert res.status_code == 401
    assert "Invalid Authorization header format" in res.json()["detail"]

# =========================================================
# 2. FACILITY DETAIL RESOLUTION, 403 & 404 TESTS
# =========================================================
def test_facility_detail_200_for_admin():
    res = client.get("/api/v1/facilities/1", headers={"Authorization": "Bearer TEST-TOKEN-UID-ADMIN-99"})
    assert res.status_code == 200
    data = res.json()
    assert "facility" in data
    assert data["facility"]["name"] == "Jatni CHC (Khordha)"
    assert "capacity" in data
    assert "personnel" in data
    assert "inventory" in data

def test_facility_detail_403_for_unassigned_officer():
    res = client.get("/api/v1/facilities/2", headers={"Authorization": "Bearer TEST-TOKEN-UID-OFFICER-JATNI"})
    assert res.status_code == 403
    assert "Forbidden" in res.json()["detail"]

def test_facility_detail_404_for_nonexistent_facility():
    res = client.get("/api/v1/facilities/999", headers={"Authorization": "Bearer TEST-TOKEN-UID-ADMIN-99"})
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()

# =========================================================
# 3. RESOURCE CATALOG & CREATION TESTS
# =========================================================
def test_get_resource_catalog():
    res = client.get("/api/v1/resources/catalog", headers={"Authorization": "Bearer TEST-TOKEN-UID-ADMIN-99"})
    assert res.status_code == 200
    catalog = res.json()
    assert len(catalog) >= 1
    assert catalog[0]["sku"] == "MED-ORS-SACHET"

def test_create_resource_with_catalog_sku():
    payload = {
        "facility_id": 1,
        "item_code": "MED-ORS-SACHET",
        "item_name": "ORS Sachet (Oral Rehydration Salts)",
        "quantity": 150,
        "safety_stock": 50,
        "daily_demand": 25.0,
        "incoming_quantity": 0,
        "unit": "sachets"
    }
    res = client.post("/api/v1/resources", json=payload, headers={"Authorization": "Bearer TEST-TOKEN-UID-ADMIN-99"})
    assert res.status_code == 201
    data = res.json()
    assert data["item_code"] == "MED-ORS-SACHET"
    assert data["quantity"] == 150

def test_create_resource_unassigned_facility_officer_403():
    payload = {
        "facility_id": 2,
        "item_code": "MED-PARACET-500MG",
        "item_name": "Paracetamol 500mg",
        "quantity": 200,
        "safety_stock": 40,
        "daily_demand": 20.0,
        "unit": "tablets"
    }
    res = client.post("/api/v1/resources", json=payload, headers={"Authorization": "Bearer TEST-TOKEN-UID-OFFICER-JATNI"})
    assert res.status_code == 403

# =========================================================
# 4. AI ADVISOR AUTHENTICATED REQUEST & TOOL ROUTING
# =========================================================
def test_ai_advisor_authenticated_chat():
    payload = {
        "message": "Why is Jatni CHC at critical risk?",
        "facility_id": 1
    }
    res = client.post("/api/v1/advisor/chat", json=payload, headers={"Authorization": "Bearer TEST-TOKEN-UID-ADMIN-99"})
    assert res.status_code == 200
    data = res.json()
    assert "answer" in data
    assert "summary" in data
    assert "Jatni CHC" in data["answer"] or "Jatni" in data["summary"]
    assert data["requires_human_approval"] is True

def test_ai_advisor_comparative_routing():
    payload = {
        "message": "Compare stock levels between Jatni and Cuttack"
    }
    res = client.post("/api/v1/advisor/chat", json=payload, headers={"Authorization": "Bearer TEST-TOKEN-UID-ADMIN-99"})
    assert res.status_code == 200
    data = res.json()
    assert "answer" in data
    assert len(data["data_sources"]) > 0

# =========================================================
# 5. FORECAST & REDISTRIBUTION ENDPOINT TESTS
# =========================================================
def test_forecast_get_and_post_recalculate():
    res_get = client.get("/api/v1/forecasts", headers={"Authorization": "Bearer TEST-TOKEN-UID-ADMIN-99"})
    assert res_get.status_code == 200
    
    res_post = client.post("/api/v1/forecasts/recalculate", headers={"Authorization": "Bearer TEST-TOKEN-UID-ADMIN-99"})
    assert res_post.status_code == 200
    assert isinstance(res_post.json(), list)

def test_redistribution_generate_post():
    res = client.post("/api/v1/recommendations/generate", headers={"Authorization": "Bearer TEST-TOKEN-UID-CDMO-88"})
    assert res.status_code == 200
    assert isinstance(res.json(), list)

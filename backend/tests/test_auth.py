import os
import sys
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Enable testing mode in settings before importing app modules
os.environ["TESTING"] = "true"

from app.config import settings
from app.database import Base, get_db, engine as db_engine
from app.models import User, Facility, UserRole, FacilityType
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
def setup_database():
    settings.TESTING = True
    Base.metadata.create_all(bind=db_engine)
    db = TestingSessionLocal()
    
    # Clean up existing test data
    db.query(User).delete()
    db.query(Facility).delete()
    db.commit()

    # 1. Create Facilities
    fac1 = Facility(
        facility_code="CHC-OD-KHU-001",
        name="Jatni CHC (Khordha)",
        facility_type=FacilityType.CHC,
        state="OD",
        district="Khordha",
        latitude=20.165,
        longitude=85.705
    )
    fac2 = Facility(
        facility_code="UPHC-OD-CTC-002",
        name="UPHC MS Das (Kafla Bazar)",
        facility_type=FacilityType.UPHC,
        state="OD",
        district="Cuttack",
        latitude=20.462,
        longitude=85.882
    )
    db.add_all([fac1, fac2])
    db.commit()

    # 2. Create Users with different roles
    admin_user = User(
        firebase_uid="UID-ADMIN-99",
        email="admin@healysis.gov.in",
        full_name="System Admin",
        role=UserRole.ADMIN,
        facility_id=None
    )
    cdmo_user = User(
        firebase_uid="UID-CDMO-88",
        email="cdmo@healysis.gov.in",
        full_name="CDMO Director",
        role=UserRole.CDMO,
        facility_id=None
    )
    officer1 = User(
        firebase_uid="UID-OFFICER-11",
        email="officer1@healysis.gov.in",
        full_name="Facility Officer 1",
        role=UserRole.FACILITY_OFFICER,
        facility_id=fac1.id
    )
    db.add_all([admin_user, cdmo_user, officer1])
    db.commit()
    db.close()

    yield

# ==========================================
# 1. Missing Token Test
# ==========================================
def test_missing_auth_header():
    res = client.get("/api/v1/auth/me")
    assert res.status_code == 401
    assert "Missing Authorization header" in res.json()["detail"]

# ==========================================
# 2. Invalid Token Test
# ==========================================
def test_invalid_auth_header_format():
    res = client.get("/api/v1/auth/me", headers={"Authorization": "InvalidTokenString"})
    assert res.status_code == 401
    assert "Invalid Authorization header format" in res.json()["detail"]

def test_invalid_token_signature():
    settings.TESTING = False
    res = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer BAD-TOKEN-12345"})
    settings.TESTING = True
    assert res.status_code == 401
    assert "Invalid" in res.json()["detail"] or "verification failed" in res.json()["detail"] or "Unknown" in res.json()["detail"]

# ==========================================
# 3. Unknown Firebase User Test
# ==========================================
def test_unknown_firebase_user():
    res = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer TEST-TOKEN-UNKNOWN-UID-999"})
    assert res.status_code == 401
    assert "Unknown Firebase user" in res.json()["detail"]

# ==========================================
# 4. Valid Firebase Identity & Profile Test
# ==========================================
def test_valid_firebase_identity():
    res = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer TEST-TOKEN-UID-OFFICER-11"})
    assert res.status_code == 200
    data = res.json()
    assert data["firebase_uid"] == "UID-OFFICER-11"
    assert data["full_name"] == "Facility Officer 1"
    assert data["role"] == "FACILITY_OFFICER"

# ==========================================
# 5. ADMIN Authorization Test
# ==========================================
def test_admin_authorization_success():
    res = client.get("/api/v1/auth/admin-only", headers={"Authorization": "Bearer TEST-TOKEN-UID-ADMIN-99"})
    assert res.status_code == 200
    assert res.json()["status"] == "AUTHORIZED"
    assert res.json()["role"] == "ADMIN"

def test_admin_authorization_forbidden_for_officer():
    res = client.get("/api/v1/auth/admin-only", headers={"Authorization": "Bearer TEST-TOKEN-UID-OFFICER-11"})
    assert res.status_code == 403
    assert "Forbidden" in res.json()["detail"]

# ==========================================
# 6. CDMO Authorization Test
# ==========================================
def test_cdmo_authorization_success():
    res = client.get("/api/v1/auth/cdmo-only", headers={"Authorization": "Bearer TEST-TOKEN-UID-CDMO-88"})
    assert res.status_code == 200
    assert res.json()["role"] == "CDMO"

    res_admin = client.get("/api/v1/auth/cdmo-only", headers={"Authorization": "Bearer TEST-TOKEN-UID-ADMIN-99"})
    assert res_admin.status_code == 200

def test_cdmo_authorization_forbidden_for_officer():
    res = client.get("/api/v1/auth/cdmo-only", headers={"Authorization": "Bearer TEST-TOKEN-UID-OFFICER-11"})
    assert res.status_code == 403
    assert "Forbidden" in res.json()["detail"]

# ==========================================
# 7. FACILITY_OFFICER Authorization & Scope Test
# ==========================================
def test_facility_officer_access_assigned_facility():
    db = TestingSessionLocal()
    fac1 = db.query(Facility).filter(Facility.facility_code == "CHC-OD-KHU-001").first()
    db.close()
    
    res = client.get(f"/api/v1/auth/facility-scoped/{fac1.id}", headers={"Authorization": "Bearer TEST-TOKEN-UID-OFFICER-11"})
    assert res.status_code == 200
    assert res.json()["facility_id"] == fac1.id

def test_facility_officer_access_unassigned_facility_forbidden():
    db = TestingSessionLocal()
    fac2 = db.query(Facility).filter(Facility.facility_code == "UPHC-OD-CTC-002").first()
    db.close()

    res = client.get(f"/api/v1/auth/facility-scoped/{fac2.id}", headers={"Authorization": "Bearer TEST-TOKEN-UID-OFFICER-11"})
    assert res.status_code == 403
    assert "restricted to facility_id=" in res.json()["detail"]

def test_cdmo_access_any_facility_success():
    db = TestingSessionLocal()
    fac2 = db.query(Facility).filter(Facility.facility_code == "UPHC-OD-CTC-002").first()
    db.close()

    res = client.get(f"/api/v1/auth/facility-scoped/{fac2.id}", headers={"Authorization": "Bearer TEST-TOKEN-UID-CDMO-88"})
    assert res.status_code == 200
    assert res.json()["facility_id"] == fac2.id

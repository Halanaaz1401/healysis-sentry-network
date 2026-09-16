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


# ==========================================
# 8. Regression Tests: Firebase UID -> Healysis User Resolution
# ==========================================
def test_cdmo_user_resolution_and_profile():
    """Verify UID-CDMO-88 resolves to verified CDMO user with correct role and global scope."""
    res = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer TEST-TOKEN-UID-CDMO-88"})
    assert res.status_code == 200
    data = res.json()
    assert data["firebase_uid"] == "UID-CDMO-88"
    assert data["role"] == "CDMO"
    assert data["facility_id"] is None


def test_facility_officer_user_resolution_and_profile():
    """Verify UID-OFFICER-JATNI resolves to verified Facility Officer with facility-scoped access."""
    # Ensure officer is seeded
    db = TestingSessionLocal()
    from seed_db import ensure_demo_users_seeded
    ensure_demo_users_seeded(db)
    db.close()

    res = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer TEST-TOKEN-UID-OFFICER-JATNI"})
    assert res.status_code == 200
    data = res.json()
    assert data["firebase_uid"] == "UID-OFFICER-JATNI"
    assert data["role"] == "FACILITY_OFFICER"
    assert data["facility_id"] is not None


def test_demo_user_self_healing_resolution_when_missing():
    """Verify that if a registered demo UID is missing from active DB in dev/demo mode, it self-heals."""
    db = TestingSessionLocal()
    db.query(User).filter(User.firebase_uid == "UID-CDMO-88").delete()
    db.commit()
    # Confirm it was deleted
    assert db.query(User).filter(User.firebase_uid == "UID-CDMO-88").first() is None
    db.close()

    # Request with demo token should trigger self-healing and succeed
    res = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer TEST-TOKEN-UID-CDMO-88"})
    assert res.status_code == 200
    data = res.json()
    assert data["firebase_uid"] == "UID-CDMO-88"
    assert data["role"] == "CDMO"


def test_cdmo_can_access_protected_apis():
    """Verify CDMO authenticated with UID-CDMO-88 can access alerts, forecasts, and recommendations without 401."""
    cdmo_headers = {"Authorization": "Bearer TEST-TOKEN-UID-CDMO-88"}

    res_alerts = client.get("/api/v1/alerts", headers=cdmo_headers)
    assert res_alerts.status_code == 200

    res_forecasts = client.get("/api/v1/forecasts", headers=cdmo_headers)
    assert res_forecasts.status_code == 200

    res_recs = client.get("/api/v1/recommendations", headers=cdmo_headers)
    assert res_recs.status_code == 200


def test_email_based_identity_reconciliation():
    """Verify a pre-registered database user binds their Firebase UID upon first authenticated token."""
    db = TestingSessionLocal()
    pre_user = User(
        firebase_uid="PENDING-FB-UID-BINDING",
        email="new.specialist@healysis.gov.in",
        full_name="New Specialist",
        role=UserRole.FACILITY_OFFICER,
        facility_id=1
    )
    db.add(pre_user)
    db.commit()
    db.close()

    # Authenticated token arrives with new Firebase UID but matching verified email
    new_uid = "UID-NEW-FIREBASE-SPEC"
    token_headers = {"Authorization": f"Bearer TEST-TOKEN-{new_uid}"}

    # First update verify_firebase_token mock behavior for this test: in security.py clean_token starting with UID- returns email
    # Let's call /api/v1/auth/me
    # To test email binding, pass a token where email matches pre_user.email
    from app.security import verify_firebase_token
    # Monkey-patch verify_firebase_token temporarily for this test
    def mock_verify(authorization=None):
        return {
            "uid": new_uid,
            "email": "new.specialist@healysis.gov.in",
            "firebase": {"sign_in_provider": "password"}
        }

    from main import app
    app.dependency_overrides[verify_firebase_token] = mock_verify
    try:
        res = client.get("/api/v1/auth/me", headers=token_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["firebase_uid"] == new_uid
        assert data["email"] == "new.specialist@healysis.gov.in"
        assert data["role"] == "FACILITY_OFFICER"

        # Check DB was updated
        db = TestingSessionLocal()
        db_user = db.query(User).filter(User.firebase_uid == new_uid).first()
        assert db_user is not None
        assert db_user.email == "new.specialist@healysis.gov.in"
        db.close()
    finally:
        app.dependency_overrides.pop(verify_firebase_token, None)


def test_feature_2_1_confirm_update_requires_authenticated_user():
    """Feature 2.1 confirm-update rejects unauthenticated or unknown UID requests."""
    res_no_auth = client.post("/api/v1/advisor/confirm-update", json={
        "confirmation_token": "dummy_token",
        "facility_id": 1,
        "item_code": "MED-ORS-SACHET",
        "quantity": 180
    })
    assert res_no_auth.status_code == 401

    res_unknown = client.post(
        "/api/v1/advisor/confirm-update",
        headers={"Authorization": "Bearer TEST-TOKEN-UNKNOWN-UID-999"},
        json={
            "confirmation_token": "dummy_token",
            "facility_id": 1,
            "item_code": "MED-ORS-SACHET",
            "quantity": 180
        }
    )
    assert res_unknown.status_code == 401
    assert "Unknown Firebase user" in res_unknown.json()["detail"]


def test_feature_2_1_confirm_update_rejects_cross_facility_access():
    """Feature 2.1 confirm-update strictly enforces facility scoping for Facility Officers."""
    officer_headers = {"Authorization": "Bearer TEST-TOKEN-UID-OFFICER-11"}
    # Officer 11 is assigned to fac1 (id=1), attempting update on facility 2 (id=2)
    res = client.post(
        "/api/v1/advisor/confirm-update",
        headers=officer_headers,
        json={
            "confirmation_token": "dummy_token",
            "facility_id": 2,
            "item_code": "MED-ORS-SACHET",
            "quantity": 180
        }
    )
    assert res.status_code == 403
    assert "restricted to facility_id=" in res.json()["detail"]


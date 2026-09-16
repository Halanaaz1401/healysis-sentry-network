import os
import sys
import pytest
from datetime import datetime, date, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

os.environ["TESTING"] = "true"

from app.config import settings
from app.database import Base, get_db, engine as db_engine
from app.models import (
    Facility, Medicine, Inventory, ConsumptionLog, Forecast, Alert, Recommendation, User,
    Conversation, Message,
    FacilityType, UserRole, MedicineCategory, ActionType, AlertSeverity, AlertType, AlertStatus
)
from app.advisor_service import generate_conversation_title, verify_update_token

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
def setup_conversations_data():
    settings.TESTING = True
    Base.metadata.create_all(bind=db_engine)
    db = TestingSessionLocal()

    # Clear conversations & messages
    db.query(Message).delete()
    db.query(Conversation).delete()
    db.query(Recommendation).delete()
    db.query(Alert).delete()
    db.query(Forecast).delete()
    db.query(Inventory).delete()
    db.query(Medicine).delete()
    db.query(Facility).delete()
    db.query(User).delete()
    db.commit()

    # Seed facilities
    fac1 = Facility(
        id=1,
        facility_code="CHC-OD-KHU-001",
        name="Jatni CHC (Khordha)",
        facility_type=FacilityType.CHC,
        state="OD",
        district="Khordha",
        latitude=20.165,
        longitude=85.705
    )
    fac2 = Facility(
        id=2,
        facility_code="PHC-OD-PURI-004",
        name="Pipili PHC (Puri)",
        facility_type=FacilityType.PHC,
        state="OD",
        district="Puri",
        latitude=20.117,
        longitude=85.833
    )
    db.add_all([fac1, fac2])
    db.commit()

    # Seed users
    cdmo = User(
        id=1,
        firebase_uid="UID-CDMO-88",
        email="cdmo.director@healysis.gov.in",
        full_name="Dr. S. Mohanty",
        role=UserRole.CDMO,
        facility_id=None
    )
    officer_jatni = User(
        id=2,
        firebase_uid="UID-OFFICER-JATNI",
        email="officer.jatni@healysis.gov.in",
        full_name="Dr. A. Nayak",
        role=UserRole.FACILITY_OFFICER,
        facility_id=1
    )
    officer_pipili = User(
        id=3,
        firebase_uid="UID-OFFICER-PIPILI",
        email="inventory.pipili@healysis.gov.in",
        full_name="R. Mohanty",
        role=UserRole.FACILITY_OFFICER,
        facility_id=2
    )
    db.add_all([cdmo, officer_jatni, officer_pipili])
    db.commit()

    # Seed medicine
    med = Medicine(
        id=1,
        code="MED-ORS-SACHET",
        name="ORS Sachet",
        category=MedicineCategory.ESSENTIAL_MEDICINE,
        unit="units"
    )
    db.add(med)
    db.commit()

    # Seed inventory & forecast
    inv = Inventory(
        facility_id=1,
        medicine_id=1,
        item_code="MED-ORS-SACHET",
        item_name="ORS Sachet",
        quantity=180,
        safety_stock=20,
        incoming_quantity=0
    )
    fc = Forecast(
        facility_id=1,
        medicine_id=1,
        item_code="MED-ORS-SACHET",
        forecast_date=date.today(),
        expected_daily_demand=15.0,
        days_of_cover=12.0,
        projected_stockout_date=date.today() + timedelta(days=12),
        confidence_score=0.95
    )
    db.add_all([inv, fc])
    db.commit()
    db.close()


def test_user_can_create_conversation():
    headers = {"Authorization": "Bearer TEST-TOKEN-UID-CDMO-88"}
    resp = client.post("/api/v1/advisor/conversations", json={"title": "Jatni Risk Review"}, headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["id"] is not None
    assert data["title"] == "Jatni Risk Review"


def test_user_can_list_own_conversations():
    headers = {"Authorization": "Bearer TEST-TOKEN-UID-CDMO-88"}
    client.post("/api/v1/advisor/conversations", json={"title": "Chat 1"}, headers=headers)
    client.post("/api/v1/advisor/conversations", json={"title": "Chat 2"}, headers=headers)

    resp = client.get("/api/v1/advisor/conversations", headers=headers)
    assert resp.status_code == 200
    convos = resp.json()
    assert len(convos) == 2
    titles = [c["title"] for c in convos]
    assert "Chat 1" in titles
    assert "Chat 2" in titles


def test_user_can_retrieve_own_conversation_with_messages():
    headers = {"Authorization": "Bearer TEST-TOKEN-UID-CDMO-88"}
    create_resp = client.post("/api/v1/advisor/conversations", json={"title": "New Chat"}, headers=headers)
    convo_id = create_resp.json()["id"]

    # Send message to conversation
    msg_resp = client.post(
        f"/api/v1/advisor/conversations/{convo_id}/messages",
        json={"message": "Why is Jatni CHC at critical risk?"},
        headers=headers
    )
    assert msg_resp.status_code == 200

    # Retrieve conversation detail
    get_resp = client.get(f"/api/v1/advisor/conversations/{convo_id}", headers=headers)
    assert get_resp.status_code == 200
    detail = get_resp.json()
    assert detail["id"] == convo_id
    assert len(detail["messages"]) == 2  # user + advisor
    assert detail["messages"][0]["sender"] == "user"
    assert detail["messages"][0]["text"] == "Why is Jatni CHC at critical risk?"
    assert detail["messages"][1]["sender"] == "advisor"
    assert detail["title"] == "Jatni CHC Risk"  # Deterministic title auto-set!


def test_cross_user_isolation_cannot_get_other_user_conversation():
    headers_cdmo = {"Authorization": "Bearer TEST-TOKEN-UID-CDMO-88"}
    headers_jatni = {"Authorization": "Bearer TEST-TOKEN-UID-OFFICER-JATNI"}

    # CDMO creates conversation
    create_resp = client.post("/api/v1/advisor/conversations", json={"title": "CDMO Private Chat"}, headers=headers_cdmo)
    convo_id = create_resp.json()["id"]

    # Jatni officer attempts to retrieve CDMO conversation
    resp = client.get(f"/api/v1/advisor/conversations/{convo_id}", headers=headers_jatni)
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Conversation not found."


def test_cross_user_isolation_cannot_post_message_to_other_user_conversation():
    headers_cdmo = {"Authorization": "Bearer TEST-TOKEN-UID-CDMO-88"}
    headers_jatni = {"Authorization": "Bearer TEST-TOKEN-UID-OFFICER-JATNI"}

    # CDMO creates conversation
    create_resp = client.post("/api/v1/advisor/conversations", json={"title": "CDMO Private Chat"}, headers=headers_cdmo)
    convo_id = create_resp.json()["id"]

    # Jatni officer attempts to post to CDMO conversation
    resp = client.post(
        f"/api/v1/advisor/conversations/{convo_id}/messages",
        json={"message": "Inject message"},
        headers=headers_jatni
    )
    assert resp.status_code == 404


def test_cross_user_isolation_cannot_delete_other_user_conversation():
    headers_cdmo = {"Authorization": "Bearer TEST-TOKEN-UID-CDMO-88"}
    headers_jatni = {"Authorization": "Bearer TEST-TOKEN-UID-OFFICER-JATNI"}

    # CDMO creates conversation
    create_resp = client.post("/api/v1/advisor/conversations", json={"title": "CDMO Private Chat"}, headers=headers_cdmo)
    convo_id = create_resp.json()["id"]

    # Jatni officer attempts to delete CDMO conversation
    resp = client.delete(f"/api/v1/advisor/conversations/{convo_id}", headers=headers_jatni)
    assert resp.status_code == 404

    # CDMO can delete own conversation
    resp_delete = client.delete(f"/api/v1/advisor/conversations/{convo_id}", headers=headers_cdmo)
    assert resp_delete.status_code == 200


def test_user_isolation_in_conversation_lists():
    headers_cdmo = {"Authorization": "Bearer TEST-TOKEN-UID-CDMO-88"}
    headers_jatni = {"Authorization": "Bearer TEST-TOKEN-UID-OFFICER-JATNI"}
    headers_pipili = {"Authorization": "Bearer TEST-TOKEN-UID-OFFICER-PIPILI"}

    # Create chats for CDMO
    client.post("/api/v1/advisor/conversations", json={"title": "CDMO Chat A"}, headers=headers_cdmo)
    client.post("/api/v1/advisor/conversations", json={"title": "CDMO Chat B"}, headers=headers_cdmo)

    # Create chat for Jatni
    client.post("/api/v1/advisor/conversations", json={"title": "Jatni Chat 1"}, headers=headers_jatni)

    # CDMO sees 2 chats
    list_cdmo = client.get("/api/v1/advisor/conversations", headers=headers_cdmo).json()
    assert len(list_cdmo) == 2
    assert all("CDMO" in c["title"] for c in list_cdmo)

    # Jatni officer sees only 1 chat
    list_jatni = client.get("/api/v1/advisor/conversations", headers=headers_jatni).json()
    assert len(list_jatni) == 1
    assert list_jatni[0]["title"] == "Jatni Chat 1"

    # Pipili officer sees 0 chats
    list_pipili = client.get("/api/v1/advisor/conversations", headers=headers_pipili).json()
    assert len(list_pipili) == 0


def test_deterministic_title_generation():
    assert generate_conversation_title("Aaj ORS ka stock 180 hai.") == "ORS Stock Update"
    assert generate_conversation_title("Why is Jatni CHC at critical risk?") == "Jatni CHC Risk"
    assert generate_conversation_title("What resources are at risk in Khordha?") == "Khordha Resource Risk"
    assert generate_conversation_title("Show me critical resources") == "Critical Resources"
    assert generate_conversation_title("Need redistribution recommendations") == "Redistribution Discussion"


def test_unauthenticated_requests_rejected():
    resp_list = client.get("/api/v1/advisor/conversations")
    assert resp_list.status_code == 401

    resp_create = client.post("/api/v1/advisor/conversations", json={"title": "Test"})
    assert resp_create.status_code == 401

    resp_get = client.get("/api/v1/advisor/conversations/1")
    assert resp_get.status_code == 401


def test_feature_2_1_noop_and_real_update_in_conversation():
    headers_jatni = {"Authorization": "Bearer TEST-TOKEN-UID-OFFICER-JATNI"}
    create_resp = client.post("/api/v1/advisor/conversations", json={"title": "New Chat"}, headers=headers_jatni)
    convo_id = create_resp.json()["id"]

    # 1. No-op (stock is 180 in DB, user says 180)
    resp_noop = client.post(
        f"/api/v1/advisor/conversations/{convo_id}/messages",
        json={"message": "Aaj ORS ka stock 180 hai."},
        headers=headers_jatni
    )
    assert resp_noop.status_code == 200
    data_noop = resp_noop.json()
    assert data_noop["pending_update"] is None
    assert "already recorded as" in data_noop["answer"]
    assert "No inventory update is required" in data_noop["answer"]

    # 2. Real update to 200
    resp_update = client.post(
        f"/api/v1/advisor/conversations/{convo_id}/messages",
        json={"message": "Aaj ORS ka stock 200 hai."},
        headers=headers_jatni
    )
    assert resp_update.status_code == 200
    data_update = resp_update.json()
    assert data_update["pending_update"] is not None
    assert data_update["pending_update"]["current_quantity"] == 180
    assert data_update["pending_update"]["new_quantity"] == 200
    token = data_update["pending_update"]["confirmation_token"]

    # 3. Confirm update with valid token
    confirm_resp = client.post("/api/v1/advisor/confirm-update", json={
        "facility_id": 1,
        "item_code": "MED-ORS-SACHET",
        "quantity": 200,
        "daily_demand": None,
        "confirmation_token": token
    }, headers=headers_jatni)
    assert confirm_resp.status_code == 200
    assert confirm_resp.json()["new_quantity"] == 200

    # 4. Loading conversation history does NOT authorize mutation
    convo_detail = client.get(f"/api/v1/advisor/conversations/{convo_id}", headers=headers_jatni).json()
    assert len(convo_detail["messages"]) == 4  # 2 user queries + 2 advisor answers
    # Verify DB quantity is 200
    db = TestingSessionLocal()
    inv = db.query(Inventory).filter(Inventory.facility_id == 1, Inventory.item_code == "MED-ORS-SACHET").first()
    assert inv.quantity == 200
    db.close()


def test_tampered_or_reused_token_fails_authorization():
    headers_jatni = {"Authorization": "Bearer TEST-TOKEN-UID-OFFICER-JATNI"}
    confirm_resp = client.post("/api/v1/advisor/confirm-update", json={
        "facility_id": 1,
        "item_code": "MED-ORS-SACHET",
        "quantity": 250,
        "daily_demand": None,
        "confirmation_token": "FAKE-OR-STALE-TOKEN-FROM-HISTORY"
    }, headers=headers_jatni)
    assert confirm_resp.status_code == 400

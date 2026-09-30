import os
import sys
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

os.environ["TESTING"] = "true"

from app.config import settings
from app.database import Base, get_db, engine as db_engine
from app.models import (
    Facility, Medicine, Inventory, Forecast, Alert, Recommendation, User,
    FacilityType, UserRole, MedicineCategory, AlertSeverity, AlertType, AlertStatus,
    UrgencyLevel, RecommendationStatus, Conversation, Message
)
from app.schemas import AdvisorChatRequest
from app.advisor_service import run_grounded_ai_advisor
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
def setup_regression_data():
    settings.TESTING = True
    Base.metadata.create_all(bind=db_engine)
    db = TestingSessionLocal()

    # Clean existing data
    db.query(Message).delete()
    db.query(Conversation).delete()
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
        id=1,
        facility_code="CHC-OD-KHU-001",
        name="Jatni CHC (Khordha)",
        facility_type=FacilityType.CHC,
        state="OD",
        district="Khordha",
        latitude=20.165,
        longitude=85.705
    )
    fac_cuttack = Facility(
        id=2,
        facility_code="UPHC-OD-CTC-002",
        name="UPHC MS Das (Kafla Bazar)",
        facility_type=FacilityType.UPHC,
        state="OD",
        district="Cuttack",
        latitude=20.462,
        longitude=85.882
    )
    db.add_all([fac_jatni, fac_cuttack])
    db.commit()

    # Medicines
    med_ins = Medicine(id=1, code="MED-INSULIN-100IU", name="Insulin 100IU", category=MedicineCategory.VACCINE, unit="vials")
    med_ors = Medicine(id=2, code="MED-ORS-S-001", name="Oral Rehydration Salts (ORS)", category=MedicineCategory.ESSENTIAL_MEDICINE, unit="sachets")
    db.add_all([med_ins, med_ors])
    db.commit()

    # Inventories: Jatni has low Insulin, Cuttack has surplus ORS
    inv_jatni = Inventory(
        facility_id=fac_jatni.id,
        medicine_id=med_ins.id,
        item_code=med_ins.code,
        item_name=med_ins.name,
        quantity=5,
        safety_stock=40,
        incoming_quantity=0
    )
    inv_cuttack = Inventory(
        facility_id=fac_cuttack.id,
        medicine_id=med_ors.id,
        item_code=med_ors.code,
        item_name=med_ors.name,
        quantity=500,
        safety_stock=50,
        incoming_quantity=0
    )
    db.add_all([inv_jatni, inv_cuttack])
    db.commit()

    # Forecast & Alert for Jatni
    fc_jatni = Forecast(
        facility_id=fac_jatni.id,
        medicine_id=med_ins.id,
        item_code=med_ins.code,
        forecast_date=date.today(),
        expected_daily_demand=5.0,
        days_of_cover=1.0,
        confidence_score=0.95
    )
    alt_jatni = Alert(
        alert_code="ALT-JATNI-INS",
        facility_id=fac_jatni.id,
        resource_id=med_ins.code,
        severity=AlertSeverity.CRITICAL,
        alert_type=AlertType.STOCKOUT_PROJECTED,
        title="Critical Insulin Shortage at Jatni CHC",
        status=AlertStatus.ACTIVE
    )
    # Recommendation
    rec_rebal = Recommendation(
        id=1,
        recommendation_code="REC-001",
        donor_facility_id=fac_cuttack.id,
        recipient_facility_id=fac_jatni.id,
        medicine_id=med_ors.id,
        item_code=med_ors.code,
        recommended_quantity=100,
        urgency_level=UrgencyLevel.URGENT,
        haversine_distance_km=37.8,
        expected_days_cover_gained=5.0,
        confidence_score=0.92,
        reason="Redistribute 100 sachets of ORS from UPHC MS Das to Jatni CHC.",
        status=RecommendationStatus.PENDING_HUMAN_APPROVAL
    )
    db.add_all([fc_jatni, alt_jatni, rec_rebal])
    db.commit()

    # Users
    admin_user = User(id=1, firebase_uid="UID-REG-ADMIN", email="admin.reg@healysis.gov.in", full_name="Admin Director", role=UserRole.ADMIN, facility_id=None)
    cdmo_user = User(id=2, firebase_uid="UID-REG-CDMO", email="cdmo.reg@healysis.gov.in", full_name="CDMO Khordha", role=UserRole.CDMO, facility_id=None)
    fo_jatni = User(id=3, firebase_uid="UID-REG-FO", email="fo.jatni@healysis.gov.in", full_name="Officer Jatni", role=UserRole.FACILITY_OFFICER, facility_id=fac_jatni.id)
    db.add_all([admin_user, cdmo_user, fo_jatni])
    db.commit()

    db.close()
    yield


# =========================================================================
# Regression Test 1: CDMO Network-Level Resource Query
# =========================================================================
def test_1_cdmo_network_level_resource_query():
    db = TestingSessionLocal()
    cdmo = db.query(User).filter(User.role == UserRole.CDMO).first()
    
    req = AdvisorChatRequest(message="What resources are available across the network?")
    resp = run_grounded_ai_advisor(req, cdmo, db)
    
    assert resp is not None
    assert len(resp.answer) > 0
    # Should reflect network resources (e.g., mentions available catalog or facilities in network)
    assert any(term in resp.answer.lower() for term in ["network", "facility", "insulin", "ors", "available", "resource", "stock"])
    db.close()


# =========================================================================
# Regression Test 2: CDMO Facility-Specific Resource Query
# =========================================================================
def test_2_cdmo_facility_specific_resource_query():
    db = TestingSessionLocal()
    cdmo = db.query(User).filter(User.role == UserRole.CDMO).first()
    
    req = AdvisorChatRequest(message="What resources are available at Jatni CHC?")
    resp = run_grounded_ai_advisor(req, cdmo, db)
    
    assert resp is not None
    # Must contain Jatni inventory (Insulin = 5)
    assert "jatni" in resp.answer.lower() or "insulin" in resp.answer.lower()
    # Must NOT dump Cuttack's resources
    assert "cuttack" not in resp.answer.lower()
    assert "kafla bazar" not in resp.answer.lower()
    db.close()


# =========================================================================
# Regression Test 3: CDMO Facility Profile Query
# =========================================================================
def test_3_cdmo_facility_profile_query():
    db = TestingSessionLocal()
    cdmo = db.query(User).filter(User.role == UserRole.CDMO).first()
    
    req = AdvisorChatRequest(message="Give me details about Jatni CHC.")
    resp = run_grounded_ai_advisor(req, cdmo, db)
    
    assert resp is not None
    ans = resp.answer.lower()
    # Should include profile elements: name/location/type/inventory
    assert "jatni" in ans
    assert ("khordha" in ans or "chc" in ans or "insulin" in ans)
    # Must not dump Cuttack facility details
    assert "kafla bazar" not in ans
    db.close()


# =========================================================================
# Regression Test 4: Risk / Forecast Query
# =========================================================================
def test_4_risk_forecast_query():
    db = TestingSessionLocal()
    cdmo = db.query(User).filter(User.role == UserRole.CDMO).first()
    
    req = AdvisorChatRequest(message="What is the forecast for Jatni CHC?")
    resp = run_grounded_ai_advisor(req, cdmo, db)
    
    assert resp is not None
    ans = resp.answer.lower()
    # Forecast exists: days_of_cover=1.0 or demand=5
    assert any(term in ans for term in ["forecast", "demand", "cover", "day", "critical", "insulin", "jatni"])
    db.close()


# =========================================================================
# Regression Test 5: Alert Query
# =========================================================================
def test_5_active_alerts_query():
    db = TestingSessionLocal()
    cdmo = db.query(User).filter(User.role == UserRole.CDMO).first()
    
    req = AdvisorChatRequest(message="What are the current alerts?")
    resp = run_grounded_ai_advisor(req, cdmo, db)
    
    assert resp is not None
    ans = resp.answer.lower()
    # Alert "Critical Insulin Shortage at Jatni CHC" should be reported
    assert any(term in ans for term in ["alert", "insulin", "shortage", "jatni", "critical"])
    db.close()


# =========================================================================
# Regression Test 6: Redistribution Query
# =========================================================================
def test_6_redistribution_query():
    db = TestingSessionLocal()
    cdmo = db.query(User).filter(User.role == UserRole.CDMO).first()
    
    req = AdvisorChatRequest(message="Are there any redistribution recommendations?")
    resp = run_grounded_ai_advisor(req, cdmo, db)
    
    assert resp is not None
    ans = resp.answer.lower()
    # There is 1 pending recommendation for ORS transfer
    assert any(term in ans for term in ["redistribution", "transfer", "ors", "jatni", "cuttack", "100", "recommendation"])
    db.close()


# =========================================================================
# Regression Test 7: Facility Officer Isolation from Another Facility
# =========================================================================
def test_7_facility_officer_isolation():
    db = TestingSessionLocal()
    fo = db.query(User).filter(User.role == UserRole.FACILITY_OFFICER).first()
    assert fo.facility_id == 1  # Jatni CHC
    
    # FO tries to query Cuttack facility (id=2)
    req = AdvisorChatRequest(message="What resources are available at UPHC MS Das Cuttack?")
    resp = run_grounded_ai_advisor(req, fo, db)
    
    assert resp is not None
    ans = resp.answer.lower()
    # Must enforce isolation: either reports Jatni or restricts from Cuttack
    # Never reveal Cuttack's 500 units of ORS to Jatni's FO
    assert "500" not in ans
    db.close()


# =========================================================================
# Regression Test 8: No Fabricated Data When Records Missing
# =========================================================================
def test_8_no_fabricated_data_when_missing():
    db = TestingSessionLocal()
    cdmo = db.query(User).filter(User.role == UserRole.CDMO).first()
    
    # Query for an unknown/unsupported medicine or missing record
    req = AdvisorChatRequest(message="What is the current stock of Covaxin at Jatni CHC?")
    resp = run_grounded_ai_advisor(req, cdmo, db)
    
    assert resp is not None
    ans = resp.answer.lower()
    # Must NOT hallucinate a number for Covaxin
    assert "i don't have enough data" in ans or "unsupported" in ans or "not available" in ans or "not tracked" in ans
    db.close()


# =========================================================================
# Regression Test 9: Gemini Cannot Alter Verified Numeric Facts
# =========================================================================
def test_9_gemini_cannot_alter_verified_numeric_facts():
    db = TestingSessionLocal()
    cdmo = db.query(User).filter(User.role == UserRole.CDMO).first()
    
    # Mock Gemini client to simulate an LLM hallucinating numbers (changing 5 to 999)
    fake_gemini_response = MagicMock()
    fake_gemini_response.text = "There are 999 vials of Insulin at Jatni CHC."
    
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = fake_gemini_response
    
    with patch("app.advisor_service.get_genai_client", return_value=mock_client):
        req = AdvisorChatRequest(message="How much insulin is available at Jatni CHC?")
        resp = run_grounded_ai_advisor(req, cdmo, db)
        
        assert resp is not None
        # The hallucinated number 999 must NOT be present in final answer!
        assert "999" not in resp.answer
        # Grounded verified quantity (5) should be preserved
        assert "5" in resp.answer
    db.close()


# =========================================================================
# Regression Test 10: Stale Conversation Recovery
# =========================================================================
def test_10_stale_conversation_recovery():
    db = TestingSessionLocal()
    fo = db.query(User).filter(User.role == UserRole.FACILITY_OFFICER).first()
    headers = {"Authorization": f"Bearer TEST-TOKEN-{fo.firebase_uid}"}
    
    # Test router endpoint with a non-existent/stale conversation ID (999999)
    response = client.post(
        "/api/v1/advisor/conversations/999999/messages",
        json={"message": "What is the status of Jatni CHC?"},
        headers=headers
    )
    assert response.status_code == 200, f"Expected 200 OK after graceful recovery, got {response.status_code}: {response.text}"
    data = response.json()
    assert "answer" in data
    assert data.get("conversation_id") is not None
    # Confirm that a valid conversation was created in DB
    convo_id = data["conversation_id"]
    convo = db.query(Conversation).filter(Conversation.id == convo_id).first()
    assert convo is not None
    assert convo.user_id == fo.id
    db.close()


# =========================================================================
# Regression Test 11: CDMO District Scoped Facility List
# =========================================================================
def test_11_cdmo_district_scoped_facility_list():
    db = TestingSessionLocal()
    cdmo = db.query(User).filter(User.role == UserRole.CDMO).first()

    req = AdvisorChatRequest(message="What facilities are in Khordha?")
    resp = run_grounded_ai_advisor(req, cdmo, db)

    assert resp is not None
    ans = resp.answer.lower()
    assert "jatni chc" in ans
    assert "cuttack" not in ans
    assert "puri" not in ans
    db.close()


# =========================================================================
# Regression Test 12: Single Resource Query Not Dumping Facility Profile
# =========================================================================
def test_12_single_resource_query_not_dumping_facility_profile():
    db = TestingSessionLocal()
    cdmo = db.query(User).filter(User.role == UserRole.CDMO).first()

    req = AdvisorChatRequest(message="What is the ORS stock at Jatni CHC?")
    resp = run_grounded_ai_advisor(req, cdmo, db)

    assert resp is not None
    ans = resp.answer.lower()
    # Must focus on ORS (or Insulin in test DB)
    assert any(term in ans for term in ["ors", "insulin"])
    # Must NOT dump general facility profile beds or doctors
    assert "beds:" not in ans
    assert "staff:" not in ans
    db.close()


# =========================================================================
# Regression Test 13: Stockout Alert Natural Language Query
# =========================================================================
def test_13_stockout_alert_intent():
    db = TestingSessionLocal()
    cdmo = db.query(User).filter(User.role == UserRole.CDMO).first()

    req = AdvisorChatRequest(message="What is the current stockout alert?")
    resp = run_grounded_ai_advisor(req, cdmo, db)

    assert resp is not None
    ans = resp.answer.lower()
    assert "alert" in ans
    assert "jatni" in ans
    db.close()


# =========================================================================
# Regression Test 14: Pending Transfer Natural Language Query
# =========================================================================
def test_14_pending_transfer_intent():
    db = TestingSessionLocal()
    cdmo = db.query(User).filter(User.role == UserRole.CDMO).first()

    req = AdvisorChatRequest(message="Is there a pending transfer?")
    resp = run_grounded_ai_advisor(req, cdmo, db)

    assert resp is not None
    ans = resp.answer.lower()
    assert any(term in ans for term in ["transfer", "redistribution", "recommendation"])
    assert any(term in ans for term in ["ors", "pipili", "jatni", "cuttack"])
    db.close()


# =========================================================================
# Regression Test 15: Network-wide Alerts, Forecasts, and Redistribution
# =========================================================================
def test_15_network_alerts_and_forecasts_and_redistribution_intents():
    db = TestingSessionLocal()
    cdmo = db.query(User).filter(User.role == UserRole.CDMO).first()

    # 1. Network Alerts
    req_alert = AdvisorChatRequest(message="What are the current alerts across the network?")
    resp_alert = run_grounded_ai_advisor(req_alert, cdmo, db)
    assert resp_alert is not None
    assert "active alerts" in resp_alert.answer.lower()
    assert "jatni" in resp_alert.answer.lower()

    # 2. Network Forecasts
    admin = db.query(User).filter(User.role == UserRole.ADMIN).first()
    req_fc = AdvisorChatRequest(message="What are the current forecasts across the network?")
    resp_fc = run_grounded_ai_advisor(req_fc, admin, db)
    assert resp_fc is not None
    assert "operational forecasts across the network" in resp_fc.answer.lower()
    assert "jatni" in resp_fc.answer.lower()

    # 3. Network Redistribution
    req_redist = AdvisorChatRequest(message="Are there any redistribution recommendations across the network?")
    resp_redist = run_grounded_ai_advisor(req_redist, cdmo, db)
    assert resp_redist is not None
    assert "redistribution recommendation" in resp_redist.answer.lower()
    assert any(t in resp_redist.answer.lower() for t in ["transfer 90 ors", "transfer 100 ors"])

    db.close()

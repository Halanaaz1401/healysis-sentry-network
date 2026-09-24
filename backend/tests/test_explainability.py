import os
import sys
from datetime import datetime, date, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
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
from app.algorithms import run_forecast_and_alert_engine, generate_and_persist_redistribution_recommendations
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
def setup_explainability_data():
    settings.TESTING = True
    Base.metadata.create_all(bind=db_engine)
    db = TestingSessionLocal()

    # Clear previous test data in foreign-key safe order
    db.query(Alert).delete()
    db.query(Recommendation).delete()
    db.query(Forecast).delete()
    db.query(ConsumptionLog).delete()
    db.query(Inventory).delete()
    db.query(User).delete()
    db.query(Facility).delete()
    db.query(Medicine).delete()
    db.commit()

    # 1. Facilities
    fac_jatni = Facility(
        id=1,
        facility_code="CHC-OD-KHU-001",
        name="Jatni CHC (Khordha)",
        facility_type=FacilityType.CHC,
        state="OD",
        district="Khordha",
        latitude=20.165,
        longitude=85.707
    )
    fac_pipili = Facility(
        id=2,
        facility_code="PHC-OD-PUR-002",
        name="Pipili PHC (Puri)",
        facility_type=FacilityType.PHC,
        state="OD",
        district="Puri",
        latitude=20.116,
        longitude=85.832
    )
    fac_behala = Facility(
        id=3,
        facility_code="UPHC-WB-KOL-001",
        name="Behala Urban PHC (Kolkata)",
        facility_type=FacilityType.UPHC,
        state="WB",
        district="Kolkata",
        latitude=22.498,
        longitude=88.318
    )
    db.add_all([fac_jatni, fac_pipili, fac_behala])
    db.commit()

    # 2. Medicines
    med_ors = Medicine(
        id=1,
        code="MED-ORS-SACHET",
        name="ORS",
        category=MedicineCategory.ESSENTIAL_MEDICINE,
        unit="sachets"
    )
    db.add(med_ors)
    db.commit()

    # 3. Standard users for RBAC testing matching security.py demo credentials
    user_admin = User(
        firebase_uid="UID-ADMIN-99",
        email="admin@healysis.gov.in",
        full_name="State Admin Officer",
        role=UserRole.ADMIN,
        facility_id=None
    )
    user_officer_jatni = User(
        firebase_uid="UID-OFFICER-JATNI",
        email="officer.jatni@healysis.gov.in",
        full_name="Jatni Facility Officer",
        role=UserRole.FACILITY_OFFICER,
        facility_id=1
    )
    user_officer_behala = User(
        firebase_uid="UID-OFFICER-BEHALA",
        email="nurse.behala@healysis.gov.in",
        full_name="Behala Facility Officer",
        role=UserRole.FACILITY_OFFICER,
        facility_id=3
    )
    db.add_all([user_admin, user_officer_jatni, user_officer_behala])
    db.commit()

    # 4. Inventory: Jatni is in critical shortage (15 units vs 40 safety stock)
    inv_jatni = Inventory(
        facility_id=1,
        medicine_id=1,
        item_code="MED-ORS-SACHET",
        item_name="ORS",
        quantity=15,
        safety_stock=40,
        incoming_quantity=0,
        unit="sachets"
    )
    # Pipili has surplus (140 units vs 40 safety stock => 100 surplus)
    inv_pipili = Inventory(
        facility_id=2,
        medicine_id=1,
        item_code="MED-ORS-SACHET",
        item_name="ORS",
        quantity=140,
        safety_stock=40,
        incoming_quantity=0,
        unit="sachets"
    )
    # Behala has safe stock
    inv_behala = Inventory(
        facility_id=3,
        medicine_id=1,
        item_code="MED-ORS-SACHET",
        item_name="ORS",
        quantity=80,
        safety_stock=30,
        incoming_quantity=0,
        unit="sachets"
    )
    db.add_all([inv_jatni, inv_pipili, inv_behala])
    db.commit()

    # 5. Consumption logs for Jatni (daily consumption of 15 units/day)
    today = date.today()
    for d in range(1, 8):
        c_log = ConsumptionLog(
            facility_id=1,
            medicine_id=1,
            item_code="MED-ORS-SACHET",
            date=today - timedelta(days=d),
            quantity_dispensed=15,
            patient_footfall=25,
            action_type=ActionType.DISPENSE
        )
        db.add(c_log)
    db.commit()

    # Run engines to generate forecasts, alerts, and recommendations
    run_forecast_and_alert_engine(db)
    generate_and_persist_redistribution_recommendations(db)

    db.close()
    yield


# ==============================================================
# 1. RISK EXPLANATION CONTAINS REAL EVIDENCE
# ==============================================================

def test_alert_explanation_contains_real_evidence():
    """
    Verifies that GET /api/v1/alerts/{id}/explanation returns real evidence matching DB records.
    """
    db = TestingSessionLocal()
    alert = db.query(Alert).filter(Alert.facility_id == 1).first()
    assert alert is not None
    alert_id = alert.id
    db.close()

    res = client.get(
        f"/api/v1/alerts/{alert_id}/explanation",
        headers={"Authorization": "Bearer TEST-TOKEN-UID-ADMIN-99"}
    )
    assert res.status_code == 200
    data = res.json()

    assert data["entity_type"] == "ALERT"
    assert data["entity_id"] == alert_id
    assert data["facility_id"] == 1
    assert "Jatni CHC" in data["facility_name"]
    assert data["resource_id"] == "MED-ORS-SACHET"
    assert data["resource_name"] == "ORS"
    assert data["severity"] == "CRITICAL"

    evidence = data["evidence"]
    assert evidence["current_stock"] == 15
    assert evidence["safety_stock"] == 40
    assert evidence["unit"] == "sachets"
    assert evidence["days_of_cover"] == 1.0
    assert evidence["risk_level"] == "CRITICAL"
    assert "EWMA" in evidence["forecast_method"]

    # Why and recommended action are grounded
    assert "Current inventory (15 sachets)" in data["why"]
    assert "safety threshold of 40 sachets" in data["why"]
    assert "1.0 days of cover" in data["why"]
    assert len(data["recommended_action"]) > 0


def test_forecast_explanation_contains_real_evidence():
    """
    Verifies that GET /api/v1/forecasts/{id}/explanation returns real evidence.
    """
    db = TestingSessionLocal()
    forecast = db.query(Forecast).filter(Forecast.facility_id == 1).first()
    assert forecast is not None
    fc_id = forecast.id
    db.close()

    res = client.get(
        f"/api/v1/forecasts/{fc_id}/explanation",
        headers={"Authorization": "Bearer TEST-TOKEN-UID-ADMIN-99"}
    )
    assert res.status_code == 200
    data = res.json()

    assert data["entity_type"] == "FORECAST"
    assert data["entity_id"] == fc_id
    assert data["facility_id"] == 1
    assert data["severity"] == "CRITICAL"

    evidence = data["evidence"]
    assert evidence["current_stock"] == 15
    assert evidence["safety_stock"] == 40
    assert evidence["days_of_cover"] == 1.0
    assert evidence["estimated_daily_demand"] == 15.0

    assert "insufficient coverage" in data["why"] or "1.0 days of cover" in data["why"]
    assert "redistribution" in data["recommended_action"].lower() or "replenish" in data["recommended_action"].lower()


# ==============================================================
# 2. RECOMMENDATION EXPLANATION CONTAINS REAL EVIDENCE
# ==============================================================

def test_recommendation_explanation_contains_real_evidence():
    """
    Verifies that GET /api/v1/recommendations/{id}/explanation returns donor/recipient evidence.
    """
    db = TestingSessionLocal()
    rec = db.query(Recommendation).filter(Recommendation.recipient_facility_id == 1).first()
    assert rec is not None
    rec_id = rec.id
    db.close()

    res = client.get(
        f"/api/v1/recommendations/{rec_id}/explanation",
        headers={"Authorization": "Bearer TEST-TOKEN-UID-ADMIN-99"}
    )
    assert res.status_code == 200
    data = res.json()

    assert data["entity_type"] == "RECOMMENDATION"
    assert data["recommendation_id"] == rec_id
    assert data["recipient_facility_id"] == 1
    assert "Jatni" in data["recipient_facility_name"]
    assert data["donor_facility_id"] == 2
    assert "Pipili" in data["donor_facility_name"]
    assert data["resource_id"] == "MED-ORS-SACHET"

    evidence = data["evidence"]
    # Real values from DB
    assert evidence["recipient_current_stock"] == 15
    assert evidence["recipient_safety_stock"] == 40
    assert evidence["recipient_days_of_cover"] == 1.0
    assert evidence["donor_current_stock"] == 140
    assert evidence["donor_safety_stock"] == 40
    assert evidence["donor_surplus"] == 100  # 140 - 40 = 100
    assert evidence["recommended_quantity"] > 0
    assert evidence["haversine_distance_km"] > 0

    assert "Pipili PHC" in data["why"]
    assert "Jatni CHC" in data["why"]
    assert "surplus" in data["why"]
    assert "Human CDMO operational approval required" in data["recommended_action"]


# ==============================================================
# 3. NO FABRICATED NUMERIC VALUES
# ==============================================================

def test_no_fabricated_numeric_values():
    """
    Asserts every number exposed in explanations exactly matches active DB state.
    """
    db = TestingSessionLocal()
    inv = db.query(Inventory).filter(Inventory.facility_id == 1, Inventory.item_code == "MED-ORS-SACHET").first()
    fc = db.query(Forecast).filter(Forecast.facility_id == 1, Forecast.item_code == "MED-ORS-SACHET").first()
    alert = db.query(Alert).filter(Alert.facility_id == 1).first()
    rec = db.query(Recommendation).filter(Recommendation.recipient_facility_id == 1).first()
    donor_inv = db.query(Inventory).filter(Inventory.facility_id == rec.donor_facility_id, Inventory.item_code == "MED-ORS-SACHET").first()
    db.close()

    # Alert explanation check
    res_alert = client.get(
        f"/api/v1/alerts/{alert.id}/explanation",
        headers={"Authorization": "Bearer TEST-TOKEN-UID-ADMIN-99"}
    ).json()
    assert res_alert["evidence"]["current_stock"] == inv.quantity
    assert res_alert["evidence"]["safety_stock"] == inv.safety_stock
    assert res_alert["evidence"]["estimated_daily_demand"] == fc.expected_daily_demand
    assert res_alert["evidence"]["days_of_cover"] == fc.days_of_cover

    # Recommendation explanation check
    res_rec = client.get(
        f"/api/v1/recommendations/{rec.id}/explanation",
        headers={"Authorization": "Bearer TEST-TOKEN-UID-ADMIN-99"}
    ).json()
    assert res_rec["evidence"]["recipient_current_stock"] == inv.quantity
    assert res_rec["evidence"]["donor_current_stock"] == donor_inv.quantity
    assert res_rec["evidence"]["donor_surplus"] == donor_inv.quantity - donor_inv.safety_stock
    assert res_rec["evidence"]["recommended_quantity"] == rec.recommended_quantity
    assert res_rec["evidence"]["haversine_distance_km"] == rec.haversine_distance_km


# ==============================================================
# 4. STRICT RBAC / FACILITY ISOLATION
# ==============================================================

def test_unauthorized_facility_officer_cannot_access_alert_explanation():
    """
    Behala facility officer (facility_id=3) MUST NOT access Jatni alert explanation (facility_id=1).
    """
    db = TestingSessionLocal()
    alert_jatni = db.query(Alert).filter(Alert.facility_id == 1).first()
    db.close()

    res = client.get(
        f"/api/v1/alerts/{alert_jatni.id}/explanation",
        headers={"Authorization": "Bearer TEST-TOKEN-UID-OFFICER-BEHALA"}
    )
    assert res.status_code == 403
    assert "Forbidden" in res.json()["detail"]


def test_unauthorized_facility_officer_cannot_access_forecast_explanation():
    """
    Behala facility officer (facility_id=3) MUST NOT access Jatni forecast explanation (facility_id=1).
    """
    db = TestingSessionLocal()
    fc_jatni = db.query(Forecast).filter(Forecast.facility_id == 1).first()
    db.close()

    res = client.get(
        f"/api/v1/forecasts/{fc_jatni.id}/explanation",
        headers={"Authorization": "Bearer TEST-TOKEN-UID-OFFICER-BEHALA"}
    )
    assert res.status_code == 403
    assert "Forbidden" in res.json()["detail"]


def test_unauthorized_facility_officer_cannot_access_recommendation_explanation():
    """
    Behala facility officer (facility_id=3) MUST NOT access Pipili->Jatni transfer explanation (1 -> 2).
    """
    db = TestingSessionLocal()
    rec = db.query(Recommendation).filter(
        Recommendation.donor_facility_id == 2,
        Recommendation.recipient_facility_id == 1
    ).first()
    db.close()

    res = client.get(
        f"/api/v1/recommendations/{rec.id}/explanation",
        headers={"Authorization": "Bearer TEST-TOKEN-UID-OFFICER-BEHALA"}
    )
    assert res.status_code == 403
    assert "Forbidden" in res.json()["detail"]


def test_authorized_facility_officer_can_access_own_explanations():
    """
    Jatni facility officer (facility_id=1) CAN access Jatni alert, forecast, and recommendation.
    """
    db = TestingSessionLocal()
    alert_jatni = db.query(Alert).filter(Alert.facility_id == 1).first()
    fc_jatni = db.query(Forecast).filter(Forecast.facility_id == 1).first()
    rec = db.query(Recommendation).filter(Recommendation.recipient_facility_id == 1).first()
    db.close()

    h = {"Authorization": "Bearer TEST-TOKEN-UID-OFFICER-JATNI"}
    r1 = client.get(f"/api/v1/alerts/{alert_jatni.id}/explanation", headers=h)
    assert r1.status_code == 200

    r2 = client.get(f"/api/v1/forecasts/{fc_jatni.id}/explanation", headers=h)
    assert r2.status_code == 200

    r3 = client.get(f"/api/v1/recommendations/{rec.id}/explanation", headers=h)
    assert r3.status_code == 200


# ==============================================================
# 5. EXPLANATIONS ARE READ-ONLY
# ==============================================================

def test_explanations_are_strictly_read_only():
    """
    Calling explanation endpoints does not modify any database records.
    """
    db = TestingSessionLocal()
    stock_before = db.query(Inventory).filter(Inventory.facility_id == 1, Inventory.item_code == "MED-ORS-SACHET").first().quantity
    alert = db.query(Alert).filter(Alert.facility_id == 1).first()
    fc = db.query(Forecast).filter(Forecast.facility_id == 1).first()
    rec = db.query(Recommendation).filter(Recommendation.recipient_facility_id == 1).first()
    rec_status_before = rec.status
    db.close()

    h = {"Authorization": "Bearer TEST-TOKEN-UID-ADMIN-99"}
    # Call all three explanation endpoints repeatedly
    for _ in range(3):
        client.get(f"/api/v1/alerts/{alert.id}/explanation", headers=h)
        client.get(f"/api/v1/forecasts/{fc.id}/explanation", headers=h)
        client.get(f"/api/v1/recommendations/{rec.id}/explanation", headers=h)

    db = TestingSessionLocal()
    stock_after = db.query(Inventory).filter(Inventory.facility_id == 1, Inventory.item_code == "MED-ORS-SACHET").first().quantity
    rec_after = db.query(Recommendation).filter(Recommendation.id == rec.id).first()
    db.close()

    assert stock_after == stock_before
    assert rec_after.status == rec_status_before


# ==============================================================
# 6. BACKWARD COMPATIBILITY
# ==============================================================

def test_existing_apis_remain_backward_compatible():
    """
    Existing list endpoints return inline explanation dictionaries while preserving existing keys.
    """
    h = {"Authorization": "Bearer TEST-TOKEN-UID-ADMIN-99"}
    
    # 1. /alerts
    res_alerts = client.get("/api/v1/alerts", headers=h)
    assert res_alerts.status_code == 200
    alerts = res_alerts.json()
    assert len(alerts) > 0
    assert "explanation" in alerts[0]
    assert alerts[0]["explanation"] is not None
    assert "alert_code" in alerts[0]
    assert "facility_name" in alerts[0]

    # 2. /forecasts
    res_fc = client.get("/api/v1/forecasts", headers=h)
    assert res_fc.status_code == 200
    forecasts = res_fc.json()
    assert len(forecasts) > 0
    assert "explanation" in forecasts[0]
    assert forecasts[0]["explanation"] is not None
    assert "days_of_cover" in forecasts[0]

    # 3. /recommendations
    res_rec = client.get("/api/v1/recommendations", headers=h)
    assert res_rec.status_code == 200
    recs = res_rec.json()
    assert len(recs) > 0
    assert "explanation" in recs[0]
    assert recs[0]["explanation"] is not None
    assert "haversine_distance_km" in recs[0]


# ==============================================================
# 7. AI ADVISOR EXPLAINABILITY QUERY
# ==============================================================

def test_ai_advisor_why_risk_returns_concrete_evidence():
    """
    AI Advisor responds to 'Why is Jatni CHC at critical risk?' with real evidence and reasons.
    """
    res = client.post(
        "/api/v1/advisor/chat",
        headers={"Authorization": "Bearer TEST-TOKEN-UID-ADMIN-99"},
        json={"message": "Why is Jatni CHC at critical risk?", "facility_id": 1}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["severity"] == "CRITICAL"
    assert data["requires_human_approval"] is True

    answer = data["answer"]
    assert "Jatni CHC" in answer
    assert "CRITICAL STOCKOUT RISK" in answer
    assert "Evidence:" in answer
    assert "Current stock: 15 sachets" in answer
    assert "Days of cover: 1.0 days" in answer
    assert "Why:" in answer
    assert "Recommended action:" in answer


def test_ai_advisor_why_recommendation_returns_concrete_evidence():
    """
    AI Advisor responds to queries asking why a redistribution recommendation was proposed.
    """
    res = client.post(
        "/api/v1/advisor/chat",
        headers={"Authorization": "Bearer TEST-TOKEN-UID-ADMIN-99"},
        json={"message": "Why transfer ORS from Pipili to Jatni?"}
    )
    assert res.status_code == 200
    data = res.json()

    answer = data["answer"]
    assert "REDISTRIBUTION RECOMMENDATION EXPLANATION" in answer or "Pipili PHC" in answer
    assert "Recipient current stock: 15" in answer
    assert "Donor surplus: 100" in answer
    assert "Why this recommendation:" in answer

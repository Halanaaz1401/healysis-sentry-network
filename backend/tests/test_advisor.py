import os
import sys
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

os.environ["TESTING"] = "true"

from app.config import settings
from datetime import datetime, date, timedelta
from app.database import Base, get_db, engine as db_engine
from app.models import (
    Facility, Medicine, Inventory, ConsumptionLog, Forecast, Alert, Recommendation, User,
    FacilityType, UserRole, MedicineCategory, ActionType, AlertSeverity, AlertType, AlertStatus
)

from app.schemas import AdvisorChatResponse
from app.advisor_tools import (
    get_facility_overview, get_resource_status, get_active_alerts,
    get_forecasts, get_redistribution_recommendations, get_facility_comparison,
    TOOL_MAP
)
from app.advisor_service import get_genai_client, run_grounded_ai_advisor, execute_tool_call

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
def setup_advisor_data():
    settings.TESTING = True
    Base.metadata.create_all(bind=db_engine)
    db = TestingSessionLocal()

    # Clean existing state
    db.query(Recommendation).delete()
    db.query(Alert).delete()
    db.query(Forecast).delete()
    db.query(ConsumptionLog).delete()
    db.query(Inventory).delete()
    db.query(User).delete()
    db.query(Facility).delete()
    db.query(Medicine).delete()
    db.commit()

    # Create Facilities
    fac_jatni = Facility(id=1, facility_code="CHC-OD-KHU-001", name="Jatni CHC (Khordha)", facility_type=FacilityType.CHC, state="OD", district="Khordha", latitude=20.165, longitude=85.705)
    fac_cuttack = Facility(id=2, facility_code="UPHC-OD-CTC-002", name="UPHC MS Das (Kafla Bazar)", facility_type=FacilityType.UPHC, state="OD", district="Cuttack", latitude=20.462, longitude=85.882)
    db.add_all([fac_jatni, fac_cuttack])
    db.commit()

    # Medicine
    med_ins = Medicine(id=1, code="MED-INSULIN-100IU", name="Insulin 100IU", category=MedicineCategory.VACCINE, unit="vials")
    db.add(med_ins)
    db.commit()

    # Inventory
    inv_jatni = Inventory(facility_id=fac_jatni.id, medicine_id=med_ins.id, item_code=med_ins.code, item_name=med_ins.name, quantity=5, safety_stock=40, incoming_quantity=0)
    db.add(inv_jatni)
    db.commit()

    # Forecast & Alert
    fc_jatni = Forecast(facility_id=fac_jatni.id, medicine_id=med_ins.id, item_code=med_ins.code, forecast_date=date.today(), expected_daily_demand=5.0, days_of_cover=1.0, confidence_score=0.95)
    alt_jatni = Alert(alert_code="ALT-JATNI-INS", facility_id=fac_jatni.id, resource_id=med_ins.code, severity=AlertSeverity.CRITICAL, alert_type=AlertType.STOCKOUT_PROJECTED, title="Critical Insulin Shortage", status=AlertStatus.ACTIVE)
    db.add_all([fc_jatni, alt_jatni])

    db.commit()

    # Users
    admin_user = User(firebase_uid="UID-ADMIN-ADV", email="admin.adv@healysis.gov.in", full_name="Admin Advisor", role=UserRole.ADMIN, facility_id=None)
    cdmo_user = User(firebase_uid="UID-CDMO-ADV", email="cdmo.adv@healysis.gov.in", full_name="CDMO Advisor", role=UserRole.CDMO, facility_id=None)
    officer_user = User(firebase_uid="UID-OFFICER-ADV", email="officer.adv@healysis.gov.in", full_name="Officer Advisor", role=UserRole.FACILITY_OFFICER, facility_id=fac_jatni.id)
    db.add_all([admin_user, cdmo_user, officer_user])
    db.commit()
    db.close()

    yield

# ==========================================
# 1. SDK Initialization & Configuration Tests
# ==========================================

def test_gemini_client_initialization_missing_key():
    settings.GEMINI_API_KEY = ""
    client_obj = get_genai_client()
    assert client_obj is None

def test_gemini_client_initialization_with_key():
    settings.GEMINI_API_KEY = "test-mock-api-key-12345"
    client_obj = get_genai_client()
    assert client_obj is not None
    settings.GEMINI_API_KEY = ""

# ==========================================
# 2. Tool Function & Argument Validation Tests
# ==========================================

def test_tool_execution_facility_overview():
    db = TestingSessionLocal()
    user = db.query(User).filter(User.firebase_uid == "UID-ADMIN-ADV").first()
    res = get_facility_overview(facility_id=1, current_user=user, db=db)
    db.close()
    assert res["facility_id"] == 1
    assert res["name"] == "Jatni CHC (Khordha)"
    assert res["active_alerts_count"] >= 1

def test_tool_execution_resource_status():
    db = TestingSessionLocal()
    user = db.query(User).filter(User.firebase_uid == "UID-ADMIN-ADV").first()
    res = get_resource_status(facility_id=1, resource_id="MED-INSULIN-100IU", current_user=user, db=db)
    db.close()
    assert res["current_stock"] == 5
    assert res["days_of_cover"] == 1.0
    assert res["risk_severity"] == "CRITICAL"

def test_unknown_tool_rejection():
    db = TestingSessionLocal()
    user = db.query(User).filter(User.firebase_uid == "UID-ADMIN-ADV").first()
    res = execute_tool_call("unknown_tool_xyz", {}, user, db)
    db.close()
    assert "Unknown tool requested" in res["error"]

# ==========================================
# 3. RBAC & Facility Scope Enforcement Tests
# ==========================================

def test_tool_facility_scope_enforcement_forbidden():
    db = TestingSessionLocal()
    officer = db.query(User).filter(User.firebase_uid == "UID-OFFICER-ADV").first()
    
    # Officer (facility_id=1) attempts to query facility_id=2 -> HTTPException 403
    with pytest.raises(Exception) as exc_info:
        get_facility_overview(facility_id=2, current_user=officer, db=db)
    db.close()
    assert "Forbidden" in str(exc_info.value)

def test_advisor_chat_endpoint_facility_officer_restricted_access():
    # Officer 1 attempts to query facility 2 via API -> 403 Forbidden
    res = client.post(
        "/api/v1/advisor/chat",
        headers={"Authorization": "Bearer TEST-TOKEN-UID-OFFICER-ADV"},
        json={"message": "Status report", "facility_id": 2}
    )
    assert res.status_code == 403
    assert "restricted to facility_id=1" in res.json()["detail"]

def test_advisor_chat_endpoint_cdmo_access_any_facility_success():
    res = client.post(
        "/api/v1/advisor/chat",
        headers={"Authorization": "Bearer TEST-TOKEN-UID-CDMO-ADV"},
        json={"message": "Status report for Cuttack", "facility_id": 2}
    )
    assert res.status_code == 200
    assert res.json()["requires_human_approval"] is True

def test_advisor_chat_endpoint_admin_access_success():
    res = client.post(
        "/api/v1/advisor/chat",
        headers={"Authorization": "Bearer TEST-TOKEN-UID-ADMIN-ADV"},
        json={"message": "Summarize critical risks across facilities"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["severity"] == "CRITICAL"
    assert "get_active_alerts" in data["data_sources"]

# ==========================================
# 4. Grounded Response & Safety Guard Tests
# ==========================================

def test_structured_response_validation_and_no_autonomous_approval():
    res = client.post(
        "/api/v1/advisor/chat",
        headers={"Authorization": "Bearer TEST-TOKEN-UID-ADMIN-ADV"},
        json={"message": "Why is Jatni at risk?"}
    )
    assert res.status_code == 200
    data = res.json()

    # Validate against Pydantic V2 schema
    parsed_resp = AdvisorChatResponse(**data)
    assert parsed_resp.requires_human_approval is True
    assert "human CDMO/Admin operational approval" in parsed_resp.limitations

def test_unavailable_data_query_response():
    res = client.post(
        "/api/v1/advisor/chat",
        headers={"Authorization": "Bearer TEST-TOKEN-UID-ADMIN-ADV"},
        json={"message": "What is the status of non_existent_medicine_xyz?"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["requires_human_approval"] is True

def test_deterministic_backend_values_preserved():
    db = TestingSessionLocal()
    admin = db.query(User).filter(User.firebase_uid == "UID-ADMIN-ADV").first()
    res = get_resource_status(facility_id=1, resource_id="MED-INSULIN-100IU", current_user=admin, db=db)
    db.close()

    # Preserved backend values
    assert res["current_stock"] == 5
    assert res["days_of_cover"] == 1.0

# ==========================================
# 5. Error & Fallback Resilience Tests
# ==========================================

def test_gemini_api_failure_fallback_graceful_response():
    # Simulate API exception
    with patch("app.advisor_service.get_genai_client") as mock_client_func:
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = Exception("Quota exceeded or API timeout")
        mock_client_func.return_value = mock_client

        res = client.post(
            "/api/v1/advisor/chat",
            headers={"Authorization": "Bearer TEST-TOKEN-UID-ADMIN-ADV"},
            json={"message": "Summarize Jatni insulin status"}
        )
        assert res.status_code == 200
        data = res.json()
        assert data["severity"] == "CRITICAL"
        assert len(data["evidence"]) >= 1

import os
import sys
from datetime import date, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

os.environ["TESTING"] = "true"

from app.config import settings
from app.database import Base, get_db, engine as db_engine
from app.models import (
    Facility, Medicine, Inventory, ConsumptionLog, Forecast, Alert, Recommendation, User, AuditEvent,
    FacilityType, UserRole, MedicineCategory, AlertSeverity, AlertType, AlertStatus, RecommendationStatus
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
def setup_network_test_data():
    settings.TESTING = True
    Base.metadata.create_all(bind=db_engine)
    db = TestingSessionLocal()

    db.query(AuditEvent).delete()
    db.query(Recommendation).delete()
    db.query(Alert).delete()
    db.query(Forecast).delete()
    db.query(ConsumptionLog).delete()
    db.query(Inventory).delete()
    db.query(User).delete()
    db.query(Facility).delete()
    db.query(Medicine).delete()
    db.commit()

    # 3 Facilities across 2 Districts (Khordha and Puri)
    fac_jatni = Facility(
        facility_code="CHC-OD-KHU-001",
        name="Jatni CHC (Khordha)",
        facility_type=FacilityType.CHC,
        state="OD",
        district="Khordha",
        latitude=20.165,
        longitude=85.705
    )
    fac_cuttack = Facility(
        facility_code="UPHC-OD-CTC-002",
        name="UPHC MS Das (Kafla Bazar)",
        facility_type=FacilityType.UPHC,
        state="OD",
        district="Cuttack",
        latitude=20.462,
        longitude=85.882
    )
    fac_pipili = Facility(
        facility_code="PHC-OD-PURI-004",
        name="Pipili PHC (Puri)",
        facility_type=FacilityType.PHC,
        state="OD",
        district="Puri",
        latitude=20.117,
        longitude=85.833
    )
    db.add_all([fac_jatni, fac_cuttack, fac_pipili])
    db.commit()

    # Medicines
    med_ors = Medicine(code="MED-ORS-SACHET", name="ORS Sachet", category=MedicineCategory.ESSENTIAL_MEDICINE, unit="sachets")
    med_ins = Medicine(code="MED-INSULIN-100IU", name="Insulin 100IU", category=MedicineCategory.VACCINE, unit="vials")
    db.add_all([med_ors, med_ins])
    db.commit()

    # Users
    user_admin = User(firebase_uid="UID-ADMIN-TEST", email="admin@healysis.gov.in", full_name="Admin User", role=UserRole.ADMIN, facility_id=None)
    user_cdmo = User(firebase_uid="UID-CDMO-TEST", email="cdmo@healysis.gov.in", full_name="CDMO User", role=UserRole.CDMO, facility_id=None)
    user_jatni_officer = User(firebase_uid="UID-JATNI-OFFICER", email="jatni.officer@healysis.gov.in", full_name="Jatni Officer", role=UserRole.FACILITY_OFFICER, facility_id=fac_jatni.id)
    db.add_all([user_admin, user_cdmo, user_jatni_officer])
    db.commit()

    # Inventories
    # Jatni: 15 ORS (Critical deficit: safety 40, demand 15/d => 1.0 day cover)
    inv_jatni_ors = Inventory(facility_id=fac_jatni.id, medicine_id=med_ors.id, item_code=med_ors.code, item_name=med_ors.name, quantity=15, safety_stock=40, incoming_quantity=0, unit="sachets")
    # Pipili: 180 ORS (Surplus: safety 40, demand 10/d => 18.0 days cover, surplus 140)
    inv_pipili_ors = Inventory(facility_id=fac_pipili.id, medicine_id=med_ors.id, item_code=med_ors.code, item_name=med_ors.name, quantity=180, safety_stock=40, incoming_quantity=0, unit="sachets")
    # Cuttack: 150 Insulin (Safe: safety 40, demand 5/d => 30.0 days cover)
    inv_cuttack_ins = Inventory(facility_id=fac_cuttack.id, medicine_id=med_ins.id, item_code=med_ins.code, item_name=med_ins.name, quantity=150, safety_stock=40, incoming_quantity=0, unit="vials")
    # Jatni: 5 Insulin (Critical deficit: safety 40, demand 10/d => 0.5 days cover)
    inv_jatni_ins = Inventory(facility_id=fac_jatni.id, medicine_id=med_ins.id, item_code=med_ins.code, item_name=med_ins.name, quantity=5, safety_stock=40, incoming_quantity=0, unit="vials")

    db.add_all([inv_jatni_ors, inv_pipili_ors, inv_cuttack_ins, inv_jatni_ins])
    db.commit()

    # Forecasts
    fc_jatni_ors = Forecast(facility_id=fac_jatni.id, medicine_id=med_ors.id, item_code=med_ors.code, forecast_date=date.today(), expected_daily_demand=15.0, days_of_cover=1.0, projected_stockout_date=date.today() + timedelta(days=1))
    fc_pipili_ors = Forecast(facility_id=fac_pipili.id, medicine_id=med_ors.id, item_code=med_ors.code, forecast_date=date.today(), expected_daily_demand=10.0, days_of_cover=18.0, projected_stockout_date=date.today() + timedelta(days=18))
    fc_cuttack_ins = Forecast(facility_id=fac_cuttack.id, medicine_id=med_ins.id, item_code=med_ins.code, forecast_date=date.today(), expected_daily_demand=5.0, days_of_cover=30.0, projected_stockout_date=date.today() + timedelta(days=30))
    fc_jatni_ins = Forecast(facility_id=fac_jatni.id, medicine_id=med_ins.id, item_code=med_ins.code, forecast_date=date.today(), expected_daily_demand=10.0, days_of_cover=0.5, projected_stockout_date=date.today())

    db.add_all([fc_jatni_ors, fc_pipili_ors, fc_cuttack_ins, fc_jatni_ins])
    db.commit()

    # Active Alert on Jatni
    alert_jatni = Alert(
        alert_code="ALT-TEST-JATNI-ORS",
        facility_id=fac_jatni.id,
        resource_id=med_ors.code,
        severity=AlertSeverity.CRITICAL,
        alert_type=AlertType.STOCKOUT_PROJECTED,
        title="Critical Stockout Projected for ORS Sachet",
        status=AlertStatus.ACTIVE
    )
    db.add(alert_jatni)
    db.commit()

    # Pending Recommendation
    rec = Recommendation(
        recommendation_code="REC-TEST-PIPILI-JATNI-ORS",
        donor_facility_id=fac_pipili.id,
        recipient_facility_id=fac_jatni.id,
        medicine_id=med_ors.id,
        item_code=med_ors.code,
        recommended_quantity=90,
        urgency_level="CRITICAL",
        reason="Pipili PHC has surplus 180 units while Jatni CHC faces stockout",
        status=RecommendationStatus.PENDING_HUMAN_APPROVAL
    )
    db.add(rec)
    db.commit()
    db.close()

    yield

# ==========================================
# 1. Network Totals & Overview Tests
# ==========================================

def test_network_intelligence_overview_cdmo():
    res = client.get("/api/v1/network/intelligence", headers={"Authorization": "Bearer TEST-TOKEN-UID-CDMO-TEST"})
    assert res.status_code == 200
    data = res.json()

    ov = data["overview"]
    assert ov["total_facilities"] == 3
    assert ov["total_resources_monitored"] == 2
    assert ov["total_stock_units"] == (15 + 180 + 150 + 5)  # 350
    assert ov["critical_facilities_count"] >= 1  # Jatni is critical
    assert ov["pending_redistribution_recommendations"] == 1
    assert ov["active_critical_alerts"] == 1
    assert "disclaimer" in data

def test_network_risk_summary_deterministic_classification():
    res = client.get("/api/v1/network/intelligence", headers={"Authorization": "Bearer TEST-TOKEN-UID-CDMO-TEST"})
    assert res.status_code == 200
    data = res.json()

    rs = data["risk_summary"]
    # With Jatni having items < 3.0 days cover and active critical alert, status must be CRITICAL
    assert rs["classification"] == "CRITICAL"
    assert "CRITICAL" in rs["headline"]
    assert len(rs["criteria_met"]) >= 1

# ==========================================
# 2. District Breakdown Tests
# ==========================================

def test_district_breakdown_aggregation():
    res = client.get("/api/v1/network/intelligence", headers={"Authorization": "Bearer TEST-TOKEN-UID-CDMO-TEST"})
    assert res.status_code == 200
    data = res.json()

    districts = {d["district"]: d for d in data["districts"]}
    assert "Khordha" in districts
    assert "Puri" in districts
    assert "Cuttack" in districts

    khordha = districts["Khordha"]
    assert khordha["facility_count"] == 1
    assert khordha["critical_facilities_count"] == 1
    assert khordha["total_inventory"] == 20  # 15 ORS + 5 Insulin
    assert khordha["resources_at_risk_count"] == 2
    assert khordha["active_alerts_count"] == 1
    assert khordha["pending_interventions_count"] == 1

    puri = districts["Puri"]
    assert puri["facility_count"] == 1
    assert puri["critical_facilities_count"] == 0
    assert puri["safe_facilities_count"] == 1
    assert puri["total_inventory"] == 180  # Pipili ORS
    assert puri["resources_surplus_count"] >= 1

# ==========================================
# 3. Resource Network Intelligence Tests
# ==========================================

def test_resource_intelligence_aggregation():
    res = client.get("/api/v1/network/intelligence", headers={"Authorization": "Bearer TEST-TOKEN-UID-CDMO-TEST"})
    assert res.status_code == 200
    data = res.json()

    resources = {r["item_code"]: r for r in data["resources"]}
    assert "MED-ORS-SACHET" in resources
    assert "MED-INSULIN-100IU" in resources

    ors = resources["MED-ORS-SACHET"]
    assert ors["total_network_stock"] == 195  # 15 + 180
    assert ors["total_daily_demand"] == 25.0  # 15.0 (Jatni) + 10.0 (Pipili)
    assert ors["network_days_of_cover"] == round(195 / 25.0, 2)
    assert ors["facilities_below_safety_count"] == 1  # Jatni
    assert ors["surplus_facilities_count"] == 1  # Pipili
    assert len(ors["potential_donors"]) >= 1
    assert len(ors["potential_recipients"]) >= 1

# ==========================================
# 4. Intervention Priority Queue Tests
# ==========================================

def test_intervention_priority_sorting():
    res = client.get("/api/v1/network/intelligence", headers={"Authorization": "Bearer TEST-TOKEN-UID-CDMO-TEST"})
    assert res.status_code == 200
    data = res.json()

    queue = data["intervention_priority"]
    assert len(queue) >= 2
    # Verify ranks are ordered 1, 2, ...
    ranks = [item["priority_rank"] for item in queue]
    assert ranks == list(range(1, len(queue) + 1))

    # All items in intervention queue must be CRITICAL or WARNING
    for item in queue:
        assert item["risk_severity"] in ["CRITICAL", "WARNING"]
        assert item["days_of_cover"] < 7.0 or item["current_stock"] < item["safety_stock"]
        assert len(item["suggested_action"]) > 5

    # Top item should be Jatni with either Insulin (0.5d cover) or ORS (1.0d cover)
    top = queue[0]
    assert top["facility_name"] == "Jatni CHC (Khordha)"
    assert top["risk_severity"] == "CRITICAL"

# ==========================================
# 5. RBAC & Isolation Security Tests
# ==========================================

def test_cdmo_and_admin_have_network_access():
    res_cdmo = client.get("/api/v1/network/intelligence", headers={"Authorization": "Bearer TEST-TOKEN-UID-CDMO-TEST"})
    assert res_cdmo.status_code == 200

    res_admin = client.get("/api/v1/network/intelligence", headers={"Authorization": "Bearer TEST-TOKEN-UID-ADMIN-TEST"})
    assert res_admin.status_code == 200

def test_facility_officer_forbidden_403_network_access():
    res_officer = client.get("/api/v1/network/intelligence", headers={"Authorization": "Bearer TEST-TOKEN-UID-JATNI-OFFICER"})
    assert res_officer.status_code == 403
    assert "Forbidden" in res_officer.json()["detail"]

def test_unauthenticated_request_rejected_401():
    res = client.get("/api/v1/network/intelligence")
    assert res.status_code == 401

# ==========================================
# 6. Read-Only Immutability Tests
# ==========================================

def test_network_intelligence_does_not_mutate_database():
    db = TestingSessionLocal()
    jatni_ors_before = db.query(Inventory).filter(Inventory.facility_id == 1, Inventory.item_code == "MED-ORS-SACHET").first().quantity
    pipili_ors_before = db.query(Inventory).filter(Inventory.facility_id == 3, Inventory.item_code == "MED-ORS-SACHET").first().quantity
    alerts_count_before = db.query(Alert).count()
    recs_count_before = db.query(Recommendation).count()
    audit_count_before = db.query(AuditEvent).count()
    db.close()

    # Invoke network intelligence endpoint 5 times
    for _ in range(5):
        res = client.get("/api/v1/network/intelligence", headers={"Authorization": "Bearer TEST-TOKEN-UID-CDMO-TEST"})
        assert res.status_code == 200

    db2 = TestingSessionLocal()
    assert db2.query(Inventory).filter(Inventory.facility_id == 1, Inventory.item_code == "MED-ORS-SACHET").first().quantity == jatni_ors_before
    assert db2.query(Inventory).filter(Inventory.facility_id == 3, Inventory.item_code == "MED-ORS-SACHET").first().quantity == pipili_ors_before
    assert db2.query(Alert).count() == alerts_count_before
    assert db2.query(Recommendation).count() == recs_count_before
    assert db2.query(AuditEvent).count() == audit_count_before
    db2.close()

# ==========================================
# 7. AI Advisor Network Intent Queries Tests
# ==========================================

def test_ai_advisor_which_districts_highest_stockout_risk():
    req_body = {
        "message": "Which districts have the highest stockout risk?"
    }
    res = client.post("/api/v1/advisor/chat", json=req_body, headers={"Authorization": "Bearer TEST-TOKEN-UID-CDMO-TEST"})
    assert res.status_code == 200
    data = res.json()
    ans = data["answer"]

    assert "DISTRICT & NETWORK INTELLIGENCE" in ans
    assert "Khordha" in ans
    assert "CRITICAL" in ans
    assert "Authoritative network intelligence aggregated from verified facility records" in ans

def test_ai_advisor_how_many_facilities_at_critical_risk():
    req_body = {
        "message": "How many facilities are currently at critical risk across the network?"
    }
    res = client.post("/api/v1/advisor/chat", json=req_body, headers={"Authorization": "Bearer TEST-TOKEN-UID-CDMO-TEST"})
    assert res.status_code == 200
    data = res.json()
    ans = data["answer"]

    assert "DISTRICT & NETWORK INTELLIGENCE" in ans
    assert "Critical" in ans
    assert "Jatni CHC" in ans or "Khordha" in ans

def test_ai_advisor_show_me_network_stock_situation():
    req_body = {
        "message": "Show me the network stock situation."
    }
    res = client.post("/api/v1/advisor/chat", json=req_body, headers={"Authorization": "Bearer TEST-TOKEN-UID-CDMO-TEST"})
    assert res.status_code == 200
    data = res.json()
    ans = data["answer"]

    assert "DISTRICT & NETWORK INTELLIGENCE" in ans
    assert "350 units" in ans or "350" in ans
    assert "ORS Sachet" in ans

def test_ai_advisor_facility_officer_cannot_view_network_intelligence():
    req_body = {
        "message": "Which districts have the highest stockout risk?"
    }
    res = client.post("/api/v1/advisor/chat", json=req_body, headers={"Authorization": "Bearer TEST-TOKEN-UID-JATNI-OFFICER"})
    assert res.status_code == 200
    data = res.json()
    assert "restricted to cdmo and admin roles" in data["answer"].lower()

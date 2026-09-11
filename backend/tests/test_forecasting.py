import os
import sys
from datetime import datetime, date, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

os.environ["TESTING"] = "true"

from app.config import settings
from app.database import Base, get_db, engine as db_engine
from app.models import (
    Facility, Medicine, Inventory, ConsumptionLog, Forecast, Alert, User,
    FacilityType, UserRole, MedicineCategory, ActionType, AlertSeverity, AlertStatus
)
from app.algorithms import (
    calculate_7day_velocity, calculate_ewma_demand, calculate_days_of_cover,
    calculate_projected_stockout_date, classify_risk_severity, run_forecast_and_alert_engine
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
def setup_forecasting_data():
    settings.TESTING = True
    Base.metadata.create_all(bind=db_engine)
    db = TestingSessionLocal()

    # Clean existing data
    db.query(Alert).delete()
    db.query(Forecast).delete()
    db.query(ConsumptionLog).delete()
    db.query(Inventory).delete()
    db.query(User).delete()
    db.query(Facility).delete()
    db.query(Medicine).delete()
    db.commit()

    # 1. Odisha Facility
    fac_od = Facility(
        facility_code="CHC-OD-KHU-001",
        name="Jatni CHC (Khordha)",
        facility_type=FacilityType.CHC,
        state="OD",
        district="Khordha",
        latitude=20.165,
        longitude=85.705
    )
    # 2. West Bengal Facility
    fac_wb = Facility(
        facility_code="UPHC-WB-KOL-012",
        name="Behala Urban PHC (Kolkata)",
        facility_type=FacilityType.UPHC,
        state="WB",
        district="Kolkata",
        latitude=22.501,
        longitude=88.312
    )
    db.add_all([fac_od, fac_wb])
    db.commit()

    # Medicine
    med_ors = Medicine(code="MED-ORS-SACHET", name="ORS Sachet", category=MedicineCategory.ESSENTIAL_MEDICINE, unit="sachets")
    med_ins = Medicine(code="MED-INSULIN-100IU", name="Insulin 100IU", category=MedicineCategory.VACCINE, unit="vials")
    db.add_all([med_ors, med_ins])
    db.commit()

    # Inventory Odisha (ORS Safe, Insulin Critical)
    inv_od_ors = Inventory(facility_id=fac_od.id, medicine_id=med_ors.id, item_code=med_ors.code, item_name=med_ors.name, quantity=200, safety_stock=40, incoming_quantity=50)
    inv_od_ins = Inventory(facility_id=fac_od.id, medicine_id=med_ins.id, item_code=med_ins.code, item_name=med_ins.name, quantity=10, safety_stock=40, incoming_quantity=0)
    
    # Inventory WB (ORS Warning)
    inv_wb_ors = Inventory(facility_id=fac_wb.id, medicine_id=med_ors.id, item_code=med_ors.code, item_name=med_ors.name, quantity=45, safety_stock=40, incoming_quantity=10)
    db.add_all([inv_od_ors, inv_od_ins, inv_wb_ors])
    db.commit()

    # Users
    user_od_officer = User(firebase_uid="UID-OD-OFFICER", email="od.officer@healysis.gov.in", full_name="Odisha Officer", role=UserRole.FACILITY_OFFICER, facility_id=fac_od.id)
    user_wb_officer = User(firebase_uid="UID-WB-OFFICER", email="wb.officer@healysis.gov.in", full_name="WB Officer", role=UserRole.FACILITY_OFFICER, facility_id=fac_wb.id)
    user_cdmo = User(firebase_uid="UID-CDMO-HQ", email="cdmo.director@healysis.gov.in", full_name="CDMO Director", role=UserRole.CDMO, facility_id=None)
    db.add_all([user_od_officer, user_wb_officer, user_cdmo])
    db.commit()

    # 7 Days Consumption for Odisha ORS (10 units per day)
    today = date.today()
    for d in range(7, 0, -1):
        c = ConsumptionLog(facility_id=fac_od.id, medicine_id=med_ors.id, item_code=med_ors.code, date=today - timedelta(days=d), quantity_dispensed=10, patient_footfall=30, action_type=ActionType.DISPENSE)
        db.add(c)

    # 7 Days Consumption for Odisha Insulin (5 units per day)
    for d in range(7, 0, -1):
        c = ConsumptionLog(facility_id=fac_od.id, medicine_id=med_ins.id, item_code=med_ins.code, date=today - timedelta(days=d), quantity_dispensed=5, patient_footfall=20, action_type=ActionType.DISPENSE)
        db.add(c)

    # 7 Days Consumption for WB ORS (10 units per day)
    for d in range(7, 0, -1):
        c = ConsumptionLog(facility_id=fac_wb.id, medicine_id=med_ors.id, item_code=med_ors.code, date=today - timedelta(days=d), quantity_dispensed=10, patient_footfall=25, action_type=ActionType.DISPENSE)
        db.add(c)

    db.commit()
    db.close()

    yield

# ==========================================
# 1. Unit Tests for Forecasting Math & Risk Rules
# ==========================================

def test_7day_consumption_velocity():
    db = TestingSessionLocal()
    fac = db.query(Facility).filter(Facility.facility_code == "CHC-OD-KHU-001").first()
    med = db.query(Medicine).filter(Medicine.code == "MED-ORS-SACHET").first()
    logs = db.query(ConsumptionLog).filter(ConsumptionLog.facility_id == fac.id, ConsumptionLog.medicine_id == med.id).all()
    db.close()

    v7 = calculate_7day_velocity(logs)
    assert v7 == 10.0  # 70 units over 7 days = 10.0/day

def test_ewma_calculation():
    db = TestingSessionLocal()
    fac = db.query(Facility).filter(Facility.facility_code == "CHC-OD-KHU-001").first()
    med = db.query(Medicine).filter(Medicine.code == "MED-ORS-SACHET").first()
    logs = db.query(ConsumptionLog).filter(ConsumptionLog.facility_id == fac.id, ConsumptionLog.medicine_id == med.id).all()
    db.close()

    ewma = calculate_ewma_demand(logs, alpha=0.3)
    assert ewma == 10.0  # Constant 10 per day yields EWMA of 10.0

def test_zero_consumption_handling():
    v7 = calculate_7day_velocity([])
    ewma = calculate_ewma_demand([])
    assert v7 == 0.0
    assert ewma == 0.0

def test_zero_stock_handling():
    doc = calculate_days_of_cover(current_stock=0, incoming_stock=0, expected_daily_demand=10.0)
    assert doc == 0.0

def test_days_of_cover_and_incoming_stock_handling():
    # stock = 200, incoming = 50, demand = 10.0 => (200 + 50) / 10 = 25.0 days
    doc = calculate_days_of_cover(current_stock=200, incoming_stock=50, expected_daily_demand=10.0)
    assert doc == 25.0

def test_safety_stock_threshold_and_risk_classifications():
    # SAFE: days_of_cover >= 7 and current_stock >= safety_stock
    sev_safe = classify_risk_severity(days_of_cover=25.0, current_stock=200, safety_stock=40)
    assert sev_safe == AlertSeverity.LOW

    # WARNING: 3.0 <= days_of_cover < 7.0 or stock < safety_stock
    sev_warn = classify_risk_severity(days_of_cover=5.5, current_stock=55, safety_stock=40)
    assert sev_warn == AlertSeverity.WARNING

    # CRITICAL: days_of_cover < 3.0 or stock == 0
    sev_crit = classify_risk_severity(days_of_cover=2.0, current_stock=10, safety_stock=40)
    assert sev_crit == AlertSeverity.CRITICAL

def test_projected_stockout_calculation():
    today = date.today()
    depletion_date = calculate_projected_stockout_date(today, days_of_cover=5.0)
    assert depletion_date == today + timedelta(days=5)

def test_deterministic_reproducible_output():
    db = TestingSessionLocal()
    fac = db.query(Facility).filter(Facility.facility_code == "CHC-OD-KHU-001").first()
    med = db.query(Medicine).filter(Medicine.code == "MED-ORS-SACHET").first()
    logs = db.query(ConsumptionLog).filter(ConsumptionLog.facility_id == fac.id, ConsumptionLog.medicine_id == med.id).all()
    db.close()

    v1 = calculate_7day_velocity(logs)
    v2 = calculate_7day_velocity(logs)
    assert v1 == v2

# ==========================================
# 2. Integration Tests for Forecast & Alert Persistence
# ==========================================

def test_forecast_and_alert_persistence():
    db = TestingSessionLocal()
    generated_forecasts, generated_alerts = run_forecast_and_alert_engine(db)
    
    # Check Forecast persistence
    saved_forecasts = db.query(Forecast).all()
    assert len(saved_forecasts) >= 3

    # Check Alert persistence
    saved_alerts = db.query(Alert).all()
    assert len(saved_alerts) >= 2  # Insulin at Odisha (CRITICAL) + ORS at WB (WARNING)
    db.close()

# ==========================================
# 3. Seeded Regional Facility & API Tests (Odisha & West Bengal)
# ==========================================

def test_seeded_odisha_facility_forecasts_and_alerts():
    db = TestingSessionLocal()
    run_forecast_and_alert_engine(db)
    fac_od = db.query(Facility).filter(Facility.facility_code == "CHC-OD-KHU-001").first()
    db.close()

    # Test Odisha Officer API access (Assigned Facility)
    res_forecast = client.get(f"/api/v1/facilities/{fac_od.id}/forecasts", headers={"Authorization": "Bearer TEST-TOKEN-UID-OD-OFFICER"})
    assert res_forecast.status_code == 200
    forecasts = res_forecast.json()
    assert len(forecasts) == 2

    res_alerts = client.get(f"/api/v1/facilities/{fac_od.id}/alerts", headers={"Authorization": "Bearer TEST-TOKEN-UID-OD-OFFICER"})
    assert res_alerts.status_code == 200
    alerts = res_alerts.json()
    assert len(alerts) >= 1
    assert alerts[0]["severity"] == "CRITICAL"  # Insulin stockout risk

def test_seeded_west_bengal_facility_forecasts_and_alerts():
    db = TestingSessionLocal()
    run_forecast_and_alert_engine(db)
    fac_wb = db.query(Facility).filter(Facility.facility_code == "UPHC-WB-KOL-012").first()
    db.close()

    # Test WB Officer API access (Assigned Facility)
    res_forecast = client.get(f"/api/v1/facilities/{fac_wb.id}/forecasts", headers={"Authorization": "Bearer TEST-TOKEN-UID-WB-OFFICER"})
    assert res_forecast.status_code == 200
    forecasts = res_forecast.json()
    assert len(forecasts) == 1

    res_alerts = client.get(f"/api/v1/facilities/{fac_wb.id}/alerts", headers={"Authorization": "Bearer TEST-TOKEN-UID-WB-OFFICER"})
    assert res_alerts.status_code == 200
    alerts = res_alerts.json()
    assert len(alerts) >= 1
    assert alerts[0]["severity"] == "WARNING"

def test_facility_scoped_authorization_enforcement():
    db = TestingSessionLocal()
    fac_wb = db.query(Facility).filter(Facility.facility_code == "UPHC-WB-KOL-012").first()
    db.close()

    # Odisha Officer tries to access West Bengal facility forecasts -> FORBIDDEN (403)
    res = client.get(f"/api/v1/facilities/{fac_wb.id}/forecasts", headers={"Authorization": "Bearer TEST-TOKEN-UID-OD-OFFICER"})
    assert res.status_code == 403
    assert "restricted to facility_id=" in res.json()["detail"]

    # CDMO Director accesses West Bengal facility forecasts -> AUTHORIZED (200)
    res_cdmo = client.get(f"/api/v1/facilities/{fac_wb.id}/forecasts", headers={"Authorization": "Bearer TEST-TOKEN-UID-CDMO-HQ"})
    assert res_cdmo.status_code == 200

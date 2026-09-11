"""
test_post_approval_consistency.py

Tests that after a redistribution approval:
  1. Donor stock quantity decreases correctly.
  2. Recipient stock quantity increases correctly.
  3. Forecast (days_of_cover) is recalculated from updated inventory.
  4. Stockout date reflects updated stock/demand state.
  5. Risk severity is recalculated from current data (not stale values).
  6. Stale CRITICAL/WARNING alerts are resolved when stock returns to safe.
  7. ACTIVE alerts remain when stock is still at risk after transfer.
  8. Forecast values are consistent with the deterministic EWMA/7-day implementation.
  9. No hardcoded risk or forecast values — all derived from live inventory.
"""
import os
import sys
from datetime import date, timedelta, datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ["TESTING"] = "true"

from app.config import settings
from app.database import Base, get_db, engine as db_engine
from app.models import (
    Facility, Medicine, Inventory, Recommendation, User, Alert, Forecast,
    ConsumptionLog, AuditEvent,
    FacilityType, UserRole, MedicineCategory, RecommendationStatus,
    UrgencyLevel, AlertStatus, AlertSeverity, ActionType,
)
from app.algorithms import (
    run_forecast_and_alert_engine,
    calculate_days_of_cover,
    calculate_projected_stockout_date,
    classify_risk_severity,
    calculate_ewma_demand,
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

CDMO_TOKEN = "Bearer TEST-TOKEN-UID-CDMO-88"


@pytest.fixture(autouse=True)
def clean_db():
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
    db.close()
    yield


@pytest.fixture()
def db_session():
    db = TestingSessionLocal()
    yield db
    db.close()


# ── Shared seed helper ──────────────────────────────────────────────────────

def _seed(db, donor_qty=150, recip_qty=5, rec_qty=50, donor_daily_demand=2.0, recip_daily_demand=10.0):
    """
    Creates two facilities, one medicine, inventory records, consumption history,
    and one PENDING recommendation. Returns a dict of all objects.
    """
    fac_donor = Facility(
        facility_code="FAC-DONOR-01", name="Donor CHC",
        facility_type=FacilityType.CHC, state="OD", district="Khordha",
        latitude=20.165, longitude=85.705,
    )
    fac_recip = Facility(
        facility_code="FAC-RECIP-01", name="Recipient PHC",
        facility_type=FacilityType.PHC, state="OD", district="Puri",
        latitude=20.117, longitude=85.833,
    )
    db.add_all([fac_donor, fac_recip])
    db.commit()

    med = Medicine(code="MED-INS-TEST", name="Test Insulin", category=MedicineCategory.VACCINE, unit="vials")
    db.add(med)
    db.commit()

    cdmo = User(firebase_uid="UID-CDMO-88", email="cdmo@healysis.gov.in",
                full_name="CDMO Director", role=UserRole.CDMO)
    db.add(cdmo)
    db.commit()

    inv_donor = Inventory(
        facility_id=fac_donor.id, medicine_id=med.id,
        item_code=med.code, item_name=med.name,
        quantity=donor_qty, safety_stock=40, incoming_quantity=0, unit=med.unit,
    )
    inv_recip = Inventory(
        facility_id=fac_recip.id, medicine_id=med.id,
        item_code=med.code, item_name=med.name,
        quantity=recip_qty, safety_stock=40, incoming_quantity=0, unit=med.unit,
    )
    db.add_all([inv_donor, inv_recip])
    db.commit()

    today = date.today()
    for d in range(7, 0, -1):
        db.add(ConsumptionLog(
            facility_id=fac_donor.id, medicine_id=med.id,
            item_code=med.code, date=today - timedelta(days=d),
            quantity_dispensed=int(donor_daily_demand), patient_footfall=20,
            action_type=ActionType.DISPENSE,
        ))
        db.add(ConsumptionLog(
            facility_id=fac_recip.id, medicine_id=med.id,
            item_code=med.code, date=today - timedelta(days=d),
            quantity_dispensed=int(recip_daily_demand), patient_footfall=40,
            action_type=ActionType.DISPENSE,
        ))
    db.commit()

    rec = Recommendation(
        recommendation_code="REC-TEST-CONSISTENCY",
        donor_facility_id=fac_donor.id,
        recipient_facility_id=fac_recip.id,
        medicine_id=med.id,
        item_code=med.code,
        recommended_quantity=rec_qty,
        urgency_level=UrgencyLevel.CRITICAL,
        haversine_distance_km=45.5,
        expected_days_cover_gained=5.0,
        confidence_score=0.92,
        reason="Test.",
        status=RecommendationStatus.PENDING_HUMAN_APPROVAL,
    )
    db.add(rec)
    db.commit()
    db.refresh(inv_donor); db.refresh(inv_recip); db.refresh(rec)
    return dict(
        fac_donor=fac_donor, fac_recip=fac_recip, med=med,
        inv_donor=inv_donor, inv_recip=inv_recip, rec=rec,
        donor_daily_demand=donor_daily_demand,
        recip_daily_demand=recip_daily_demand,
    )


# ── 1. Stock quantity correctness ───────────────────────────────────────────

class TestStockQuantityAfterApproval:

    def test_donor_stock_decremented_by_exact_transfer_amount(self, db_session):
        s = _seed(db_session, donor_qty=150, rec_qty=50)
        res = client.post(
            f"/api/v1/recommendations/{s['rec'].id}/action",
            json={"action": "APPROVE"},
            headers={"Authorization": CDMO_TOKEN},
        )
        assert res.status_code == 200
        db_session.expire_all()
        inv = db_session.query(Inventory).filter(
            Inventory.facility_id == s["fac_donor"].id,
            Inventory.medicine_id == s["med"].id,
        ).first()
        assert inv.quantity == 150 - 50

    def test_recipient_stock_incremented_by_exact_transfer_amount(self, db_session):
        s = _seed(db_session, recip_qty=5, rec_qty=50)
        client.post(
            f"/api/v1/recommendations/{s['rec'].id}/action",
            json={"action": "APPROVE"},
            headers={"Authorization": CDMO_TOKEN},
        )
        db_session.expire_all()
        inv = db_session.query(Inventory).filter(
            Inventory.facility_id == s["fac_recip"].id,
            Inventory.medicine_id == s["med"].id,
        ).first()
        assert inv.quantity == 5 + 50


# ── 2. Forecast consistency ─────────────────────────────────────────────────

class TestForecastConsistencyAfterApproval:

    def test_recipient_forecast_days_of_cover_updated_after_approval(self, db_session):
        """
        Recipient has 5 units, daily demand ~10. After receiving 50 units (total 55),
        days_of_cover should increase significantly from ~0.5 to ~5.5.
        The forecast engine must use the new quantity.
        """
        s = _seed(db_session, recip_qty=5, rec_qty=50, recip_daily_demand=10.0)

        # Seed forecast engine first to create a baseline pre-approval forecast
        run_forecast_and_alert_engine(db_session)
        db_session.expire_all()

        pre_fc = db_session.query(Forecast).filter(
            Forecast.facility_id == s["fac_recip"].id,
            Forecast.medicine_id == s["med"].id,
        ).first()
        pre_doc = pre_fc.days_of_cover if pre_fc else 0.0

        # Approve — transfer committed, then forecast engine re-runs
        client.post(
            f"/api/v1/recommendations/{s['rec'].id}/action",
            json={"action": "APPROVE"},
            headers={"Authorization": CDMO_TOKEN},
        )
        db_session.expire_all()

        post_fc = db_session.query(Forecast).filter(
            Forecast.facility_id == s["fac_recip"].id,
            Forecast.medicine_id == s["med"].id,
        ).first()
        assert post_fc is not None
        # Days of cover must have improved (recipient received more stock)
        assert post_fc.days_of_cover > pre_doc

    def test_donor_forecast_days_of_cover_updated_after_approval(self, db_session):
        """
        Donor starts with 150 units. After donating 50, it has 100. DoC must reflect 100.
        """
        s = _seed(db_session, donor_qty=150, rec_qty=50, donor_daily_demand=2.0)
        run_forecast_and_alert_engine(db_session)
        db_session.expire_all()

        pre_fc = db_session.query(Forecast).filter(
            Forecast.facility_id == s["fac_donor"].id,
            Forecast.medicine_id == s["med"].id,
        ).first()
        pre_doc = pre_fc.days_of_cover if pre_fc else 999.0

        client.post(
            f"/api/v1/recommendations/{s['rec'].id}/action",
            json={"action": "APPROVE"},
            headers={"Authorization": CDMO_TOKEN},
        )
        db_session.expire_all()

        post_fc = db_session.query(Forecast).filter(
            Forecast.facility_id == s["fac_donor"].id,
            Forecast.medicine_id == s["med"].id,
        ).first()
        assert post_fc is not None
        # DoC must decrease (donor gave away stock)
        assert post_fc.days_of_cover < pre_doc

    def test_forecast_days_of_cover_matches_deterministic_formula(self, db_session):
        """
        Verify the forecast engine's days_of_cover is exactly what
        calculate_days_of_cover() returns for the post-transfer inventory state.
        """
        s = _seed(db_session, recip_qty=5, rec_qty=50, recip_daily_demand=10.0)
        client.post(
            f"/api/v1/recommendations/{s['rec'].id}/action",
            json={"action": "APPROVE"},
            headers={"Authorization": CDMO_TOKEN},
        )
        db_session.expire_all()

        inv = db_session.query(Inventory).filter(
            Inventory.facility_id == s["fac_recip"].id,
            Inventory.medicine_id == s["med"].id,
        ).first()

        # Recompute EWMA / velocity using the same consumption logs the engine uses
        today = date.today()
        logs = db_session.query(ConsumptionLog).filter(
            ConsumptionLog.facility_id == s["fac_recip"].id,
            ConsumptionLog.medicine_id == s["med"].id,
            ConsumptionLog.date >= today - timedelta(days=30),
        ).order_by(ConsumptionLog.date.asc()).all()
        from app.algorithms import calculate_ewma_demand, calculate_7day_velocity
        ewma = calculate_ewma_demand(logs)
        v7 = calculate_7day_velocity(logs)
        expected_demand = ewma if ewma > 0 else v7

        expected_doc = calculate_days_of_cover(inv.quantity, inv.incoming_quantity, expected_demand)

        fc = db_session.query(Forecast).filter(
            Forecast.facility_id == s["fac_recip"].id,
            Forecast.medicine_id == s["med"].id,
        ).first()
        assert fc is not None
        assert abs(fc.days_of_cover - expected_doc) < 0.01

    def test_stockout_date_reflects_post_transfer_state(self, db_session):
        """
        Pre-transfer: recipient has 5 units at 10/day → stockout in 0 days.
        Post-transfer: recipient has 55 units → stockout date is in the future.
        """
        s = _seed(db_session, recip_qty=5, rec_qty=50, recip_daily_demand=10.0)
        run_forecast_and_alert_engine(db_session)
        db_session.expire_all()

        pre_fc = db_session.query(Forecast).filter(
            Forecast.facility_id == s["fac_recip"].id,
            Forecast.medicine_id == s["med"].id,
        ).first()
        pre_stockout = pre_fc.projected_stockout_date if pre_fc else None

        client.post(
            f"/api/v1/recommendations/{s['rec'].id}/action",
            json={"action": "APPROVE"},
            headers={"Authorization": CDMO_TOKEN},
        )
        db_session.expire_all()

        post_fc = db_session.query(Forecast).filter(
            Forecast.facility_id == s["fac_recip"].id,
            Forecast.medicine_id == s["med"].id,
        ).first()
        assert post_fc is not None
        # Stockout date must have moved further into the future (or been cleared)
        if pre_stockout and post_fc.projected_stockout_date:
            assert post_fc.projected_stockout_date > pre_stockout


# ── 3. Risk severity consistency ────────────────────────────────────────────

class TestRiskSeverityAfterApproval:

    def test_recipient_severity_recalculated_from_current_inventory(self, db_session):
        """
        Recipient was CRITICAL (5 units, 10/day, DoC < 1).
        After receiving 100 units: DoC >> 7, severity must be LOW.
        """
        s = _seed(db_session, recip_qty=5, rec_qty=100, recip_daily_demand=10.0)
        # Plant a CRITICAL alert to simulate the pre-approval state
        alert_code = f"ALT-{s['fac_recip'].facility_code}-{s['med'].code}"
        alert = Alert(
            alert_code=alert_code,
            facility_id=s["fac_recip"].id,
            resource_id=s["med"].code,
            severity=AlertSeverity.CRITICAL,
            alert_type="STOCKOUT_PROJECTED",
            title="Critical Stockout Projected for Test Insulin",
            evidence_json={},
            status=AlertStatus.ACTIVE,
        )
        db_session.add(alert)
        db_session.commit()

        client.post(
            f"/api/v1/recommendations/{s['rec'].id}/action",
            json={"action": "APPROVE"},
            headers={"Authorization": CDMO_TOKEN},
        )
        db_session.expire_all()

        # After 100 units arrive at recip (had 5, now 105), DoC = 105/10 = 10.5 → LOW
        inv = db_session.query(Inventory).filter(
            Inventory.facility_id == s["fac_recip"].id,
            Inventory.medicine_id == s["med"].id,
        ).first()
        severity = classify_risk_severity(
            calculate_days_of_cover(inv.quantity, inv.incoming_quantity, 10.0),
            inv.quantity,
            inv.safety_stock,
        )
        assert severity == AlertSeverity.LOW

    def test_donor_severity_correct_after_stock_reduction(self, db_session):
        """
        Donor has 150 units, daily demand 2 → DoC = 75 → LOW.
        After donating 50, donor has 100, DoC = 50 → still LOW.
        """
        s = _seed(db_session, donor_qty=150, rec_qty=50, donor_daily_demand=2.0)
        client.post(
            f"/api/v1/recommendations/{s['rec'].id}/action",
            json={"action": "APPROVE"},
            headers={"Authorization": CDMO_TOKEN},
        )
        db_session.expire_all()

        inv = db_session.query(Inventory).filter(
            Inventory.facility_id == s["fac_donor"].id,
            Inventory.medicine_id == s["med"].id,
        ).first()
        doc = calculate_days_of_cover(inv.quantity, inv.incoming_quantity, 2.0)
        severity = classify_risk_severity(doc, inv.quantity, inv.safety_stock)
        assert severity == AlertSeverity.LOW
        assert inv.quantity == 100


# ── 4. Alert resolution (the stale-alert bug) ───────────────────────────────

class TestAlertResolutionAfterApproval:

    def test_critical_alert_resolved_when_stock_becomes_safe(self, db_session):
        """
        BUG FIX: Recipient was CRITICAL. After receiving enough stock to exceed 7 days
        of cover, the existing CRITICAL alert must be RESOLVED, not left ACTIVE.
        """
        s = _seed(db_session, recip_qty=5, rec_qty=100, recip_daily_demand=10.0)
        alert_code = f"ALT-{s['fac_recip'].facility_code}-{s['med'].code}"
        alert = Alert(
            alert_code=alert_code,
            facility_id=s["fac_recip"].id,
            resource_id=s["med"].code,
            severity=AlertSeverity.CRITICAL,
            alert_type="STOCKOUT_PROJECTED",
            title="Critical Stockout Projected for Test Insulin",
            evidence_json={},
            status=AlertStatus.ACTIVE,
        )
        db_session.add(alert)
        db_session.commit()
        alert_id = alert.id

        client.post(
            f"/api/v1/recommendations/{s['rec'].id}/action",
            json={"action": "APPROVE"},
            headers={"Authorization": CDMO_TOKEN},
        )
        db_session.expire_all()

        resolved = db_session.query(Alert).filter(Alert.id == alert_id).first()
        assert resolved is not None
        assert resolved.status == AlertStatus.RESOLVED, (
            f"Expected RESOLVED, got {resolved.status}. "
            "Stale CRITICAL alert was not resolved after redistribution raised stock to safe level."
        )

    def test_warning_alert_resolved_when_stock_becomes_safe(self, db_session):
        """
        Same as above but starting from WARNING severity.
        """
        s = _seed(db_session, recip_qty=20, rec_qty=80, recip_daily_demand=10.0)
        alert_code = f"ALT-{s['fac_recip'].facility_code}-{s['med'].code}"
        alert = Alert(
            alert_code=alert_code,
            facility_id=s["fac_recip"].id,
            resource_id=s["med"].code,
            severity=AlertSeverity.WARNING,
            alert_type="STOCKOUT_PROJECTED",
            title="Stock Warning: Test Insulin",
            evidence_json={},
            status=AlertStatus.ACTIVE,
        )
        db_session.add(alert)
        db_session.commit()
        alert_id = alert.id

        # After receiving 80, total = 100. DoC = 100/10 = 10 → LOW → RESOLVED
        client.post(
            f"/api/v1/recommendations/{s['rec'].id}/action",
            json={"action": "APPROVE"},
            headers={"Authorization": CDMO_TOKEN},
        )
        db_session.expire_all()

        resolved = db_session.query(Alert).filter(Alert.id == alert_id).first()
        assert resolved.status == AlertStatus.RESOLVED

    def test_alert_remains_active_when_stock_still_at_risk(self, db_session):
        """
        Recipient receives only a small transfer that doesn't bring it to safe level.
        The alert should remain ACTIVE (or still be WARNING/CRITICAL).
        Transfer: 5 units. Recipient: 5 → 10. DoC = 10/10 = 1.0 → CRITICAL.
        """
        s = _seed(db_session, recip_qty=5, rec_qty=5, recip_daily_demand=10.0)
        alert_code = f"ALT-{s['fac_recip'].facility_code}-{s['med'].code}"
        alert = Alert(
            alert_code=alert_code,
            facility_id=s["fac_recip"].id,
            resource_id=s["med"].code,
            severity=AlertSeverity.CRITICAL,
            alert_type="STOCKOUT_PROJECTED",
            title="Critical Stockout Projected for Test Insulin",
            evidence_json={},
            status=AlertStatus.ACTIVE,
        )
        db_session.add(alert)
        db_session.commit()
        alert_id = alert.id

        client.post(
            f"/api/v1/recommendations/{s['rec'].id}/action",
            json={"action": "APPROVE"},
            headers={"Authorization": CDMO_TOKEN},
        )
        db_session.expire_all()

        # DoC = 10/10 = 1.0 → CRITICAL → alert must still be ACTIVE
        still_active = db_session.query(Alert).filter(Alert.id == alert_id).first()
        assert still_active.status == AlertStatus.ACTIVE

    def test_acknowledged_alert_not_overridden_by_resolve(self, db_session):
        """
        An ACKNOWLEDGED alert (operator has seen it) should not be flipped to RESOLVED
        by the engine — only ACTIVE alerts should be auto-resolved.
        """
        s = _seed(db_session, recip_qty=5, rec_qty=100, recip_daily_demand=10.0)
        alert_code = f"ALT-{s['fac_recip'].facility_code}-{s['med'].code}"
        alert = Alert(
            alert_code=alert_code,
            facility_id=s["fac_recip"].id,
            resource_id=s["med"].code,
            severity=AlertSeverity.CRITICAL,
            alert_type="STOCKOUT_PROJECTED",
            title="Critical Stockout Projected for Test Insulin",
            evidence_json={},
            status=AlertStatus.ACKNOWLEDGED,
        )
        db_session.add(alert)
        db_session.commit()
        alert_id = alert.id

        client.post(
            f"/api/v1/recommendations/{s['rec'].id}/action",
            json={"action": "APPROVE"},
            headers={"Authorization": CDMO_TOKEN},
        )
        db_session.expire_all()

        # ACKNOWLEDGED should remain ACKNOWLEDGED — the engine only touches ACTIVE ones
        ack_alert = db_session.query(Alert).filter(Alert.id == alert_id).first()
        assert ack_alert.status == AlertStatus.ACKNOWLEDGED


# ── 5. Engine determinism ───────────────────────────────────────────────────

class TestEngineDeterminism:

    def test_run_forecast_engine_direct_uses_current_inventory(self, db_session):
        """
        Directly mutate inventory quantity, then run the engine.
        The resulting Forecast.days_of_cover must reflect the mutated value.
        """
        s = _seed(db_session, recip_qty=5, recip_daily_demand=10.0)

        # Run engine to create initial forecast
        run_forecast_and_alert_engine(db_session)
        db_session.expire_all()

        # Manually set inventory to 200 (simulating a large restock)
        inv = db_session.query(Inventory).filter(
            Inventory.facility_id == s["fac_recip"].id,
            Inventory.medicine_id == s["med"].id,
        ).first()
        inv.quantity = 200
        db_session.commit()

        # Re-run engine
        run_forecast_and_alert_engine(db_session)
        db_session.expire_all()

        fc = db_session.query(Forecast).filter(
            Forecast.facility_id == s["fac_recip"].id,
            Forecast.medicine_id == s["med"].id,
        ).first()
        # DoC = 200/10 = 20 → must be >> 7 (not 0.5 from old state)
        assert fc.days_of_cover > 7.0

    def test_no_hardcoded_doc_values_in_forecast(self, db_session):
        """
        Verify that different inventory quantities yield different days_of_cover values.
        Proves the calculation is driven by live data, not constants.
        """
        s = _seed(db_session, recip_qty=5, recip_daily_demand=10.0)
        run_forecast_and_alert_engine(db_session)
        db_session.expire_all()
        fc_a = db_session.query(Forecast).filter(
            Forecast.facility_id == s["fac_recip"].id,
        ).first()
        doc_a = fc_a.days_of_cover

        inv = db_session.query(Inventory).filter(
            Inventory.facility_id == s["fac_recip"].id,
        ).first()
        inv.quantity = 80
        db_session.commit()

        run_forecast_and_alert_engine(db_session)
        db_session.expire_all()
        fc_b = db_session.query(Forecast).filter(
            Forecast.facility_id == s["fac_recip"].id,
        ).first()
        doc_b = fc_b.days_of_cover

        # Different quantities → different DoC values (not hardcoded)
        assert doc_a != doc_b

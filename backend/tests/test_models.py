import os
import sys
from datetime import datetime, date
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.database import Base
from app.models import (
    User, Facility, Medicine, Inventory, ConsumptionLog, Bed, 
    Personnel, PersonnelAttendance, Forecast, Alert, Recommendation, 
    Requisition, AuditEvent, UserRole, FacilityType, MedicineCategory, 
    ActionType, PersonnelRole, AlertSeverity, AlertType, AlertStatus, 
    UrgencyLevel, RecommendationStatus, RequisitionStatus, EventType
)

TEST_DB_URL = "sqlite:///:memory:"

@pytest.fixture
def db_session():
    engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_database_foundation_all_models(db_session):
    # 1. Create Facility
    fac = Facility(
        facility_code="CHC-OD-KHU-001",
        name="Jatni CHC (Khordha)",
        facility_type=FacilityType.CHC,
        state="OD",
        district="Khordha",
        latitude=20.165,
        longitude=85.705
    )
    db_session.add(fac)
    db_session.commit()
    assert fac.id is not None
    assert fac.state == "OD"
    assert fac.district == "Khordha"

    # 2. Create User
    user = User(
        firebase_uid="FB-USER-001",
        email="doctor.nayak@healysis.gov.in",
        full_name="Dr. A. Nayak",
        role=UserRole.FACILITY_OFFICER,
        facility_id=fac.id
    )
    db_session.add(user)
    db_session.commit()
    assert user.id is not None
    assert user.facility.name == "Jatni CHC (Khordha)"

    # 3. Create Medicine
    med = Medicine(
        code="MED-ORS-SACHET",
        name="ORS Sachet",
        category=MedicineCategory.ESSENTIAL_MEDICINE,
        unit="sachets"
    )
    db_session.add(med)
    db_session.commit()
    assert med.id is not None

    # 4. Create Inventory
    inv = Inventory(
        facility_id=fac.id,
        medicine_id=med.id,
        item_code=med.code,
        item_name=med.name,
        quantity=150,
        safety_stock=40,
        batch="BATCH-2026-A",
        expiry=date(2027, 12, 31),
        incoming_quantity=100,
        unit="sachets"
    )
    db_session.add(inv)
    db_session.commit()
    assert inv.id is not None

    # 5. Create ConsumptionLog
    clog = ConsumptionLog(
        facility_id=fac.id,
        medicine_id=med.id,
        item_code=med.code,
        date=date.today(),
        quantity_dispensed=15,
        patient_footfall=45,
        encounter_token="PAT-IN-9001",
        action_type=ActionType.DISPENSE
    )
    db_session.add(clog)

    # 6. Create Bed
    bed = Bed(
        facility_id=fac.id,
        general_capacity=20,
        general_occupied=12,
        icu_capacity=5,
        icu_occupied=3,
        oxygen_capacity=10,
        oxygen_occupied=7,
        isolation_capacity=5,
        isolation_occupied=1
    )
    db_session.add(bed)

    # 7. Create Personnel
    pers = Personnel(
        facility_id=fac.id,
        doctors_count=4,
        nurses_count=12,
        pharmacists_count=2,
        asha_count=15
    )
    db_session.add(pers)

    # 8. Create PersonnelAttendance
    att = PersonnelAttendance(
        facility_id=fac.id,
        date=date.today(),
        role=PersonnelRole.DOCTOR,
        scheduled=4,
        present=4,
        absent=0
    )
    db_session.add(att)

    # 9. Create Forecast
    fc = Forecast(
        facility_id=fac.id,
        medicine_id=med.id,
        item_code=med.code,
        forecast_date=date.today(),
        expected_daily_demand=12.5,
        days_of_cover=12.0,
        projected_stockout_date=date(2026, 9, 15),
        confidence_score=0.95
    )
    db_session.add(fc)

    # 10. Create Alert
    alt = Alert(
        alert_code="ALT-2026-0001",
        facility_id=fac.id,
        resource_id=med.code,
        severity=AlertSeverity.WARNING,
        alert_type=AlertType.STOCKOUT_PROJECTED,
        title="ORS Buffer Depletion",
        evidence_json={"current_stock": 150, "days_of_cover": 12.0},
        projected_impact_date=date(2026, 9, 15),
        status=AlertStatus.ACTIVE
    )
    db_session.add(alt)

    # Create Second Facility for Redistribution/Requisition tests
    fac2 = Facility(
        facility_code="UPHC-OD-CTC-002",
        name="UPHC MS Das (Kafla Bazar)",
        facility_type=FacilityType.UPHC,
        state="OD",
        district="Cuttack",
        latitude=20.462,
        longitude=85.882
    )
    db_session.add(fac2)
    db_session.commit()

    # 11. Create Recommendation
    rec = Recommendation(
        recommendation_code="REC-2026-0001",
        donor_facility_id=fac.id,
        recipient_facility_id=fac2.id,
        medicine_id=med.id,
        item_code=med.code,
        recommended_quantity=50,
        urgency_level=UrgencyLevel.URGENT,
        haversine_distance_km=34.5,
        expected_days_cover_gained=4.5,
        confidence_score=0.92,
        reason="Recipient node at critical buffer depletion",
        status=RecommendationStatus.PENDING_HUMAN_APPROVAL
    )
    db_session.add(rec)

    # 12. Create Requisition
    req = Requisition(
        req_code="REQ-2026-0001",
        requester_node="Cuttack (Kafla Bazar)",
        source_facility_id=fac.id,
        target_facility_id=fac2.id,
        medicine_id=med.id,
        quantity=50,
        urgency_reason="Emergency OPD surge",
        status=RequisitionStatus.PENDING_APPROVAL
    )
    db_session.add(req)

    # 13. Create AuditEvent
    evt = AuditEvent(
        event_id="EVT-2026-10001",
        timestamp=datetime.utcnow(),
        actor_user_id=user.id,
        action="DISPENSE",
        facility_id=fac.id,
        payload_json={"quantity": 15, "token": "PAT-IN-9001"},
        previous_hash="GENESIS_ROOT_HEALYSIS_000",
        current_hash="a1b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef0",
        event_type=EventType.TRANSACTION,
        is_tampered=False
    )
    db_session.add(evt)

    db_session.commit()

    # Verify all 13 models persisted and have IDs
    assert clog.id is not None
    assert bed.id is not None
    assert pers.id is not None
    assert att.id is not None
    assert fc.id is not None
    assert alt.id is not None
    assert rec.id is not None
    assert req.id is not None
    assert evt.id is not None

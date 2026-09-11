import sys
import os
from datetime import datetime, date, timedelta, timezone

sys.path.insert(0, os.path.dirname(__file__))

from app.database import Base, engine, SessionLocal
from app.models import (
    Facility, User, Medicine, Inventory, ConsumptionLog, Bed, Personnel, 
    PersonnelAttendance, Forecast, Alert, Recommendation, Requisition, AuditEvent,
    FacilityType, UserRole, MedicineCategory, ActionType, PersonnelRole, 
    AlertSeverity, AlertType, AlertStatus, UrgencyLevel, RecommendationStatus, 
    RequisitionStatus, EventType
)

def ensure_demo_users_seeded(db):
    facilities = db.query(Facility).all()
    if not facilities:
        return
    fac_ids = [f.id for f in facilities]
    users_data = [
        {"uid": "UID-ADMIN-99", "email": "admin@healysis.gov.in", "name": "System Admin", "role": UserRole.ADMIN, "facility_id": None},
        {"uid": "UID-CDMO-88", "email": "cdmo.director@healysis.gov.in", "name": "Dr. S. Mohanty", "role": UserRole.CDMO, "facility_id": None},
        {"uid": "UID-OFFICER-JATNI", "email": "officer.jatni@healysis.gov.in", "name": "Dr. A. Nayak", "role": UserRole.FACILITY_OFFICER, "facility_id": fac_ids[0] if len(fac_ids) > 0 else None},
        {"uid": "UID-OFFICER-MSDAS", "email": "pharmacist.cuttack@healysis.gov.in", "name": "S. Patra", "role": UserRole.FACILITY_OFFICER, "facility_id": fac_ids[1] if len(fac_ids) > 1 else None},
        {"uid": "UID-OFFICER-PIPILI", "email": "inventory.pipili@healysis.gov.in", "name": "R. Mohanty", "role": UserRole.FACILITY_OFFICER, "facility_id": fac_ids[2] if len(fac_ids) > 2 else None},
        {"uid": "UID-OFFICER-BEHALA", "email": "nurse.behala@healysis.gov.in", "name": "T. Banerjee", "role": UserRole.FACILITY_OFFICER, "facility_id": fac_ids[3] if len(fac_ids) > 3 else None},
        {"uid": "UID-OFFICER-DIAMOND", "email": "officer.diamond@healysis.gov.in", "name": "K. Biswas", "role": UserRole.FACILITY_OFFICER, "facility_id": fac_ids[4] if len(fac_ids) > 4 else None},
    ]
    for u in users_data:
        existing = db.query(User).filter(User.firebase_uid == u["uid"]).first()
        if not existing:
            existing = db.query(User).filter(User.email == u["email"]).first()
        if existing:
            existing.firebase_uid = u["uid"]
            existing.email = u["email"]
            existing.full_name = u["name"]
            existing.role = u["role"]
            existing.facility_id = u["facility_id"]
        else:
            user_obj = User(
                firebase_uid=u["uid"],
                email=u["email"],
                full_name=u["name"],
                role=u["role"],
                facility_id=u["facility_id"]
            )
            db.add(user_obj)
    db.commit()

def seed_database():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        print("Seeding database foundation...")

        # 1. Facilities (State -> District -> Facility)
        facilities_data = [
            {"code": "CHC-OD-KHU-001", "name": "Jatni CHC (Khordha)", "type": FacilityType.CHC, "state": "OD", "district": "Khordha", "lat": 20.165, "long": 85.705},
            {"code": "UPHC-OD-CTC-002", "name": "UPHC MS Das (Kafla Bazar)", "type": FacilityType.UPHC, "state": "OD", "district": "Cuttack", "lat": 20.462, "long": 85.882},
            {"code": "PHC-OD-PURI-004", "name": "Pipili PHC (Puri)", "type": FacilityType.PHC, "state": "OD", "district": "Puri", "lat": 20.117, "long": 85.833},
            {"code": "UPHC-WB-KOL-012", "name": "Behala Urban PHC (Kolkata)", "type": FacilityType.UPHC, "state": "WB", "district": "Kolkata", "lat": 22.501, "long": 88.312},
            {"code": "PHC-WB-S24P-008", "name": "Diamond Harbour PHC", "type": FacilityType.PHC, "state": "WB", "district": "South 24 Parganas", "lat": 22.193, "long": 88.188}
        ]

        facility_objs = []
        for f in facilities_data:
            fac = db.query(Facility).filter(Facility.facility_code == f["code"]).first()
            if not fac:
                fac = Facility(
                    facility_code=f["code"],
                    name=f["name"],
                    facility_type=f["type"],
                    state=f["state"],
                    district=f["district"],
                    latitude=f["lat"],
                    longitude=f["long"]
                )
                db.add(fac)
                db.commit()
                db.refresh(fac)
            else:
                fac.name = f["name"]
                fac.facility_type = f["type"]
                fac.state = f["state"]
                fac.district = f["district"]
                fac.latitude = f["lat"]
                fac.longitude = f["long"]
                db.commit()
            facility_objs.append(fac)

        # 2. Seed 7 Operational Demo Users
        users_data = [
            {"uid": "UID-ADMIN-99", "email": "admin@healysis.gov.in", "name": "System Admin", "role": UserRole.ADMIN, "facility_id": None},
            {"uid": "UID-CDMO-88", "email": "cdmo.director@healysis.gov.in", "name": "Dr. S. Mohanty", "role": UserRole.CDMO, "facility_id": None},
            {"uid": "UID-OFFICER-JATNI", "email": "officer.jatni@healysis.gov.in", "name": "Dr. A. Nayak", "role": UserRole.FACILITY_OFFICER, "facility_id": facility_objs[0].id},
            {"uid": "UID-OFFICER-MSDAS", "email": "pharmacist.cuttack@healysis.gov.in", "name": "S. Patra", "role": UserRole.FACILITY_OFFICER, "facility_id": facility_objs[1].id},
            {"uid": "UID-OFFICER-PIPILI", "email": "inventory.pipili@healysis.gov.in", "name": "R. Mohanty", "role": UserRole.FACILITY_OFFICER, "facility_id": facility_objs[2].id},
            {"uid": "UID-OFFICER-BEHALA", "email": "nurse.behala@healysis.gov.in", "name": "T. Banerjee", "role": UserRole.FACILITY_OFFICER, "facility_id": facility_objs[3].id},
            {"uid": "UID-OFFICER-DIAMOND", "email": "officer.diamond@healysis.gov.in", "name": "K. Biswas", "role": UserRole.FACILITY_OFFICER, "facility_id": facility_objs[4].id},
        ]
        for u in users_data:
            existing = db.query(User).filter(User.firebase_uid == u["uid"]).first()
            if not existing:
                existing = db.query(User).filter(User.email == u["email"]).first()
            if existing:
                existing.firebase_uid = u["uid"]
                existing.email = u["email"]
                existing.full_name = u["name"]
                existing.role = u["role"]
                existing.facility_id = u["facility_id"]
            else:
                user_obj = User(
                    firebase_uid=u["uid"],
                    email=u["email"],
                    full_name=u["name"],
                    role=u["role"],
                    facility_id=u["facility_id"]
                )
                db.add(user_obj)
        db.commit()

        # 3. Essential Medicines
        medicines_data = [
            {"code": "MED-ORS-SACHET", "name": "ORS Sachet (Oral Rehydration Salts)", "category": MedicineCategory.ESSENTIAL_MEDICINE, "unit": "sachets"},
            {"code": "MED-PARACET-500MG", "name": "Paracetamol 500mg", "category": MedicineCategory.ESSENTIAL_MEDICINE, "unit": "tablets"},
            {"code": "MED-INSULIN-100IU", "name": "Insulin 100IU Injection", "category": MedicineCategory.VACCINE, "unit": "vials"},
            {"code": "MED-AMOXICILLIN-250", "name": "Amoxicillin 250mg Capsule", "category": MedicineCategory.ESSENTIAL_MEDICINE, "unit": "capsules"},
            {"code": "MED-CETIRIZINE-10", "name": "Cetirizine 10mg", "category": MedicineCategory.ESSENTIAL_MEDICINE, "unit": "tablets"},
        ]

        medicine_objs = []
        for m in medicines_data:
            med = db.query(Medicine).filter(Medicine.code == m["code"]).first()
            if not med:
                med = Medicine(code=m["code"], name=m["name"], category=m["category"], unit=m["unit"])
                db.add(med)
                db.commit()
                db.refresh(med)
            medicine_objs.append(med)

        # 4. Seed Inventory, Beds, Personnel per facility
        for idx, fac in enumerate(facility_objs):
            # Beds
            bed = db.query(Bed).filter(Bed.facility_id == fac.id).first()
            if not bed:
                bed = Bed(
                    facility_id=fac.id,
                    general_capacity=20 + (idx * 5),
                    general_occupied=10 + (idx * 3),
                    icu_capacity=4,
                    icu_occupied=2,
                    oxygen_capacity=10,
                    oxygen_occupied=5,
                    isolation_capacity=4,
                    isolation_occupied=1
                )
                db.add(bed)

            # Personnel
            pers = db.query(Personnel).filter(Personnel.facility_id == fac.id).first()
            if not pers:
                pers = Personnel(
                    facility_id=fac.id,
                    doctors_count=3,
                    nurses_count=8,
                    pharmacists_count=2,
                    asha_count=12
                )
                db.add(pers)

            # Inventory items
            for med in medicine_objs:
                # Set Jatni CHC (idx=0) ORS Sachet to shortage state (quantity=15)
                is_jatni_ors = (idx == 0 and med.code == "MED-ORS-SACHET")
                inv_qty = 15 if is_jatni_ors else (120 + (idx * 30))

                inv = db.query(Inventory).filter(
                    Inventory.facility_id == fac.id,
                    Inventory.medicine_id == med.id
                ).first()

                if inv:
                    inv.quantity = inv_qty
                    inv.safety_stock = 40
                    inv.incoming_quantity = 50 if not is_jatni_ors else 0
                else:
                    inv = Inventory(
                        facility_id=fac.id,
                        medicine_id=med.id,
                        item_code=med.code,
                        item_name=med.name,
                        quantity=inv_qty,
                        safety_stock=40,
                        batch=f"BATCH-2026-0{idx+1}",
                        expiry=date(2027, 6, 30),
                        incoming_quantity=50 if not is_jatni_ors else 0,
                        unit=med.unit
                    )
                    db.add(inv)

                # Historical consumption (last 7 days)
                dispensed = 15 if is_jatni_ors else (8 + (idx * 2))
                db.query(ConsumptionLog).filter(
                    ConsumptionLog.facility_id == fac.id,
                    ConsumptionLog.medicine_id == med.id
                ).delete()

                for d_offset in range(7, 0, -1):
                    c_date = date.today() - timedelta(days=d_offset)
                    c_log = ConsumptionLog(
                        facility_id=fac.id,
                        medicine_id=med.id,
                        item_code=med.code,
                        date=c_date,
                        quantity_dispensed=dispensed,
                        patient_footfall=25 + (idx * 5),
                        encounter_token=f"PAT-IN-80{d_offset}{idx}",
                        action_type=ActionType.DISPENSE
                    )
                    db.add(c_log)

        db.commit()

        # Execute forecast, alert & redistribution engines to populate initial queue
        from app.algorithms import run_forecast_and_alert_engine, generate_and_persist_redistribution_recommendations
        run_forecast_and_alert_engine(db)
        generate_and_persist_redistribution_recommendations(db)

        # Initial Genesis Block Audit Event
        genesis_evt = db.query(AuditEvent).filter(AuditEvent.event_id == "EVT-GENESIS-000").first()
        if not genesis_evt:
            genesis_evt = AuditEvent(
                event_id="EVT-GENESIS-000",
                timestamp=datetime.now(timezone.utc),
                action="GENESIS_BLOCK_INITIALIZATION",
                payload_json={"system": "Healysis Database Foundation V2"},
                previous_hash="GENESIS_ROOT_HEALYSIS_000",
                current_hash="0000000000000000000000000000000000000000000000000000000000000000",
                event_type=EventType.SYSTEM,
                is_tampered=False
            )
            db.add(genesis_evt)
            db.commit()

        print("Database foundation successfully seeded!")

    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()

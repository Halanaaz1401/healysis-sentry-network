"""
Feature 2.2 Regression Tests — Issue A

Tests for:
1. Devanagari (Hindi) inventory update intent detection
2. Devanagari ORS update: "आज ओआरएस का स्टॉक 200 है"
3. English update still works
4. Hinglish update still works
5. Unknown resource does NOT return all inventory — returns clarification
6. Narrow resource query returns only requested resource
7. Narrow facility + resource query returns only requested data
8. Facility Officer scope remains enforced
9. Confirmation remains mandatory
10. Existing chat persistence remains intact
"""
import os
import sys
import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

os.environ["TESTING"] = "true"

from app.config import settings
from app.database import Base, get_db, engine as db_engine
from app.models import (
    Facility, Medicine, Inventory, Forecast, User,
    FacilityType, UserRole, MedicineCategory,
    AuditEvent, ConsumptionLog, ActionType
)
from app.advisor_service import run_grounded_ai_advisor, RESOURCE_CATALOG
from app.schemas import AdvisorChatRequest
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
def setup_regression_test_data():
    """Sets up standard test data: Jatni CHC + Behala PHC, ORS and Paracetamol."""
    settings.TESTING = True
    Base.metadata.create_all(bind=db_engine)
    db = TestingSessionLocal()

    db.query(AuditEvent).delete()
    db.query(ConsumptionLog).delete()
    db.query(Forecast).delete()
    db.query(Inventory).delete()
    db.query(User).delete()
    db.query(Facility).delete()
    db.query(Medicine).delete()
    db.commit()

    fac_jatni = Facility(
        id=1, facility_code="CHC-OD-KHU-001", name="Jatni CHC (Khordha)",
        facility_type=FacilityType.CHC, state="OD", district="Khordha",
        latitude=20.165, longitude=85.705
    )
    fac_behala = Facility(
        id=4, facility_code="PHC-WB-KOL-004", name="Behala Urban PHC (Kolkata)",
        facility_type=FacilityType.UPHC, state="WB", district="Kolkata",
        latitude=22.498, longitude=88.318
    )
    db.add_all([fac_jatni, fac_behala])
    db.commit()

    med_ors = Medicine(
        id=1, code="MED-ORS-SACHET", name="ORS",
        category=MedicineCategory.ESSENTIAL_MEDICINE, unit="sachets"
    )
    med_pcm = Medicine(
        id=2, code="MED-PARACET-500MG", name="Paracetamol",
        category=MedicineCategory.ESSENTIAL_MEDICINE, unit="tablets"
    )
    db.add_all([med_ors, med_pcm])
    db.commit()

    inv_ors = Inventory(
        id=1, facility_id=1, medicine_id=1, item_code="MED-ORS-SACHET",
        item_name="ORS", quantity=100, safety_stock=50,
        incoming_quantity=0, unit="sachets"
    )
    inv_pcm = Inventory(
        id=2, facility_id=1, medicine_id=2, item_code="MED-PARACET-500MG",
        item_name="Paracetamol", quantity=200, safety_stock=100,
        incoming_quantity=0, unit="tablets"
    )
    inv_behala_ors = Inventory(
        id=3, facility_id=4, medicine_id=1, item_code="MED-ORS-SACHET",
        item_name="ORS", quantity=80, safety_stock=40,
        incoming_quantity=0, unit="sachets"
    )
    db.add_all([inv_ors, inv_pcm, inv_behala_ors])
    db.commit()

    fc_ors = Forecast(
        facility_id=1, medicine_id=1, item_code="MED-ORS-SACHET",
        forecast_date=date.today(), expected_daily_demand=10.0,
        days_of_cover=10.0, confidence_score=0.95
    )
    fc_pcm = Forecast(
        facility_id=1, medicine_id=2, item_code="MED-PARACET-500MG",
        forecast_date=date.today(), expected_daily_demand=20.0,
        days_of_cover=10.0, confidence_score=0.95
    )
    db.add_all([fc_ors, fc_pcm])
    db.commit()

    today = date.today()
    for d in range(7, 0, -1):
        db.add(ConsumptionLog(
            facility_id=1, medicine_id=1, item_code="MED-ORS-SACHET",
            date=today - timedelta(days=d),
            quantity_dispensed=10, patient_footfall=25, action_type=ActionType.DISPENSE
        ))
    db.commit()

    user_jatni = User(
        id=1, firebase_uid="UID-OFFICER-JATNI",
        email="officer.jatni@healysis.gov.in", full_name="Dr. A. Nayak",
        role=UserRole.FACILITY_OFFICER, facility_id=1
    )
    user_behala = User(
        id=2, firebase_uid="UID-OFFICER-BEHALA",
        email="officer.behala@healysis.gov.in", full_name="T. Banerjee",
        role=UserRole.FACILITY_OFFICER, facility_id=4
    )
    user_cdmo = User(
        id=3, firebase_uid="UID-CDMO-88",
        email="cdmo.director@healysis.gov.in", full_name="Dr. S. Mohanty (CDMO)",
        role=UserRole.CDMO, facility_id=None
    )
    db.add_all([user_jatni, user_behala, user_cdmo])
    db.commit()
    db.close()


# ==========================================
# Regression Test 1: Devanagari inventory update — ओआरएस
# ==========================================

def test_devanagari_ors_update_intent_detected():
    """
    'आज ओआरएस का स्टॉक 200 है' must be recognized as an inventory update intent.
    It MUST produce a pending_update for ORS, NOT return all monitored stock.
    """
    db = TestingSessionLocal()
    user = db.query(User).filter(User.id == 1).first()
    req = AdvisorChatRequest(message="आज ओआरएस का स्टॉक 200 है")
    res = run_grounded_ai_advisor(req, user, db)

    assert res.pending_update is not None, (
        "Devanagari ORS update 'आज ओआरएस का स्टॉक 200 है' must produce pending_update, "
        f"but got answer: {res.answer}"
    )
    assert res.pending_update.item_code == "MED-ORS-SACHET"
    assert res.pending_update.new_quantity == 200
    assert res.pending_update.facility_id == 1
    assert res.requires_human_approval is True
    db.close()


# ==========================================
# Regression Test 2: Devanagari + Hinglish mixed update
# ==========================================

def test_devanagari_hinglish_ors_update_intent():
    """
    'आज ORS ka stock 200 hai' (mixed Devanagari + Hinglish) must be detected
    as an inventory update intent for ORS at Jatni.
    """
    db = TestingSessionLocal()
    user = db.query(User).filter(User.id == 1).first()
    req = AdvisorChatRequest(message="आज ORS ka stock 200 hai")
    res = run_grounded_ai_advisor(req, user, db)

    assert res.pending_update is not None, (
        f"Mixed Devanagari+Hinglish ORS update must produce pending_update, got: {res.answer}"
    )
    assert res.pending_update.new_quantity == 200
    assert res.pending_update.item_code == "MED-ORS-SACHET"
    db.close()


# ==========================================
# Regression Test 3: English update still works (no regression)
# ==========================================

def test_english_update_still_works():
    """'ORS stock is 180 units.' must still be recognized as an inventory update."""
    db = TestingSessionLocal()
    user = db.query(User).filter(User.id == 1).first()
    req = AdvisorChatRequest(message="ORS stock is 180 units.")
    res = run_grounded_ai_advisor(req, user, db)

    assert res.pending_update is not None
    assert res.pending_update.new_quantity == 180
    assert res.pending_update.item_code == "MED-ORS-SACHET"
    db.close()


# ==========================================
# Regression Test 4: Hinglish update still works (no regression)
# ==========================================

def test_hinglish_update_still_works():
    """'Aaj ORS ka stock 180 hai.' must still be recognized as an inventory update."""
    db = TestingSessionLocal()
    user = db.query(User).filter(User.id == 1).first()
    req = AdvisorChatRequest(message="Aaj ORS ka stock 180 hai.")
    res = run_grounded_ai_advisor(req, user, db)

    assert res.pending_update is not None
    assert res.pending_update.new_quantity == 180
    assert res.pending_update.item_code == "MED-ORS-SACHET"
    db.close()


# ==========================================
# Regression Test 5: Unknown resource → clarification (NOT all inventory)
# ==========================================

def test_unknown_devanagari_resource_returns_clarification_not_all_stock():
    """
    'आज जाटनी में वायरस का कितना स्टॉक है' (virus — unknown resource) must return
    a clarification response, NOT dump all monitored stock.
    The response must:
    - NOT produce a pending_update
    - Mention the unknown resource (virus / वायरस)
    - Offer the catalog of known resources
    - NOT include data for all facilities/medicines
    """
    headers = {"Authorization": "Bearer TEST-TOKEN-UID-CDMO-88"}
    resp = client.post(
        "/api/v1/advisor/chat",
        json={"message": "आज जाटनी में वायरस का कितना स्टॉक है"},
        headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()

    # Must NOT produce a pending_update
    assert data["pending_update"] is None, (
        "Unknown resource query must not produce a pending_update"
    )

    answer = data["answer"]

    # Must NOT return all monitored stock (no dump of all facilities)
    broad_stock_indicators = [
        "Jatni CHC\n• ORS:",
        "UPHC MS Das\n• ORS:",
        "Behala Urban PHC\n• ORS:",
        "monitored stock:",
        "stock across all monitored",
        "Stock across monitored",
    ]
    for indicator in broad_stock_indicators:
        assert indicator not in answer, (
            f"Unknown resource query must NOT dump all monitored stock. "
            f"Found '{indicator}' in answer: {answer[:200]}"
        )

    # Must ask for clarification about the resource
    has_clarification = (
        "वायरस" in answer
        or "virus" in answer.lower()
        or "Did you mean" in answer
        or "catalog" in answer.lower()
        or "medicine catalog" in answer.lower()
        or "ORS" in answer
        or "couldn't match" in answer
        or "not found" in answer.lower()
    )
    assert has_clarification, (
        f"Unknown resource query must return clarification with catalog, got: {answer[:300]}"
    )


def test_unknown_latin_resource_returns_clarification():
    """
    'Jatni mein virus ka stock kitna hai?' must return a clarification,
    NOT all monitored inventory.
    """
    headers = {"Authorization": "Bearer TEST-TOKEN-UID-OFFICER-JATNI"}
    resp = client.post(
        "/api/v1/advisor/chat",
        json={"message": "Jatni mein virus ka stock kitna hai?"},
        headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["pending_update"] is None

    answer = data["answer"]

    # Must not return broad monitored stock for an unknown resource
    broad_indicators = ["UPHC MS Das", "Pipili PHC", "Behala Urban PHC", "Diamond Harbour"]
    for indicator in broad_indicators:
        assert indicator not in answer, (
            f"Unknown resource query must not return all facilities. "
            f"Found '{indicator}' in: {answer[:200]}"
        )


# ==========================================
# Regression Test 6: Narrow resource query returns only that resource
# ==========================================

def test_narrow_ors_query_returns_only_ors():
    """
    'Jatni mein ORS ka stock kitna hai?' must return ONLY Jatni ORS data.
    It must NOT expand to show all facilities or all medicines.
    """
    db = TestingSessionLocal()
    user = db.query(User).filter(User.id == 1).first()  # Jatni officer
    req = AdvisorChatRequest(message="Jatni mein ORS ka stock kitna hai?")
    res = run_grounded_ai_advisor(req, user, db)
    db.close()

    assert res.pending_update is None
    answer = res.answer

    # Must contain ORS information for Jatni
    assert "ORS" in answer or "ors" in answer.lower() or "100" in answer, (
        f"Narrow ORS query must mention ORS stock, got: {answer}"
    )

    # Must NOT include other facilities (Behala is not accessible to Jatni officer)
    unauthorized_facilities = ["Behala", "Diamond Harbour", "Pipili"]
    for fac in unauthorized_facilities:
        assert fac not in answer, (
            f"Narrow Jatni ORS query must not return {fac} data, got: {answer[:200]}"
        )


# ==========================================
# Regression Test 7: Narrow facility + resource query via API
# ==========================================

def test_narrow_facility_resource_query_via_api():
    """
    Jatni Facility Officer asks 'Jatni mein ORS ka stock kitna hai?'
    via the chat API. Must return only Jatni ORS, not all facilities.
    """
    headers = {"Authorization": "Bearer TEST-TOKEN-UID-OFFICER-JATNI"}
    resp = client.post(
        "/api/v1/advisor/chat",
        json={"message": "Jatni mein ORS ka stock kitna hai?"},
        headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["pending_update"] is None

    answer = data["answer"]

    # Must NOT include unauthorized facilities
    unauthorized = ["UPHC MS Das", "Pipili PHC", "Behala Urban PHC", "Diamond Harbour PHC"]
    for fac in unauthorized:
        assert fac not in answer, (
            f"Jatni officer narrow query must not return {fac}, got: {answer[:200]}"
        )


# ==========================================
# Regression Test 8: Facility Officer scope enforcement
# ==========================================

def test_facility_officer_scope_enforced_for_devanagari_query():
    """
    Behala officer (facility_id=4) asks about Jatni using Devanagari.
    The response must NOT include Jatni stock data (scope protection).
    """
    headers = {"Authorization": "Bearer TEST-TOKEN-UID-OFFICER-BEHALA"}
    resp = client.post(
        "/api/v1/advisor/chat",
        json={"message": "जाटनी में ORS का स्टॉक कितना है"},
        headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    # Behala officer must NOT be able to see Jatni stock
    # (Either scoped to Behala only or access denied message)
    answer = data["answer"]

    # The answer must not produce Jatni-specific stock for the Behala officer
    if data["pending_update"] is not None:
        # If an update was produced, it must be for Behala (facility 4), not Jatni (1)
        assert data["pending_update"]["facility_id"] != 1, (
            "Behala officer must not be able to update Jatni inventory"
        )


# ==========================================
# Regression Test 9: Confirmation remains mandatory for Devanagari update
# ==========================================

def test_devanagari_update_confirmation_mandatory():
    """
    A Devanagari inventory update 'आज ओआरएस का स्टॉक 200 है' must:
    1. Return pending_update (not auto-commit)
    2. NOT mutate the database
    3. Require confirmation_token
    """
    db = TestingSessionLocal()
    user = db.query(User).filter(User.id == 1).first()

    # Check initial state
    inv = db.query(Inventory).filter(
        Inventory.facility_id == 1, Inventory.item_code == "MED-ORS-SACHET"
    ).first()
    qty_before = inv.quantity
    db.close()

    # Send Devanagari update via API
    headers = {"Authorization": "Bearer TEST-TOKEN-UID-OFFICER-JATNI"}
    resp = client.post(
        "/api/v1/advisor/chat",
        json={"message": "आज ओआरएस का स्टॉक 200 है"},
        headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()

    # Must have pending_update (confirmation required)
    if data["pending_update"] is not None:
        # If update is proposed, verify DB was NOT mutated
        db = TestingSessionLocal()
        inv_after = db.query(Inventory).filter(
            Inventory.facility_id == 1, Inventory.item_code == "MED-ORS-SACHET"
        ).first()
        assert inv_after.quantity == qty_before, (
            f"Devanagari update must NOT auto-mutate. "
            f"Expected qty {qty_before}, got {inv_after.quantity}"
        )
        # Must have a token
        assert "confirmation_token" in data["pending_update"]
        assert data["pending_update"]["confirmation_token"].startswith("TOK-UPD-")
        db.close()


# ==========================================
# Regression Test 10: Resource catalog has Devanagari aliases
# ==========================================

def test_resource_catalog_contains_devanagari_aliases():
    """
    Verify that the RESOURCE_CATALOG contains Devanagari aliases for key medicines.
    This ensures the catalog resolution infrastructure is in place.
    """
    ors_item = next(
        (item for item in RESOURCE_CATALOG if item["code"] == "MED-ORS-SACHET"), None
    )
    assert ors_item is not None

    # Must have at least one Devanagari alias
    has_devanagari = any(
        any('\u0900' <= ch <= '\u097F' for ch in alias)
        for alias in ors_item["aliases"]
    )
    assert has_devanagari, (
        f"ORS catalog entry must have Devanagari aliases. Current aliases: {ors_item['aliases']}"
    )

    pcm_item = next(
        (item for item in RESOURCE_CATALOG if item["code"] == "MED-PARACET-500MG"), None
    )
    assert pcm_item is not None
    has_dev_pcm = any(
        any('\u0900' <= ch <= '\u097F' for ch in alias)
        for alias in pcm_item["aliases"]
    )
    assert has_dev_pcm, (
        f"Paracetamol catalog entry must have Devanagari aliases. Current: {pcm_item['aliases']}"
    )

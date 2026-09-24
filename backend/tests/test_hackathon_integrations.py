import os
import sys
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ["TESTING"] = "true"

from app.config import settings
from app.database import Base, get_db, engine as db_engine
from app.models import Facility, Medicine, Inventory, User, UserRole, FacilityType, MedicineCategory
from seed_db import ensure_facilities_seeded, ensure_demo_users_seeded
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

ADMIN_TOKEN = "Bearer TEST-TOKEN-UID-ADMIN-99"
CDMO_TOKEN = "Bearer TEST-TOKEN-UID-CDMO-88"
OFFICER_JATNI = "Bearer TEST-TOKEN-UID-OFFICER-JATNI"

@pytest.fixture(autouse=True)
def setup_db():
    settings.TESTING = True
    settings.ALLOW_DEMO_TOKENS = True
    Base.metadata.create_all(bind=db_engine)
    db = TestingSessionLocal()
    ensure_facilities_seeded(db)
    ensure_demo_users_seeded(db)
    db.close()
    yield

# =========================================================
# 1. MULTIMODAL VISION INSPECTION TESTS
# =========================================================

def test_multimodal_vision_valid_image():
    import base64
    # Valid minimal JPEG (SOI marker \xff\xd8\xff + filler)
    jpeg_bytes = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00\xff\xd9"
    payload = {
        "image_base64": base64.b64encode(jpeg_bytes).decode("utf-8"),
        "filename": "delivery_challan_ors.jpg",
        "mime_type": "image/jpeg",
        "prompt": "Inspect received carton for ORS stock intake"
    }

    res = client.post("/api/v1/advisor/analyze-image", headers={"Authorization": OFFICER_JATNI}, json=payload)
    assert res.status_code == 200
    res_data = res.json()
    assert res_data["detected_medicine"] is not None
    assert "ORS" in res_data["detected_medicine"]
    assert res_data["is_nlem_matched"] is True
    assert res_data["requires_human_approval"] is True
    assert "advisory" in res_data["advisory_disclaimer"].lower()

def test_multimodal_vision_corrupted_header_rejected():
    import base64
    bad_bytes = b"NOT_A_VALID_IMAGE_HEADER_AT_ALL_JUST_RANDOM_TEXT"
    payload = {
        "image_base64": base64.b64encode(bad_bytes).decode("utf-8"),
        "filename": "fake_image.jpg",
        "mime_type": "image/jpeg"
    }
    res = client.post("/api/v1/advisor/analyze-image", headers={"Authorization": OFFICER_JATNI}, json=payload)
    assert res.status_code == 400
    assert "Invalid image" in res.json()["detail"]

def test_multimodal_vision_invalid_mime_rejected():
    import base64
    text_bytes = b"Hello world text file"
    payload = {
        "image_base64": base64.b64encode(text_bytes).decode("utf-8"),
        "filename": "notes.txt",
        "mime_type": "text/plain"
    }
    res = client.post("/api/v1/advisor/analyze-image", headers={"Authorization": OFFICER_JATNI}, json=payload)
    assert res.status_code == 400
    assert "Invalid MIME type" in res.json()["detail"]

def test_multimodal_vision_unauthenticated_rejected():
    import base64
    jpeg_bytes = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00\xff\xd9"
    payload = {
        "image_base64": base64.b64encode(jpeg_bytes).decode("utf-8"),
        "filename": "challan.jpg",
        "mime_type": "image/jpeg"
    }
    res = client.post("/api/v1/advisor/analyze-image", json=payload)
    assert res.status_code == 401

# =========================================================
# 2. BIGQUERY INTEGRATION & SCHEMA TESTS
# =========================================================

def test_bigquery_schema_endpoint():
    res = client.get("/api/v1/network/bigquery-schema", headers={"Authorization": CDMO_TOKEN})
    assert res.status_code == 200
    data = res.json()
    assert "dataset_id" in data
    assert len(data["tables"]) == 3
    table_ids = [t["table_id"] for t in data["tables"]]
    assert "facilities_spatial_telemetry" in table_ids
    assert "inventory_burn_rate_snapshots" in table_ids
    assert "cryptographic_audit_ledger" in table_ids

def test_bigquery_export_inventory_endpoint():
    res = client.get("/api/v1/network/bigquery-export?table=inventory", headers={"Authorization": CDMO_TOKEN})
    assert res.status_code == 200
    data = res.json()
    assert data["table"] == "inventory_burn_rate_snapshots"
    assert data["count"] > 0
    first_record = data["records"][0]
    assert "facility_code" in first_record
    assert "medicine_code" in first_record
    assert "days_of_cover" in first_record

def test_bigquery_export_facilities_endpoint():
    res = client.get("/api/v1/network/bigquery-export?table=facilities", headers={"Authorization": CDMO_TOKEN})
    assert res.status_code == 200
    data = res.json()
    assert data["table"] == "facilities_spatial_telemetry"
    assert data["count"] > 0
    first_record = data["records"][0]
    assert "latitude" in first_record
    assert "longitude" in first_record

def test_bigquery_rbac_facility_officer_forbidden():
    res = client.get("/api/v1/network/bigquery-schema", headers={"Authorization": OFFICER_JATNI})
    assert res.status_code == 403

# =========================================================
# 3. GEOSPATIAL COORDINATES IN RECOMMENDATIONS
# =========================================================

def test_recommendation_geospatial_coordinates():
    res = client.get("/api/v1/recommendations", headers={"Authorization": CDMO_TOKEN})
    assert res.status_code == 200
    recs = res.json()
    if recs:
        r = recs[0]
        assert "donor_latitude" in r
        assert "donor_longitude" in r
        assert "recipient_latitude" in r
        assert "recipient_longitude" in r
        assert "haversine_distance_km" in r

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import Settings
from app.models import Facility, Alert, AlertSeverity, AlertType, AlertStatus, User, UserRole, FacilityType
from app.advisor_service import format_grounded_operational_answer, StructuredQuery

def test_production_mode_disables_demo_tokens_and_docs_by_default(monkeypatch):
    """
    Regression Test: In production mode (APP_ENV=production), demo tokens and
    OpenAPI documentation must default to disabled unless explicitly overridden.
    """
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("ALLOW_DEMO_TOKENS", raising=False)
    monkeypatch.delenv("ENABLE_DOCS", raising=False)
    
    prod_settings = Settings()
    assert prod_settings.APP_ENV == "production"
    assert prod_settings.ALLOW_DEMO_TOKENS is False, "ALLOW_DEMO_TOKENS must be False by default in production"
    assert prod_settings.ENABLE_DOCS is False, "ENABLE_DOCS must be False by default in production"

def test_development_mode_enables_demo_tokens_and_docs_by_default(monkeypatch):
    """
    Regression Test: In development mode (APP_ENV=development), demo tokens and
    OpenAPI documentation remain enabled for local testing and developer workflow.
    """
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("ALLOW_DEMO_TOKENS", raising=False)
    monkeypatch.delenv("ENABLE_DOCS", raising=False)
    
    dev_settings = Settings()
    assert dev_settings.APP_ENV == "development"
    assert dev_settings.ALLOW_DEMO_TOKENS is True
    assert dev_settings.ENABLE_DOCS is True

def test_active_alerts_intent_uses_alert_title_not_message():
    """
    Regression Test: Ensure format_grounded_operational_answer for ACTIVE_ALERTS
    intent correctly accesses `alt.title` without raising AttributeError.
    """
    # In-memory test session
    engine = create_engine("sqlite:///:memory:")
    from app.database import Base
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    fac = Facility(
        id=101,
        facility_code="TEST-FAC-01",
        name="Test Community Health Centre",
        facility_type=FacilityType.CHC,
        state="OD",
        district="Khordha",
        latitude=20.0,
        longitude=85.0
    )
    db.add(fac)
    db.commit()

    alert = Alert(
        id=501,
        alert_code="ALT-TEST-501",
        facility_id=101,
        resource_id="MED-ORS-SACHET",
        severity=AlertSeverity.CRITICAL,
        alert_type=AlertType.STOCKOUT_PROJECTED,
        title="Critical stockout projected for ORS Sachet within 48 hours",
        status=AlertStatus.ACTIVE
    )
    db.add(alert)
    db.commit()

    admin_user = User(
        id=1,
        firebase_uid="UID-TEST-ADMIN",
        email="admin@test.gov.in",
        full_name="Test Admin",
        role=UserRole.ADMIN
    )

    query = StructuredQuery()
    query.intent = "ACTIVE_ALERTS"
    query.facility_scope = [fac]
    query.resource_scope = []
    query.geographic_scope = "Odisha"
    query.answer_style = "SUMMARY"

    answer_text, severity = format_grounded_operational_answer(query, admin_user, db)
    db.close()

    assert "Critical stockout projected for ORS Sachet within 48 hours" in answer_text
    assert severity == "CRITICAL"

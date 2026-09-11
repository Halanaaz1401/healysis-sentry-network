from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Alert, AlertStatus, User, UserRole
from app.schemas import AlertResponse
from app.security import (
    get_current_user, require_facility_officer, require_cdmo, 
    verify_facility_access
)

router = APIRouter(prefix="/api/v1", tags=["Early Warning Alerts"])

@router.get("/alerts", response_model=List[AlertResponse])
def get_all_alerts(
    current_user: User = Depends(require_facility_officer),
    db: Session = Depends(get_db)
):
    """
    Returns active early warning alerts.
    FACILITY_OFFICER sees only their assigned facility alerts.
    CDMO and ADMIN see all facilities.
    """
    query = db.query(Alert)
    if current_user.role == UserRole.FACILITY_OFFICER:
        if current_user.facility_id is None:
            return []
        query = query.filter(Alert.facility_id == current_user.facility_id)

    return query.order_by(Alert.severity.desc(), Alert.created_at.desc()).all()

@router.get("/alerts/{alert_id}", response_model=AlertResponse)
def get_alert_by_id(
    alert_id: int,
    current_user: User = Depends(require_facility_officer),
    db: Session = Depends(get_db)
):
    """
    Returns a single early warning alert by ID.
    Enforces facility-scoped access.
    """
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert with id={alert_id} not found."
        )

    verify_facility_access(alert.facility_id, current_user)
    return alert

@router.get("/facilities/{facility_id}/alerts", response_model=List[AlertResponse])
def get_facility_alerts(
    facility_id: int,
    current_user: User = Depends(require_facility_officer),
    db: Session = Depends(get_db)
):
    """
    Returns early warning alerts for a specific facility_id.
    Enforces facility-scoped access.
    """
    verify_facility_access(facility_id, current_user)
    return db.query(Alert).filter(Alert.facility_id == facility_id).order_by(Alert.severity.desc()).all()

@router.post("/alerts/{alert_id}/acknowledge", response_model=AlertResponse)
def acknowledge_alert(
    alert_id: int,
    current_user: User = Depends(require_cdmo),
    db: Session = Depends(get_db)
):
    """
    Acknowledges an active early warning alert.
    Requires CDMO or ADMIN role.
    """
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert with id={alert_id} not found."
        )

    alert.status = AlertStatus.ACKNOWLEDGED
    db.commit()
    db.refresh(alert)
    return alert

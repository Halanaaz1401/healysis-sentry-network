from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    Facility, User, UserRole, Inventory, Alert, Forecast, Bed, Personnel, PersonnelAttendance
)
from app.schemas import FacilityResponse
from app.security import (
    get_current_user, require_facility_officer, verify_facility_access
)

router = APIRouter(prefix="/api/v1", tags=["Facilities & Health Network Infrastructure"])

@router.get("/facilities", response_model=List[FacilityResponse])
@router.get("/facilities/", response_model=List[FacilityResponse], include_in_schema=False)
def get_all_facilities(
    current_user: User = Depends(require_facility_officer),
    db: Session = Depends(get_db)
):
    """
    Returns list of monitored healthcare facilities.
    FACILITY_OFFICER is scoped to their assigned facility.
    CDMO and ADMIN can view all network nodes.
    """
    query = db.query(Facility)
    if current_user.role == UserRole.FACILITY_OFFICER:
        if current_user.facility_id is None:
            return []
        query = query.filter(Facility.id == current_user.facility_id)

    return query.order_by(Facility.id.asc()).all()

@router.get("/facilities/{facility_id}")
def get_facility_details(
    facility_id: int,
    current_user: User = Depends(require_facility_officer),
    db: Session = Depends(get_db)
):
    """
    Returns comprehensive facility details profile.
    Enforces facility-scoped authorization for FACILITY_OFFICER role.
    """
    verify_facility_access(facility_id, current_user)

    fac = db.query(Facility).filter(Facility.id == facility_id).first()
    if not fac:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Facility with id={facility_id} not found."
        )

    # Assigned Facility Officer
    officers = db.query(User).filter(
        User.facility_id == facility_id,
        User.role == UserRole.FACILITY_OFFICER
    ).all()

    officer_info = [
        {
            "id": u.id,
            "full_name": u.full_name,
            "email": u.email,
            "role": u.role.value
        }
        for u in officers
    ]

    # Capacity & Beds
    bed = db.query(Bed).filter(Bed.facility_id == facility_id).first()
    bed_data = {
        "general_capacity": bed.general_capacity if bed else 30,
        "general_occupied": bed.general_occupied if bed else 15,
        "icu_capacity": bed.icu_capacity if bed else 4,
        "icu_occupied": bed.icu_occupied if bed else 2,
        "oxygen_capacity": bed.oxygen_capacity if bed else 10,
        "oxygen_occupied": bed.oxygen_occupied if bed else 5,
        "isolation_capacity": bed.isolation_capacity if bed else 4,
        "isolation_occupied": bed.isolation_occupied if bed else 1,
        "total_beds": (bed.general_capacity + bed.icu_capacity) if bed else 34,
        "total_occupied": (bed.general_occupied + bed.icu_occupied) if bed else 17,
        "occupancy_rate_pct": round(((bed.general_occupied + bed.icu_occupied) / (bed.general_capacity + bed.icu_capacity)) * 100, 1) if (bed and (bed.general_capacity + bed.icu_capacity) > 0) else 50.0
    }

    # Personnel
    pers = db.query(Personnel).filter(Personnel.facility_id == facility_id).first()
    personnel_data = {
        "doctors_count": pers.doctors_count if pers else 3,
        "nurses_count": pers.nurses_count if pers else 8,
        "pharmacists_count": pers.pharmacists_count if pers else 2,
        "asha_count": pers.asha_count if pers else 12,
        "total_staff": (pers.doctors_count + pers.nurses_count + pers.pharmacists_count + pers.asha_count) if pers else 25
    }

    # Inventory
    inventory_items = db.query(Inventory).filter(Inventory.facility_id == facility_id).all()
    inventory_data = [
        {
            "id": inv.id,
            "item_code": inv.item_code,
            "item_name": inv.item_name,
            "quantity": inv.quantity,
            "safety_stock": inv.safety_stock,
            "incoming_quantity": inv.incoming_quantity,
            "batch": inv.batch,
            "expiry": str(inv.expiry) if inv.expiry else None,
            "unit": inv.unit
        }
        for inv in inventory_items
    ]

    # Active Alerts
    alerts = db.query(Alert).filter(Alert.facility_id == facility_id, Alert.status == "ACTIVE").all()
    alert_data = [
        {
            "id": a.id,
            "alert_code": a.alert_code,
            "resource_id": a.resource_id,
            "severity": a.severity.value,
            "title": a.title,
            "projected_impact_date": str(a.projected_impact_date) if a.projected_impact_date else None,
            "created_at": a.created_at.isoformat() if a.created_at else None
        }
        for a in alerts
    ]

    # Demand Forecasts
    forecasts = db.query(Forecast).filter(Forecast.facility_id == facility_id).all()
    forecast_data = [
        {
            "id": f.id,
            "item_code": f.item_code,
            "expected_daily_demand": f.expected_daily_demand,
            "days_of_cover": f.days_of_cover,
            "projected_stockout_date": str(f.projected_stockout_date) if f.projected_stockout_date else None,
            "confidence_score": f.confidence_score
        }
        for f in forecasts
    ]

    return {
        "facility": {
            "id": fac.id,
            "facility_code": fac.facility_code,
            "name": fac.name,
            "facility_type": fac.facility_type.value,
            "state": fac.state,
            "district": fac.district,
            "latitude": fac.latitude,
            "longitude": fac.longitude,
            "status": "OPERATIONAL"
        },
        "assigned_officers": officer_info,
        "capacity": bed_data,
        "personnel": personnel_data,
        "inventory": inventory_data,
        "active_alerts": alert_data,
        "forecasts": forecast_data
    }

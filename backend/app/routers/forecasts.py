from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Forecast, Facility, Medicine, Inventory, User, UserRole
from app.schemas import ForecastResponse, RiskExplanationResponse
from app.security import (
    get_current_user, require_facility_officer, require_cdmo, 
    verify_facility_access
)
from app.algorithms import run_forecast_and_alert_engine, classify_risk_severity
from app.explainability import build_risk_explanation_for_forecast

router = APIRouter(prefix="/api/v1", tags=["Demand Forecasting & Risk Engine"])

def _enrich_forecast(f: Forecast, db: Session) -> ForecastResponse:
    inv = db.query(Inventory).filter(
        Inventory.facility_id == f.facility_id,
        Inventory.medicine_id == f.medicine_id
    ).first()
    
    current_stock = inv.quantity if inv else 0
    safety_stock = inv.safety_stock if inv else 40
    incoming_quantity = inv.incoming_quantity if inv else 0
    
    if inv:
        severity = classify_risk_severity(f.days_of_cover, inv.quantity, inv.safety_stock)
        risk_level = severity.value if hasattr(severity, 'value') else str(severity)
    else:
        risk_level = "CRITICAL" if f.days_of_cover < 3 else ("WARNING" if f.days_of_cover < 7 else "SAFE")

    explanation = build_risk_explanation_for_forecast(f, db)

    return ForecastResponse(
        id=f.id,
        facility_id=f.facility_id,
        medicine_id=f.medicine_id,
        item_code=f.item_code,
        forecast_date=f.forecast_date,
        expected_daily_demand=f.expected_daily_demand,
        days_of_cover=f.days_of_cover,
        projected_stockout_date=f.projected_stockout_date,
        confidence_score=f.confidence_score,
        calculated_at=f.calculated_at,
        facility_name=f.facility.name if f.facility else None,
        district=f.facility.district if f.facility else None,
        state=f.facility.state if f.facility else None,
        item_name=f.medicine.name if f.medicine else None,
        current_stock=current_stock,
        safety_stock=safety_stock,
        incoming_quantity=incoming_quantity,
        risk_level=risk_level,
        explanation=explanation
    )

@router.get("/forecasts", response_model=List[ForecastResponse])
def get_all_forecasts(
    current_user: User = Depends(require_facility_officer),
    db: Session = Depends(get_db)
):
    """
    Returns list of demand forecasts.
    FACILITY_OFFICER sees only their assigned facility data.
    CDMO and ADMIN see all facilities.
    """
    query = db.query(Forecast)
    if current_user.role == UserRole.FACILITY_OFFICER:
        if current_user.facility_id is None:
            return []
        query = query.filter(Forecast.facility_id == current_user.facility_id)

    forecasts = query.order_by(Forecast.days_of_cover.asc()).all()
    return [_enrich_forecast(f, db) for f in forecasts]

@router.get("/forecasts/{forecast_id}", response_model=ForecastResponse)
def get_forecast_by_id(
    forecast_id: int,
    current_user: User = Depends(require_facility_officer),
    db: Session = Depends(get_db)
):
    """
    Returns a single demand forecast record by ID.
    Enforces facility-scoped access.
    """
    forecast = db.query(Forecast).filter(Forecast.id == forecast_id).first()
    if not forecast:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Forecast with id={forecast_id} not found."
        )

    verify_facility_access(forecast.facility_id, current_user)
    return _enrich_forecast(forecast, db)

@router.get("/forecasts/{forecast_id}/explanation", response_model=RiskExplanationResponse)
def get_forecast_explanation(
    forecast_id: int,
    current_user: User = Depends(require_facility_officer),
    db: Session = Depends(get_db)
):
    """
    Returns an authoritative, deterministic explanation of demand forecast calculations,
    days of cover, and stockout risk.
    Enforces facility-scoped access control.
    """
    forecast = db.query(Forecast).filter(Forecast.id == forecast_id).first()
    if not forecast:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Forecast with id={forecast_id} not found."
        )

    verify_facility_access(forecast.facility_id, current_user)
    explanation = build_risk_explanation_for_forecast(forecast, db)
    return RiskExplanationResponse(**explanation)


@router.get("/facilities/{facility_id}/forecasts", response_model=List[ForecastResponse])
def get_facility_forecasts(
    facility_id: int,
    current_user: User = Depends(require_facility_officer),
    db: Session = Depends(get_db)
):
    """
    Returns demand forecasts for a specific facility_id.
    Enforces facility-scoped access.
    """
    verify_facility_access(facility_id, current_user)
    forecasts = db.query(Forecast).filter(Forecast.facility_id == facility_id).order_by(Forecast.days_of_cover.asc()).all()
    return [_enrich_forecast(f, db) for f in forecasts]

@router.post("/forecasts/recalculate", response_model=List[ForecastResponse])
def recalculate_forecasts(
    facility_id: Optional[int] = None,
    current_user: User = Depends(require_cdmo),
    db: Session = Depends(get_db)
):
    """
    Triggers deterministic demand forecast & risk engine execution.
    Requires CDMO or ADMIN role.
    """
    if facility_id and current_user.role == UserRole.FACILITY_OFFICER:
        verify_facility_access(facility_id, current_user)

    generated_forecasts, _ = run_forecast_and_alert_engine(db, facility_id_filter=facility_id)
    return [_enrich_forecast(f, db) for f in generated_forecasts]

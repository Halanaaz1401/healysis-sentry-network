from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from app.models import (
    Facility, Inventory, Forecast, Alert, Recommendation, Medicine,
    User, UserRole, AlertSeverity, RecommendationStatus
)
from app.security import verify_facility_access

def get_facility_overview(facility_id: int, current_user: User, db: Session) -> Dict[str, Any]:
    """
    Backend function tool 1: Returns verified facility overview, location, inventory count, active alerts, and forecasts.
    """
    verify_facility_access(facility_id, current_user)
    fac = db.query(Facility).filter(Facility.id == facility_id).first()
    if not fac:
        return {"error": f"Facility with id={facility_id} not found."}

    inv_items = db.query(Inventory).filter(Inventory.facility_id == fac.id).all()
    alerts = db.query(Alert).filter(Alert.facility_id == fac.id, Alert.status == "ACTIVE").all()
    forecasts = db.query(Forecast).filter(Forecast.facility_id == fac.id).all()

    return {
        "facility_id": fac.id,
        "facility_code": fac.facility_code,
        "name": fac.name,
        "facility_type": fac.facility_type.value,
        "state": fac.state,
        "district": fac.district,
        "latitude": fac.latitude,
        "longitude": fac.longitude,
        "total_inventory_skus": len(inv_items),
        "active_alerts_count": len(alerts),
        "active_alerts": [
            {
                "alert_code": a.alert_code,
                "resource_id": a.resource_id,
                "severity": a.severity.value,
                "title": a.title,
                "projected_impact_date": str(a.projected_impact_date) if a.projected_impact_date else None
            }
            for a in alerts
        ],
        "forecasts_summary": [
            {
                "item_code": f.item_code,
                "days_of_cover": f.days_of_cover,
                "expected_daily_demand": f.expected_daily_demand,
                "projected_stockout_date": str(f.projected_stockout_date) if f.projected_stockout_date else None
            }
            for f in forecasts
        ]
    }

def get_resource_status(facility_id: int, resource_id: str, current_user: User, db: Session) -> Dict[str, Any]:
    """
    Backend function tool 2: Returns stock, incoming, safety stock, daily demand, days of cover, projected stockout, and severity.
    """
    verify_facility_access(facility_id, current_user)
    inv = db.query(Inventory).filter(
        Inventory.facility_id == facility_id,
        Inventory.item_code == resource_id
    ).first()

    if not inv:
        return {"error": f"Resource '{resource_id}' not found at facility_id={facility_id}."}

    forecast = db.query(Forecast).filter(
        Forecast.facility_id == facility_id,
        Forecast.item_code == resource_id
    ).first()

    doc = forecast.days_of_cover if forecast else 0.0
    daily_demand = forecast.expected_daily_demand if forecast else 0.0
    stockout_date = str(forecast.projected_stockout_date) if forecast and forecast.projected_stockout_date else None

    severity = "CRITICAL" if doc < 3.0 or inv.quantity == 0 else ("WARNING" if doc < 7.0 or inv.quantity < inv.safety_stock else "SAFE")

    return {
        "facility_id": facility_id,
        "item_code": inv.item_code,
        "item_name": inv.item_name,
        "current_stock": inv.quantity,
        "incoming_stock": inv.incoming_quantity,
        "safety_stock": inv.safety_stock,
        "unit": inv.unit,
        "expected_daily_demand": daily_demand,
        "days_of_cover": doc,
        "projected_stockout_date": stockout_date,
        "risk_severity": severity,
        "forecast_method": "EWMA + 7-Day Velocity (alpha=0.3)",
        "data_quality": "VERIFIED_DB_RECORD"
    }

def get_active_alerts(facility_id: Optional[int], severity: Optional[str], current_user: User, db: Session) -> List[Dict[str, Any]]:
    """
    Backend function tool 3: Returns active early warning alerts with evidence JSON.
    """
    query = db.query(Alert).filter(Alert.status == "ACTIVE")
    
    if current_user.role == UserRole.FACILITY_OFFICER:
        if current_user.facility_id is None:
            return []
        query = query.filter(Alert.facility_id == current_user.facility_id)
    elif facility_id:
        verify_facility_access(facility_id, current_user)
        query = query.filter(Alert.facility_id == facility_id)

    if severity:
        query = query.filter(Alert.severity == severity.upper())

    alerts = query.order_by(Alert.severity.desc(), Alert.created_at.desc()).all()
    return [
        {
            "alert_id": a.id,
            "alert_code": a.alert_code,
            "facility_id": a.facility_id,
            "resource_id": a.resource_id,
            "severity": a.severity.value,
            "title": a.title,
            "evidence": a.evidence_json,
            "projected_impact_date": str(a.projected_impact_date) if a.projected_impact_date else None,
            "created_at": a.created_at.isoformat()
        }
        for a in alerts
    ]

def get_forecasts(facility_id: Optional[int], resource_id: Optional[str], current_user: User, db: Session) -> List[Dict[str, Any]]:
    """
    Backend function tool 4: Returns verified demand forecasts.
    """
    query = db.query(Forecast)
    if current_user.role == UserRole.FACILITY_OFFICER:
        if current_user.facility_id is None:
            return []
        query = query.filter(Forecast.facility_id == current_user.facility_id)
    elif facility_id:
        verify_facility_access(facility_id, current_user)
        query = query.filter(Forecast.facility_id == facility_id)

    if resource_id:
        query = query.filter(Forecast.item_code == resource_id)

    forecasts = query.order_by(Forecast.days_of_cover.asc()).all()
    return [
        {
            "forecast_id": f.id,
            "facility_id": f.facility_id,
            "item_code": f.item_code,
            "expected_daily_demand": f.expected_daily_demand,
            "days_of_cover": f.days_of_cover,
            "projected_stockout_date": str(f.projected_stockout_date) if f.projected_stockout_date else None,
            "confidence_score": f.confidence_score
        }
        for f in forecasts
    ]

def get_redistribution_recommendations(facility_id: Optional[int], status: Optional[str], current_user: User, db: Session) -> List[Dict[str, Any]]:
    """
    Backend function tool 5: Returns cross-district redistribution candidate recommendations.
    """
    query = db.query(Recommendation)
    if current_user.role == UserRole.FACILITY_OFFICER:
        if current_user.facility_id is None:
            return []
        query = query.filter(
            (Recommendation.donor_facility_id == current_user.facility_id) |
            (Recommendation.recipient_facility_id == current_user.facility_id)
        )
    elif facility_id:
        verify_facility_access(facility_id, current_user)
        query = query.filter(
            (Recommendation.donor_facility_id == facility_id) |
            (Recommendation.recipient_facility_id == facility_id)
        )

    if status:
        query = query.filter(Recommendation.status == status.upper())

    recs = query.order_by(Recommendation.urgency_level.desc()).all()
    return [
        {
            "recommendation_id": r.id,
            "recommendation_code": r.recommendation_code,
            "donor_facility_id": r.donor_facility_id,
            "recipient_facility_id": r.recipient_facility_id,
            "item_code": r.item_code,
            "recommended_quantity": r.recommended_quantity,
            "haversine_distance_km": r.haversine_distance_km,
            "expected_days_cover_gained": r.expected_days_cover_gained,
            "confidence_score": r.confidence_score,
            "reason": r.reason,
            "status": r.status.value,
            "requires_human_approval": True
        }
        for r in recs
    ]

def get_facility_comparison(facility_ids: List[int], current_user: User, db: Session) -> List[Dict[str, Any]]:
    """
    Backend function tool 6: Returns a comparative overview of stock risk, days of cover, and alerts across specified facility IDs.
    """
    comparison = []
    for fid in facility_ids:
        if current_user.role == UserRole.FACILITY_OFFICER and current_user.facility_id != fid:
            continue
        overview = get_facility_overview(fid, current_user, db)
        if "error" not in overview:
            comparison.append(overview)
def get_risk_explanation(facility_id: int, resource_id: str, current_user: User, db: Session) -> Dict[str, Any]:
    """
    Backend function tool 7: Returns grounded explainable risk telemetry and deterministic reasoning for a facility resource.
    """
    verify_facility_access(facility_id, current_user)
    alert = db.query(Alert).filter(Alert.facility_id == facility_id, Alert.resource_id == resource_id).first()
    if alert:
        from app.explainability import build_risk_explanation_for_alert
        return build_risk_explanation_for_alert(alert, db)
    
    fc = db.query(Forecast).filter(Forecast.facility_id == facility_id, Forecast.item_code == resource_id).first()
    if fc:
        from app.explainability import build_risk_explanation_for_forecast
        return build_risk_explanation_for_forecast(fc, db)
        
    return {"error": f"No risk record found for facility_id={facility_id}, resource={resource_id}"}

def get_recommendation_explanation(recommendation_id: int, current_user: User, db: Session) -> Dict[str, Any]:
    """
    Backend function tool 8: Returns grounded explainable redistribution route and surplus evidence.
    """
    rec = db.query(Recommendation).filter(Recommendation.id == recommendation_id).first()
    if not rec:
        return {"error": f"Recommendation #{recommendation_id} not found."}
    if current_user.role == UserRole.FACILITY_OFFICER:
        if current_user.facility_id not in [rec.donor_facility_id, rec.recipient_facility_id]:
            return {"error": "Access forbidden: restricted to assigned facility."}
    from app.explainability import build_recommendation_explanation
    return build_recommendation_explanation(rec, db)

def simulate_redistribution_scenario(
    donor_facility_id: int,
    recipient_facility_id: int,
    resource_id: str,
    transfer_quantity: int,
    current_user: User,
    db: Session
) -> Dict[str, Any]:
    """
    Backend function tool 9: Executes a read-only What-If Redistribution Simulation without modifying any database records.
    """
    from app.schemas import RedistributionSimulationRequest
    from app.simulation_service import run_redistribution_simulation

    req = RedistributionSimulationRequest(
        donor_facility_id=donor_facility_id,
        recipient_facility_id=recipient_facility_id,
        item_code=resource_id,
        transfer_quantity=transfer_quantity
    )
    res = run_redistribution_simulation(req, current_user, db)
    return res.model_dump()

def get_transfer_verification(recommendation_id: int, current_user: User, db: Session) -> Dict[str, Any]:
    """
    Backend function tool 10: Returns authoritative, deterministic Before -> After Verification for a redistribution recommendation.
    Cross-checks database inventory and SHA-256 audit ledger across all 12 parameters without database mutation.
    """
    from app.verification_service import verify_redistribution_execution
    try:
        res = verify_redistribution_execution(recommendation_id, current_user, db)
        return res.model_dump(mode="json")
    except Exception as exc:
        return {"error": str(exc)}

def get_network_intelligence(current_user: User, db: Session) -> Dict[str, Any]:
    """
    Backend function tool 11: Returns authoritative Network and District Intelligence.
    Strictly read-only.
    """
    from app.network_intelligence_service import compute_network_intelligence
    if current_user.role == UserRole.FACILITY_OFFICER:
        return {"error": "Access forbidden: Network Intelligence is restricted to CDMO and ADMIN roles."}
    res = compute_network_intelligence(db)
    return res.model_dump(mode="json")

TOOL_MAP = {
    "get_facility_overview": get_facility_overview,
    "get_resource_status": get_resource_status,
    "get_active_alerts": get_active_alerts,
    "get_forecasts": get_forecasts,
    "get_redistribution_recommendations": get_redistribution_recommendations,
    "get_facility_comparison": get_facility_comparison,
    "get_risk_explanation": get_risk_explanation,
    "get_recommendation_explanation": get_recommendation_explanation,
    "simulate_redistribution_scenario": simulate_redistribution_scenario,
    "get_transfer_verification": get_transfer_verification,
    "get_network_intelligence": get_network_intelligence,
}



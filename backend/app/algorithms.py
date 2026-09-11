import math
from datetime import datetime, date, timedelta, timezone
from typing import List, Dict, Optional, Tuple, Any
from sqlalchemy.orm import Session

from app.models import (
    Facility, Inventory, ConsumptionLog, Forecast, Alert, Medicine, Recommendation,
    AlertSeverity, AlertType, AlertStatus, ActionType, UrgencyLevel, RecommendationStatus
)

ALPHA_EWMA = 0.3
EARTH_RADIUS_KM = 6371.0

def calculate_haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculates the Haversine distance in kilometers between two GPS coordinate pairs.
    Formula:
    a = sin²(Δlat/2) + cos(lat1) * cos(lat2) * sin²(Δlon/2)
    c = 2 * atan2(√a, √(1-a))
    d = R * c
    """
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    
    a = (math.sin(d_lat / 2.0) ** 2) + (
        math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * (math.sin(d_lon / 2.0) ** 2)
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    distance = EARTH_RADIUS_KM * c
    return round(distance, 2)

def calculate_7day_velocity(consumption_logs: List[ConsumptionLog]) -> float:
    """
    Calculates 7-day average daily consumption velocity Vd.
    Vd = total consumption over recent 7 days / 7
    """
    if not consumption_logs:
        return 0.0

    dispense_logs = [c for c in consumption_logs if c.action_type == ActionType.DISPENSE]
    if not dispense_logs:
        return 0.0

    total_dispensed = sum(c.quantity_dispensed for c in dispense_logs)
    num_days = max(len(set(c.date for c in dispense_logs)), 7)
    
    velocity = total_dispensed / float(num_days)
    return round(velocity, 2)

def calculate_ewma_demand(consumption_logs: List[ConsumptionLog], alpha: float = ALPHA_EWMA) -> float:
    """
    Calculates Exponentially Weighted Moving Average (EWMA) demand.
    EWMA_t = alpha * C_t + (1 - alpha) * EWMA_{t-1}
    """
    if not consumption_logs:
        return 0.0

    sorted_logs = sorted(
        [c for c in consumption_logs if c.action_type == ActionType.DISPENSE], 
        key=lambda x: x.date
    )
    if not sorted_logs:
        return 0.0

    ewma = float(sorted_logs[0].quantity_dispensed)
    for log in sorted_logs[1:]:
        ewma = (alpha * float(log.quantity_dispensed)) + ((1.0 - alpha) * ewma)

    return round(max(0.0, ewma), 2)

def calculate_days_of_cover(current_stock: int, incoming_stock: int, expected_daily_demand: float) -> float:
    """
    Calculates days of cover based on available stock and expected daily demand.
    days_of_cover = (current_stock + incoming_stock) / expected_daily_demand
    """
    available_stock = max(0, current_stock + max(0, incoming_stock))
    if available_stock == 0:
        return 0.0

    if expected_daily_demand <= 0.0:
        return 999.0

    days_cover = float(available_stock) / expected_daily_demand
    return round(days_cover, 2)

def calculate_projected_stockout_date(start_date: date, days_of_cover: float) -> Optional[date]:
    """
    Calculates when available stock is projected to deplete below zero.
    """
    if days_of_cover >= 999.0 or math.isinf(days_of_cover):
        return None

    depletion_days = max(0, math.floor(days_of_cover))
    return start_date + timedelta(days=depletion_days)

def classify_risk_severity(days_of_cover: float, current_stock: int, safety_stock: int) -> AlertSeverity:
    """
    Deterministic risk classification:
    - CRITICAL: days_of_cover < 3.0 or current_stock == 0
    - WARNING: 3.0 <= days_of_cover < 7.0 or current_stock < safety_stock
    - SAFE: days_of_cover >= 7.0 and current_stock >= safety_stock
    """
    if days_of_cover < 3.0 or current_stock == 0:
        return AlertSeverity.CRITICAL
    elif days_of_cover < 7.0 or current_stock < safety_stock:
        return AlertSeverity.WARNING
    else:
        return AlertSeverity.LOW

def calculate_donor_transferable_quantity(donor_inventory: Inventory, today_date: Optional[date] = None) -> int:
    """
    Calculates max transferable quantity for a donor facility without pushing it below safety stock:
    transferable_quantity = max(0, donor_available_stock - donor_safety_stock)
    Excludes expired batch inventory.
    """
    today_val = today_date or date.today()
    if donor_inventory.expiry and donor_inventory.expiry < today_val:
        return 0

    available = max(0, donor_inventory.quantity)
    safety = max(0, donor_inventory.safety_stock)
    transferable = max(0, available - safety)
    return transferable

def calculate_recipient_required_quantity(recipient_inventory: Inventory, expected_daily_demand: float) -> int:
    """
    Calculates required stock quantity for a recipient node to achieve a 7-day safety buffer:
    target_stock = max(safety_stock * 2, ceil(daily_demand * 7))
    required_quantity = max(0, target_stock - (current_stock + incoming_stock))
    """
    available = max(0, recipient_inventory.quantity + recipient_inventory.incoming_quantity)
    target_buffer = max(recipient_inventory.safety_stock * 2, math.ceil(expected_daily_demand * 7.0))
    required = max(0, target_buffer - available)
    return required

def score_redistribution_candidate(
    donor_transferable_qty: int,
    donor_safety_stock: int,
    distance_km: float,
    urgency_level: UrgencyLevel
) -> float:
    """
    Deterministic scoring formula for ranking donor candidates:
    - Surplus Score: donor_transferable_qty / donor_safety_stock
    - Distance Penalty: 1 / (1 + distance_km / 50.0)
    - Urgency Weight: CRITICAL = 2.0, URGENT = 1.5, ROUTINE = 1.0
    Score = surplus_score * distance_penalty * urgency_weight * 100
    """
    distance_penalty = 1.0 / (1.0 + (distance_km / 50.0))
    surplus_score = float(donor_transferable_qty) / float(max(1, donor_safety_stock))
    
    urgency_weight = 1.0
    if urgency_level == UrgencyLevel.CRITICAL:
        urgency_weight = 2.0
    elif urgency_level == UrgencyLevel.URGENT:
        urgency_weight = 1.5

    final_score = surplus_score * distance_penalty * urgency_weight * 100.0
    return round(final_score, 2)

def run_forecast_and_alert_engine(db: Session, facility_id_filter: Optional[int] = None) -> Tuple[List[Forecast], List[Alert]]:
    """
    Executes the deterministic forecasting and early warning risk engine across database facilities.
    """
    today = date.today()
    query = db.query(Facility)
    if facility_id_filter:
        query = query.filter(Facility.id == facility_id_filter)
    facilities = query.all()

    generated_forecasts: List[Forecast] = []
    generated_alerts: List[Alert] = []

    for fac in facilities:
        inventory_items = db.query(Inventory).filter(Inventory.facility_id == fac.id).all()

        for inv in inventory_items:
            start_history_date = today - timedelta(days=30)
            c_logs = db.query(ConsumptionLog).filter(
                ConsumptionLog.facility_id == fac.id,
                ConsumptionLog.medicine_id == inv.medicine_id,
                ConsumptionLog.date >= start_history_date
            ).order_by(ConsumptionLog.date.asc()).all()

            v7 = calculate_7day_velocity(c_logs)
            ewma = calculate_ewma_demand(c_logs)
            
            expected_demand = ewma if ewma > 0 else v7
            doc = calculate_days_of_cover(inv.quantity, inv.incoming_quantity, expected_demand)
            projected_stockout = calculate_projected_stockout_date(today, doc)
            severity = classify_risk_severity(doc, inv.quantity, inv.safety_stock)

            forecast = db.query(Forecast).filter(
                Forecast.facility_id == fac.id,
                Forecast.medicine_id == inv.medicine_id
            ).first()

            if not forecast:
                forecast = Forecast(
                    facility_id=fac.id,
                    medicine_id=inv.medicine_id,
                    item_code=inv.item_code,
                    forecast_date=today,
                    expected_daily_demand=expected_demand,
                    days_of_cover=doc,
                    projected_stockout_date=projected_stockout,
                    confidence_score=0.95 if c_logs else 0.70,
                    calculated_at=datetime.now(timezone.utc)
                )
                db.add(forecast)
            else:
                forecast.forecast_date = today
                forecast.expected_daily_demand = expected_demand
                forecast.days_of_cover = doc
                forecast.projected_stockout_date = projected_stockout
                forecast.confidence_score = 0.95 if c_logs else 0.70
                forecast.calculated_at = datetime.now(timezone.utc)

            generated_forecasts.append(forecast)

            if severity in [AlertSeverity.WARNING, AlertSeverity.CRITICAL]:
                alert_code = f"ALT-{fac.facility_code}-{inv.item_code}"
                alert = db.query(Alert).filter(Alert.alert_code == alert_code).first()

                title = f"Critical Stockout Projected for {inv.item_name}" if severity == AlertSeverity.CRITICAL else f"Stock Warning: {inv.item_name} Below Buffer"
                action_text = f"Emergency Stock Rebalance to {fac.name}" if severity == AlertSeverity.CRITICAL else f"Prepare Stock Order for {fac.name}"

                evidence = {
                    "current_quantity": inv.quantity,
                    "incoming_quantity": inv.incoming_quantity,
                    "safety_stock": inv.safety_stock,
                    "expected_daily_demand": expected_demand,
                    "days_of_cover": doc,
                    "forecast_method": "EWMA + 7-Day Velocity (alpha=0.3)",
                    "historical_days_evaluated": len(c_logs),
                    "recommended_action": action_text
                }

                if not alert:
                    alert = Alert(
                        alert_code=alert_code,
                        facility_id=fac.id,
                        resource_id=inv.item_code,
                        severity=severity,
                        alert_type=AlertType.STOCKOUT_PROJECTED if doc < 7 else AlertType.GHOST_DRAWDOWN,
                        title=title,
                        evidence_json=evidence,
                        projected_impact_date=projected_stockout,
                        status=AlertStatus.ACTIVE
                    )
                    db.add(alert)
                else:
                    alert.severity = severity
                    alert.title = title
                    alert.evidence_json = evidence
                    alert.projected_impact_date = projected_stockout
                    alert.status = AlertStatus.ACTIVE

                generated_alerts.append(alert)

            else:
                # Severity is LOW (safe). Resolve any existing ACTIVE alert for this
                # facility+item so that stale CRITICAL/WARNING alerts are not retained
                # after a redistribution transfer raises stock above the safe threshold.
                alert_code = f"ALT-{fac.facility_code}-{inv.item_code}"
                existing_alert = db.query(Alert).filter(
                    Alert.alert_code == alert_code,
                    Alert.status == AlertStatus.ACTIVE,
                ).first()
                if existing_alert:
                    existing_alert.status = AlertStatus.RESOLVED
                    existing_alert.severity = AlertSeverity.LOW
                    existing_alert.evidence_json = {
                        "current_quantity": inv.quantity,
                        "incoming_quantity": inv.incoming_quantity,
                        "safety_stock": inv.safety_stock,
                        "expected_daily_demand": expected_demand,
                        "days_of_cover": doc,
                        "forecast_method": "EWMA + 7-Day Velocity (alpha=0.3)",
                        "historical_days_evaluated": len(c_logs),
                        "resolved_reason": "Stock level returned to safe threshold after redistribution or replenishment."
                    }

    db.commit()
    return generated_forecasts, generated_alerts


def generate_and_persist_redistribution_recommendations(db: Session) -> List[Recommendation]:
    """
    Executes the deterministic cross-district redistribution engine:
    1. Identifies recipient facilities facing shortages (days_of_cover < 7.0 or CRITICAL/WARNING alert).
    2. Discovers eligible donor facilities (same medicine, non-expired stock, stock > safety stock, donor != recipient).
    3. Calculates Haversine distance, transferable quantity, and deterministic ranking score.
    4. Generates human-readable explanations based on calculation inputs.
    5. Persists recommendations into DB with status PENDING_HUMAN_APPROVAL.
    """
    # 1. Run forecast engine to ensure fresh telemetry
    run_forecast_and_alert_engine(db)
    today = date.today()

    # Query recipient forecasts facing shortage (days_of_cover < 7.0)
    shortage_forecasts = db.query(Forecast).filter(Forecast.days_of_cover < 7.0).all()
    if not shortage_forecasts:
        return []

    generated_recommendations: List[Recommendation] = []

    for fc in shortage_forecasts:
        recipient_fac = db.query(Facility).filter(Facility.id == fc.facility_id).first()
        recipient_inv = db.query(Inventory).filter(
            Inventory.facility_id == fc.facility_id,
            Inventory.medicine_id == fc.medicine_id
        ).first()

        if not recipient_fac or not recipient_inv:
            continue

        required_qty = calculate_recipient_required_quantity(recipient_inv, fc.expected_daily_demand)
        if required_qty <= 0:
            continue

        urgency = UrgencyLevel.CRITICAL if fc.days_of_cover < 3.0 else UrgencyLevel.URGENT

        # Find candidate donor facilities with the same medicine_id
        candidate_inventories = db.query(Inventory).filter(
            Inventory.medicine_id == fc.medicine_id,
            Inventory.facility_id != fc.facility_id,
            Inventory.quantity > Inventory.safety_stock
        ).all()

        scored_donors = []
        for d_inv in candidate_inventories:
            d_fac = db.query(Facility).filter(Facility.id == d_inv.facility_id).first()
            if not d_fac:
                continue

            transferable_qty = calculate_donor_transferable_quantity(d_inv, today)
            if transferable_qty <= 0:
                continue

            # Calculate Haversine distance
            dist_km = calculate_haversine_distance(
                recipient_fac.latitude, recipient_fac.longitude,
                d_fac.latitude, d_fac.longitude
            )

            # Recommend volume capped by recipient requirement and donor surplus
            recommended_transfer_qty = min(required_qty, transferable_qty)

            # Score candidate
            score = score_redistribution_candidate(
                donor_transferable_qty=transferable_qty,
                donor_safety_stock=d_inv.safety_stock,
                distance_km=dist_km,
                urgency_level=urgency
            )

            scored_donors.append({
                "donor_facility": d_fac,
                "donor_inventory": d_inv,
                "transferable_qty": transferable_qty,
                "recommended_qty": recommended_transfer_qty,
                "distance_km": dist_km,
                "score": score
            })

        if not scored_donors:
            continue

        # Rank candidates deterministically by score descending, then distance ascending
        scored_donors.sort(key=lambda x: (-x["score"], x["distance_km"]))
        top_candidate = scored_donors[0]

        donor_fac = top_candidate["donor_facility"]
        donor_inv = top_candidate["donor_inventory"]
        rec_qty = top_candidate["recommended_qty"]
        dist_km = top_candidate["distance_km"]
        score = top_candidate["score"]

        # Calculate days of cover gained for recipient
        days_gained = round(float(rec_qty) / max(0.01, fc.expected_daily_demand), 1)

        # Generate human-readable explanation from calculation inputs
        depletion_str = f"{fc.days_of_cover} days" if fc.days_of_cover > 0 else "0 days (stockout)"
        reason_explanation = (
            f"{recipient_fac.name} is projected to face stock depletion in {depletion_str}. "
            f"{donor_fac.name} has {top_candidate['transferable_qty']} transferable units while remaining "
            f"above its safety stock threshold (safety stock = {donor_inv.safety_stock}) and is {dist_km} km away."
        )

        rec_code = f"REC-{recipient_fac.facility_code}-{donor_fac.facility_code}-{fc.item_code}"
        existing_rec = db.query(Recommendation).filter(Recommendation.recommendation_code == rec_code).first()

        if not existing_rec:
            rec_obj = Recommendation(
                recommendation_code=rec_code,
                donor_facility_id=donor_fac.id,
                recipient_facility_id=recipient_fac.id,
                medicine_id=fc.medicine_id,
                item_code=fc.item_code,
                recommended_quantity=rec_qty,
                urgency_level=urgency,
                haversine_distance_km=dist_km,
                expected_days_cover_gained=days_gained,
                confidence_score=min(1.0, round(score / 100.0, 2)),
                reason=reason_explanation,
                status=RecommendationStatus.PENDING_HUMAN_APPROVAL
            )
            db.add(rec_obj)
            generated_recommendations.append(rec_obj)
        else:
            existing_rec.recommended_quantity = rec_qty
            existing_rec.urgency_level = urgency
            existing_rec.haversine_distance_km = dist_km
            existing_rec.expected_days_cover_gained = days_gained
            existing_rec.confidence_score = min(1.0, round(score / 100.0, 2))
            existing_rec.reason = reason_explanation
            generated_recommendations.append(existing_rec)

    db.commit()
    for rec in generated_recommendations:
        db.refresh(rec)
    return generated_recommendations


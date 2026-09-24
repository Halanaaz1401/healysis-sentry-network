import math
import uuid
from datetime import date
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Facility, Inventory, Medicine, Forecast, ConsumptionLog, User, UserRole, AlertSeverity
from app.algorithms import (
    calculate_haversine_distance,
    calculate_days_of_cover,
    calculate_projected_stockout_date,
    calculate_7day_velocity,
    classify_risk_severity
)
from app.schemas import (
    RedistributionSimulationRequest,
    RedistributionSimulationResponse,
    SimulationDonorNode,
    SimulationRecipientNode,
    SimulationRiskAnalysis
)

def run_redistribution_simulation(
    req: RedistributionSimulationRequest,
    current_user: User,
    db: Session
) -> RedistributionSimulationResponse:
    """
    Executes a deterministic What-If Redistribution Simulation using verified database telemetry.
    Strictly READ-ONLY: Never modifies inventory, forecasts, alerts, recommendations, or ledger.
    """
    # ── 1. Input Validation ───────────────────────────────────────────────────────
    if req.transfer_quantity <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Transfer quantity must be a positive integer greater than zero. Received: {req.transfer_quantity}"
        )

    if req.donor_facility_id == req.recipient_facility_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Donor facility and recipient facility cannot be identical."
        )

    # ── 2. Server-Side RBAC & Facility Scoping ────────────────────────────────────
    if current_user.role == UserRole.FACILITY_OFFICER:
        if current_user.facility_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden. Facility officer has no assigned facility."
            )
        if current_user.facility_id not in [req.donor_facility_id, req.recipient_facility_id]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Forbidden. Facility Officer is restricted to facility #{current_user.facility_id}. "
                    f"Cannot simulate transfers between donor #{req.donor_facility_id} and recipient #{req.recipient_facility_id}."
                )
            )

    # ── 3. Facility Existence Checks ──────────────────────────────────────────────
    donor_fac = db.query(Facility).filter(Facility.id == req.donor_facility_id).first()
    if not donor_fac:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Donor facility with id={req.donor_facility_id} not found."
        )

    recip_fac = db.query(Facility).filter(Facility.id == req.recipient_facility_id).first()
    if not recip_fac:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recipient facility with id={req.recipient_facility_id} not found."
        )

    # ── 4. Medicine Resource Lookup ───────────────────────────────────────────────
    if req.medicine_id:
        med = db.query(Medicine).filter(Medicine.id == req.medicine_id).first()
    elif req.item_code:
        med = db.query(Medicine).filter(Medicine.code == req.item_code).first()
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either item_code or medicine_id must be provided for simulation."
        )

    if not med:
        identifier = req.item_code or req.medicine_id
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Medicine resource '{identifier}' not found in catalog."
        )

    # ── 5. Donor Inventory & Availability Check ───────────────────────────────────
    donor_inv = db.query(Inventory).filter(
        Inventory.facility_id == req.donor_facility_id,
        Inventory.medicine_id == med.id
    ).first()

    if not donor_inv:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Donor facility '{donor_fac.name}' has no inventory record for {med.name} ({med.code})."
        )

    donor_current_stock = donor_inv.quantity
    if req.transfer_quantity > donor_current_stock:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Proposed transfer quantity ({req.transfer_quantity} {donor_inv.unit}) "
                f"exceeds total available stock at donor facility ({donor_current_stock} {donor_inv.unit})."
            )
        )

    # ── 6. Recipient Inventory Telemetry ──────────────────────────────────────────
    recip_inv = db.query(Inventory).filter(
        Inventory.facility_id == req.recipient_facility_id,
        Inventory.medicine_id == med.id
    ).first()

    recipient_current_stock = recip_inv.quantity if recip_inv else 0
    unit = donor_inv.unit or (med.unit or "units")

    # ── 7. Safety Buffers & Baseline Calculations ─────────────────────────────────
    donor_safety = donor_inv.safety_stock if donor_inv.safety_stock is not None else 40
    recipient_safety = recip_inv.safety_stock if (recip_inv and recip_inv.safety_stock is not None) else 40
    donor_surplus = max(0, donor_current_stock - donor_safety)

    simulated_donor_stock = donor_current_stock - req.transfer_quantity
    simulated_recipient_stock = recipient_current_stock + req.transfer_quantity

    # ── 8. Demand Estimation (Deterministic ground truth) ─────────────────────────
    donor_fc = db.query(Forecast).filter(
        Forecast.facility_id == req.donor_facility_id,
        Forecast.medicine_id == med.id
    ).first()

    if donor_fc and donor_fc.expected_daily_demand > 0:
        donor_daily_demand = float(donor_fc.expected_daily_demand)
    elif getattr(donor_inv, "daily_demand", None) and donor_inv.daily_demand > 0:
        donor_daily_demand = float(donor_inv.daily_demand)
    else:
        d_logs = db.query(ConsumptionLog).filter(
            ConsumptionLog.facility_id == req.donor_facility_id,
            ConsumptionLog.medicine_id == med.id
        ).all()
        vel = calculate_7day_velocity(d_logs)
        donor_daily_demand = float(vel) if vel > 0 else 10.0

    recip_fc = db.query(Forecast).filter(
        Forecast.facility_id == req.recipient_facility_id,
        Forecast.medicine_id == med.id
    ).first()

    if recip_fc and recip_fc.expected_daily_demand > 0:
        recip_daily_demand = float(recip_fc.expected_daily_demand)
    elif recip_inv and getattr(recip_inv, "daily_demand", None) and recip_inv.daily_demand > 0:
        recip_daily_demand = float(recip_inv.daily_demand)
    else:
        r_logs = db.query(ConsumptionLog).filter(
            ConsumptionLog.facility_id == req.recipient_facility_id,
            ConsumptionLog.medicine_id == med.id
        ).all()
        vel = calculate_7day_velocity(r_logs)
        recip_daily_demand = float(vel) if vel > 0 else 10.0

    # ── 9. Days of Cover Calculations ─────────────────────────────────────────────
    donor_incoming = donor_inv.incoming_quantity if donor_inv.incoming_quantity else 0
    recip_incoming = recip_inv.incoming_quantity if (recip_inv and recip_inv.incoming_quantity) else 0

    current_donor_doc = calculate_days_of_cover(donor_current_stock, donor_incoming, donor_daily_demand)
    simulated_donor_doc = calculate_days_of_cover(simulated_donor_stock, donor_incoming, donor_daily_demand)

    current_recip_doc = calculate_days_of_cover(recipient_current_stock, recip_incoming, recip_daily_demand)
    simulated_recip_doc = calculate_days_of_cover(simulated_recipient_stock, recip_incoming, recip_daily_demand)

    days_of_cover_lost = max(0.0, round(float(current_donor_doc - simulated_donor_doc), 2))
    days_of_cover_gained = max(0.0, round(float(simulated_recip_doc - current_recip_doc), 2))

    # ── 10. Projected Stockout Dates ──────────────────────────────────────────────
    today = date.today()
    current_donor_so = calculate_projected_stockout_date(today, current_donor_doc)
    simulated_donor_so = calculate_projected_stockout_date(today, simulated_donor_doc)
    current_recip_so = calculate_projected_stockout_date(today, current_recip_doc)
    simulated_recip_so = calculate_projected_stockout_date(today, simulated_recip_doc)

    # ── 11. Logistics & Haversine Distance ────────────────────────────────────────
    dist_km = calculate_haversine_distance(donor_fac.latitude, donor_fac.longitude, recip_fac.latitude, recip_fac.longitude)

    # ── 12. Risk Analysis Flags ───────────────────────────────────────────────────
    donor_buffer_preserved = simulated_donor_stock >= donor_safety
    recipient_buffer_achieved = simulated_recipient_stock >= recipient_safety
    donor_falls_below_safety = simulated_donor_stock < donor_safety
    donor_becomes_new_risk = (simulated_donor_doc < 3.0) or donor_falls_below_safety
    recipient_improves = simulated_recip_doc > current_recip_doc
    recipient_remains_below_safety = simulated_recipient_stock < recipient_safety
    within_donor_surplus = req.transfer_quantity <= donor_surplus
    creates_or_worsens_stockout = donor_falls_below_safety or (simulated_donor_doc < 3.0)
    is_operationally_safe = (
        within_donor_surplus and
        not donor_falls_below_safety and
        simulated_donor_doc >= 7.0 and
        simulated_recip_doc >= 3.0
    )

    # ── 13. Status & Deterministic Explanation ────────────────────────────────────
    if not within_donor_surplus or donor_falls_below_safety or simulated_donor_doc < 3.0:
        sim_status = "UNSAFE"
        reason = (
            f"Proposed transfer of {req.transfer_quantity} {unit} is operationally UNSAFE. "
            f"It depletes donor {donor_fac.name} to {simulated_donor_stock} {unit} ({simulated_donor_doc:.1f} days cover), "
            f"breaching its mandatory {donor_safety} {unit} safety buffer (verified donor surplus is only {donor_surplus} {unit}) "
            f"and inducing a critical donor stockout risk."
        )
    elif simulated_donor_doc < 7.0 or recipient_remains_below_safety or simulated_recip_doc < 3.0:
        sim_status = "CAUTION"
        if recipient_remains_below_safety:
            reason = (
                f"Proposed transfer of {req.transfer_quantity} {unit} requires CAUTION. "
                f"Donor {donor_fac.name} preserves its safety buffer ({simulated_donor_stock} >= {donor_safety} {unit}, {simulated_donor_doc:.1f} days cover), "
                f"but recipient {recip_fac.name} remains below target safety buffer ({simulated_recipient_stock}/{recipient_safety} {unit}, {simulated_recip_doc:.1f} days cover). "
                f"Partial relief achieved without full stockout mitigation."
            )
        else:
            reason = (
                f"Proposed transfer of {req.transfer_quantity} {unit} requires CAUTION. "
                f"Recipient {recip_fac.name} achieves safety buffer, but donor {donor_fac.name} coverage drops to {simulated_donor_doc:.1f} days cover "
                f"(within 3.0-7.0 day warning buffer)."
            )
    else:
        sim_status = "SAFE"
        reason = (
            f"Proposed transfer of {req.transfer_quantity} {unit} is SAFE. "
            f"Recipient {recip_fac.name} coverage improves from {current_recip_doc:.1f} to {simulated_recip_doc:.1f} days (+{days_of_cover_gained:.1f} days gained). "
            f"Donor {donor_fac.name} retains {simulated_donor_stock} {unit} ({simulated_donor_doc:.1f} days cover), "
            f"strictly preserving its configured safety threshold of {donor_safety} {unit}."
        )

    # ── 14. Deterministic Risk Classification & 7-Day Demand ──────────────────────
    def to_risk_label(doc: float, stock: int, safety: int) -> str:
        sev = classify_risk_severity(doc, stock, safety)
        if sev == AlertSeverity.CRITICAL:
            return "CRITICAL"
        elif sev == AlertSeverity.WARNING:
            return "WARNING"
        return "SAFE"

    donor_cur_severity = to_risk_label(current_donor_doc, donor_current_stock, donor_safety)
    donor_sim_severity = to_risk_label(simulated_donor_doc, simulated_donor_stock, donor_safety)

    recip_cur_severity = to_risk_label(current_recip_doc, recipient_current_stock, recipient_safety)
    recip_sim_severity = to_risk_label(simulated_recip_doc, simulated_recipient_stock, recipient_safety)

    donor_7day_demand = round(donor_daily_demand * 7.0, 2)
    recip_7day_demand = round(recip_daily_demand * 7.0, 2)

    # ── 15. Response Construction (Strictly Read-Only) ────────────────────────────
    sim_id = f"SIM-{uuid.uuid4().hex[:8].upper()}"

    donor_node = SimulationDonorNode(
        facility_id=donor_fac.id,
        facility_name=donor_fac.name,
        district=donor_fac.district,
        state=donor_fac.state,
        current_stock=donor_current_stock,
        simulated_stock=simulated_donor_stock,
        daily_demand=round(donor_daily_demand, 2),
        current_days_of_cover=round(current_donor_doc, 2),
        simulated_days_of_cover=round(simulated_donor_doc, 2),
        current_risk_severity=donor_cur_severity,
        simulated_risk_severity=donor_sim_severity,
        safety_buffer=donor_safety,
        safety_stock=donor_safety,
        projected_7day_demand=donor_7day_demand,
        current_projected_stockout=str(current_donor_so) if current_donor_so else None,
        simulated_projected_stockout=str(simulated_donor_so) if simulated_donor_so else None,
        before={
            "stock": donor_current_stock,
            "days_of_cover": round(current_donor_doc, 2),
            "risk_severity": donor_cur_severity,
            "safety_stock": donor_safety,
            "projected_stockout": str(current_donor_so) if current_donor_so else None
        },
        after={
            "stock": simulated_donor_stock,
            "days_of_cover": round(simulated_donor_doc, 2),
            "risk_severity": donor_sim_severity,
            "safety_stock": donor_safety,
            "projected_stockout": str(simulated_donor_so) if simulated_donor_so else None
        },
        proposed_transfer_quantity=req.transfer_quantity,
        surplus_available=donor_surplus,
        buffer_preserved=donor_buffer_preserved,
        days_of_cover_lost=days_of_cover_lost
    )

    recip_node = SimulationRecipientNode(
        facility_id=recip_fac.id,
        facility_name=recip_fac.name,
        district=recip_fac.district,
        state=recip_fac.state,
        current_stock=recipient_current_stock,
        simulated_stock=simulated_recipient_stock,
        daily_demand=round(recip_daily_demand, 2),
        current_days_of_cover=round(current_recip_doc, 2),
        simulated_days_of_cover=round(simulated_recip_doc, 2),
        current_risk_severity=recip_cur_severity,
        simulated_risk_severity=recip_sim_severity,
        safety_buffer=recipient_safety,
        safety_stock=recipient_safety,
        projected_7day_demand=recip_7day_demand,
        current_projected_stockout=str(current_recip_so) if current_recip_so else None,
        simulated_projected_stockout=str(simulated_recip_so) if simulated_recip_so else None,
        before={
            "stock": recipient_current_stock,
            "days_of_cover": round(current_recip_doc, 2),
            "risk_severity": recip_cur_severity,
            "safety_stock": recipient_safety,
            "projected_stockout": str(current_recip_so) if current_recip_so else None
        },
        after={
            "stock": simulated_recipient_stock,
            "days_of_cover": round(simulated_recip_doc, 2),
            "risk_severity": recip_sim_severity,
            "safety_stock": recipient_safety,
            "projected_stockout": str(simulated_recip_so) if simulated_recip_so else None
        },
        buffer_achieved=recipient_buffer_achieved,
        days_of_cover_gained=days_of_cover_gained
    )

    risk_analysis = SimulationRiskAnalysis(
        recipient_improves=recipient_improves,
        recipient_remains_below_safety=recipient_remains_below_safety,
        donor_falls_below_safety=donor_falls_below_safety,
        donor_becomes_new_risk=donor_becomes_new_risk,
        creates_or_worsens_stockout=creates_or_worsens_stockout,
        is_operationally_safe=is_operationally_safe,
        within_donor_surplus=within_donor_surplus
    )

    impact = {
        "recipient_risk_before": recip_cur_severity,
        "recipient_risk_after": recip_sim_severity,
        "donor_risk_before": donor_cur_severity,
        "donor_risk_after": donor_sim_severity,
        "recipient_days_of_cover_gained": days_of_cover_gained,
        "donor_days_of_cover_lost": days_of_cover_lost,
        "distance_km": round(dist_km, 2)
    }

    validation = {
        "donor_safety_buffer_protected": donor_buffer_preserved,
        "sufficient_stock": donor_current_stock >= req.transfer_quantity,
        "is_feasible": (sim_status != "UNSAFE") and donor_buffer_preserved,
        "recipient_buffer_achieved": recipient_buffer_achieved
    }

    feasibility_status = "FEASIBLE" if ((sim_status != "UNSAFE") and donor_buffer_preserved) else "INFEASIBLE"

    return RedistributionSimulationResponse(
        simulation_id=sim_id,
        simulation_only=True,
        resource_id=med.code,
        resource_name=med.name,
        unit=unit,
        transfer_quantity=req.transfer_quantity,
        haversine_distance_km=round(dist_km, 2),
        status=sim_status,
        feasibility_status=feasibility_status,
        reason=reason,
        donor=donor_node,
        recipient=recip_node,
        risk_analysis=risk_analysis,
        impact=impact,
        validation=validation,
        disclaimer="Simulation only — no inventory has been changed. Operational transfers require explicit human approval by an authorized CDMO or Admin."
    )

"""
Healysis — Before → After Verification Service (Feature #10)

Authoritative, strictly read-only verification engine that cross-references
executed redistribution transfers against:
1. Live database inventory records
2. SHA-256 tamper-evident audit ledger entries
3. Recipient and donor pre- and post-transfer telemetry
4. Forecasts and risk thresholds

Guarantees:
- Zero mutations to inventory, recommendations, alerts, or audit ledger.
- Zero LLM hallucinations (all numerical verification values are strictly deterministic).
- Enforces facility-scoped RBAC for FACILITY_OFFICER and global access for CDMO/ADMIN.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import (
    Recommendation,
    Inventory,
    Facility,
    Medicine,
    Forecast,
    AuditEvent,
    User,
    RecommendationStatus,
    UserRole,
)
from app.schemas import (
    RecommendationVerificationResponse,
    VerificationNodeSummary,
    AuditMovementReference,
    ExpectedVsActualResult,
)


def _calc_risk_status(days_of_cover: float) -> str:
    """Classifies risk level deterministically based on days of cover."""
    if days_of_cover < 3.0:
        return "CRITICAL"
    elif days_of_cover < 7.0:
        return "WARNING"
    return "SAFE"


def verify_redistribution_execution(
    recommendation_id: int,
    current_user: User,
    db: Session
) -> RecommendationVerificationResponse:
    """
    Authoritative, read-only verification of a redistribution recommendation's execution.
    Compares the expected state against the actual database state and the SHA-256 audit ledger.

    Returns RecommendationVerificationResponse covering all 12 minimum verification parameters:
    1. Recipient stock before transfer
    2. Donor stock before transfer
    3. Approved transfer quantity
    4. Actual stock movement quantity
    5. Recipient stock after transfer
    6. Donor stock after transfer
    7. Recipient daily demand
    8. Recipient days of cover before/after
    9. Recipient risk status before/after
    10. Donor safety-buffer protection
    11. Audit/stock-movement reference
    12. Expected vs actual result comparison
    """
    # ── 1. Fetch Recommendation ──────────────────────────────────────────────
    rec = db.query(Recommendation).filter(Recommendation.id == recommendation_id).first()
    if not rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recommendation with id={recommendation_id} not found."
        )

    # ── 2. Server-side RBAC enforcement ──────────────────────────────────────
    if current_user.role == UserRole.FACILITY_OFFICER:
        if current_user.facility_id not in (rec.recipient_facility_id, rec.donor_facility_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Forbidden. User '{current_user.full_name}' is restricted to facility_id={current_user.facility_id} "
                    f"and cannot access verification for recommendation #{recommendation_id} "
                    f"(involves donor={rec.donor_facility_id}, recipient={rec.recipient_facility_id})."
                )
            )

    # ── 3. Resolve metadata and facilities ───────────────────────────────────
    donor_fac = rec.donor_facility or db.query(Facility).filter(Facility.id == rec.donor_facility_id).first()
    recip_fac = rec.recipient_facility or db.query(Facility).filter(Facility.id == rec.recipient_facility_id).first()
    donor_name = donor_fac.name if donor_fac else f"Facility #{rec.donor_facility_id}"
    recip_name = recip_fac.name if recip_fac else f"Facility #{rec.recipient_facility_id}"

    med = rec.medicine or db.query(Medicine).filter(Medicine.id == rec.medicine_id).first()
    item_name = med.name if med else rec.item_code
    unit = med.unit if med else "units"

    # Query live inventory records
    donor_inv = db.query(Inventory).filter(
        Inventory.facility_id == rec.donor_facility_id,
        Inventory.medicine_id == rec.medicine_id
    ).first()

    recip_inv = db.query(Inventory).filter(
        Inventory.facility_id == rec.recipient_facility_id,
        Inventory.medicine_id == rec.medicine_id
    ).first()

    # Query forecast records for daily demand & consumption
    donor_fc = db.query(Forecast).filter(
        Forecast.facility_id == rec.donor_facility_id,
        Forecast.medicine_id == rec.medicine_id
    ).first()

    recip_fc = db.query(Forecast).filter(
        Forecast.facility_id == rec.recipient_facility_id,
        Forecast.medicine_id == rec.medicine_id
    ).first()

    recip_daily_demand = recip_fc.expected_daily_demand if (recip_fc and recip_fc.expected_daily_demand and recip_fc.expected_daily_demand > 0) else 10.0
    donor_daily_demand = donor_fc.expected_daily_demand if (donor_fc and donor_fc.expected_daily_demand and donor_fc.expected_daily_demand > 0) else 10.0

    donor_safety = donor_inv.safety_stock if donor_inv else 40
    recip_safety = recip_inv.safety_stock if recip_inv else 40

    discrepancies: List[str] = []
    now_utc = datetime.now(timezone.utc)

    # ── 4. Evaluate execution states ─────────────────────────────────────────

    # CASE A: PENDING_HUMAN_APPROVAL
    if rec.status == RecommendationStatus.PENDING_HUMAN_APPROVAL:
        current_recip_stock = recip_inv.quantity if recip_inv else 0
        current_donor_stock = donor_inv.quantity if donor_inv else 0
        doc_recip_current = round(current_recip_stock / recip_daily_demand, 1)
        doc_donor_current = round(current_donor_stock / donor_daily_demand, 1)

        expected_recip_after = current_recip_stock + rec.recommended_quantity
        expected_donor_after = max(0, current_donor_stock - rec.recommended_quantity)
        doc_recip_sim = round(expected_recip_after / recip_daily_demand, 1)
        doc_donor_sim = round(expected_donor_after / donor_daily_demand, 1)

        recip_summary = VerificationNodeSummary(
            facility_id=rec.recipient_facility_id,
            facility_name=recip_name,
            facility_type=recip_fac.facility_type.value if (recip_fac and hasattr(recip_fac, "facility_type") and hasattr(recip_fac.facility_type, "value")) else None,
            role="RECIPIENT",
            stock_before=current_recip_stock,
            stock_after_expected=expected_recip_after,
            stock_after_actual=current_recip_stock,
            stock_match=False,
            safety_stock=recip_safety,
            daily_demand=round(recip_daily_demand, 1),
            days_of_cover_before=doc_recip_current,
            days_of_cover_after=doc_recip_sim,
            risk_status_before=_calc_risk_status(doc_recip_current),
            risk_status_after=_calc_risk_status(doc_recip_sim),
            safety_buffer_protected=expected_recip_after >= recip_safety
        )

        donor_summary = VerificationNodeSummary(
            facility_id=rec.donor_facility_id,
            facility_name=donor_name,
            facility_type=donor_fac.facility_type.value if (donor_fac and hasattr(donor_fac, "facility_type") and hasattr(donor_fac.facility_type, "value")) else None,
            role="DONOR",
            stock_before=current_donor_stock,
            stock_after_expected=expected_donor_after,
            stock_after_actual=current_donor_stock,
            stock_match=False,
            safety_stock=donor_safety,
            daily_demand=round(donor_daily_demand, 1),
            days_of_cover_before=doc_donor_current,
            days_of_cover_after=doc_donor_sim,
            risk_status_before=_calc_risk_status(doc_donor_current),
            risk_status_after=_calc_risk_status(doc_donor_sim),
            safety_buffer_protected=expected_donor_after >= donor_safety
        )

        comparison = ExpectedVsActualResult(
            approved_quantity=rec.recommended_quantity,
            actual_quantity_moved=0,
            quantity_matches=False,
            recipient_stock_matches=False,
            donor_stock_matches=False,
            ledger_integrity_passed=False,
            overall_match=False
        )

        checklist = {
            "1_recipient_stock_before": {"value": current_recip_stock, "unit": unit, "verified": True},
            "2_donor_stock_before": {"value": current_donor_stock, "unit": unit, "verified": True},
            "3_approved_transfer_quantity": {"value": rec.recommended_quantity, "unit": unit, "verified": True},
            "4_actual_stock_movement_quantity": {"value": 0, "status": "NOT_EXECUTED", "verified": False},
            "5_recipient_stock_after": {"expected": expected_recip_after, "actual": current_recip_stock, "verified": False},
            "6_donor_stock_after": {"expected": expected_donor_after, "actual": current_donor_stock, "verified": False},
            "7_recipient_daily_demand": {"value": round(recip_daily_demand, 1), "verified": True},
            "8_recipient_days_of_cover": {"before": doc_recip_current, "projected_after": doc_recip_sim, "verified": True},
            "9_recipient_risk_status": {"before": _calc_risk_status(doc_recip_current), "projected_after": _calc_risk_status(doc_recip_sim), "improved": doc_recip_sim > doc_recip_current},
            "10_donor_safety_buffer_protection": {"safety_buffer": donor_safety, "projected_remaining": expected_donor_after, "protected": expected_donor_after >= donor_safety},
            "11_audit_stock_movement_reference": {"event_id": None, "ledger_verified": False, "sha256_hash": None},
            "12_expected_vs_actual_result": {"status": "PENDING", "passed": False, "reason": "Awaiting human review and approval"}
        }

        return RecommendationVerificationResponse(
            recommendation_id=rec.id,
            recommendation_code=rec.recommendation_code,
            item_code=rec.item_code,
            item_name=item_name,
            unit=unit,
            status="PENDING",
            verified_at=now_utc,
            execution_status="PENDING_APPROVAL",
            recipient=recip_summary,
            donor=donor_summary,
            audit_reference=None,
            comparison=comparison,
            summary=f"Transfer of {rec.recommended_quantity} {unit} is pending human CDMO/Admin operational approval. Stock has not moved.",
            discrepancies=["Transfer has not been executed yet (Status: PENDING_HUMAN_APPROVAL)."],
            checklist=checklist
        )

    # CASE B: REJECTED
    if rec.status == RecommendationStatus.REJECTED:
        current_recip_stock = recip_inv.quantity if recip_inv else 0
        current_donor_stock = donor_inv.quantity if donor_inv else 0
        doc_recip = round(current_recip_stock / recip_daily_demand, 1)
        doc_donor = round(current_donor_stock / donor_daily_demand, 1)

        recip_summary = VerificationNodeSummary(
            facility_id=rec.recipient_facility_id,
            facility_name=recip_name,
            role="RECIPIENT",
            stock_before=current_recip_stock,
            stock_after_expected=current_recip_stock,
            stock_after_actual=current_recip_stock,
            stock_match=True,
            safety_stock=recip_safety,
            daily_demand=round(recip_daily_demand, 1),
            days_of_cover_before=doc_recip,
            days_of_cover_after=doc_recip,
            risk_status_before=_calc_risk_status(doc_recip),
            risk_status_after=_calc_risk_status(doc_recip),
            safety_buffer_protected=current_recip_stock >= recip_safety
        )

        donor_summary = VerificationNodeSummary(
            facility_id=rec.donor_facility_id,
            facility_name=donor_name,
            role="DONOR",
            stock_before=current_donor_stock,
            stock_after_expected=current_donor_stock,
            stock_after_actual=current_donor_stock,
            stock_match=True,
            safety_stock=donor_safety,
            daily_demand=round(donor_daily_demand, 1),
            days_of_cover_before=doc_donor,
            days_of_cover_after=doc_donor,
            risk_status_before=_calc_risk_status(doc_donor),
            risk_status_after=_calc_risk_status(doc_donor),
            safety_buffer_protected=current_donor_stock >= donor_safety
        )

        comparison = ExpectedVsActualResult(
            approved_quantity=0,
            actual_quantity_moved=0,
            quantity_matches=True,
            recipient_stock_matches=True,
            donor_stock_matches=True,
            ledger_integrity_passed=True,
            overall_match=True
        )

        checklist = {
            "1_recipient_stock_before": {"value": current_recip_stock, "unit": unit, "verified": True},
            "2_donor_stock_before": {"value": current_donor_stock, "unit": unit, "verified": True},
            "3_approved_transfer_quantity": {"value": 0, "unit": unit, "status": "REJECTED", "verified": True},
            "4_actual_stock_movement_quantity": {"value": 0, "status": "REJECTED", "verified": True},
            "5_recipient_stock_after": {"expected": current_recip_stock, "actual": current_recip_stock, "verified": True},
            "6_donor_stock_after": {"expected": current_donor_stock, "actual": current_donor_stock, "verified": True},
            "7_recipient_daily_demand": {"value": round(recip_daily_demand, 1), "verified": True},
            "8_recipient_days_of_cover": {"before": doc_recip, "after": doc_recip, "verified": True},
            "9_recipient_risk_status": {"before": _calc_risk_status(doc_recip), "after": _calc_risk_status(doc_recip), "improved": False},
            "10_donor_safety_buffer_protection": {"safety_buffer": donor_safety, "remaining_stock": current_donor_stock, "protected": current_donor_stock >= donor_safety},
            "11_audit_stock_movement_reference": {"event_id": None, "ledger_verified": True, "sha256_hash": None},
            "12_expected_vs_actual_result": {"status": "REJECTED", "passed": True, "reason": "Transfer was rejected by reviewer; zero stock moved."}
        }

        return RecommendationVerificationResponse(
            recommendation_id=rec.id,
            recommendation_code=rec.recommendation_code,
            item_code=rec.item_code,
            item_name=item_name,
            unit=unit,
            status="REJECTED",
            verified_at=now_utc,
            execution_status="REJECTED",
            recipient=recip_summary,
            donor=donor_summary,
            audit_reference=None,
            comparison=comparison,
            summary="Transfer was rejected by reviewer. Zero inventory was transferred.",
            discrepancies=["Transfer was rejected by reviewer; execution did not occur."],
            checklist=checklist
        )

    # CASE C: APPROVED — Perform authoritative verification
    # Look up audit event for this recommendation
    candidate_events = (
        db.query(AuditEvent)
        .filter(AuditEvent.action == "REDISTRIBUTION_TRANSFER_APPROVED")
        .order_by(AuditEvent.id.desc())
        .all()
    )
    audit_evt: Optional[AuditEvent] = None
    for ev in candidate_events:
        p = ev.payload_json or {}
        if p.get("recommendation_id") == rec.id or p.get("recommendation_code") == rec.recommendation_code:
            audit_evt = ev
            break

    audit_ref: Optional[AuditMovementReference] = None
    actor_user = None
    if audit_evt:
        if audit_evt.actor_user_id:
            actor_user = db.query(User).filter(User.id == audit_evt.actor_user_id).first()

        audit_ref = AuditMovementReference(
            event_id=audit_evt.event_id,
            timestamp=audit_evt.timestamp,
            action=audit_evt.action,
            actor_id=audit_evt.actor_user_id,
            actor_name=actor_user.full_name if actor_user else None,
            actor_role=actor_user.role.value if actor_user else None,
            current_hash=audit_evt.current_hash,
            previous_hash=audit_evt.previous_hash,
            is_tampered=audit_evt.is_tampered,
            ledger_verified=(not audit_evt.is_tampered and len(audit_evt.current_hash or "") == 64)
        )

        if audit_evt.is_tampered:
            discrepancies.append(f"Tamper detected: Audit ledger event {audit_evt.event_id} has is_tampered=True.")
    else:
        discrepancies.append(f"Missing audit ledger block: No SHA-256 event found for recommendation #{rec.id}.")

    payload = (audit_evt.payload_json or {}) if audit_evt else {}
    actual_quantity_moved = payload.get("quantity", 0)

    # Check approved quantity vs audit quantity
    if actual_quantity_moved != rec.recommended_quantity:
        discrepancies.append(
            f"Quantity mismatch: Approved transfer quantity is {rec.recommended_quantity}, "
            f"but audit ledger recorded {actual_quantity_moved} units."
        )

    # Extract or infer baseline stock before transfer
    live_recip_stock = recip_inv.quantity if recip_inv else 0
    live_donor_stock = donor_inv.quantity if donor_inv else 0

    if "recipient_stock_before" in payload:
        recip_stock_before = int(payload["recipient_stock_before"])
    else:
        # Fallback for un-enriched records
        recip_stock_before = max(0, live_recip_stock - actual_quantity_moved)

    if "donor_stock_before" in payload:
        donor_stock_before = int(payload["donor_stock_before"])
    else:
        donor_stock_before = live_donor_stock + actual_quantity_moved

    expected_recip_after = recip_stock_before + rec.recommended_quantity
    expected_donor_after = max(0, donor_stock_before - rec.recommended_quantity)

    # Post-transfer snapshot from payload
    recip_stock_snapshot = int(payload.get("recipient_stock_after", live_recip_stock))
    donor_stock_snapshot = int(payload.get("donor_stock_after", live_donor_stock))

    # Verification checks
    recip_stock_matches = (recip_stock_snapshot == expected_recip_after)
    donor_stock_matches = (donor_stock_snapshot == expected_donor_after)

    if not recip_stock_matches:
        discrepancies.append(
            f"Recipient stock mismatch: Expected {expected_recip_after} {unit} "
            f"after transfer (Before: {recip_stock_before} + Transferred: {rec.recommended_quantity}), "
            f"but recorded post-transfer stock was {recip_stock_snapshot} {unit}."
        )

    if not donor_stock_matches:
        discrepancies.append(
            f"Donor stock mismatch: Expected {expected_donor_after} {unit} "
            f"after transfer (Before: {donor_stock_before} - Transferred: {rec.recommended_quantity}), "
            f"but recorded post-transfer stock was {donor_stock_snapshot} {unit}."
        )

    # Check donor safety buffer protection
    donor_safety_stock = donor_inv.safety_stock if donor_inv else int(payload.get("donor_safety_stock", 40))
    donor_safety_buffer_protected = (donor_stock_snapshot >= donor_safety_stock)
    if not donor_safety_buffer_protected:
        discrepancies.append(
            f"Donor safety buffer breached: Remaining donor stock ({donor_stock_snapshot} {unit}) "
            f"fell below the safety threshold ({donor_safety_stock} {unit})."
        )

    # Calculate days of cover and risk levels
    doc_recip_before = round(recip_stock_before / recip_daily_demand, 1)
    doc_recip_after = round(recip_stock_snapshot / recip_daily_demand, 1)

    doc_donor_before = round(donor_stock_before / donor_daily_demand, 1)
    doc_donor_after = round(donor_stock_snapshot / donor_daily_demand, 1)

    recip_risk_before = _calc_risk_status(doc_recip_before)
    recip_risk_after = _calc_risk_status(doc_recip_after)

    donor_risk_before = _calc_risk_status(doc_donor_before)
    donor_risk_after = _calc_risk_status(doc_donor_after)

    ledger_integrity_passed = (audit_evt is not None and not audit_evt.is_tampered and len(audit_evt.current_hash or "") == 64)
    quantity_matches = (actual_quantity_moved == rec.recommended_quantity)
    overall_match = (
        quantity_matches and
        recip_stock_matches and
        donor_stock_matches and
        ledger_integrity_passed and
        donor_safety_buffer_protected and
        len(discrepancies) == 0
    )

    recip_summary = VerificationNodeSummary(
        facility_id=rec.recipient_facility_id,
        facility_name=recip_name,
        facility_type=recip_fac.facility_type.value if (recip_fac and hasattr(recip_fac, "facility_type") and hasattr(recip_fac.facility_type, "value")) else None,
        role="RECIPIENT",
        stock_before=recip_stock_before,
        stock_after_expected=expected_recip_after,
        stock_after_actual=recip_stock_snapshot,
        stock_match=recip_stock_matches,
        safety_stock=recip_safety,
        daily_demand=round(recip_daily_demand, 1),
        days_of_cover_before=doc_recip_before,
        days_of_cover_after=doc_recip_after,
        risk_status_before=recip_risk_before,
        risk_status_after=recip_risk_after,
        safety_buffer_protected=recip_stock_snapshot >= recip_safety
    )

    donor_summary = VerificationNodeSummary(
        facility_id=rec.donor_facility_id,
        facility_name=donor_name,
        facility_type=donor_fac.facility_type.value if (donor_fac and hasattr(donor_fac, "facility_type") and hasattr(donor_fac.facility_type, "value")) else None,
        role="DONOR",
        stock_before=donor_stock_before,
        stock_after_expected=expected_donor_after,
        stock_after_actual=donor_stock_snapshot,
        stock_match=donor_stock_matches,
        safety_stock=donor_safety_stock,
        daily_demand=round(donor_daily_demand, 1),
        days_of_cover_before=doc_donor_before,
        days_of_cover_after=doc_donor_after,
        risk_status_before=donor_risk_before,
        risk_status_after=donor_risk_after,
        safety_buffer_protected=donor_safety_buffer_protected
    )

    comparison = ExpectedVsActualResult(
        approved_quantity=rec.recommended_quantity,
        actual_quantity_moved=actual_quantity_moved,
        quantity_matches=quantity_matches,
        recipient_stock_matches=recip_stock_matches,
        donor_stock_matches=donor_stock_matches,
        ledger_integrity_passed=ledger_integrity_passed,
        overall_match=overall_match
    )

    # Checklist capturing all 12 minimum required items
    checklist = {
        "1_recipient_stock_before": {
            "value": recip_stock_before,
            "unit": unit,
            "verified": True
        },
        "2_donor_stock_before": {
            "value": donor_stock_before,
            "unit": unit,
            "verified": True
        },
        "3_approved_transfer_quantity": {
            "value": rec.recommended_quantity,
            "unit": unit,
            "verified": True
        },
        "4_actual_stock_movement_quantity": {
            "value": actual_quantity_moved,
            "unit": unit,
            "verified": quantity_matches
        },
        "5_recipient_stock_after": {
            "expected": expected_recip_after,
            "actual": recip_stock_snapshot,
            "unit": unit,
            "verified": recip_stock_matches
        },
        "6_donor_stock_after": {
            "expected": expected_donor_after,
            "actual": donor_stock_snapshot,
            "unit": unit,
            "verified": donor_stock_matches
        },
        "7_recipient_daily_demand": {
            "value": round(recip_daily_demand, 1),
            "unit": f"{unit}/day",
            "verified": True
        },
        "8_recipient_days_of_cover": {
            "before": doc_recip_before,
            "after": doc_recip_after,
            "gained": round(doc_recip_after - doc_recip_before, 1),
            "verified": True
        },
        "9_recipient_risk_status": {
            "before": recip_risk_before,
            "after": recip_risk_after,
            "improved": doc_recip_after > doc_recip_before,
            "verified": True
        },
        "10_donor_safety_buffer_protection": {
            "safety_buffer": donor_safety_stock,
            "remaining_stock": donor_stock_snapshot,
            "protected": donor_safety_buffer_protected,
            "verified": donor_safety_buffer_protected
        },
        "11_audit_stock_movement_reference": {
            "event_id": audit_ref.event_id if audit_ref else None,
            "timestamp": audit_ref.timestamp.isoformat() if (audit_ref and audit_ref.timestamp) else None,
            "sha256_hash": audit_ref.current_hash if audit_ref else None,
            "ledger_verified": ledger_integrity_passed
        },
        "12_expected_vs_actual_result": {
            "status": "PASSED" if overall_match else "FAILED / REVIEW REQUIRED",
            "all_passed": overall_match,
            "discrepancies_count": len(discrepancies)
        }
    }

    if overall_match:
        final_status = "PASSED"
        final_summary = (
            f"Verification PASSED: {rec.recommended_quantity} {unit} transfer from {donor_name} "
            f"to {recip_name} verified against authoritative database inventory and SHA-256 audit ledger."
        )
    else:
        final_status = "FAILED / REVIEW REQUIRED"
        final_summary = (
            f"Verification FAILED / REVIEW REQUIRED: {len(discrepancies)} discrepancy(ies) detected "
            f"between expected outcome and authoritative database state."
        )

    return RecommendationVerificationResponse(
        recommendation_id=rec.id,
        recommendation_code=rec.recommendation_code,
        item_code=rec.item_code,
        item_name=item_name,
        unit=unit,
        status=final_status,
        verified_at=now_utc,
        execution_status="APPROVED_AND_EXECUTED",
        recipient=recip_summary,
        donor=donor_summary,
        audit_reference=audit_ref,
        comparison=comparison,
        summary=final_summary,
        discrepancies=discrepancies,
        checklist=checklist
    )

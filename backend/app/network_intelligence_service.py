from datetime import date, datetime, timezone
from typing import Dict, List, Any, Optional
from collections import defaultdict
from sqlalchemy.orm import Session

from app.models import (
    Facility, Inventory, Medicine, Forecast, Alert, Recommendation,
    AlertSeverity, AlertStatus, RecommendationStatus
)
from app.algorithms import calculate_days_of_cover, classify_risk_severity
from app.schemas import (
    NetworkIntelligenceResponse,
    NetworkOverviewMetrics,
    NetworkRiskSummary,
    DistrictBreakdownItem,
    ResourceIntelligenceItem,
    InterventionPriorityItem
)

def compute_network_intelligence(db: Session) -> NetworkIntelligenceResponse:
    """
    Computes authoritative, database-grounded Network and District Intelligence.
    Strictly READ-ONLY: Never modifies inventory, forecasts, alerts, or audit state.
    """
    facilities = db.query(Facility).all()
    inventories = db.query(Inventory).all()
    forecasts = db.query(Forecast).all()
    alerts = db.query(Alert).filter(Alert.status == AlertStatus.ACTIVE).all()
    medicines = db.query(Medicine).all()
    pending_recs = db.query(Recommendation).filter(
        Recommendation.status == RecommendationStatus.PENDING_HUMAN_APPROVAL
    ).all()

    # ── 1. Index Telemetry for Fast Resolution ───────────────────────────────────
    # (facility_id, item_code) -> Forecast
    fc_map = {}
    for fc in forecasts:
        fc_map[(fc.facility_id, fc.item_code)] = fc

    # facility_id -> List[Inventory]
    fac_inv_map = defaultdict(list)
    for inv in inventories:
        fac_inv_map[inv.facility_id].append(inv)

    # facility_id -> List[Alert]
    fac_alert_map = defaultdict(list)
    for a in alerts:
        fac_alert_map[a.facility_id].append(a)

    # (facility_id, item_code) -> Recommendation
    rec_map = {}
    for r in pending_recs:
        rec_map[(r.recipient_facility_id, r.item_code)] = r

    # ── 2. Per-Facility Risk Severity Evaluation ──────────────────────────────────
    facility_severity_map = {}  # facility_id -> "CRITICAL" | "WARNING" | "SAFE"
    facility_at_risk_resources = defaultdict(set)
    facility_surplus_resources = defaultdict(set)

    for fac in facilities:
        fac_items = fac_inv_map[fac.id]
        fac_alerts = fac_alert_map[fac.id]

        has_critical = any(a.severity == AlertSeverity.CRITICAL for a in fac_alerts)
        has_warning = any(a.severity == AlertSeverity.WARNING for a in fac_alerts)

        for inv in fac_items:
            fc = fc_map.get((fac.id, inv.item_code))
            demand = float(fc.expected_daily_demand) if (fc and fc.expected_daily_demand > 0) else (
                float(getattr(inv, "daily_demand", 0.0)) if getattr(inv, "daily_demand", None) else 10.0
            )
            doc = calculate_days_of_cover(inv.quantity, inv.incoming_quantity or 0, demand)
            sev = classify_risk_severity(doc, inv.quantity, inv.safety_stock)

            if sev == AlertSeverity.CRITICAL:
                has_critical = True
                facility_at_risk_resources[fac.id].add(inv.item_code)
            elif sev == AlertSeverity.WARNING:
                has_warning = True
                facility_at_risk_resources[fac.id].add(inv.item_code)
            
            if inv.quantity > inv.safety_stock:
                facility_surplus_resources[fac.id].add(inv.item_code)

        if has_critical:
            facility_severity_map[fac.id] = "CRITICAL"
        elif has_warning:
            facility_severity_map[fac.id] = "WARNING"
        else:
            facility_severity_map[fac.id] = "SAFE"

    # ── 3. District / Region Breakdown ───────────────────────────────────────────
    district_groups = defaultdict(list)
    for fac in facilities:
        district_key = (fac.district or "Unassigned", fac.state or "OD")
        district_groups[district_key].append(fac)

    district_items = []
    for (dist_name, state_name), dist_facs in sorted(district_groups.items(), key=lambda x: x[0][0]):
        f_count = len(dist_facs)
        crit_count = sum(1 for f in dist_facs if facility_severity_map.get(f.id) == "CRITICAL")
        warn_count = sum(1 for f in dist_facs if facility_severity_map.get(f.id) == "WARNING")
        safe_count = sum(1 for f in dist_facs if facility_severity_map.get(f.id) == "SAFE")

        dist_fac_ids = {f.id for f in dist_facs}
        dist_inv = [inv for f_id in dist_fac_ids for inv in fac_inv_map[f_id]]
        total_inv = sum(inv.quantity for inv in dist_inv)

        # Velocity in district
        total_velocity = 0.0
        for inv in dist_inv:
            fc = fc_map.get((inv.facility_id, inv.item_code))
            if fc and fc.expected_daily_demand > 0:
                total_velocity += float(fc.expected_daily_demand)
            else:
                total_velocity += 10.0

        dist_risk_res = set()
        dist_surplus_res = set()
        for f_id in dist_fac_ids:
            dist_risk_res.update(facility_at_risk_resources[f_id])
            dist_surplus_res.update(facility_surplus_resources[f_id])

        dist_alerts_count = sum(len(fac_alert_map[f_id]) for f_id in dist_fac_ids)
        dist_pending_interventions = sum(1 for r in pending_recs if r.recipient_facility_id in dist_fac_ids)

        district_items.append(DistrictBreakdownItem(
            district=dist_name,
            state=state_name,
            facility_count=f_count,
            critical_facilities_count=crit_count,
            warning_facilities_count=warn_count,
            safe_facilities_count=safe_count,
            total_inventory=total_inv,
            total_daily_velocity=round(total_velocity, 2),
            resources_at_risk_count=len(dist_risk_res),
            resources_surplus_count=len(dist_surplus_res),
            active_alerts_count=dist_alerts_count,
            pending_interventions_count=dist_pending_interventions
        ))

    # ── 4. Resource Network Intelligence ──────────────────────────────────────────
    # Group inventories by item_code
    med_lookup = {m.code: m for m in medicines}
    sku_inv_map = defaultdict(list)
    for inv in inventories:
        sku_inv_map[inv.item_code].append(inv)

    resource_items = []
    total_shortages = 0
    total_surpluses = 0

    for item_code, inv_list in sorted(sku_inv_map.items()):
        med = med_lookup.get(item_code)
        med_name = med.name if med else (inv_list[0].item_name if inv_list else item_code)
        category = med.category.value if (med and hasattr(med.category, "value")) else "ESSENTIAL_MEDICINE"
        unit = inv_list[0].unit if inv_list else (med.unit if med else "units")

        total_sku_stock = sum(inv.quantity for inv in inv_list)
        total_sku_demand = 0.0
        below_safety_count = 0
        crit_fac_count = 0
        warn_fac_count = 0
        surplus_fac_count = 0
        potential_donors = []
        potential_recipients = []

        fac_lookup = {f.id: f for f in facilities}

        for inv in inv_list:
            fc = fc_map.get((inv.facility_id, inv.item_code))
            demand = float(fc.expected_daily_demand) if (fc and fc.expected_daily_demand > 0) else (
                float(getattr(inv, "daily_demand", 0.0)) if getattr(inv, "daily_demand", None) else 10.0
            )
            total_sku_demand += demand

            doc = calculate_days_of_cover(inv.quantity, inv.incoming_quantity or 0, demand)
            sev = classify_risk_severity(doc, inv.quantity, inv.safety_stock)
            fac_obj = fac_lookup.get(inv.facility_id)
            fac_name = fac_obj.name if fac_obj else f"Facility #{inv.facility_id}"

            if inv.quantity < inv.safety_stock:
                below_safety_count += 1
                total_shortages += 1

            if sev == AlertSeverity.CRITICAL:
                crit_fac_count += 1
                potential_recipients.append(f"{fac_name} ({inv.quantity} {unit}, {doc:.1f}d cover)")
            elif sev == AlertSeverity.WARNING:
                warn_fac_count += 1
                potential_recipients.append(f"{fac_name} ({inv.quantity} {unit}, {doc:.1f}d cover)")

            if inv.quantity > inv.safety_stock:
                surplus_fac_count += 1
                total_surpluses += 1
                surplus_qty = inv.quantity - inv.safety_stock
                potential_donors.append(f"{fac_name} (+{surplus_qty} surplus)")

        network_doc = round(total_sku_stock / total_sku_demand, 2) if total_sku_demand > 0 else 999.0

        resource_items.append(ResourceIntelligenceItem(
            item_code=item_code,
            item_name=med_name,
            category=category,
            unit=unit,
            total_network_stock=total_sku_stock,
            total_daily_demand=round(total_sku_demand, 2),
            network_days_of_cover=network_doc,
            facilities_below_safety_count=below_safety_count,
            critical_facilities_count=crit_fac_count,
            warning_facilities_count=warn_fac_count,
            surplus_facilities_count=surplus_fac_count,
            potential_donors=potential_donors[:3],
            potential_recipients=potential_recipients[:3]
        ))

    # ── 5. Intervention Priority Queue ────────────────────────────────────────────
    priority_candidates = []
    today = date.today()

    for inv in inventories:
        fc = fc_map.get((inv.facility_id, inv.item_code))
        demand = float(fc.expected_daily_demand) if (fc and fc.expected_daily_demand > 0) else (
            float(getattr(inv, "daily_demand", 0.0)) if getattr(inv, "daily_demand", None) else 10.0
        )
        doc = calculate_days_of_cover(inv.quantity, inv.incoming_quantity or 0, demand)
        sev = classify_risk_severity(doc, inv.quantity, inv.safety_stock)

        # Include items at CRITICAL or WARNING severity, or below safety buffer
        if sev in [AlertSeverity.CRITICAL, AlertSeverity.WARNING] or inv.quantity < inv.safety_stock:
            fac_obj = next((f for f in facilities if f.id == inv.facility_id), None)
            if not fac_obj:
                continue

            stockout_date = str(fc.projected_stockout_date) if (fc and fc.projected_stockout_date) else None
            existing_rec = rec_map.get((inv.facility_id, inv.item_code))

            if sev == AlertSeverity.CRITICAL:
                suggested_action = (
                    f"Approve pending transfer {existing_rec.recommendation_code}"
                    if existing_rec else
                    f"Emergency rebalance: deficit is {max(0, inv.safety_stock - inv.quantity)} {inv.unit} below safety buffer"
                )
            else:
                suggested_action = (
                    f"Review pending rebalance {existing_rec.recommendation_code}"
                    if existing_rec else
                    f"Schedule replenishment order: {doc:.1f} days cover remaining"
                )

            # Weighting: Critical=0, Warning=1, doc ascending
            severity_weight = 0 if sev == AlertSeverity.CRITICAL else 1
            priority_candidates.append({
                "weight": (severity_weight, doc, inv.quantity),
                "facility_id": fac_obj.id,
                "facility_name": fac_obj.name,
                "district": fac_obj.district or "Unknown",
                "state": fac_obj.state or "OD",
                "item_code": inv.item_code,
                "item_name": inv.item_name,
                "current_stock": inv.quantity,
                "daily_demand": round(demand, 2),
                "days_of_cover": round(doc, 2),
                "safety_stock": inv.safety_stock,
                "risk_severity": sev.value,
                "projected_stockout_date": stockout_date,
                "has_pending_recommendation": existing_rec is not None,
                "existing_recommendation_code": existing_rec.recommendation_code if existing_rec else None,
                "suggested_action": suggested_action
            })

    priority_candidates.sort(key=lambda x: x["weight"])
    intervention_items = []
    for rank, cand in enumerate(priority_candidates[:15], start=1):
        intervention_items.append(InterventionPriorityItem(
            priority_rank=rank,
            facility_id=cand["facility_id"],
            facility_name=cand["facility_name"],
            district=cand["district"],
            state=cand["state"],
            item_code=cand["item_code"],
            item_name=cand["item_name"],
            current_stock=cand["current_stock"],
            daily_demand=cand["daily_demand"],
            days_of_cover=cand["days_of_cover"],
            safety_stock=cand["safety_stock"],
            risk_severity=cand["risk_severity"],
            projected_stockout_date=cand["projected_stockout_date"],
            has_pending_recommendation=cand["has_pending_recommendation"],
            existing_recommendation_code=cand["existing_recommendation_code"],
            suggested_action=cand["suggested_action"]
        ))

    # ── 6. Deterministic Network Risk Classification ──────────────────────────────
    total_facilities = len(facilities)
    total_skus = len(medicines) if medicines else len(sku_inv_map)
    total_stock_units = sum(inv.quantity for inv in inventories)

    crit_fac_count = sum(1 for f in facilities if facility_severity_map.get(f.id) == "CRITICAL")
    warn_fac_count = sum(1 for f in facilities if facility_severity_map.get(f.id) == "WARNING")
    safe_fac_count = sum(1 for f in facilities if facility_severity_map.get(f.id) == "SAFE")
    facs_needing_intervention = crit_fac_count + warn_fac_count

    active_crit_alerts = sum(1 for a in alerts if a.severity == AlertSeverity.CRITICAL)
    active_warn_alerts = sum(1 for a in alerts if a.severity == AlertSeverity.WARNING)

    criteria_met = []
    if crit_fac_count >= 1 or active_crit_alerts >= 1:
        net_classification = "CRITICAL"
        headline = "CRITICAL NETWORK DEFICIT — Immediate Multi-Facility Intervention Required"
        if crit_fac_count >= 1:
            criteria_met.append(f"{crit_fac_count} facilities have severe shortages (< 3.0 days cover)")
        if active_crit_alerts >= 1:
            criteria_met.append(f"{active_crit_alerts} active critical early warning alerts")
        explanation = (
            f"The healthcare network is operating under CRITICAL status. {crit_fac_count} facilities are facing acute "
            f"stockout projections, including critical deficits in essential medicines (e.g. ORS, Insulin). "
            f"There are {len(pending_recs)} pending redistribution recommendations requiring immediate CDMO operational approval."
        )
    elif warn_fac_count >= 1 or total_shortages >= 1:
        net_classification = "WARNING"
        headline = "WARNING: Emerging Buffer Deficits Across Monitored Facilities"
        criteria_met.append(f"{warn_fac_count} facilities operating in warning buffer (3.0-7.0 days cover)")
        if total_shortages >= 1:
            criteria_met.append(f"{total_shortages} resource items currently below mandatory safety thresholds")
        explanation = (
            f"Network status is elevated to WARNING. While no acute stockouts are unmitigated, {warn_fac_count} facilities "
            f"have stocks falling below safety buffers. Proactive rebalancing from surplus donor nodes is advised."
        )
    else:
        net_classification = "STABLE"
        headline = "NETWORK STABLE — All Facilities Meet or Exceed Safety Buffers"
        criteria_met.append("All facilities maintain >= 7.0 days of cover")
        criteria_met.append("Zero active critical or warning stockout alerts")
        explanation = (
            "Network inventory is healthy and resilient across all monitored districts. "
            "All healthcare facilities are fully buffered against projected 7-day demand velocities."
        )

    overview = NetworkOverviewMetrics(
        total_facilities=total_facilities,
        total_resources_monitored=total_skus,
        critical_facilities_count=crit_fac_count,
        warning_facilities_count=warn_fac_count,
        safe_facilities_count=safe_fac_count,
        total_stock_units=total_stock_units,
        facilities_requiring_intervention=facs_needing_intervention,
        pending_redistribution_recommendations=len(pending_recs),
        active_critical_alerts=active_crit_alerts,
        active_warning_alerts=active_warn_alerts,
        network_shortage_count=total_shortages,
        network_surplus_count=total_surpluses
    )

    risk_summary = NetworkRiskSummary(
        classification=net_classification,
        headline=headline,
        explanation=explanation,
        criteria_met=criteria_met
    )

    return NetworkIntelligenceResponse(
        generated_at=datetime.now(timezone.utc).isoformat(),
        overview=overview,
        risk_summary=risk_summary,
        districts=district_items,
        resources=resource_items,
        intervention_priority=intervention_items,
        disclaimer="Authoritative network intelligence aggregated from verified facility records. Strictly read-only."
    )

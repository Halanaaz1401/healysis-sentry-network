from typing import Dict, Any, List
from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.database import get_db
from app.models import User, Facility, Inventory, Forecast, AuditEvent, Medicine
from app.security import require_cdmo
from app.schemas import NetworkIntelligenceResponse
from app.network_intelligence_service import compute_network_intelligence

router = APIRouter(prefix="/api/v1/network", tags=["Network & District Intelligence"])

@router.get("/intelligence", response_model=NetworkIntelligenceResponse)
def get_network_intelligence_endpoint(
    current_user: User = Depends(require_cdmo),
    db: Session = Depends(get_db)
):
    """
    Feature #11: Returns deterministic, database-grounded District & Network Intelligence.
    Strictly READ-ONLY.
    RBAC: Restricted to CDMO and ADMIN roles. Facility Officers receive HTTP 403 Forbidden.
    """
    return compute_network_intelligence(db)


@router.get("/bigquery-schema")
def get_bigquery_schema_endpoint(
    current_user: User = Depends(require_cdmo)
):
    """
    Returns standard Google Cloud BigQuery TableSchema specifications
    for Healysis healthcare supply-chain analytics tables.
    Allows automated enterprise data pipeline sync to BigQuery datasets.
    """
    schemas = {
        "dataset_id": "healysis_telemetry_analytics",
        "tables": [
            {
                "table_id": "facilities_spatial_telemetry",
                "schema": [
                    {"name": "facility_id", "type": "INTEGER", "mode": "REQUIRED"},
                    {"name": "facility_code", "type": "STRING", "mode": "REQUIRED"},
                    {"name": "name", "type": "STRING", "mode": "REQUIRED"},
                    {"name": "facility_type", "type": "STRING", "mode": "REQUIRED"},
                    {"name": "state", "type": "STRING", "mode": "REQUIRED"},
                    {"name": "district", "type": "STRING", "mode": "REQUIRED"},
                    {"name": "latitude", "type": "FLOAT", "mode": "REQUIRED"},
                    {"name": "longitude", "type": "FLOAT", "mode": "REQUIRED"},
                    {"name": "created_at", "type": "TIMESTAMP", "mode": "REQUIRED"}
                ]
            },
            {
                "table_id": "inventory_burn_rate_snapshots",
                "schema": [
                    {"name": "facility_code", "type": "STRING", "mode": "REQUIRED"},
                    {"name": "facility_name", "type": "STRING", "mode": "REQUIRED"},
                    {"name": "district", "type": "STRING", "mode": "REQUIRED"},
                    {"name": "medicine_code", "type": "STRING", "mode": "REQUIRED"},
                    {"name": "medicine_name", "type": "STRING", "mode": "REQUIRED"},
                    {"name": "quantity", "type": "INTEGER", "mode": "REQUIRED"},
                    {"name": "safety_stock", "type": "INTEGER", "mode": "REQUIRED"},
                    {"name": "daily_demand", "type": "FLOAT", "mode": "NULLABLE"},
                    {"name": "days_of_cover", "type": "FLOAT", "mode": "NULLABLE"},
                    {"name": "risk_severity", "type": "STRING", "mode": "REQUIRED"},
                    {"name": "snapshot_timestamp", "type": "TIMESTAMP", "mode": "REQUIRED"}
                ]
            },
            {
                "table_id": "cryptographic_audit_ledger",
                "schema": [
                    {"name": "event_id", "type": "STRING", "mode": "REQUIRED"},
                    {"name": "timestamp", "type": "TIMESTAMP", "mode": "REQUIRED"},
                    {"name": "actor_user_id", "type": "INTEGER", "mode": "NULLABLE"},
                    {"name": "action", "type": "STRING", "mode": "REQUIRED"},
                    {"name": "facility_id", "type": "INTEGER", "mode": "NULLABLE"},
                    {"name": "previous_hash", "type": "STRING", "mode": "REQUIRED"},
                    {"name": "current_hash", "type": "STRING", "mode": "REQUIRED"},
                    {"name": "is_tampered", "type": "BOOLEAN", "mode": "REQUIRED"}
                ]
            }
        ]
    }
    return schemas


@router.get("/bigquery-export")
def get_bigquery_export_endpoint(
    table: str = Query(default="inventory", description="Table to export: 'inventory', 'facilities', or 'audit'"),
    current_user: User = Depends(require_cdmo),
    db: Session = Depends(get_db)
):
    """
    Exports clean, validated NDJSON-compatible records ready for direct ingestion
    into Google Cloud BigQuery streaming or batch load jobs.
    """
    now_iso = datetime.now(timezone.utc).isoformat()

    if table == "facilities":
        facilities = db.query(Facility).all()
        rows = [
            {
                "facility_id": f.id,
                "facility_code": f.facility_code,
                "name": f.name,
                "facility_type": f.facility_type.value if hasattr(f.facility_type, "value") else str(f.facility_type),
                "state": f.state,
                "district": f.district,
                "latitude": f.latitude,
                "longitude": f.longitude,
                "created_at": f.created_at.isoformat() if hasattr(f, "created_at") and f.created_at else now_iso
            }
            for f in facilities
        ]
        return {"table": "facilities_spatial_telemetry", "count": len(rows), "records": rows}

    elif table == "audit":
        events = db.query(AuditEvent).order_by(AuditEvent.timestamp.desc()).limit(200).all()
        rows = [
            {
                "event_id": e.event_id,
                "timestamp": e.timestamp.isoformat() if e.timestamp else now_iso,
                "actor_user_id": e.actor_user_id,
                "action": e.action,
                "facility_id": e.facility_id,
                "previous_hash": e.previous_hash,
                "current_hash": e.current_hash,
                "is_tampered": e.is_tampered
            }
            for e in events
        ]
        return {"table": "cryptographic_audit_ledger", "count": len(rows), "records": rows}

    else:
        # Default: inventory burn rate snapshots
        inv_items = db.query(Inventory).all()
        rows = []
        for inv in inv_items:
            fac = inv.facility or db.query(Facility).filter(Facility.id == inv.facility_id).first()
            med = inv.medicine or db.query(Medicine).filter(Medicine.id == inv.medicine_id).first()
            fc = db.query(Forecast).filter(
                Forecast.facility_id == inv.facility_id,
                Forecast.item_code == inv.item_code
            ).first()

            demand = fc.expected_daily_demand if fc else 10.0
            doc = fc.days_of_cover if fc else (round(inv.quantity / demand, 1) if demand > 0 else 999.0)
            risk = "CRITICAL" if doc < 3.0 else ("WARNING" if inv.quantity < inv.safety_stock else "SAFE")

            rows.append({
                "facility_code": fac.facility_code if fac else "UNKNOWN",
                "facility_name": fac.name if fac else "Unknown Facility",
                "district": fac.district if fac else "Unknown District",
                "medicine_code": inv.item_code,
                "medicine_name": med.name if med else inv.item_name,
                "quantity": inv.quantity,
                "safety_stock": inv.safety_stock,
                "daily_demand": demand,
                "days_of_cover": doc,
                "risk_severity": risk,
                "snapshot_timestamp": now_iso
            })
        return {"table": "inventory_burn_rate_snapshots", "count": len(rows), "records": rows}


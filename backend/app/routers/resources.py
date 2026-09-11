from datetime import date, timedelta
from typing import List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    Inventory, Forecast, Facility, Medicine, User, UserRole, MedicineCategory
)
from app.schemas import InventoryResponse
from app.security import (
    get_current_user, require_facility_officer, require_cdmo, require_admin,
    verify_facility_access
)

router = APIRouter(prefix="/api/v1", tags=["Medicine Inventory & Resource Management"])

class ResourceCreateRequest(BaseModel):
    facility_id: int = Field(..., description="Target facility ID")
    item_code: str = Field(..., min_length=2, max_length=50, description="SKU Item Code e.g. MED-ORS-SACHET")
    item_name: str = Field(..., min_length=2, max_length=150, description="Resource Name")
    quantity: int = Field(..., ge=0, description="Current Stock Quantity")
    safety_stock: int = Field(..., ge=0, description="Safety Buffer Threshold")
    daily_demand: float = Field(..., gt=0, description="Expected Daily Demand")
    incoming_quantity: int = Field(default=0, ge=0, description="Incoming stock in transit")
    unit: str = Field(default="units", description="Unit of measurement")
    batch: Optional[str] = Field(default="BATCH-2026-N1", description="Batch code")

class CatalogItemResponse(BaseModel):
    id: int
    sku: str
    name: str
    generic_name: Optional[str] = None
    category: str
    unit_of_measure: str
    active: bool = True

from app.algorithms import classify_risk_severity

def _enrich_inventory(inv: Inventory, db: Session) -> InventoryResponse:
    res = InventoryResponse.model_validate(inv)
    if inv.facility:
        res.facility_name = inv.facility.name
        res.district = inv.facility.district
        res.state = inv.facility.state

    forecast = db.query(Forecast).filter(
        Forecast.facility_id == inv.facility_id,
        Forecast.medicine_id == inv.medicine_id
    ).first()

    if forecast:
        res.days_of_cover = forecast.days_of_cover
        res.daily_demand = forecast.expected_daily_demand
        severity = classify_risk_severity(forecast.days_of_cover, inv.quantity, inv.safety_stock)
        res.risk_level = severity.value if hasattr(severity, 'value') else str(severity)
    else:
        res.days_of_cover = 99.0
        res.daily_demand = 10.0
        res.risk_level = "SAFE" if inv.quantity >= inv.safety_stock else "WARNING"

    return res

@router.get("/resources/catalog", response_model=List[CatalogItemResponse])
def get_resource_catalog(
    current_user: User = Depends(require_facility_officer),
    db: Session = Depends(get_db)
):
    """
    Returns list of standard medicine resource catalog SKUs.
    """
    medicines = db.query(Medicine).order_by(Medicine.id.asc()).all()
    catalog = []
    for m in medicines:
        catalog.append(CatalogItemResponse(
            id=m.id,
            sku=m.code,
            name=m.name,
            generic_name=m.name,
            category=m.category.value if hasattr(m.category, 'value') else str(m.category),
            unit_of_measure=m.unit,
            active=True
        ))
    return catalog

@router.get("/resources", response_model=List[InventoryResponse])
@router.get("/resources/", response_model=List[InventoryResponse], include_in_schema=False)
def get_all_resources(
    facility_id: Optional[int] = None,
    current_user: User = Depends(require_facility_officer),
    db: Session = Depends(get_db)
):
    """
    Returns list of inventory resources.
    FACILITY_OFFICER sees only their assigned facility resources.
    CDMO and ADMIN see resources across all facilities.
    """
    query = db.query(Inventory)
    if current_user.role == UserRole.FACILITY_OFFICER:
        if current_user.facility_id is None:
            return []
        query = query.filter(Inventory.facility_id == current_user.facility_id)
    elif facility_id:
        verify_facility_access(facility_id, current_user)
        query = query.filter(Inventory.facility_id == facility_id)

    items = query.order_by(Inventory.id.asc()).all()
    return [_enrich_inventory(inv, db) for inv in items]

@router.get("/resources/{resource_id}", response_model=InventoryResponse)
def get_resource_by_id(
    resource_id: int,
    current_user: User = Depends(require_facility_officer),
    db: Session = Depends(get_db)
):
    """
    Returns single inventory item by ID.
    Enforces facility-scoped authorization for FACILITY_OFFICER.
    """
    item = db.query(Inventory).filter(Inventory.id == resource_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resource with id={resource_id} not found."
        )

    verify_facility_access(item.facility_id, current_user)
    return _enrich_inventory(item, db)

@router.post("/resources", response_model=InventoryResponse, status_code=status.HTTP_201_CREATED)
def create_resource(
    req: ResourceCreateRequest,
    current_user: User = Depends(require_facility_officer),
    db: Session = Depends(get_db)
):
    """
    Adds new resource item to inventory and creates corresponding demand forecast.
    FACILITY_OFFICER can only add resources to their assigned facility.
    Calculates deterministic Days of Cover and risk severity.
    """
    verify_facility_access(req.facility_id, current_user)

    fac = db.query(Facility).filter(Facility.id == req.facility_id).first()
    if not fac:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Facility with id={req.facility_id} does not exist."
        )

    # Ensure Medicine record exists
    med = db.query(Medicine).filter(Medicine.code == req.item_code).first()
    if not med:
        med = Medicine(
            code=req.item_code,
            name=req.item_name,
            category=MedicineCategory.ESSENTIAL_MEDICINE,
            unit=req.unit
        )
        db.add(med)
        db.commit()
        db.refresh(med)

    # Check for existing inventory SKU in facility
    existing_inv = db.query(Inventory).filter(
        Inventory.facility_id == req.facility_id,
        Inventory.item_code == req.item_code
    ).first()

    if existing_inv:
        # Update existing SKU quantity
        existing_inv.quantity = req.quantity
        existing_inv.safety_stock = req.safety_stock
        existing_inv.incoming_quantity = req.incoming_quantity
        existing_inv.unit = req.unit
        inv_item = existing_inv
    else:
        # Create new Inventory record
        inv_item = Inventory(
            facility_id=req.facility_id,
            medicine_id=med.id,
            item_code=req.item_code,
            item_name=req.item_name,
            quantity=req.quantity,
            safety_stock=req.safety_stock,
            incoming_quantity=req.incoming_quantity,
            batch=req.batch or "BATCH-2026-N1",
            expiry=date.today() + timedelta(days=365),
            unit=req.unit
        )
        db.add(inv_item)

    db.commit()
    db.refresh(inv_item)

    # Calculate deterministic Days of Cover and Projected Stockout Date
    doc = round(req.quantity / req.daily_demand, 1) if req.daily_demand > 0 else 99.0
    stockout_days = int(doc) if doc < 365 else 365
    stockout_date = date.today() + timedelta(days=stockout_days)

    # Create or update matching Forecast record
    forecast = db.query(Forecast).filter(
        Forecast.facility_id == req.facility_id,
        Forecast.item_code == req.item_code
    ).first()

    if forecast:
        forecast.expected_daily_demand = req.daily_demand
        forecast.days_of_cover = doc
        forecast.projected_stockout_date = stockout_date
    else:
        forecast = Forecast(
            facility_id=req.facility_id,
            medicine_id=med.id,
            item_code=req.item_code,
            forecast_date=date.today(),
            expected_daily_demand=req.daily_demand,
            days_of_cover=doc,
            projected_stockout_date=stockout_date,
            confidence_score=0.92
        )
        db.add(forecast)

    db.commit()
    return _enrich_inventory(inv_item, db)

class ResourceUpdateRequest(BaseModel):
    quantity: Optional[int] = Field(None, ge=0, description="Updated Stock Quantity")
    safety_stock: Optional[int] = Field(None, ge=0, description="Updated Safety Buffer Threshold")
    daily_demand: Optional[float] = Field(None, gt=0, description="Updated Expected Daily Demand")
    incoming_quantity: Optional[int] = Field(None, ge=0, description="Updated Incoming Stock")

@router.put("/resources/{resource_id}", response_model=InventoryResponse)
def update_resource(
    resource_id: int,
    req: ResourceUpdateRequest,
    current_user: User = Depends(require_facility_officer),
    db: Session = Depends(get_db)
):
    """
    Updates existing resource stock quantity, safety stock, or daily demand.
    Enforces facility-scoped access.
    Recalculates deterministic Days of Cover.
    """
    inv = db.query(Inventory).filter(Inventory.id == resource_id).first()
    if not inv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resource with id={resource_id} not found."
        )

    verify_facility_access(inv.facility_id, current_user)

    if req.quantity is not None:
        inv.quantity = req.quantity
    if req.safety_stock is not None:
        inv.safety_stock = req.safety_stock
    if req.incoming_quantity is not None:
        inv.incoming_quantity = req.incoming_quantity

    db.commit()
    db.refresh(inv)

    # Recalculate forecast Days of Cover if demand or stock changed
    forecast = db.query(Forecast).filter(
        Forecast.facility_id == inv.facility_id,
        Forecast.item_code == inv.item_code
    ).first()

    if forecast:
        demand = req.daily_demand if req.daily_demand is not None else forecast.expected_daily_demand
        doc = round(inv.quantity / demand, 1) if demand > 0 else 99.0
        forecast.expected_daily_demand = demand
        forecast.days_of_cover = doc
        forecast.projected_stockout_date = date.today() + timedelta(days=int(doc)) if doc < 365 else None
        db.commit()

    return _enrich_inventory(inv, db)

@router.delete("/resources/{resource_id}", status_code=status.HTTP_200_OK)
def delete_resource(
    resource_id: int,
    current_user: User = Depends(require_cdmo),
    db: Session = Depends(get_db)
):
    """
    Deletes inventory resource record.
    Requires CDMO or ADMIN role.
    """
    inv = db.query(Inventory).filter(Inventory.id == resource_id).first()
    if not inv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resource with id={resource_id} not found."
        )

    db.delete(inv)
    db.commit()
    return {"status": "DELETED", "message": f"Resource id={resource_id} deleted successfully."}

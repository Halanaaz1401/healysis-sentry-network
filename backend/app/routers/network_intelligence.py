from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
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

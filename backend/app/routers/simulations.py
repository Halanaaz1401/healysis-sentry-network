from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import RedistributionSimulationRequest, RedistributionSimulationResponse
from app.security import require_facility_officer
from app.simulation_service import run_redistribution_simulation

router = APIRouter(prefix="/api/v1", tags=["What-If Operational Simulations"])

@router.post("/simulations/redistribution", response_model=RedistributionSimulationResponse)
def simulate_redistribution(
    req: RedistributionSimulationRequest,
    current_user: User = Depends(require_facility_officer),
    db: Session = Depends(get_db)
):
    """
    Executes a deterministic What-If stock redistribution simulation.
    Strictly read-only: evaluates donor and recipient inventory impact, projected days of cover,
    and safety buffer integrity without mutating any database records or ledger blocks.
    Enforces server-side RBAC and facility scoping.
    """
    return run_redistribution_simulation(req=req, current_user=current_user, db=db)

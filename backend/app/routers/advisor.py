from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, UserRole
from app.schemas import AdvisorChatRequest, AdvisorChatResponse
from app.security import (
    get_current_user, require_facility_officer, verify_facility_access
)
from app.advisor_service import run_grounded_ai_advisor

router = APIRouter(prefix="/api/v1/advisor", tags=["Healysis AI Advisor & Operational Intelligence"])

@router.post("/chat", response_model=AdvisorChatResponse)
def advisor_chat_endpoint(
    request: AdvisorChatRequest,
    current_user: User = Depends(require_facility_officer),
    db: Session = Depends(get_db)
):
    """
    Grounded AI Advisor endpoint.
    Processes natural language operational queries against verified backend tools.
    Enforces server-side RBAC and facility-scoped access control.
    """
    # Enforce facility scope if user is FACILITY_OFFICER
    if current_user.role == UserRole.FACILITY_OFFICER:
        if request.facility_id and request.facility_id != current_user.facility_id:
            verify_facility_access(request.facility_id, current_user)

    response = run_grounded_ai_advisor(request, current_user, db)
    return response

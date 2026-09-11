from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, UserRole, Facility
from app.schemas import UserResponse, UserCreate
from app.security import (
    get_current_user, require_admin, require_cdmo, require_facility_officer,
    verify_facility_access
)

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication & RBAC"])

@router.get("/me", response_model=UserResponse)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """
    Returns authenticated Healysis user profile, server-enforced role, and facility assignment.
    """
    return current_user

@router.get("/admin-only")
def admin_only_endpoint(current_user: User = Depends(require_admin)):
    """
    Protected endpoint accessible only to ADMIN role.
    """
    return {
        "status": "AUTHORIZED",
        "message": f"Welcome Admin {current_user.full_name}",
        "role": current_user.role.value
    }

@router.get("/cdmo-only")
def cdmo_only_endpoint(current_user: User = Depends(require_cdmo)):
    """
    Protected endpoint accessible to CDMO and ADMIN roles.
    """
    return {
        "status": "AUTHORIZED",
        "message": f"Welcome CDMO Director {current_user.full_name}",
        "role": current_user.role.value
    }

@router.get("/facility-scoped/{facility_id}")
def facility_scoped_endpoint(
    facility_id: int,
    current_user: User = Depends(require_facility_officer)
):
    """
    Protected endpoint enforcing facility-scoped access.
    FACILITY_OFFICER can only access their assigned facility_id.
    CDMO and ADMIN can access any facility_id.
    """
    verify_facility_access(facility_id, current_user)
    return {
        "status": "AUTHORIZED",
        "facility_id": facility_id,
        "accessed_by": current_user.full_name,
        "user_role": current_user.role.value
    }

@router.post("/register-user", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(
    user_in: UserCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    ADMIN-only endpoint to register a new user in the Healysis database bound to a Firebase UID.
    """
    existing = db.query(User).filter(
        (User.firebase_uid == user_in.firebase_uid) | (User.email == user_in.email)
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this firebase_uid or email already exists."
        )

    if user_in.facility_id:
        facility = db.query(Facility).filter(Facility.id == user_in.facility_id).first()
        if not facility:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Assigned facility_id={user_in.facility_id} does not exist."
            )

    new_user = User(
        firebase_uid=user_in.firebase_uid,
        email=user_in.email,
        full_name=user_in.full_name,
        role=user_in.role,
        facility_id=user_in.facility_id
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

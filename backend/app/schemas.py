from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, EmailStr, field_validator
from app.models import (
    UserRole, FacilityType, MedicineCategory, ActionType, 
    PersonnelRole, AlertSeverity, AlertType, AlertStatus, 
    UrgencyLevel, RecommendationStatus, RequisitionStatus
)

# ==========================================
# User Schemas
# ==========================================
class UserBase(BaseModel):
    firebase_uid: str = Field(..., min_length=1, max_length=128)
    email: str = Field(..., pattern=r"^[^@]+@[^@]+\.[^@]+$", max_length=255)
    full_name: str = Field(..., min_length=1, max_length=255)
    role: UserRole
    facility_id: Optional[int] = Field(None, ge=1)


class UserCreate(UserBase):
    pass

class UserResponse(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# ==========================================
# Facility Schemas
# ==========================================
class FacilityBase(BaseModel):
    facility_code: str = Field(..., min_length=1, max_length=64)
    name: str = Field(..., min_length=1, max_length=255)
    facility_type: FacilityType
    state: str = Field(..., min_length=2, max_length=64)
    district: str = Field(..., min_length=2, max_length=64)
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)

class FacilityCreate(FacilityBase):
    pass

class FacilityResponse(FacilityBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# ==========================================
# Inventory / Resource Schemas
# ==========================================
class InventoryResponse(BaseModel):
    id: int
    facility_id: int
    medicine_id: int
    item_code: str
    item_name: str
    quantity: int
    safety_stock: int
    batch: Optional[str] = None
    expiry: Optional[date] = None
    incoming_quantity: int = 0
    unit: str = "units"
    created_at: datetime
    updated_at: datetime
    facility_name: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    days_of_cover: Optional[float] = None
    daily_demand: Optional[float] = None
    risk_level: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

# ==========================================
# Forecast Schemas
# ==========================================
class ForecastResponse(BaseModel):
    id: int
    facility_id: int
    medicine_id: int
    item_code: str
    forecast_date: date
    expected_daily_demand: float
    days_of_cover: float
    projected_stockout_date: Optional[date] = None
    confidence_score: float
    calculated_at: datetime
    facility_name: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    item_name: Optional[str] = None
    current_stock: Optional[int] = None
    safety_stock: Optional[int] = None
    incoming_quantity: Optional[int] = None
    risk_level: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

# ==========================================
# Alert Schemas
# ==========================================
class AlertResponse(BaseModel):
    id: int
    alert_code: str
    facility_id: int
    resource_id: str
    severity: AlertSeverity
    alert_type: AlertType
    title: str
    evidence_json: Optional[Dict[str, Any]] = None
    projected_impact_date: Optional[date] = None
    status: AlertStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# ==========================================
# Recommendation Schemas
# ==========================================
class RecommendationResponse(BaseModel):
    id: int
    recommendation_code: str
    donor_facility_id: int
    recipient_facility_id: int
    medicine_id: int
    item_code: str
    recommended_quantity: int
    urgency_level: UrgencyLevel
    haversine_distance_km: float
    expected_days_cover_gained: float
    confidence_score: float
    reason: str
    status: RecommendationStatus
    created_at: datetime
    donor_facility_name: Optional[str] = None
    donor_district: Optional[str] = None
    donor_state: Optional[str] = None
    recipient_facility_name: Optional[str] = None
    recipient_district: Optional[str] = None
    recipient_state: Optional[str] = None
    item_name: Optional[str] = None
    donor_current_stock: Optional[int] = None
    donor_safety_stock: Optional[int] = None
    recipient_current_stock: Optional[int] = None
    recipient_safety_stock: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)

# ==========================================
# Gemini AI Advisor Schemas
# ==========================================
class ChatMessage(BaseModel):
    role: str = Field(..., description="Role: 'user' or 'model'/'assistant'")
    content: str = Field(..., min_length=1, max_length=1000, description="Text content of message")

class AdvisorChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000, description="User query for AI Advisor (Max 1000 chars)")
    facility_id: Optional[int] = Field(None, ge=1, description="Optional target facility ID context")
    history: Optional[List[ChatMessage]] = Field(default=[], description="Optional conversation history")
    conversation_id: Optional[int] = Field(None, ge=1, description="Optional conversation ID to bind message to")

    @field_validator("message")
    def sanitize_message(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("User message cannot be empty or whitespace only.")
        return s

class PendingInventoryUpdate(BaseModel):
    facility_id: int = Field(..., description="Target facility ID")
    facility_name: str = Field(..., description="Target facility name")
    item_code: str = Field(..., description="Medicine SKU code e.g. MED-ORS-SACHET")
    item_name: str = Field(..., description="Medicine display name")
    current_quantity: int = Field(..., description="Current stock in database")
    new_quantity: int = Field(..., ge=0, description="Proposed new stock quantity")
    current_daily_demand: float = Field(..., description="Current expected daily demand")
    new_daily_demand: Optional[float] = Field(None, gt=0, description="Optional updated daily demand")
    unit: str = Field("units", description="Unit of measurement")
    confirmation_token: str = Field(..., description="Cryptographic confirmation token binding the update payload")

class AdvisorChatResponse(BaseModel):
    answer: str = Field(..., description="Grounded AI response explaining backend operational state")
    summary: str = Field(..., description="Executive 1-sentence summary of answer")
    severity: Optional[str] = Field("SAFE", description="Risk severity level ('SAFE', 'WARNING', 'CRITICAL')")
    evidence: List[Dict[str, Any]] = Field(default=[], description="Structured evidence payload from backend tools")
    data_sources: List[str] = Field(default=[], description="Names of verified backend tools consulted")
    recommended_actions: List[str] = Field(default=[], description="Actionable next steps for human decision-maker review")
    limitations: str = Field("This AI Advisor provides decision support only. All redistribution actions require human CDMO/Admin operational approval.", description="System safety notice")
    requires_human_approval: bool = Field(True, description="Strict safety flag indicating human approval is mandatory")
    pending_update: Optional[PendingInventoryUpdate] = Field(None, description="Structured inventory update proposal awaiting human confirmation")
    conversation_id: Optional[int] = Field(None, description="Active conversation ID")

    model_config = ConfigDict(from_attributes=True)

class ConversationCreate(BaseModel):
    title: Optional[str] = Field(None, max_length=255, description="Initial conversation title")

class ConversationSummary(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class MessageSchema(BaseModel):
    id: int
    conversation_id: int
    sender: str
    text: str
    meta_json: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ConversationDetail(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime
    messages: List[MessageSchema]

    model_config = ConfigDict(from_attributes=True)

class InventoryUpdateConfirmationRequest(BaseModel):
    facility_id: int = Field(..., ge=1, description="Target facility ID")
    item_code: str = Field(..., min_length=2, max_length=50, description="Medicine SKU code")
    quantity: int = Field(..., ge=0, description="New stock quantity")
    daily_demand: Optional[float] = Field(None, gt=0, description="Optional new daily demand")
    confirmation_token: str = Field(..., description="Token issued during chat preview")

class InventoryUpdateConfirmationResponse(BaseModel):
    status: str = Field("SUCCESS", description="Operation status")
    message: str = Field(..., description="Grounded confirmation message")
    facility_id: int
    facility_name: str
    item_code: str
    item_name: str
    previous_quantity: int
    new_quantity: int
    daily_demand: float
    days_of_cover: float
    severity: str
    audit_event_id: str

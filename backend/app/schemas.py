from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, EmailStr, field_validator
from app.models import (
    UserRole, FacilityType, MedicineCategory, ActionType, 
    PersonnelRole, AlertSeverity, AlertType, AlertStatus, 
    UrgencyLevel, RecommendationStatus, RequisitionStatus,
    NotificationChannel, NotificationStatus
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
    explanation: Optional[Dict[str, Any]] = None

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
    facility_name: Optional[str] = None
    item_name: Optional[str] = None
    explanation: Optional[Dict[str, Any]] = None
    notification_lifecycle: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)

class AlertActionRequest(BaseModel):
    reason: Optional[str] = Field(None, max_length=500, description="Optional operator reason for action")


class RiskExplanationResponse(BaseModel):
    entity_type: str = "ALERT"
    entity_id: int
    code: str
    facility_id: int
    facility_name: str
    resource_id: str
    resource_name: str
    severity: str
    evidence: Dict[str, Any]
    why: str
    recommended_action: str

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
    donor_surplus: Optional[int] = None
    recipient_current_stock: Optional[int] = None
    recipient_safety_stock: Optional[int] = None
    recipient_days_of_cover: Optional[float] = None
    recipient_daily_demand: Optional[float] = None
    requester_name: Optional[str] = None
    requester_role: Optional[str] = None
    requesting_facility_name: Optional[str] = None
    reviewed_by_name: Optional[str] = None
    reviewed_by_role: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    explanation: Optional[Dict[str, Any]] = None
    verification_status: Optional[str] = None
    verification_summary: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class RecommendationExplanationResponse(BaseModel):
    entity_type: str = "RECOMMENDATION"
    recommendation_id: int
    recommendation_code: str
    resource_id: str
    resource_name: str
    donor_facility_id: int
    donor_facility_name: str
    recipient_facility_id: int
    recipient_facility_name: str
    recommended_quantity: int
    urgency_level: str
    evidence: Dict[str, Any]
    why: str
    recommended_action: str
    provenance: Optional[Dict[str, Any]] = None
    answers: Optional[Dict[str, str]] = None

    model_config = ConfigDict(from_attributes=True)

# ==========================================
# What-If Simulation Schemas
# ==========================================
class RedistributionSimulationRequest(BaseModel):
    donor_facility_id: int = Field(..., description="ID of donor facility providing stock")
    recipient_facility_id: int = Field(..., description="ID of recipient facility receiving stock")
    item_code: Optional[str] = Field(None, description="SKU item code e.g. MED-ORS-SACHET")
    medicine_id: Optional[int] = Field(None, description="Medicine ID (optional if item_code provided)")
    transfer_quantity: int = Field(..., description="Proposed transfer quantity (> 0)")

class SimulationNodeMetrics(BaseModel):
    facility_id: int
    facility_name: str
    district: Optional[str] = None
    state: Optional[str] = None
    current_stock: int
    simulated_stock: int
    daily_demand: float
    current_days_of_cover: float
    simulated_days_of_cover: float
    current_risk_severity: str = "SAFE"
    simulated_risk_severity: str = "SAFE"
    safety_buffer: int
    safety_stock: Optional[int] = None
    projected_7day_demand: float = 0.0
    current_projected_stockout: Optional[str] = None
    simulated_projected_stockout: Optional[str] = None
    before: Optional[Dict[str, Any]] = None
    after: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)

class SimulationDonorNode(SimulationNodeMetrics):
    proposed_transfer_quantity: Optional[int] = None
    surplus_available: int
    buffer_preserved: bool
    days_of_cover_lost: float

class SimulationRecipientNode(SimulationNodeMetrics):
    buffer_achieved: bool
    days_of_cover_gained: float

class SimulationRiskAnalysis(BaseModel):
    recipient_improves: bool
    recipient_remains_below_safety: bool
    donor_falls_below_safety: bool
    donor_becomes_new_risk: bool
    creates_or_worsens_stockout: bool
    is_operationally_safe: bool
    within_donor_surplus: bool

    model_config = ConfigDict(from_attributes=True)

class RedistributionSimulationResponse(BaseModel):
    simulation_id: str
    simulation_only: bool = True
    resource_id: str
    resource_name: str
    unit: str
    transfer_quantity: int
    haversine_distance_km: float
    status: str  # "SAFE" | "CAUTION" | "UNSAFE"
    feasibility_status: str = "FEASIBLE"  # "FEASIBLE" | "INFEASIBLE"
    reason: str
    donor: SimulationDonorNode
    recipient: SimulationRecipientNode
    risk_analysis: SimulationRiskAnalysis
    impact: Optional[Dict[str, Any]] = None
    validation: Optional[Dict[str, Any]] = None
    disclaimer: str = "Simulation only — no inventory has been changed. Operational transfers require explicit human approval by an authorized CDMO or Admin."

    model_config = ConfigDict(from_attributes=True)

# ==========================================
# Before -> After Verification Schemas
# ==========================================
class VerificationNodeSummary(BaseModel):
    facility_id: int
    facility_name: str
    facility_type: Optional[str] = None
    role: str  # "RECIPIENT" or "DONOR"
    stock_before: int
    stock_after_expected: int
    stock_after_actual: int
    stock_match: bool
    safety_stock: int
    daily_demand: float
    days_of_cover_before: float
    days_of_cover_after: float
    risk_status_before: str
    risk_status_after: str
    safety_buffer_protected: bool

    model_config = ConfigDict(from_attributes=True)

class AuditMovementReference(BaseModel):
    event_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    action: Optional[str] = None
    actor_id: Optional[int] = None
    actor_name: Optional[str] = None
    actor_role: Optional[str] = None
    current_hash: Optional[str] = None
    previous_hash: Optional[str] = None
    is_tampered: bool = False
    ledger_verified: bool = False

    model_config = ConfigDict(from_attributes=True)

class ExpectedVsActualResult(BaseModel):
    approved_quantity: int
    actual_quantity_moved: int
    quantity_matches: bool
    recipient_stock_matches: bool
    donor_stock_matches: bool
    ledger_integrity_passed: bool
    overall_match: bool

    model_config = ConfigDict(from_attributes=True)

class RecommendationVerificationResponse(BaseModel):
    recommendation_id: int
    recommendation_code: str
    item_code: str
    item_name: str
    unit: str
    status: str  # "PASSED" | "FAILED / REVIEW REQUIRED" | "PENDING" | "REJECTED"
    verified_at: datetime
    execution_status: str  # "APPROVED_AND_EXECUTED" | "PENDING_APPROVAL" | "REJECTED"
    recipient: VerificationNodeSummary
    donor: VerificationNodeSummary
    audit_reference: Optional[AuditMovementReference] = None
    comparison: ExpectedVsActualResult
    summary: str
    discrepancies: List[str] = Field(default_factory=list)
    checklist: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)

# ==========================================
# Notification & Escalation Schemas
# ==========================================
class NotificationResponse(BaseModel):
    id: int
    notification_code: str
    alert_id: int
    facility_id: int
    facility_name: Optional[str] = None
    resource_id: Optional[str] = None
    item_name: Optional[str] = None
    severity: str
    channel: str
    recipient_role: str
    recipient_user_id: Optional[int] = None
    title: str
    message: str
    status: str
    escalation_level: int
    escalation_reason: Optional[str] = None
    is_escalated: bool
    escalated_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    acknowledged_by_user_id: Optional[int] = None
    acknowledged_by_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    alert_details: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)

class UnreadNotificationsResponse(BaseModel):
    unread_count: int
    escalated_count: int
    notifications: List[NotificationResponse]

class NotificationAcknowledgeRequest(BaseModel):
    reason: Optional[str] = Field(None, max_length=500, description="Optional operator reason for acknowledgment")

class EscalationProcessRequest(BaseModel):
    force_timeout_minutes: Optional[int] = Field(None, ge=0, description="Optional override timeout in minutes for testing or emergency run")

# ==========================================
# Gemini AI Advisor Schemas
# ==========================================
class ChatMessage(BaseModel):
    role: str = Field(..., description="Role: 'user' or 'model'/'assistant'")
    content: str = Field(..., min_length=1, max_length=1000, description="Text content of message")

class AdvisorChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000, description="User query for AI Advisor (Max 1000 chars)")
    language: Optional[str] = Field("en", description="Preferred response language: 'en', 'hi', 'hinglish'")
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

# ==========================================
# Feature #11: Network Intelligence Schemas
# ==========================================

class DistrictBreakdownItem(BaseModel):
    district: str
    state: str
    facility_count: int
    critical_facilities_count: int
    warning_facilities_count: int
    safe_facilities_count: int
    total_inventory: int
    total_daily_velocity: float
    resources_at_risk_count: int
    resources_surplus_count: int
    active_alerts_count: int
    pending_interventions_count: int

    model_config = ConfigDict(from_attributes=True)

class ResourceIntelligenceItem(BaseModel):
    item_code: str
    item_name: str
    category: str
    unit: str
    total_network_stock: int
    total_daily_demand: float
    network_days_of_cover: float
    facilities_below_safety_count: int
    critical_facilities_count: int
    warning_facilities_count: int
    surplus_facilities_count: int
    potential_donors: List[str] = []
    potential_recipients: List[str] = []

    model_config = ConfigDict(from_attributes=True)

class InterventionPriorityItem(BaseModel):
    priority_rank: int
    facility_id: int
    facility_name: str
    district: str
    state: str
    item_code: str
    item_name: str
    current_stock: int
    daily_demand: float
    days_of_cover: float
    safety_stock: int
    risk_severity: str
    projected_stockout_date: Optional[str] = None
    has_pending_recommendation: bool = False
    existing_recommendation_code: Optional[str] = None
    suggested_action: str

    model_config = ConfigDict(from_attributes=True)

class NetworkOverviewMetrics(BaseModel):
    total_facilities: int
    total_resources_monitored: int
    critical_facilities_count: int
    warning_facilities_count: int
    safe_facilities_count: int
    total_stock_units: int
    facilities_requiring_intervention: int
    pending_redistribution_recommendations: int
    active_critical_alerts: int
    active_warning_alerts: int
    network_shortage_count: int
    network_surplus_count: int

    model_config = ConfigDict(from_attributes=True)

class NetworkRiskSummary(BaseModel):
    classification: str  # "CRITICAL" | "WARNING" | "STABLE"
    headline: str
    explanation: str
    criteria_met: List[str] = []

    model_config = ConfigDict(from_attributes=True)

class NetworkIntelligenceResponse(BaseModel):
    generated_at: str
    overview: NetworkOverviewMetrics
    risk_summary: NetworkRiskSummary
    districts: List[DistrictBreakdownItem]
    resources: List[ResourceIntelligenceItem]
    intervention_priority: List[InterventionPriorityItem]
    disclaimer: str = "Authoritative network intelligence aggregated from verified facility records. Strictly read-only."

    model_config = ConfigDict(from_attributes=True)

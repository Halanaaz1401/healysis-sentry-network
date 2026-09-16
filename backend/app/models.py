import enum
from datetime import datetime, date, timezone
from typing import Optional, List
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Date, JSON, Enum, 
    ForeignKey, Index, Text, UniqueConstraint
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.database import Base

def utc_now():
    return datetime.now(timezone.utc)


# ==========================================
# Enums
# ==========================================
class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    CDMO = "CDMO"
    FACILITY_OFFICER = "FACILITY_OFFICER"

class FacilityType(str, enum.Enum):
    PHC = "PHC"
    UPHC = "UPHC"
    CHC = "CHC"
    DISTRICT_HOSPITAL = "DISTRICT_HOSPITAL"

class MedicineCategory(str, enum.Enum):
    ESSENTIAL_MEDICINE = "ESSENTIAL_MEDICINE"
    VACCINE = "VACCINE"
    MEDICAL_SUPPLY = "MEDICAL_SUPPLY"

class ActionType(str, enum.Enum):
    DISPENSE = "DISPENSE"
    RECEIVE = "RECEIVE"
    SPOILAGE = "SPOILAGE"

class PersonnelRole(str, enum.Enum):
    DOCTOR = "DOCTOR"
    NURSE = "NURSE"
    PHARMACIST = "PHARMACIST"
    ASHA = "ASHA"

class AlertSeverity(str, enum.Enum):
    LOW = "LOW"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"

class AlertType(str, enum.Enum):
    STOCKOUT_PROJECTED = "STOCKOUT_PROJECTED"
    GHOST_DRAWDOWN = "GHOST_DRAWDOWN"
    SPOILAGE_SPIKE = "SPOILAGE_SPIKE"
    BED_PRESSURE = "BED_PRESSURE"
    STAFFING_DEFICIT = "STAFFING_DEFICIT"

class AlertStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"

class UrgencyLevel(str, enum.Enum):
    ROUTINE = "ROUTINE"
    URGENT = "URGENT"
    CRITICAL = "CRITICAL"

class RecommendationStatus(str, enum.Enum):
    PENDING_HUMAN_APPROVAL = "PENDING_HUMAN_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    DISPATCHED = "DISPATCHED"

class RequisitionStatus(str, enum.Enum):
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED_AND_DISPATCHED = "APPROVED_AND_DISPATCHED"
    REJECTED = "REJECTED"

class EventType(str, enum.Enum):
    TRANSACTION = "TRANSACTION"
    RULE_ALERT = "RULE_ALERT"
    REQUISITION = "REQUISITION"
    SYSTEM = "SYSTEM"

# ==========================================
# Domain Models
# ==========================================

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    firebase_uid = Column(String(128), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.FACILITY_OFFICER)
    facility_id = Column(Integer, ForeignKey("facilities.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    facility = relationship("Facility", back_populates="staff_members")
    audit_events = relationship("AuditEvent", back_populates="actor")
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")


class Facility(Base):
    """
    Domain Relationship: State -> District -> Facility
    """
    __tablename__ = "facilities"

    id = Column(Integer, primary_key=True, index=True)
    facility_code = Column(String(64), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    facility_type = Column(Enum(FacilityType), nullable=False)
    state = Column(String(64), index=True, nullable=False)        # State hierarchy (e.g. OD, WB)
    district = Column(String(64), index=True, nullable=False)     # District hierarchy (e.g. Khordha, Puri)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    staff_members = relationship("User", back_populates="facility")
    inventory_items = relationship("Inventory", back_populates="facility", cascade="all, delete-orphan")
    consumption_logs = relationship("ConsumptionLog", back_populates="facility", cascade="all, delete-orphan")
    bed_capacity = relationship("Bed", back_populates="facility", uselist=False, cascade="all, delete-orphan")
    personnel_roster = relationship("Personnel", back_populates="facility", uselist=False, cascade="all, delete-orphan")
    personnel_attendance = relationship("PersonnelAttendance", back_populates="facility", cascade="all, delete-orphan")
    forecasts = relationship("Forecast", back_populates="facility", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="facility", cascade="all, delete-orphan")
    donor_recommendations = relationship("Recommendation", foreign_keys="Recommendation.donor_facility_id", back_populates="donor_facility")
    recipient_recommendations = relationship("Recommendation", foreign_keys="Recommendation.recipient_facility_id", back_populates="recipient_facility")
    source_requisitions = relationship("Requisition", foreign_keys="Requisition.source_facility_id", back_populates="source_facility")
    target_requisitions = relationship("Requisition", foreign_keys="Requisition.target_facility_id", back_populates="target_facility")
    audit_events = relationship("AuditEvent", back_populates="facility")


class Medicine(Base):
    __tablename__ = "medicines"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(64), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    category = Column(Enum(MedicineCategory), nullable=False, default=MedicineCategory.ESSENTIAL_MEDICINE)
    unit = Column(String(32), nullable=False, default="units")
    created_at = Column(DateTime, default=utc_now, nullable=False)

    inventory_entries = relationship("Inventory", back_populates="medicine")
    consumption_entries = relationship("ConsumptionLog", back_populates="medicine")
    forecast_entries = relationship("Forecast", back_populates="medicine")


class Inventory(Base):
    """
    Facility -> Inventory Relationship
    """
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, index=True)
    facility_id = Column(Integer, ForeignKey("facilities.id", ondelete="CASCADE"), nullable=False, index=True)
    medicine_id = Column(Integer, ForeignKey("medicines.id", ondelete="RESTRICT"), nullable=False, index=True)
    item_code = Column(String(64), index=True, nullable=False)
    item_name = Column(String(255), nullable=False)
    quantity = Column(Integer, nullable=False, default=0)
    safety_stock = Column(Integer, nullable=False, default=30)
    batch = Column(String(64), nullable=True)
    expiry = Column(Date, nullable=True)
    incoming_quantity = Column(Integer, nullable=False, default=0)
    unit = Column(String(32), nullable=False, default="units")
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    facility = relationship("Facility", back_populates="inventory_items")
    medicine = relationship("Medicine", back_populates="inventory_entries")

    __table_args__ = (
        UniqueConstraint("facility_id", "medicine_id", "batch", name="uix_facility_medicine_batch"),
    )


class ConsumptionLog(Base):
    """
    Facility -> Consumption Relationship (Historical Daily Usage)
    """
    __tablename__ = "consumption_logs"

    id = Column(Integer, primary_key=True, index=True)
    facility_id = Column(Integer, ForeignKey("facilities.id", ondelete="CASCADE"), nullable=False, index=True)
    medicine_id = Column(Integer, ForeignKey("medicines.id", ondelete="RESTRICT"), nullable=False, index=True)
    item_code = Column(String(64), index=True, nullable=False)
    date = Column(Date, index=True, nullable=False)
    quantity_dispensed = Column(Integer, nullable=False, default=0)
    patient_footfall = Column(Integer, nullable=False, default=0)
    encounter_token = Column(String(64), index=True, nullable=True)
    action_type = Column(Enum(ActionType), nullable=False, default=ActionType.DISPENSE)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    facility = relationship("Facility", back_populates="consumption_logs")
    medicine = relationship("Medicine", back_populates="consumption_entries")


class Bed(Base):
    """
    Facility -> Beds Relationship (Wards & Capacity)
    """
    __tablename__ = "beds"

    id = Column(Integer, primary_key=True, index=True)
    facility_id = Column(Integer, ForeignKey("facilities.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    general_capacity = Column(Integer, nullable=False, default=20)
    general_occupied = Column(Integer, nullable=False, default=0)
    icu_capacity = Column(Integer, nullable=False, default=5)
    icu_occupied = Column(Integer, nullable=False, default=0)
    oxygen_capacity = Column(Integer, nullable=False, default=10)
    oxygen_occupied = Column(Integer, nullable=False, default=0)
    isolation_capacity = Column(Integer, nullable=False, default=5)
    isolation_occupied = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    facility = relationship("Facility", back_populates="bed_capacity")


class Personnel(Base):
    """
    Facility -> Personnel Relationship (Overall Roster)
    """
    __tablename__ = "personnel"

    id = Column(Integer, primary_key=True, index=True)
    facility_id = Column(Integer, ForeignKey("facilities.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    doctors_count = Column(Integer, nullable=False, default=2)
    nurses_count = Column(Integer, nullable=False, default=6)
    pharmacists_count = Column(Integer, nullable=False, default=2)
    asha_count = Column(Integer, nullable=False, default=10)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    facility = relationship("Facility", back_populates="personnel_roster")


class PersonnelAttendance(Base):
    """
    Facility -> PersonnelAttendance Relationship (Daily Shift Tracking)
    """
    __tablename__ = "personnel_attendance"

    id = Column(Integer, primary_key=True, index=True)
    facility_id = Column(Integer, ForeignKey("facilities.id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(Date, index=True, nullable=False)
    role = Column(Enum(PersonnelRole), nullable=False)
    scheduled = Column(Integer, nullable=False, default=0)
    present = Column(Integer, nullable=False, default=0)
    absent = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    facility = relationship("Facility", back_populates="personnel_attendance")


class Forecast(Base):
    """
    Facility -> Forecasts Relationship (Predictive Modeling Output)
    """
    __tablename__ = "forecasts"

    id = Column(Integer, primary_key=True, index=True)
    facility_id = Column(Integer, ForeignKey("facilities.id", ondelete="CASCADE"), nullable=False, index=True)
    medicine_id = Column(Integer, ForeignKey("medicines.id", ondelete="RESTRICT"), nullable=False, index=True)
    item_code = Column(String(64), index=True, nullable=False)
    forecast_date = Column(Date, index=True, nullable=False)
    expected_daily_demand = Column(Float, nullable=False, default=0.0)
    days_of_cover = Column(Float, nullable=False, default=0.0)
    projected_stockout_date = Column(Date, nullable=True)
    confidence_score = Column(Float, nullable=False, default=1.0)
    calculated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    facility = relationship("Facility", back_populates="forecasts")
    medicine = relationship("Medicine", back_populates="forecast_entries")


class Alert(Base):
    """
    Facility -> Alerts Relationship (Early Warning Engine)
    """
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    alert_code = Column(String(64), unique=True, index=True, nullable=False)
    facility_id = Column(Integer, ForeignKey("facilities.id", ondelete="CASCADE"), nullable=False, index=True)
    resource_id = Column(String(64), index=True, nullable=True)
    severity = Column(Enum(AlertSeverity), nullable=False, default=AlertSeverity.WARNING)
    alert_type = Column(Enum(AlertType), nullable=False)
    title = Column(String(255), nullable=False)
    evidence_json = Column(JSON, nullable=True)
    projected_impact_date = Column(Date, nullable=True)
    status = Column(Enum(AlertStatus), nullable=False, default=AlertStatus.ACTIVE)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=utc_now, nullable=False)

    facility = relationship("Facility", back_populates="alerts")


class Recommendation(Base):
    """
    Facility -> Recommendations Relationship (Redistribution Engine)
    """
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True)
    recommendation_code = Column(String(64), unique=True, index=True, nullable=False)
    donor_facility_id = Column(Integer, ForeignKey("facilities.id", ondelete="CASCADE"), nullable=False, index=True)
    recipient_facility_id = Column(Integer, ForeignKey("facilities.id", ondelete="CASCADE"), nullable=False, index=True)
    medicine_id = Column(Integer, ForeignKey("medicines.id", ondelete="RESTRICT"), nullable=False, index=True)
    item_code = Column(String(64), nullable=False)
    recommended_quantity = Column(Integer, nullable=False)
    urgency_level = Column(Enum(UrgencyLevel), nullable=False, default=UrgencyLevel.ROUTINE)
    haversine_distance_km = Column(Float, nullable=False, default=0.0)
    expected_days_cover_gained = Column(Float, nullable=False, default=0.0)
    confidence_score = Column(Float, nullable=False, default=1.0)
    reason = Column(Text, nullable=False)
    status = Column(Enum(RecommendationStatus), nullable=False, default=RecommendationStatus.PENDING_HUMAN_APPROVAL)
    reviewed_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    donor_facility = relationship("Facility", foreign_keys=[donor_facility_id], back_populates="donor_recommendations")
    recipient_facility = relationship("Facility", foreign_keys=[recipient_facility_id], back_populates="recipient_recommendations")
    medicine = relationship("Medicine")


class Requisition(Base):
    """
    Facility -> Requisitions Relationship (Two-Tier Request Flow)
    """
    __tablename__ = "requisitions"

    id = Column(Integer, primary_key=True, index=True)
    req_code = Column(String(64), unique=True, index=True, nullable=False)
    requester_node = Column(String(128), nullable=False)
    source_facility_id = Column(Integer, ForeignKey("facilities.id", ondelete="CASCADE"), nullable=False, index=True)
    target_facility_id = Column(Integer, ForeignKey("facilities.id", ondelete="CASCADE"), nullable=False, index=True)
    medicine_id = Column(Integer, ForeignKey("medicines.id", ondelete="RESTRICT"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    urgency_reason = Column(String(255), nullable=False)
    status = Column(Enum(RequisitionStatus), nullable=False, default=RequisitionStatus.PENDING_APPROVAL)
    reviewed_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    source_facility = relationship("Facility", foreign_keys=[source_facility_id], back_populates="source_requisitions")
    target_facility = relationship("Facility", foreign_keys=[target_facility_id], back_populates="target_requisitions")


class AuditEvent(Base):
    """
    Facility -> AuditEvents Relationship (SHA-256 Tamper-Evident Ledger)
    """
    __tablename__ = "audit_events"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String(64), unique=True, index=True, nullable=False)
    timestamp = Column(DateTime, index=True, default=datetime.utcnow, nullable=False)
    actor_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(128), nullable=False)
    facility_id = Column(Integer, ForeignKey("facilities.id", ondelete="SET NULL"), nullable=True, index=True)
    payload_json = Column(JSON, nullable=True)
    previous_hash = Column(String(64), index=True, nullable=False)
    current_hash = Column(String(64), index=True, nullable=False)
    event_type = Column(Enum(EventType), nullable=False, default=EventType.TRANSACTION)
    is_tampered = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    actor = relationship("User", back_populates="audit_events")
    facility = relationship("Facility", back_populates="audit_events")


class Conversation(Base):
    """
    AI Advisor Multi-Conversation Model
    """
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False, default="New Chat")
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False, index=True)

    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at")


class Message(Base):
    """
    AI Advisor Individual Message Record
    """
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    sender = Column(String(32), nullable=False)  # 'user' or 'advisor'
    text = Column(Text, nullable=False)
    meta_json = Column(JSON, nullable=True)  # stores structured fields: summary, severity, recommended_actions, limitations, pending_update, update_result
    created_at = Column(DateTime, default=utc_now, nullable=False, index=True)

    conversation = relationship("Conversation", back_populates="messages")

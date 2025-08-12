from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Float, Enum as SQLEnum
from sqlalchemy.sql import func
from datetime import datetime
import enum
from ..core.database import Base


class AlertStatus(str, enum.Enum):
    NEW = "New"
    UNDER_REVIEW = "Under Review"
    ACTION_REQUIRED = "Action Required"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"
    CLOSED = "Closed"


class Priority(str, enum.Enum):
    P1_IMMEDIATE = "P1-Immediate"
    P2_48H = "P2-Within 48h"
    P3_WEEK = "P3-Within 1 week"
    P4_ROUTINE = "P4-Routine"


class Severity(str, enum.Enum):
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class Alert(Base):
    __tablename__ = "alerts"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Alert Identification
    alert_id = Column(String, unique=True, index=True)
    govuk_reference = Column(String)
    content_id = Column(String, unique=True, index=True)
    url = Column(String)
    title = Column(String)
    published_date = Column(DateTime)
    issued_date = Column(DateTime)
    
    # Classification & Triage
    alert_type = Column(String)  # Class 1/2/3/4 Recall, NatPSA, FSN, Safety Update
    severity = Column(SQLEnum(Severity, native_enum=False))
    message_type = Column(String)  # Medicines recall/Device alert/Safety roundup
    medical_specialties = Column(Text)  # Pipe-separated list
    auto_relevance = Column(String)  # Auto-Relevant/Auto-Not-Relevant/Manual-Review
    final_relevance = Column(String)  # Relevant/Not-Relevant
    relevance_reason = Column(Text)
    
    # Drug/Device Details
    product_name = Column(String)
    active_ingredient = Column(String)
    manufacturer = Column(String)
    batch_numbers = Column(Text)
    expiry_dates = Column(Text)
    therapeutic_area = Column(String)
    
    # Action Management
    status = Column(SQLEnum(AlertStatus, native_enum=False), default=AlertStatus.NEW)
    priority = Column(SQLEnum(Priority, native_enum=False))
    assigned_to = Column(String, default="Dr Anjan Chakraborty")
    date_first_reviewed = Column(DateTime)
    action_required = Column(Text)
    emis_search_terms = Column(Text)
    
    # Implementation Tracking
    emis_search_completed = Column(Boolean, default=False)
    emis_search_date = Column(DateTime)
    emis_search_reason = Column(Text)  # Why EMIS search wasn't done
    patients_affected_count = Column(Integer)
    
    # Emergency Drugs Check
    emergency_drugs_check = Column(Boolean, default=False)
    emergency_drugs_affected = Column(Text)  # Which emergency drugs are affected
    
    # Communication
    practice_team_notified = Column(Boolean, default=False)
    practice_team_notified_date = Column(DateTime)
    team_notification_method = Column(String)  # Email/Meeting/Phone/Multiple
    patients_contacted = Column(String)  # Yes/No/In Progress
    contact_method = Column(String)  # SMS/Letter/Phone/F2F
    communication_template = Column(String)
    
    # Patient Harm Tracking
    medication_stopped = Column(Boolean, default=False)
    medication_stopped_date = Column(DateTime)
    medication_alternative_provided = Column(Boolean, default=False)
    medication_not_stopped_reason = Column(Text)
    patient_harm_assessed = Column(Boolean, default=False)
    harm_assessment_planned_date = Column(DateTime)
    patient_harm_occurred = Column(Boolean, default=False)
    harm_severity = Column(String)  # Minor/Moderate/Severe
    patient_harm_details = Column(Text)
    recalls_completed = Column(Boolean)
    
    # Compliance & Audit
    action_completed_date = Column(DateTime)
    time_to_first_review = Column(Float)  # Hours
    time_to_completion = Column(Float)  # Hours
    evidence_uploaded = Column(Boolean, default=False)
    evidence_links = Column(Text)
    cqc_reportable = Column(Boolean, default=False)
    notes = Column(Text)
    
    # System Metadata
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    last_synced = Column(DateTime)
    data_source = Column(String, default="GOV.UK")
    backfilled = Column(Boolean, default=False)
    teams_notified = Column(Boolean, default=False)
    teams_notified_date = Column(DateTime)
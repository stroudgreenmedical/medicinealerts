from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class AlertStatusEnum(str, Enum):
    NEW = "New"
    UNDER_REVIEW = "Under Review"
    ACTION_REQUIRED = "Action Required"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"
    CLOSED = "Closed"


class PriorityEnum(str, Enum):
    P1_IMMEDIATE = "P1-Immediate"
    P2_48H = "P2-Within 48h"
    P3_WEEK = "P3-Within 1 week"
    P4_ROUTINE = "P4-Routine"


class SeverityEnum(str, Enum):
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class AlertBase(BaseModel):
    title: str
    status: AlertStatusEnum
    priority: Optional[PriorityEnum]
    severity: Optional[SeverityEnum]


class AlertCreate(AlertBase):
    pass


class AlertUpdate(BaseModel):
    status: Optional[AlertStatusEnum] = None
    priority: Optional[PriorityEnum] = None
    date_first_reviewed: Optional[datetime] = None
    action_required: Optional[str] = None
    emis_search_completed: Optional[bool] = None
    emis_search_date: Optional[datetime] = None
    emis_search_reason: Optional[str] = None
    patients_affected_count: Optional[int] = None
    emergency_drugs_check: Optional[bool] = None
    emergency_drugs_affected: Optional[str] = None
    practice_team_notified: Optional[bool] = None
    practice_team_notified_date: Optional[datetime] = None
    team_notification_method: Optional[str] = None
    patients_contacted: Optional[str] = None
    contact_method: Optional[str] = None
    communication_template: Optional[str] = None
    medication_stopped: Optional[bool] = None
    medication_stopped_date: Optional[datetime] = None
    medication_alternative_provided: Optional[bool] = None
    medication_not_stopped_reason: Optional[str] = None
    patient_harm_assessed: Optional[bool] = None
    harm_assessment_planned_date: Optional[datetime] = None
    patient_harm_occurred: Optional[bool] = None
    harm_severity: Optional[str] = None
    patient_harm_details: Optional[str] = None
    recalls_completed: Optional[bool] = None
    action_completed_date: Optional[datetime] = None
    evidence_uploaded: Optional[bool] = None
    evidence_links: Optional[str] = None
    cqc_reportable: Optional[bool] = None
    notes: Optional[str] = None
    final_relevance: Optional[str] = None
    alert_category: Optional[str] = None


class AlertResponse(AlertBase):
    id: int
    alert_id: str
    govuk_reference: Optional[str]
    content_id: str
    url: str
    published_date: Optional[datetime]
    issued_date: Optional[datetime]
    alert_type: Optional[str]
    message_type: Optional[str]
    medical_specialties: Optional[str]
    auto_relevance: Optional[str]
    final_relevance: Optional[str]
    relevance_reason: Optional[str]
    product_name: Optional[str]
    active_ingredient: Optional[str]
    manufacturer: Optional[str]
    batch_numbers: Optional[str]
    expiry_dates: Optional[str]
    therapeutic_area: Optional[str]
    assigned_to: Optional[str]
    date_first_reviewed: Optional[datetime]
    action_required: Optional[str]
    emis_search_terms: Optional[str]
    emis_search_completed: Optional[bool]
    emis_search_date: Optional[datetime]
    emis_search_reason: Optional[str]
    patients_affected_count: Optional[int]
    emergency_drugs_check: Optional[bool]
    emergency_drugs_affected: Optional[str]
    practice_team_notified: Optional[bool]
    practice_team_notified_date: Optional[datetime]
    team_notification_method: Optional[str]
    patients_contacted: Optional[str]
    contact_method: Optional[str]
    communication_template: Optional[str]
    medication_stopped: Optional[bool]
    medication_stopped_date: Optional[datetime]
    medication_alternative_provided: Optional[bool]
    medication_not_stopped_reason: Optional[str]
    patient_harm_assessed: Optional[bool]
    harm_assessment_planned_date: Optional[datetime]
    patient_harm_occurred: Optional[bool]
    harm_severity: Optional[str]
    patient_harm_details: Optional[str]
    recalls_completed: Optional[bool]
    action_completed_date: Optional[datetime]
    time_to_first_review: Optional[float]
    time_to_completion: Optional[float]
    evidence_uploaded: Optional[bool]
    evidence_links: Optional[str]
    cqc_reportable: Optional[bool]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    teams_notified: Optional[bool]
    alert_category: Optional[str] = None
    data_source: Optional[str] = None
    source_urls: Optional[str] = None
    is_duplicate: Optional[bool] = None
    primary_alert_id: Optional[int] = None
    
    class Config:
        from_attributes = True


class AlertListResponse(BaseModel):
    total: int
    items: List[AlertResponse]


class DashboardStats(BaseModel):
    total_alerts: int
    new_alerts: int
    urgent_alerts: int
    overdue_alerts: int
    completed_alerts: int
    not_relevant_alerts: int
    alerts_by_status: dict
    alerts_by_priority: dict
    alerts_by_type: dict
    recent_alerts: List[AlertResponse]


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    username: str
    email: str
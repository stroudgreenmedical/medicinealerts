from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_
from typing import Optional, List
from datetime import datetime, timedelta

from ...core.database import get_db
from ...models.alert import Alert, AlertStatus, Priority
from ...schemas.alert import (
    AlertResponse, AlertListResponse, AlertUpdate,
    AlertStatusEnum, PriorityEnum, SeverityEnum
)
from ..deps import get_current_user

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("/", response_model=AlertListResponse)
async def get_alerts(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[AlertStatusEnum] = None,
    priority: Optional[PriorityEnum] = None,
    severity: Optional[SeverityEnum] = None,
    relevance: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """
    Get list of alerts with optional filtering
    """
    query = db.query(Alert)
    
    # Apply filters
    if status:
        query = query.filter(Alert.status == status)
    
    if priority:
        query = query.filter(Alert.priority == priority)
    
    if severity:
        query = query.filter(Alert.severity == severity)
    
    if relevance:
        query = query.filter(
            or_(
                Alert.auto_relevance == relevance,
                Alert.final_relevance == relevance
            )
        )
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Alert.title.ilike(search_term),
                Alert.product_name.ilike(search_term),
                Alert.govuk_reference.ilike(search_term),
                Alert.alert_id.ilike(search_term)
            )
        )
    
    # Get total count
    total = query.count()
    
    # Apply pagination and ordering
    alerts = query.order_by(desc(Alert.published_date)).offset(skip).limit(limit).all()
    
    return AlertListResponse(
        total=total,
        items=[AlertResponse.from_orm(alert) for alert in alerts]
    )


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """
    Get single alert by ID
    """
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return AlertResponse.from_orm(alert)


@router.put("/{alert_id}", response_model=AlertResponse)
async def update_alert(
    alert_id: int,
    alert_update: AlertUpdate,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """
    Update alert details
    """
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    # Track if this is first review
    if not alert.date_first_reviewed and alert_update.date_first_reviewed:
        alert.date_first_reviewed = alert_update.date_first_reviewed
        # Calculate time to first review
        if alert.published_date:
            delta = alert_update.date_first_reviewed - alert.published_date
            alert.time_to_first_review = delta.total_seconds() / 3600  # Convert to hours
    
    # Update fields from request
    update_data = alert_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(alert, field):
            setattr(alert, field, value)
    
    # Track completion
    if alert_update.status == AlertStatusEnum.COMPLETED and not alert.action_completed_date:
        alert.action_completed_date = datetime.now()
        # Calculate time to completion
        if alert.published_date:
            delta = alert.action_completed_date - alert.published_date
            alert.time_to_completion = delta.total_seconds() / 3600  # Convert to hours
    
    alert.updated_at = datetime.now()
    
    db.commit()
    db.refresh(alert)
    
    return AlertResponse.from_orm(alert)


@router.get("/overdue/list", response_model=AlertListResponse)
async def get_overdue_alerts(
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """
    Get list of overdue alerts based on priority
    """
    now = datetime.now()
    overdue_conditions = []
    
    # P1 - Overdue after 4 hours
    p1_deadline = now - timedelta(hours=4)
    overdue_conditions.append(
        and_(
            Alert.priority == Priority.P1_IMMEDIATE,
            Alert.status.in_([AlertStatus.NEW, AlertStatus.ACTION_REQUIRED]),
            Alert.created_at < p1_deadline
        )
    )
    
    # P2 - Overdue after 48 hours
    p2_deadline = now - timedelta(hours=48)
    overdue_conditions.append(
        and_(
            Alert.priority == Priority.P2_48H,
            Alert.status.in_([AlertStatus.NEW, AlertStatus.ACTION_REQUIRED]),
            Alert.created_at < p2_deadline
        )
    )
    
    # P3 - Overdue after 1 week
    p3_deadline = now - timedelta(days=7)
    overdue_conditions.append(
        and_(
            Alert.priority == Priority.P3_WEEK,
            Alert.status.in_([AlertStatus.NEW, AlertStatus.ACTION_REQUIRED]),
            Alert.created_at < p3_deadline
        )
    )
    
    # Query with OR condition
    query = db.query(Alert).filter(or_(*overdue_conditions))
    
    total = query.count()
    alerts = query.order_by(Alert.priority, Alert.created_at).all()
    
    return AlertListResponse(
        total=total,
        items=[AlertResponse.from_orm(alert) for alert in alerts]
    )


@router.post("/{alert_id}/mark-reviewed", response_model=AlertResponse)
async def mark_alert_reviewed(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """
    Mark an alert as reviewed (convenience endpoint)
    """
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    if not alert.date_first_reviewed:
        alert.date_first_reviewed = datetime.now()
        if alert.published_date:
            delta = alert.date_first_reviewed - alert.published_date
            alert.time_to_first_review = delta.total_seconds() / 3600
    
    if alert.status == AlertStatus.NEW:
        alert.status = AlertStatus.UNDER_REVIEW
    
    alert.updated_at = datetime.now()
    
    db.commit()
    db.refresh(alert)
    
    return AlertResponse.from_orm(alert)
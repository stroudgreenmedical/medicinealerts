from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime, timedelta

from ...core.database import get_db
from ...models.alert import Alert, AlertStatus, Priority, Severity
from ...schemas.alert import DashboardStats, AlertResponse
from ..deps import get_current_user

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """
    Get dashboard statistics
    """
    # Total alerts
    total_alerts = db.query(Alert).count()
    
    # New alerts (last 24 hours)
    yesterday = datetime.now() - timedelta(days=1)
    new_alerts = db.query(Alert).filter(Alert.created_at >= yesterday).count()
    
    # Urgent alerts (P1 and P2 that are not completed)
    urgent_alerts = db.query(Alert).filter(
        Alert.priority.in_(['P1-Immediate', 'P2-Within 48h']),
        Alert.status != 'Completed'
    ).count()
    
    # Overdue alerts
    now = datetime.now()
    overdue_count = 0
    
    # P1 overdue after 4 hours
    p1_deadline = now - timedelta(hours=4)
    overdue_count += db.query(Alert).filter(
        Alert.priority == 'P1-Immediate',
        Alert.status.in_(['New', 'Action Required']),
        Alert.created_at < p1_deadline
    ).count()
    
    # P2 overdue after 48 hours
    p2_deadline = now - timedelta(hours=48)
    overdue_count += db.query(Alert).filter(
        Alert.priority == 'P2-Within 48h',
        Alert.status.in_(['New', 'Action Required']),
        Alert.created_at < p2_deadline
    ).count()
    
    # P3 overdue after 1 week
    p3_deadline = now - timedelta(days=7)
    overdue_count += db.query(Alert).filter(
        Alert.priority == 'P3-Within 1 week',
        Alert.status.in_(['New', 'Action Required']),
        Alert.created_at < p3_deadline
    ).count()
    
    # Completed alerts
    completed_alerts = db.query(Alert).filter(
        Alert.status == 'Completed'
    ).count()
    
    # Alerts by status
    status_counts = db.query(
        Alert.status,
        func.count(Alert.id)
    ).group_by(Alert.status).all()
    
    alerts_by_status = {
        status.value if hasattr(status, 'value') else status: count 
        for status, count in status_counts
    }
    
    # Alerts by priority
    priority_counts = db.query(
        Alert.priority,
        func.count(Alert.id)
    ).group_by(Alert.priority).all()
    
    alerts_by_priority = {
        (priority.value if hasattr(priority, 'value') else priority) if priority else "None": count 
        for priority, count in priority_counts
    }
    
    # Alerts by type
    type_counts = db.query(
        Alert.alert_type,
        func.count(Alert.id)
    ).group_by(Alert.alert_type).all()
    
    alerts_by_type = {
        alert_type or "Unknown": count 
        for alert_type, count in type_counts
    }
    
    # Recent alerts (last 10)
    recent_alerts = db.query(Alert).order_by(
        desc(Alert.created_at)
    ).limit(10).all()
    
    return DashboardStats(
        total_alerts=total_alerts,
        new_alerts=new_alerts,
        urgent_alerts=urgent_alerts,
        overdue_alerts=overdue_count,
        completed_alerts=completed_alerts,
        alerts_by_status=alerts_by_status,
        alerts_by_priority=alerts_by_priority,
        alerts_by_type=alerts_by_type,
        recent_alerts=[AlertResponse.from_orm(alert) for alert in recent_alerts]
    )
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text, func, desc
from datetime import datetime, timedelta

from ...core.database import get_db
from ...models.alert import Alert
from ...schemas.alert import DashboardStats, AlertResponse
from ..deps import get_current_user

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """
    Get dashboard statistics using raw SQL to avoid enum issues
    """
    # Total alerts
    total_alerts = db.execute(text("SELECT COUNT(*) FROM alerts")).scalar()
    
    # New alerts (last 24 hours)
    yesterday = datetime.now() - timedelta(days=1)
    new_alerts = db.execute(
        text("SELECT COUNT(*) FROM alerts WHERE created_at >= :yesterday"),
        {"yesterday": yesterday}
    ).scalar()
    
    # Urgent alerts (P1 and P2 that are not completed)
    urgent_alerts = db.execute(
        text("""
            SELECT COUNT(*) FROM alerts 
            WHERE priority IN ('P1-Immediate', 'P2-Within 48h') 
            AND status != 'Completed'
        """)
    ).scalar()
    
    # Overdue alerts
    now = datetime.now()
    overdue_count = 0
    
    # P1 overdue after 4 hours
    p1_deadline = now - timedelta(hours=4)
    overdue_count += db.execute(
        text("""
            SELECT COUNT(*) FROM alerts 
            WHERE priority = 'P1-Immediate' 
            AND status IN ('New', 'Action Required')
            AND created_at < :deadline
        """),
        {"deadline": p1_deadline}
    ).scalar()
    
    # P2 overdue after 48 hours
    p2_deadline = now - timedelta(hours=48)
    overdue_count += db.execute(
        text("""
            SELECT COUNT(*) FROM alerts 
            WHERE priority = 'P2-Within 48h' 
            AND status IN ('New', 'Action Required')
            AND created_at < :deadline
        """),
        {"deadline": p2_deadline}
    ).scalar()
    
    # P3 overdue after 1 week
    p3_deadline = now - timedelta(days=7)
    overdue_count += db.execute(
        text("""
            SELECT COUNT(*) FROM alerts 
            WHERE priority = 'P3-Within 1 week' 
            AND status IN ('New', 'Action Required')
            AND created_at < :deadline
        """),
        {"deadline": p3_deadline}
    ).scalar()
    
    # Completed alerts
    completed_alerts = db.execute(
        text("SELECT COUNT(*) FROM alerts WHERE status = 'Completed'")
    ).scalar()
    
    # Alerts by status
    status_results = db.execute(
        text("SELECT status, COUNT(*) FROM alerts GROUP BY status")
    ).fetchall()
    alerts_by_status = {status: count for status, count in status_results}
    
    # Alerts by priority
    priority_results = db.execute(
        text("SELECT priority, COUNT(*) FROM alerts GROUP BY priority")
    ).fetchall()
    alerts_by_priority = {
        priority if priority else "None": count 
        for priority, count in priority_results
    }
    
    # Alerts by type
    type_results = db.execute(
        text("SELECT alert_type, COUNT(*) FROM alerts GROUP BY alert_type")
    ).fetchall()
    alerts_by_type = {
        alert_type if alert_type else "Unknown": count 
        for alert_type, count in type_results
    }
    
    # Recent alerts (last 10) - using ORM carefully
    recent_alerts = []
    recent_rows = db.execute(
        text("""
            SELECT id, alert_id, govuk_reference, content_id, url, title, 
                   published_date, issued_date, alert_type, severity, priority, 
                   message_type, medical_specialties, auto_relevance, final_relevance,
                   relevance_reason, product_name, active_ingredient, manufacturer,
                   batch_numbers, expiry_dates, therapeutic_area, status, assigned_to,
                   date_first_reviewed, action_required, emis_search_terms,
                   emis_search_completed, emis_search_date, emis_search_reason,
                   patients_affected_count, emergency_drugs_check, emergency_drugs_affected,
                   practice_team_notified, practice_team_notified_date, team_notification_method,
                   patients_contacted, contact_method, communication_template,
                   medication_stopped, medication_stopped_date, medication_alternative_provided,
                   medication_not_stopped_reason, patient_harm_assessed, harm_assessment_planned_date,
                   patient_harm_occurred, harm_severity, patient_harm_details,
                   recalls_completed, action_completed_date, time_to_first_review,
                   time_to_completion, evidence_uploaded, evidence_links, cqc_reportable,
                   notes, created_at, updated_at, teams_notified
            FROM alerts 
            ORDER BY created_at DESC 
            LIMIT 10
        """)
    ).fetchall()
    
    for row in recent_rows:
        alert_dict = {
            "id": row[0],
            "alert_id": row[1],
            "govuk_reference": row[2],
            "content_id": row[3],
            "url": row[4],
            "title": row[5],
            "published_date": row[6],
            "issued_date": row[7],
            "alert_type": row[8],
            "severity": row[9],
            "priority": row[10],
            "message_type": row[11],
            "medical_specialties": row[12],
            "auto_relevance": row[13],
            "final_relevance": row[14],
            "relevance_reason": row[15],
            "product_name": row[16],
            "active_ingredient": row[17],
            "manufacturer": row[18],
            "batch_numbers": row[19],
            "expiry_dates": row[20],
            "therapeutic_area": row[21],
            "status": row[22],
            "assigned_to": row[23],
            "date_first_reviewed": row[24],
            "action_required": row[25],
            "emis_search_terms": row[26],
            "emis_search_completed": bool(row[27]) if row[27] is not None else False,
            "emis_search_date": row[28],
            "emis_search_reason": row[29],
            "patients_affected_count": row[30],
            "emergency_drugs_check": bool(row[31]) if row[31] is not None else None,
            "emergency_drugs_affected": row[32],
            "practice_team_notified": bool(row[33]) if row[33] is not None else False,
            "practice_team_notified_date": row[34],
            "team_notification_method": row[35],
            "patients_contacted": row[36],
            "contact_method": row[37],
            "communication_template": row[38],
            "medication_stopped": bool(row[39]) if row[39] is not None else None,
            "medication_stopped_date": row[40],
            "medication_alternative_provided": bool(row[41]) if row[41] is not None else None,
            "medication_not_stopped_reason": row[42],
            "patient_harm_assessed": bool(row[43]) if row[43] is not None else None,
            "harm_assessment_planned_date": row[44],
            "patient_harm_occurred": bool(row[45]) if row[45] is not None else None,
            "harm_severity": row[46],
            "patient_harm_details": row[47],
            "recalls_completed": bool(row[48]) if row[48] is not None else None,
            "action_completed_date": row[49],
            "time_to_first_review": row[50],
            "time_to_completion": row[51],
            "evidence_uploaded": bool(row[52]) if row[52] is not None else False,
            "evidence_links": row[53],
            "cqc_reportable": bool(row[54]) if row[54] is not None else False,
            "notes": row[55],
            "created_at": row[56],
            "updated_at": row[57],
            "teams_notified": bool(row[58]) if row[58] is not None else False,
        }
        recent_alerts.append(AlertResponse(**alert_dict))
    
    return DashboardStats(
        total_alerts=total_alerts or 0,
        new_alerts=new_alerts or 0,
        urgent_alerts=urgent_alerts or 0,
        overdue_alerts=overdue_count,
        completed_alerts=completed_alerts or 0,
        alerts_by_status=alerts_by_status,
        alerts_by_priority=alerts_by_priority,
        alerts_by_type=alerts_by_type,
        recent_alerts=recent_alerts
    )
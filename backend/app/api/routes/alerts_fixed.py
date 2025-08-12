from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, List
from datetime import datetime, timedelta

from ...core.database import get_db
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
    Get list of alerts with optional filtering using raw SQL to avoid enum issues
    """
    # Build WHERE clause
    where_conditions = []
    params = {}
    
    if status:
        where_conditions.append("status = :status")
        params["status"] = status.value
    
    if priority:
        where_conditions.append("priority = :priority")
        params["priority"] = priority.value
    
    if severity:
        where_conditions.append("severity = :severity")
        params["severity"] = severity.value
    
    if relevance:
        where_conditions.append("(auto_relevance = :relevance OR final_relevance = :relevance)")
        params["relevance"] = relevance
    
    if search:
        where_conditions.append("""
            (title LIKE :search OR 
             product_name LIKE :search OR 
             govuk_reference LIKE :search OR 
             alert_id LIKE :search)
        """)
        params["search"] = f"%{search}%"
    
    where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
    
    # Get total count
    count_query = f"SELECT COUNT(*) FROM alerts WHERE {where_clause}"
    total = db.execute(text(count_query), params).scalar()
    
    # Get paginated results
    select_query = f"""
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
        WHERE {where_clause}
        ORDER BY published_date DESC NULLS LAST, created_at DESC
        LIMIT :limit OFFSET :skip
    """
    
    params["limit"] = limit
    params["skip"] = skip
    
    rows = db.execute(text(select_query), params).fetchall()
    
    alerts = []
    for row in rows:
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
        alerts.append(AlertResponse(**alert_dict))
    
    return AlertListResponse(
        total=total or 0,
        items=alerts
    )


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """
    Get single alert by ID using raw SQL
    """
    query = text("""
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
        WHERE id = :alert_id
    """)
    
    row = db.execute(query, {"alert_id": alert_id}).fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Alert not found")
    
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
    
    return AlertResponse(**alert_dict)


@router.put("/{alert_id}", response_model=AlertResponse)
async def update_alert(
    alert_id: int,
    alert_update: AlertUpdate,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """
    Update alert using raw SQL
    """
    # First check if alert exists
    check_query = text("SELECT id FROM alerts WHERE id = :alert_id")
    exists = db.execute(check_query, {"alert_id": alert_id}).fetchone()
    
    if not exists:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    # Build UPDATE statement
    update_fields = []
    params = {"alert_id": alert_id}
    
    # Convert AlertUpdate to dict and process updates
    update_data = alert_update.dict(exclude_unset=True)
    
    for field, value in update_data.items():
        if value is not None:
            # Convert enum values to strings
            if hasattr(value, 'value'):
                value = value.value
            
            update_fields.append(f"{field} = :{field}")
            params[field] = value
    
    if update_fields:
        # Add updated_at
        update_fields.append("updated_at = :updated_at")
        params["updated_at"] = datetime.now()
        
        # Calculate time metrics if needed
        if "date_first_reviewed" in update_data:
            # Get created_at for time calculation
            created_query = text("SELECT created_at FROM alerts WHERE id = :alert_id")
            created_at = db.execute(created_query, {"alert_id": alert_id}).scalar()
            if created_at:
                time_diff = (update_data["date_first_reviewed"] - created_at).total_seconds() / 3600
                update_fields.append("time_to_first_review = :time_to_first_review")
                params["time_to_first_review"] = time_diff
        
        if "action_completed_date" in update_data:
            # Get created_at for time calculation
            created_query = text("SELECT created_at FROM alerts WHERE id = :alert_id")
            created_at = db.execute(created_query, {"alert_id": alert_id}).scalar()
            if created_at:
                time_diff = (update_data["action_completed_date"] - created_at).total_seconds() / 3600
                update_fields.append("time_to_completion = :time_to_completion")
                params["time_to_completion"] = time_diff
        
        update_query = text(f"""
            UPDATE alerts 
            SET {', '.join(update_fields)}
            WHERE id = :alert_id
        """)
        
        db.execute(update_query, params)
        db.commit()
    
    # Return updated alert
    return await get_alert(alert_id, db, current_user)


@router.post("/{alert_id}/mark-reviewed", response_model=AlertResponse)
async def mark_alert_reviewed(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """
    Mark alert as reviewed
    """
    # Check if alert exists
    check_query = text("SELECT id, created_at FROM alerts WHERE id = :alert_id")
    result = db.execute(check_query, {"alert_id": alert_id}).fetchone()
    
    if not result:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    alert_id_val, created_at = result
    now = datetime.now()
    
    # Calculate time to first review
    time_to_review = (now - created_at).total_seconds() / 3600 if created_at else None
    
    # Update alert
    update_query = text("""
        UPDATE alerts 
        SET date_first_reviewed = :now,
            status = 'Under Review',
            time_to_first_review = :time_to_review,
            updated_at = :now
        WHERE id = :alert_id
    """)
    
    db.execute(update_query, {
        "alert_id": alert_id,
        "now": now,
        "time_to_review": time_to_review
    })
    db.commit()
    
    # Return updated alert
    return await get_alert(alert_id, db, current_user)


@router.get("/overdue/list")
async def get_overdue_alerts(
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """
    Get list of overdue alerts based on priority SLAs
    """
    now = datetime.now()
    
    # Define SLA deadlines
    p1_deadline = now - timedelta(hours=4)
    p2_deadline = now - timedelta(hours=48)
    p3_deadline = now - timedelta(days=7)
    
    query = text("""
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
        WHERE status IN ('New', 'Action Required')
        AND (
            (priority = 'P1-Immediate' AND created_at < :p1_deadline) OR
            (priority = 'P2-Within 48h' AND created_at < :p2_deadline) OR
            (priority = 'P3-Within 1 week' AND created_at < :p3_deadline)
        )
        ORDER BY 
            CASE priority 
                WHEN 'P1-Immediate' THEN 1
                WHEN 'P2-Within 48h' THEN 2
                WHEN 'P3-Within 1 week' THEN 3
                ELSE 4
            END,
            created_at ASC
    """)
    
    rows = db.execute(query, {
        "p1_deadline": p1_deadline,
        "p2_deadline": p2_deadline,
        "p3_deadline": p3_deadline
    }).fetchall()
    
    alerts = []
    for row in rows:
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
        alerts.append(AlertResponse(**alert_dict))
    
    return alerts
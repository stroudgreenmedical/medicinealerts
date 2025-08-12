from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional
import pandas as pd
from pathlib import Path
import tempfile

from ...core.database import get_db
from ...models.alert import Alert
from ...services.excel_export import ExcelExportService
from ..deps import get_current_user

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/export/excel")
async def export_to_excel(
    start_date: Optional[datetime] = Query(None, description="Start date for export"),
    end_date: Optional[datetime] = Query(None, description="End date for export"),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """
    Export alerts to Excel file
    """
    # Default to last 30 days if no dates provided
    if not end_date:
        end_date = datetime.now()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    # Query alerts
    query = db.query(Alert).filter(
        Alert.created_at >= start_date,
        Alert.created_at <= end_date
    ).order_by(Alert.published_date.desc())
    
    alerts = query.all()
    
    # Create Excel file
    excel_service = ExcelExportService()
    file_path = excel_service.export_alerts(alerts, start_date, end_date)
    
    # Return file
    filename = f"MHRA_Alerts_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.xlsx"
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@router.get("/summary/monthly")
async def get_monthly_summary(
    year: int = Query(..., description="Year"),
    month: int = Query(..., ge=1, le=12, description="Month"),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """
    Get monthly summary statistics
    """
    # Calculate date range
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1) - timedelta(seconds=1)
    else:
        end_date = datetime(year, month + 1, 1) - timedelta(seconds=1)
    
    # Query alerts for the month
    alerts = db.query(Alert).filter(
        Alert.published_date >= start_date,
        Alert.published_date <= end_date
    ).all()
    
    # Calculate statistics
    total_alerts = len(alerts)
    relevant_alerts = len([a for a in alerts if a.final_relevance == "Relevant"])
    completed_alerts = len([a for a in alerts if a.status == "Completed"])
    
    # Average response times
    response_times = [a.time_to_first_review for a in alerts if a.time_to_first_review]
    avg_response_time = sum(response_times) / len(response_times) if response_times else 0
    
    completion_times = [a.time_to_completion for a in alerts if a.time_to_completion]
    avg_completion_time = sum(completion_times) / len(completion_times) if completion_times else 0
    
    # Group by alert type
    alert_types = {}
    for alert in alerts:
        alert_type = alert.alert_type or "Unknown"
        alert_types[alert_type] = alert_types.get(alert_type, 0) + 1
    
    return {
        "period": f"{year}-{month:02d}",
        "total_alerts": total_alerts,
        "relevant_alerts": relevant_alerts,
        "completed_alerts": completed_alerts,
        "completion_rate": (completed_alerts / relevant_alerts * 100) if relevant_alerts > 0 else 0,
        "avg_response_time_hours": round(avg_response_time, 2),
        "avg_completion_time_hours": round(avg_completion_time, 2),
        "alerts_by_type": alert_types
    }


@router.get("/summary/annual")
async def get_annual_summary(
    year: int = Query(..., description="Year"),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """
    Get annual summary statistics
    """
    start_date = datetime(year, 1, 1)
    end_date = datetime(year + 1, 1, 1) - timedelta(seconds=1)
    
    # Query all alerts for the year
    alerts = db.query(Alert).filter(
        Alert.published_date >= start_date,
        Alert.published_date <= end_date
    ).all()
    
    # Monthly breakdown
    monthly_stats = []
    for month in range(1, 13):
        month_start = datetime(year, month, 1)
        if month == 12:
            month_end = datetime(year + 1, 1, 1) - timedelta(seconds=1)
        else:
            month_end = datetime(year, month + 1, 1) - timedelta(seconds=1)
        
        month_alerts = [a for a in alerts if month_start <= a.published_date <= month_end]
        
        monthly_stats.append({
            "month": month,
            "total": len(month_alerts),
            "relevant": len([a for a in month_alerts if a.final_relevance == "Relevant"]),
            "completed": len([a for a in month_alerts if a.status == "Completed"])
        })
    
    # Overall statistics
    total_alerts = len(alerts)
    relevant_alerts = len([a for a in alerts if a.final_relevance == "Relevant"])
    completed_alerts = len([a for a in alerts if a.status == "Completed"])
    
    # Compliance metrics
    on_time_reviews = len([a for a in alerts if a.time_to_first_review and a.time_to_first_review <= 24])
    compliance_rate = (on_time_reviews / total_alerts * 100) if total_alerts > 0 else 0
    
    return {
        "year": year,
        "total_alerts": total_alerts,
        "relevant_alerts": relevant_alerts,
        "completed_alerts": completed_alerts,
        "completion_rate": (completed_alerts / relevant_alerts * 100) if relevant_alerts > 0 else 0,
        "compliance_rate": round(compliance_rate, 2),
        "monthly_breakdown": monthly_stats
    }
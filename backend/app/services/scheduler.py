from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
import logging
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from ..core.database import SessionLocal
from ..core.config import settings
from ..models.alert import Alert, AlertStatus
from .govuk_client import GovUKClient
from .triage import TriageService
from .teams_notify import TeamsNotificationService
from .alert_processor import AlertProcessor

logger = logging.getLogger(__name__)


class SchedulerService:
    """Service for managing scheduled tasks"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.govuk_client = GovUKClient()
        self.triage_service = TriageService()
        self.teams_service = TeamsNotificationService()
        self.alert_processor = AlertProcessor()
        
    def start(self):
        """Start the scheduler with configured jobs"""
        
        # Main polling job - every 4 hours
        self.scheduler.add_job(
            self.poll_for_alerts,
            IntervalTrigger(hours=settings.POLL_INTERVAL_HOURS),
            id="poll_alerts",
            name="Poll GOV.UK for new alerts",
            misfire_grace_time=3600  # 1 hour grace period
        )
        
        # Daily summary job - at 9 AM
        self.scheduler.add_job(
            self.send_daily_summary,
            CronTrigger(hour=9, minute=0),
            id="daily_summary",
            name="Send daily summary"
        )
        
        # Weekly report generation - Monday at 8 AM
        self.scheduler.add_job(
            self.generate_weekly_report,
            CronTrigger(day_of_week=0, hour=8, minute=0),
            id="weekly_report",
            name="Generate weekly report"
        )
        
        # Check for overdue alerts - every hour
        self.scheduler.add_job(
            self.check_overdue_alerts,
            IntervalTrigger(hours=1),
            id="check_overdue",
            name="Check for overdue alerts"
        )
        
        self.scheduler.start()
        logger.info("Scheduler started with all jobs configured")
    
    def stop(self):
        """Stop the scheduler"""
        self.scheduler.shutdown()
        logger.info("Scheduler stopped")
    
    async def poll_for_alerts(self):
        """Main job to poll GOV.UK for new alerts"""
        logger.info("Starting alert polling job")
        
        try:
            # Fetch recent alerts (last 7 days to catch any missed)
            alerts_data = await self.govuk_client.fetch_recent_alerts(days=7)
            
            new_count = 0
            relevant_count = 0
            
            db = SessionLocal()
            try:
                for alert_data in alerts_data:
                    # Check if we've already processed this alert
                    content_id = alert_data.get("content_id")
                    if not content_id:
                        continue
                    
                    existing = db.query(Alert).filter_by(content_id=content_id).first()
                    if existing:
                        continue
                    
                    # Enrich the alert with detailed content
                    enriched = await self.govuk_client.enrich_alert(alert_data)
                    
                    # Process the alert
                    alert = await self.alert_processor.process_alert(enriched, db)
                    
                    if alert:
                        new_count += 1
                        
                        # Send Teams notification if relevant
                        if alert.auto_relevance == "Auto-Relevant":
                            relevant_count += 1
                            await self.teams_service.send_alert_notification(alert)
                
                db.commit()
                
            finally:
                db.close()
            
            logger.info(f"Polling complete: {new_count} new alerts, {relevant_count} relevant")
            
            # Send summary if there were new alerts
            if new_count > 0:
                await self.teams_service.send_summary_notification(
                    new_alerts=new_count,
                    relevant_alerts=relevant_count,
                    period_hours=settings.POLL_INTERVAL_HOURS
                )
                
        except Exception as e:
            logger.error(f"Error in polling job: {e}")
            await self.teams_service.send_error_notification(
                "Alert polling failed",
                str(e)
            )
    
    async def send_daily_summary(self):
        """Send daily summary of alerts"""
        logger.info("Generating daily summary")
        
        db = SessionLocal()
        try:
            # Get alerts from last 24 hours
            yesterday = datetime.now() - timedelta(days=1)
            
            new_alerts = db.query(Alert).filter(
                Alert.created_at >= yesterday
            ).count()
            
            pending_alerts = db.query(Alert).filter(
                Alert.status.in_([AlertStatus.NEW, AlertStatus.ACTION_REQUIRED])
            ).count()
            
            overdue_alerts = self._get_overdue_alerts(db)
            
            # Create summary message
            summary = f"""
            Daily MHRA Alerts Summary:
            - New alerts (24h): {new_alerts}
            - Pending review: {pending_alerts}
            - Overdue: {len(overdue_alerts)}
            """
            
            # Send notification if there are pending items
            if pending_alerts > 0 or len(overdue_alerts) > 0:
                await self.teams_service.send_summary_notification(
                    new_alerts=new_alerts,
                    relevant_alerts=pending_alerts,
                    period_hours=24
                )
                
        finally:
            db.close()
    
    async def generate_weekly_report(self):
        """Generate weekly Excel report"""
        logger.info("Generating weekly report")
        
        # This will be implemented with the Excel export service
        # For now, just log
        pass
    
    async def check_overdue_alerts(self):
        """Check for overdue alerts based on priority"""
        logger.info("Checking for overdue alerts")
        
        db = SessionLocal()
        try:
            overdue = self._get_overdue_alerts(db)
            
            if overdue:
                logger.warning(f"Found {len(overdue)} overdue alerts")
                # Could send specific notifications for critical overdue items
                
        finally:
            db.close()
    
    def _get_overdue_alerts(self, db: Session) -> list:
        """Get list of overdue alerts based on priority"""
        overdue = []
        now = datetime.now()
        
        # P1 - Should be actioned immediately (overdue after 4 hours)
        p1_deadline = now - timedelta(hours=4)
        p1_overdue = db.query(Alert).filter(
            and_(
                Alert.priority == "P1-Immediate",
                Alert.status.in_([AlertStatus.NEW, AlertStatus.ACTION_REQUIRED]),
                Alert.created_at < p1_deadline
            )
        ).all()
        overdue.extend(p1_overdue)
        
        # P2 - Should be actioned within 48 hours
        p2_deadline = now - timedelta(hours=48)
        p2_overdue = db.query(Alert).filter(
            and_(
                Alert.priority == "P2-Within 48h",
                Alert.status.in_([AlertStatus.NEW, AlertStatus.ACTION_REQUIRED]),
                Alert.created_at < p2_deadline
            )
        ).all()
        overdue.extend(p2_overdue)
        
        # P3 - Should be actioned within 1 week
        p3_deadline = now - timedelta(days=7)
        p3_overdue = db.query(Alert).filter(
            and_(
                Alert.priority == "P3-Within 1 week",
                Alert.status.in_([AlertStatus.NEW, AlertStatus.ACTION_REQUIRED]),
                Alert.created_at < p3_deadline
            )
        ).all()
        overdue.extend(p3_overdue)
        
        return overdue
    
    async def run_backfill(self, years: int = None):
        """
        Run backfill for historical data
        
        Args:
            years: Number of years to backfill (default from config)
        """
        years = years or settings.BACKFILL_YEARS
        logger.info(f"Starting backfill for {years} years")
        
        since_date = datetime.now() - timedelta(days=years * 365)
        
        try:
            # Fetch all medical safety alerts
            alerts_data = await self.govuk_client.fetch_all_alerts(
                document_type="medical_safety_alert",
                since_date=since_date
            )
            
            # Also fetch drug safety updates
            dsu_data = await self.govuk_client.fetch_all_alerts(
                document_type="drug_safety_update",
                since_date=since_date
            )
            
            all_alerts = alerts_data + dsu_data
            logger.info(f"Found {len(all_alerts)} alerts to backfill")
            
            db = SessionLocal()
            try:
                processed = 0
                for alert_data in all_alerts:
                    content_id = alert_data.get("content_id")
                    if not content_id:
                        continue
                    
                    # Check if already exists
                    existing = db.query(Alert).filter_by(content_id=content_id).first()
                    if existing:
                        continue
                    
                    # Enrich and process
                    enriched = await self.govuk_client.enrich_alert(alert_data)
                    alert = await self.alert_processor.process_alert(
                        enriched, 
                        db, 
                        backfill=True  # Don't send notifications for backfill
                    )
                    
                    if alert:
                        processed += 1
                    
                    # Commit in batches
                    if processed % 100 == 0:
                        db.commit()
                        logger.info(f"Processed {processed} alerts")
                
                db.commit()
                logger.info(f"Backfill complete: processed {processed} alerts")
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error in backfill: {e}")
            raise
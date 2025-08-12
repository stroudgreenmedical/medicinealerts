from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
import logging
import hashlib

from ..models.alert import Alert, AlertStatus, Priority, Severity
from .triage import TriageService
from ..core.config import settings

logger = logging.getLogger(__name__)


class AlertProcessor:
    """Service for processing alerts from GOV.UK data"""
    
    def __init__(self):
        self.triage_service = TriageService()
    
    async def process_alert(
        self,
        alert_data: Dict[str, Any],
        db: Session,
        backfill: bool = False
    ) -> Optional[Alert]:
        """
        Process a single alert from GOV.UK data
        
        Args:
            alert_data: Raw alert data from GOV.UK API
            db: Database session
            backfill: Whether this is part of backfill (skip notifications)
            
        Returns:
            Alert object if processed successfully, None otherwise
        """
        try:
            # Extract basic information
            content_id = alert_data.get("content_id")
            if not content_id:
                logger.warning("Alert missing content_id, skipping")
                return None
            
            # Check if already exists
            existing = db.query(Alert).filter_by(content_id=content_id).first()
            if existing:
                return self._update_existing_alert(existing, alert_data, db)
            
            # Create new alert
            alert = Alert()
            
            # Set identification fields
            alert.content_id = content_id
            alert.alert_id = self._generate_alert_id(content_id)
            alert.url = alert_data.get("link", "")
            alert.title = alert_data.get("title", "")
            alert.govuk_reference = self._extract_reference(alert.title)
            
            # Set dates
            alert.published_date = self._parse_date(alert_data.get("public_timestamp"))
            alert.issued_date = self._parse_date(alert_data.get("issued_date"))
            
            # Set classification fields
            alert.alert_type = alert_data.get("alert_type", "")
            alert.message_type = alert_data.get("message_type", "")
            
            # Handle medical specialties
            specialties = alert_data.get("medical_specialties", [])
            if isinstance(specialties, list):
                alert.medical_specialties = " | ".join(specialties)
            else:
                alert.medical_specialties = str(specialties) if specialties else ""
            
            # Perform triage
            relevance, reason, severity, priority = self.triage_service.triage_alert(alert_data)
            alert.auto_relevance = relevance
            alert.relevance_reason = reason
            alert.severity = Severity(severity)
            alert.priority = Priority(priority)
            
            # Set initial status based on relevance
            if relevance == "Auto-Relevant":
                alert.status = AlertStatus.ACTION_REQUIRED
                alert.final_relevance = "Relevant"
            elif relevance == "Auto-Not-Relevant":
                alert.status = AlertStatus.CLOSED
                alert.final_relevance = "Not-Relevant"
            else:  # Manual-Review
                alert.status = AlertStatus.NEW
                alert.final_relevance = None
            
            # Extract product details
            product_details = self.triage_service.extract_product_details(alert_data)
            alert.product_name = product_details.get("product_name")
            alert.active_ingredient = product_details.get("active_ingredient")
            alert.manufacturer = product_details.get("manufacturer")
            alert.batch_numbers = product_details.get("batch_numbers")
            alert.expiry_dates = product_details.get("expiry_dates")
            alert.therapeutic_area = product_details.get("therapeutic_area")
            
            # Generate EMIS search terms
            alert.emis_search_terms = self.triage_service.generate_emis_search_terms(product_details)
            
            # Set approver
            alert.assigned_to = self._get_current_approver()
            
            # Set metadata
            alert.data_source = "GOV.UK"
            alert.backfilled = backfill
            
            # Add to database
            db.add(alert)
            
            # Log the processing
            logger.info(f"Processed alert: {alert.title} - {relevance}")
            
            return alert
            
        except Exception as e:
            logger.error(f"Error processing alert: {e}")
            return None
    
    def _update_existing_alert(
        self,
        existing: Alert,
        new_data: Dict[str, Any],
        db: Session
    ) -> Alert:
        """
        Update an existing alert with new data
        
        Only updates metadata fields, not user-entered data
        """
        # Update metadata that might have changed
        if new_data.get("title"):
            existing.title = new_data["title"]
        
        if new_data.get("message_type"):
            existing.message_type = new_data["message_type"]
        
        # Update specialties if they've changed
        specialties = new_data.get("medical_specialties", [])
        if specialties:
            if isinstance(specialties, list):
                new_specialties = " | ".join(specialties)
            else:
                new_specialties = str(specialties)
            
            if new_specialties != existing.medical_specialties:
                existing.medical_specialties = new_specialties
                # Re-triage if specialties changed
                relevance, reason, severity, priority = self.triage_service.triage_alert(new_data)
                
                # Only update if not manually overridden
                if not existing.final_relevance or existing.final_relevance == existing.auto_relevance:
                    existing.auto_relevance = relevance
                    existing.relevance_reason = reason
        
        existing.updated_at = datetime.now()
        
        return existing
    
    def _generate_alert_id(self, content_id: str) -> str:
        """Generate a short, unique alert ID"""
        # Use first 8 chars of content_id hash
        hash_obj = hashlib.md5(content_id.encode())
        return f"MHRA-{hash_obj.hexdigest()[:8].upper()}"
    
    def _extract_reference(self, title: str) -> Optional[str]:
        """Extract GOV.UK reference from title if present"""
        import re
        
        # Common patterns for references
        patterns = [
            r"\(([A-Z]+\(\d+\)[A-Z]?/\d+)\)",  # e.g., EL(25)A/29
            r"\(([A-Z]+/\d+/\d+)\)",            # e.g., MDR/2025/001
            r"\(([A-Z]+-\d+-\d+)\)",            # e.g., NatPSA-2025-001
        ]
        
        for pattern in patterns:
            match = re.search(pattern, title)
            if match:
                return match.group(1)
        
        return None
    
    def _parse_date(self, date_str: Any) -> Optional[datetime]:
        """Parse date from various formats"""
        if not date_str:
            return None
        
        if isinstance(date_str, datetime):
            return date_str
        
        date_str = str(date_str)
        
        try:
            # Try ISO format first
            if "T" in date_str:
                return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            # Try simple date format
            else:
                return datetime.strptime(date_str, "%Y-%m-%d")
        except (ValueError, AttributeError):
            logger.warning(f"Could not parse date: {date_str}")
            return None
    
    def _get_current_approver(self) -> str:
        """Get current approver based on date"""
        switch_date = datetime.strptime(settings.APPROVER_SWITCH_DATE, "%Y-%m-%d")
        if datetime.now() < switch_date:
            return settings.APPROVER_NAME
        return settings.APPROVER_AFTER
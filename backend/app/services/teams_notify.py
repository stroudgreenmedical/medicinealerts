import httpx
from typing import Dict, Any, Optional
from datetime import datetime
import logging
from tenacity import retry, stop_after_attempt, wait_exponential
from ..core.config import settings
from ..models.alert import Alert

logger = logging.getLogger(__name__)


class TeamsNotificationService:
    """Service for sending notifications to Microsoft Teams"""
    
    def __init__(self):
        self.webhook_url = settings.TEAMS_WEBHOOK_URL
        self.approver = self._get_current_approver()
    
    def _get_current_approver(self) -> str:
        """Determine current approver based on date"""
        switch_date = datetime.strptime(settings.APPROVER_SWITCH_DATE, "%Y-%m-%d")
        if datetime.now() < switch_date:
            return settings.APPROVER_NAME
        return settings.APPROVER_AFTER
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def send_alert_notification(self, alert: Alert) -> bool:
        """
        Send an alert notification to Teams
        
        Args:
            alert: Alert object to notify about
            
        Returns:
            True if notification sent successfully
        """
        if not self.webhook_url:
            logger.warning("Teams webhook URL not configured")
            return False
        
        card = self._create_adaptive_card(alert)
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(self.webhook_url, json=card)
                response.raise_for_status()
                logger.info(f"Teams notification sent for alert {alert.alert_id}")
                return True
            except httpx.HTTPError as e:
                logger.error(f"Failed to send Teams notification: {e}")
                return False
    
    def _create_adaptive_card(self, alert: Alert) -> Dict[str, Any]:
        """Create an adaptive card for the alert"""
        
        # Determine color based on priority
        color_map = {
            "P1-Immediate": "FF0000",      # Red
            "P2-Within 48h": "FF8C00",     # Dark Orange
            "P3-Within 1 week": "FFD700",  # Gold
            "P4-Routine": "32CD32"         # Lime Green
        }
        theme_color = color_map.get(alert.priority.value if alert.priority else "P4-Routine", "0078D7")
        
        # Format dates
        published = alert.published_date.strftime("%d %B %Y") if alert.published_date else "Unknown"
        issued = alert.issued_date.strftime("%d %B %Y") if alert.issued_date else published
        
        # Create facts for the card
        facts = [
            {"name": "Alert Type", "value": alert.alert_type or "Unknown"},
            {"name": "Message Type", "value": alert.message_type or "Unknown"},
            {"name": "Severity", "value": alert.severity.value if alert.severity else "Unknown"},
            {"name": "Priority", "value": alert.priority.value if alert.priority else "Unknown"},
            {"name": "Medical Specialties", "value": alert.medical_specialties or "Not specified"},
            {"name": "Published", "value": published},
            {"name": "Issued", "value": issued},
            {"name": "Assigned To", "value": self.approver}
        ]
        
        # Add product details if available
        if alert.product_name:
            facts.insert(2, {"name": "Product", "value": alert.product_name})
        if alert.batch_numbers:
            facts.append({"name": "Batch Numbers", "value": alert.batch_numbers})
        
        card = {
            "@type": "MessageCard",
            "@context": "https://schema.org/extensions",
            "summary": f"MHRA Alert: {alert.title}",
            "themeColor": theme_color,
            "title": alert.title,
            "sections": [
                {
                    "activityTitle": "New MHRA Alert Requires Review",
                    "activitySubtitle": f"Auto-classified as {alert.auto_relevance}",
                    "activityImage": "https://www.gov.uk/assets/static/govuk-apple-touch-icon-180x180.png",
                    "facts": facts,
                    "text": alert.relevance_reason or "This alert has been classified as relevant for GP/Dispensing GP practices."
                }
            ],
            "potentialAction": [
                {
                    "@type": "OpenUri",
                    "name": "View on GOV.UK",
                    "targets": [
                        {
                            "os": "default",
                            "uri": alert.url
                        }
                    ]
                },
                {
                    "@type": "OpenUri",
                    "name": "Open Dashboard",
                    "targets": [
                        {
                            "os": "default",
                            "uri": f"http://synology.local:8080/alerts/{alert.id}"
                        }
                    ]
                }
            ]
        }
        
        return card
    
    async def send_summary_notification(
        self,
        new_alerts: int,
        relevant_alerts: int,
        period_hours: int = 24
    ) -> bool:
        """
        Send a summary notification to Teams
        
        Args:
            new_alerts: Number of new alerts found
            relevant_alerts: Number of relevant alerts
            period_hours: Period covered by the summary
            
        Returns:
            True if notification sent successfully
        """
        if not self.webhook_url:
            return False
        
        card = {
            "@type": "MessageCard",
            "@context": "https://schema.org/extensions",
            "summary": f"MHRA Alerts Summary",
            "themeColor": "0078D7",
            "title": "MHRA Alerts Summary",
            "sections": [
                {
                    "activityTitle": f"Summary for the last {period_hours} hours",
                    "facts": [
                        {"name": "Total New Alerts", "value": str(new_alerts)},
                        {"name": "Relevant to GP", "value": str(relevant_alerts)},
                        {"name": "Auto-closed", "value": str(new_alerts - relevant_alerts)},
                        {"name": "Reviewer", "value": self.approver}
                    ]
                }
            ],
            "potentialAction": [
                {
                    "@type": "OpenUri",
                    "name": "Open Dashboard",
                    "targets": [
                        {
                            "os": "default",
                            "uri": "http://synology.local:8080/"
                        }
                    ]
                }
            ]
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(self.webhook_url, json=card)
                response.raise_for_status()
                return True
            except httpx.HTTPError as e:
                logger.error(f"Failed to send summary notification: {e}")
                return False
    
    async def send_error_notification(self, error_message: str, error_details: str = "") -> bool:
        """
        Send an error notification to Teams
        
        Args:
            error_message: Main error message
            error_details: Additional error details
            
        Returns:
            True if notification sent successfully
        """
        if not self.webhook_url:
            return False
        
        card = {
            "@type": "MessageCard",
            "@context": "https://schema.org/extensions",
            "summary": "MHRA Alerts System Error",
            "themeColor": "FF0000",  # Red for errors
            "title": "⚠️ MHRA Alerts System Error",
            "sections": [
                {
                    "activityTitle": "System Error Detected",
                    "facts": [
                        {"name": "Error", "value": error_message},
                        {"name": "Time", "value": datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
                        {"name": "System", "value": "MHRA Alerts Automator"}
                    ],
                    "text": error_details if error_details else "Please check the system logs for more information."
                }
            ],
            "potentialAction": [
                {
                    "@type": "OpenUri",
                    "name": "Check System",
                    "targets": [
                        {
                            "os": "default",
                            "uri": "http://synology.local:8080/admin"
                        }
                    ]
                }
            ]
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(self.webhook_url, json=card)
                response.raise_for_status()
                return True
            except httpx.HTTPError:
                # If we can't send error notifications, just log it
                logger.error(f"Could not send error notification to Teams")
                return False
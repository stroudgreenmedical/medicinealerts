from typing import Dict, Tuple, List, Any
import re
from ..core.config import settings
from ..models.alert import Severity, Priority
import logging

logger = logging.getLogger(__name__)


class TriageService:
    """Service for triaging alerts for GP relevance"""
    
    def __init__(self):
        self.relevant_specialties = settings.RELEVANT_SPECIALTIES
        self.allow_list = []  # Can be populated from config
        self.deny_list = []   # Can be populated from config
    
    def triage_alert(self, alert_data: Dict[str, Any]) -> Tuple[str, str, str, str]:
        """
        Triage an alert for GP relevance
        
        Returns:
            Tuple of (relevance, reason, severity, priority)
            relevance: "Auto-Relevant", "Auto-Not-Relevant", or "Manual-Review"
            reason: Explanation for the classification
            severity: Critical/High/Medium/Low
            priority: P1-P4
        """
        content_id = alert_data.get("content_id", "")
        title = alert_data.get("title", "").lower()
        message_type = alert_data.get("message_type", "").lower()
        alert_type = alert_data.get("alert_type", "").lower()
        
        # Get medical specialties - handle both list and string formats
        specialties = alert_data.get("medical_specialties", [])
        if isinstance(specialties, str):
            specialties = [s.strip() for s in specialties.split("|") if s.strip()]
        elif not isinstance(specialties, list):
            specialties = []
        
        # Check deny list first
        if content_id in self.deny_list:
            return "Auto-Not-Relevant", "Content ID in deny list", "Low", "P4-Routine"
        
        # Check allow list
        if content_id in self.allow_list:
            severity, priority = self._determine_severity_priority(alert_type, message_type)
            return "Auto-Relevant", "Content ID in allow list", severity, priority
        
        # Check medical specialties
        relevant_found = False
        for specialty in specialties:
            if any(relevant in specialty for relevant in self.relevant_specialties):
                relevant_found = True
                break
        
        # Determine relevance based on rules
        if relevant_found:
            severity, priority = self._determine_severity_priority(alert_type, message_type)
            
            # Special handling for specific message types
            if "national patient safety alert" in message_type:
                return "Auto-Relevant", f"National Patient Safety Alert with GP specialty", "Critical", "P1-Immediate"
            elif "mhra safety roundup" in message_type:
                return "Auto-Relevant", f"MHRA Safety Roundup with GP specialty", severity, priority
            else:
                specialties_str = ", ".join(specialties)
                return "Auto-Relevant", f"Specialties include: {specialties_str}", severity, priority
        
        # Check for keywords that might indicate relevance
        gp_keywords = [
            "general practice", "gp", "primary care", "prescribing",
            "community pharmacy", "dispensing"
        ]
        
        if any(keyword in title for keyword in gp_keywords):
            return "Manual-Review", "GP-related keywords in title but no GP specialty listed", "Medium", "P3-Within 1 week"
        
        # Default to not relevant
        return "Auto-Not-Relevant", "No GP/Dispensing GP specialties listed", "Low", "P4-Routine"
    
    def _determine_severity_priority(self, alert_type: str, message_type: str) -> Tuple[str, str]:
        """
        Determine severity and priority based on alert type
        
        Returns:
            Tuple of (severity, priority)
        """
        alert_type_lower = alert_type.lower() if alert_type else ""
        message_type_lower = message_type.lower() if message_type else ""
        
        # Class 1 recalls - most serious
        if "class 1" in alert_type_lower or "class 1" in message_type_lower:
            return "Critical", "P1-Immediate"
        
        # Class 2 recalls - serious
        elif "class 2" in alert_type_lower or "class 2" in message_type_lower:
            return "High", "P2-Within 48h"
        
        # National Patient Safety Alerts
        elif "national patient safety" in message_type_lower:
            return "Critical", "P1-Immediate"
        
        # Class 3 recalls
        elif "class 3" in alert_type_lower or "class 3" in message_type_lower:
            return "Medium", "P3-Within 1 week"
        
        # Class 4 recalls or general alerts
        elif "class 4" in alert_type_lower or "class 4" in message_type_lower:
            return "Low", "P4-Routine"
        
        # Field Safety Notices
        elif "field safety" in message_type_lower or "fsn" in alert_type_lower:
            return "Medium", "P3-Within 1 week"
        
        # Safety updates/roundups
        elif "safety update" in message_type_lower or "safety roundup" in message_type_lower:
            return "Medium", "P3-Within 1 week"
        
        # Default
        else:
            return "Medium", "P3-Within 1 week"
    
    def extract_product_details(self, alert_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract product details from alert data
        
        Returns:
            Dictionary with product information
        """
        title = alert_data.get("title", "")
        body = alert_data.get("body", "")
        description = alert_data.get("description", "")
        
        details = {
            "product_name": None,
            "active_ingredient": None,
            "manufacturer": None,
            "batch_numbers": None,
            "expiry_dates": None,
            "therapeutic_area": None
        }
        
        # Try to extract product name from title
        # Common patterns: "Class X Medicines Recall: [Product Name]"
        product_match = re.search(r"Recall:\s*([^(\[]+)", title)
        if product_match:
            details["product_name"] = product_match.group(1).strip()
        
        # Extract batch numbers (common patterns)
        batch_patterns = [
            r"Batch(?:es)?[:\s]+([A-Z0-9, ]+)",
            r"Lot(?:s)?[:\s]+([A-Z0-9, ]+)",
            r"Batch Number(?:s)?[:\s]+([A-Z0-9, ]+)"
        ]
        
        text_to_search = f"{title} {description} {body}"
        for pattern in batch_patterns:
            match = re.search(pattern, text_to_search, re.IGNORECASE)
            if match:
                details["batch_numbers"] = match.group(1).strip()
                break
        
        # Extract expiry dates
        expiry_patterns = [
            r"Expiry[:\s]+([0-9/\-A-Za-z ]+)",
            r"Exp(?:iry)? Date[:\s]+([0-9/\-A-Za-z ]+)",
            r"Use [Bb]y[:\s]+([0-9/\-A-Za-z ]+)"
        ]
        
        for pattern in expiry_patterns:
            match = re.search(pattern, text_to_search, re.IGNORECASE)
            if match:
                details["expiry_dates"] = match.group(1).strip()
                break
        
        # Try to identify therapeutic area from common keywords
        therapeutic_keywords = {
            "cardiovascular": ["heart", "cardiac", "blood pressure", "hypertension", "ace inhibitor", "beta blocker"],
            "diabetes": ["diabetes", "insulin", "metformin", "glucose", "blood sugar"],
            "respiratory": ["asthma", "copd", "inhaler", "respiratory", "broncho"],
            "mental health": ["antidepressant", "anxiety", "psychiatric", "mental health", "ssri"],
            "pain management": ["painkiller", "analgesic", "opioid", "nsaid", "pain relief"],
            "antibiotics": ["antibiotic", "infection", "antimicrobial", "penicillin"],
        }
        
        text_lower = text_to_search.lower()
        for area, keywords in therapeutic_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                details["therapeutic_area"] = area
                break
        
        return details
    
    def generate_emis_search_terms(self, alert_data: Dict[str, Any]) -> str:
        """
        Generate suggested EMIS search terms based on alert
        
        Returns:
            Suggested search query string for EMIS
        """
        product_name = alert_data.get("product_name", "")
        active_ingredient = alert_data.get("active_ingredient", "")
        batch_numbers = alert_data.get("batch_numbers", "")
        
        search_terms = []
        
        if product_name:
            # Clean product name for search
            clean_name = re.sub(r"[^\w\s]", "", product_name)
            search_terms.append(clean_name)
        
        if active_ingredient and active_ingredient != product_name:
            search_terms.append(active_ingredient)
        
        if batch_numbers:
            # Add batch number as separate search if it's short enough
            if len(batch_numbers) < 20:
                search_terms.append(f"batch:{batch_numbers}")
        
        return " OR ".join(search_terms) if search_terms else "Check prescription records"
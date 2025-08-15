from typing import Dict, Tuple, List, Any
import re
from ..core.config import settings
from ..models.alert import Severity, Priority
import logging

logger = logging.getLogger(__name__)


class TriageService:
    """Service for triaging alerts for GP relevance"""
    
    # Alert categories based on update_alert_sorting.md
    ALERT_CATEGORIES = {
        'MEDICINES_RECALL': 'Medicines Recall',
        'NATPSA': 'National Patient Safety Alert',
        'DEVICE_ALERT': 'Medical Device Alert',
        'SAFETY_ROUNDUP': 'MHRA Safety Roundup',
        'DSU': 'Drug Safety Update',
        'SUPPLY_ALERT': 'Medicine Supply Alert',
        'SSP': 'Serious Shortage Protocol'
    }
    
    def __init__(self):
        self.relevant_specialties = settings.RELEVANT_SPECIALTIES
        self.allow_list = []  # Can be populated from config
        self.deny_list = []   # Can be populated from config
    
    def triage_alert(self, alert_data: Dict[str, Any]) -> Tuple[str, str, str, str, str]:
        """
        Triage an alert for GP relevance
        
        Returns:
            Tuple of (relevance, reason, severity, priority, category)
            relevance: Always "Manual-Review" for manual triage
            reason: Explanation for the classification
            severity: Critical/High/Medium/Low
            priority: P1-P4
            category: One of the 8 defined alert categories
        """
        title = (alert_data.get("title") or "").lower()
        message_type = (alert_data.get("message_type") or "").lower()
        alert_type = (alert_data.get("alert_type") or "").lower()
        
        # Detect alert category
        category = self._detect_alert_category(title, message_type, alert_type)
        
        # Determine severity and priority based on category
        severity, priority = self._determine_severity_priority(alert_type, message_type, category)
        
        # Always return Manual-Review to allow pharmacist to decide
        return "Manual-Review", "Pending pharmacist review", severity, priority, category
    
    def _detect_alert_category(self, title: str, message_type: str, alert_type: str) -> str:
        """
        Detect which of the 8 alert categories this belongs to
        
        Returns:
            Alert category string
        """
        title_lower = title.lower() if title else ""
        message_lower = message_type.lower() if message_type else ""
        alert_lower = alert_type.lower() if alert_type else ""
        
        # Check for National Patient Safety Alert (highest priority)
        if "national patient safety" in title_lower or "natpsa" in title_lower:
            return self.ALERT_CATEGORIES['NATPSA']
        
        # Check for Medicines Recalls (Class 1-4)
        if "class 1" in title_lower or "class 2" in title_lower or "class 3" in title_lower or "class 4" in title_lower:
            return self.ALERT_CATEGORIES['MEDICINES_RECALL']
        if "medicines recall" in title_lower or "medicines defect" in title_lower:
            return self.ALERT_CATEGORIES['MEDICINES_RECALL']
        
        # Check for Medical Device Alerts (FSN/DSI)
        if "field safety notice" in title_lower or "fsn" in alert_lower:
            return self.ALERT_CATEGORIES['DEVICE_ALERT']
        if "device safety information" in title_lower or "dsi" in title_lower:
            return self.ALERT_CATEGORIES['DEVICE_ALERT']
        if "device-safety-information" in alert_lower:
            return self.ALERT_CATEGORIES['DEVICE_ALERT']
        
        # Check for MHRA Safety Roundup
        if "safety roundup" in title_lower or "mhra safety roundup" in message_lower:
            return self.ALERT_CATEGORIES['SAFETY_ROUNDUP']
        
        # Check for Drug Safety Update
        if "drug safety update" in title_lower or "dsu" in title_lower:
            return self.ALERT_CATEGORIES['DSU']
        if "drug_safety_update" in alert_lower:
            return self.ALERT_CATEGORIES['DSU']
        
        # Check for Supply Alerts (MSN/SDA)
        if "supply" in title_lower or "shortage" in title_lower:
            return self.ALERT_CATEGORIES['SUPPLY_ALERT']
        if "msn" in title_lower or "sda" in title_lower:
            return self.ALERT_CATEGORIES['SUPPLY_ALERT']
        
        # Check for Serious Shortage Protocols
        if "serious shortage protocol" in title_lower or "ssp" in title_lower:
            return self.ALERT_CATEGORIES['SSP']
        
        # Default to most appropriate based on message type
        if "medical_safety_alert" in alert_lower:
            return self.ALERT_CATEGORIES['MEDICINES_RECALL']
        
        # Default to Medical Device Alert for uncategorized items
        return self.ALERT_CATEGORIES['DEVICE_ALERT']  # Default category
    
    def _determine_severity_priority(self, alert_type: str, message_type: str, category: str) -> Tuple[str, str]:
        """
        Determine severity and priority based on alert type and category
        
        Returns:
            Tuple of (severity, priority)
        """
        alert_type_lower = alert_type.lower() if alert_type else ""
        message_type_lower = message_type.lower() if message_type else ""
        
        # Priority hierarchy based on update_alert_sorting.md
        # P1-Immediate: NatPSAs, Class 1 Recalls
        # P2-Within 48h: Class 2 Recalls, Active SSPs
        # P3-Within 1 week: Class 3 Recalls, FSNs/DSIs, DSU, Safety Roundup, MSNs/SDAs
        # P4-Routine: Class 4 Recalls, general updates
        
        # National Patient Safety Alerts - highest priority
        if category == self.ALERT_CATEGORIES['NATPSA']:
            return "Critical", "P1-Immediate"
        
        # Class 1 recalls - most serious
        if "class 1" in alert_type_lower or "class 1" in message_type_lower:
            return "Critical", "P1-Immediate"
        
        # Class 2 recalls - serious
        elif "class 2" in alert_type_lower or "class 2" in message_type_lower:
            return "High", "P2-Within 48h"
        
        # Serious Shortage Protocols - urgent when active
        elif category == self.ALERT_CATEGORIES['SSP']:
            return "High", "P2-Within 48h"
        
        # Class 3 recalls
        elif "class 3" in alert_type_lower or "class 3" in message_type_lower:
            return "Medium", "P3-Within 1 week"
        
        # Medical Device Alerts (FSN/DSI)
        elif category == self.ALERT_CATEGORIES['DEVICE_ALERT']:
            return "Medium", "P3-Within 1 week"
        
        # Drug Safety Updates and Safety Roundup
        elif category in [self.ALERT_CATEGORIES['DSU'], self.ALERT_CATEGORIES['SAFETY_ROUNDUP']]:
            return "Medium", "P3-Within 1 week"
        
        # Supply alerts
        elif category == self.ALERT_CATEGORIES['SUPPLY_ALERT']:
            return "Medium", "P3-Within 1 week"
        
        # Class 4 recalls or general alerts
        elif "class 4" in alert_type_lower or "class 4" in message_type_lower:
            return "Low", "P4-Routine"
        
        # Default for unclassified
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
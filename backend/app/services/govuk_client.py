import httpx
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import logging
from tenacity import retry, stop_after_attempt, wait_exponential
from ..core.config import settings

logger = logging.getLogger(__name__)


class GovUKClient:
    """Client for interacting with GOV.UK Search and Content APIs"""
    
    def __init__(self):
        self.search_api = settings.GOVUK_SEARCH_API
        self.content_api = settings.GOVUK_CONTENT_API
        self.org_filter = settings.ORG_FILTER
        
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def search_alerts(
        self,
        document_type: str = "medical_safety_alert",
        start: int = 0,
        count: int = 100,
        order: str = "-public_timestamp"
    ) -> Dict[str, Any]:
        """
        Search for alerts using GOV.UK Search API
        
        Args:
            document_type: Type of document to search for
            start: Pagination offset
            count: Number of results to return
            order: Sort order for results
        """
        params = {
            "filter_content_store_document_type": document_type,
            "filter_organisations": self.org_filter,
            "order": order,
            "count": count,
            "start": start,
            "fields": "title,link,public_timestamp,description,content_id"
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(self.search_api, params=params)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Error searching GOV.UK: {e}")
                raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def get_content(self, path: str) -> Dict[str, Any]:
        """
        Get detailed content for a specific alert
        
        Args:
            path: The path to the content (from search results link)
        """
        # Remove domain if present
        if path.startswith("http"):
            path = path.replace("https://www.gov.uk", "").replace("http://www.gov.uk", "")
        
        url = f"{self.content_api}{path}"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(url)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Error fetching content from {url}: {e}")
                raise
    
    async def fetch_recent_alerts(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Fetch alerts from the last N days
        
        Args:
            days: Number of days to look back
        """
        all_results = []
        
        # Fetch medical safety alerts
        alerts = await self.search_alerts("medical_safety_alert")
        all_results.extend(alerts.get("results", []))
        
        # Also fetch drug safety updates
        updates = await self.search_alerts("drug_safety_update")
        all_results.extend(updates.get("results", []))
        
        # Filter by date if needed
        cutoff_date = datetime.now() - timedelta(days=days)
        filtered = []
        
        for result in all_results:
            pub_date = self._parse_date(result.get("public_timestamp"))
            if pub_date and pub_date >= cutoff_date:
                filtered.append(result)
        
        return filtered
    
    async def fetch_all_alerts(
        self,
        document_type: str = "medical_safety_alert",
        since_date: Optional[datetime] = None,
        max_results: int = 10000
    ) -> List[Dict[str, Any]]:
        """
        Fetch all alerts with pagination
        
        Args:
            document_type: Type of document to fetch
            since_date: Only fetch alerts after this date
            max_results: Maximum number of results to fetch
        """
        all_results = []
        start = 0
        count = 100
        
        while start < max_results:
            batch = await self.search_alerts(
                document_type=document_type,
                start=start,
                count=min(count, max_results - start)
            )
            
            results = batch.get("results", [])
            if not results:
                break
            
            # Filter by date if specified
            if since_date:
                for result in results:
                    pub_date = self._parse_date(result.get("public_timestamp"))
                    if pub_date and pub_date >= since_date:
                        all_results.append(result)
                    elif pub_date and pub_date < since_date:
                        # Results are ordered by date desc, so we can stop
                        return all_results
            else:
                all_results.extend(results)
            
            start += count
            
            # Check if we've fetched all available results
            total = batch.get("total", 0)
            if start >= total:
                break
        
        return all_results
    
    async def enrich_alert(self, alert: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich an alert with detailed content from the Content API
        
        Args:
            alert: Alert from search results
        """
        link = alert.get("link", "")
        if not link:
            return alert
        
        try:
            content = await self.get_content(link)
            
            # Extract relevant fields
            details = content.get("details", {})
            
            alert["message_type"] = details.get("metadata", {}).get("message_type")
            alert["medical_specialties"] = details.get("metadata", {}).get("medical_specialism", [])
            alert["issued_date"] = details.get("metadata", {}).get("issue_date")
            alert["alert_type"] = details.get("metadata", {}).get("alert_type")
            
            # Extract body content if needed
            alert["body"] = details.get("body")
            alert["attachments"] = details.get("attachments", [])
            
            return alert
        except Exception as e:
            logger.warning(f"Could not enrich alert {link}: {e}")
            return alert
    
    @staticmethod
    def _parse_date(date_str: str) -> Optional[datetime]:
        """Parse date string from GOV.UK API"""
        if not date_str:
            return None
        
        try:
            # Handle ISO format with timezone
            if "T" in date_str:
                return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            else:
                return datetime.strptime(date_str, "%Y-%m-%d")
        except (ValueError, AttributeError):
            logger.warning(f"Could not parse date: {date_str}")
            return None
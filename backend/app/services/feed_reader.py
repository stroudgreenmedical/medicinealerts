"""
RSS/ATOM Feed Reader Service for additional alert sources
"""

import feedparser
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import json
from sqlalchemy.orm import Session

from ..models.alert import Alert
from ..core.database import SessionLocal
from .alert_processor import AlertProcessor
from .triage import TriageService

logger = logging.getLogger(__name__)


class FeedReaderService:
    """Service for reading RSS/ATOM feeds from various alert sources"""
    
    # Feed URLs for different sources
    FEEDS = {
        'GOV_UK_DRUG_DEVICE': {
            'url': 'https://www.gov.uk/drug-device-alerts.atom',
            'source': 'GOV.UK ATOM',
            'type': 'atom'
        },
        # Future feeds can be added here
        # 'NHS_ENGLAND_SAFETY': {
        #     'url': 'https://www.england.nhs.uk/patient-safety-alerts.atom',
        #     'source': 'NHS England',
        #     'type': 'atom'
        # }
    }
    
    def __init__(self):
        self.alert_processor = AlertProcessor()
        self.triage_service = TriageService()
    
    async def fetch_feed(self, feed_config: Dict[str, str]) -> Optional[Dict]:
        """
        Fetch and parse an RSS/ATOM feed
        
        Args:
            feed_config: Configuration dict with url, source, and type
            
        Returns:
            Parsed feed data or None if error
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(feed_config['url'])
                response.raise_for_status()
                
                # Parse the feed
                feed = feedparser.parse(response.text)
                
                if feed.bozo:
                    logger.warning(f"Feed parsing issue for {feed_config['url']}: {feed.bozo_exception}")
                
                return feed
                
        except Exception as e:
            logger.error(f"Error fetching feed {feed_config['url']}: {e}")
            return None
    
    def parse_atom_entry(self, entry: Dict, source: str) -> Dict[str, Any]:
        """
        Parse an ATOM feed entry into alert data format
        
        Args:
            entry: Feed entry from feedparser
            source: Source identifier
            
        Returns:
            Alert data dictionary
        """
        # Extract key fields from ATOM entry
        alert_data = {
            'content_id': entry.get('id', ''),
            'title': entry.get('title', ''),
            'link': entry.get('link', ''),
            'public_timestamp': entry.get('published', entry.get('updated', '')),
            'description': entry.get('summary', ''),
            'data_source': source,
            'source_urls': json.dumps([entry.get('link', '')])
        }
        
        # Try to extract additional metadata from content
        if 'content' in entry:
            content = entry['content'][0] if isinstance(entry['content'], list) else entry['content']
            alert_data['body'] = content.get('value', '')
        
        # Parse categories/tags if available
        if 'tags' in entry:
            tags = [tag.get('term', '') for tag in entry.tags]
            alert_data['tags'] = tags
        
        return alert_data
    
    async def process_feed_entry(self, entry_data: Dict[str, Any], db: Session) -> Optional[Alert]:
        """
        Process a feed entry and create/update alert
        
        Args:
            entry_data: Parsed entry data
            db: Database session
            
        Returns:
            Alert object if processed, None otherwise
        """
        try:
            content_id = entry_data.get('content_id')
            if not content_id:
                logger.warning("Feed entry missing content_id")
                return None
            
            # Check for existing alert
            existing = db.query(Alert).filter_by(content_id=content_id).first()
            
            if existing:
                # Check if this is from a different source
                if existing.data_source != entry_data.get('data_source'):
                    # Update source URLs to include both sources
                    existing_urls = json.loads(existing.source_urls or '[]')
                    new_urls = json.loads(entry_data.get('source_urls', '[]'))
                    all_urls = list(set(existing_urls + new_urls))
                    existing.source_urls = json.dumps(all_urls)
                    
                    logger.info(f"Updated alert {content_id} with additional source")
                
                return existing
            
            # Create new alert
            alert = Alert()
            
            # Basic fields
            alert.content_id = content_id
            alert.title = entry_data.get('title', '')
            alert.url = entry_data.get('link', '')
            alert.alert_id = f"FEED-{content_id[:20]}"  # Generate ID from content_id
            
            # Parse dates
            pub_date = entry_data.get('public_timestamp')
            if pub_date:
                try:
                    alert.published_date = datetime.fromisoformat(pub_date.replace('Z', '+00:00'))
                except:
                    pass
            
            # Set source tracking
            alert.data_source = entry_data.get('data_source', 'RSS Feed')
            alert.source_urls = entry_data.get('source_urls', '[]')
            
            # Perform triage
            relevance, reason, severity, priority, category = self.triage_service.triage_alert(entry_data)
            alert.auto_relevance = relevance
            alert.relevance_reason = reason
            alert.severity = severity
            alert.priority = priority
            alert.alert_category = category
            
            # Set status based on relevance
            if relevance == "Auto-Relevant":
                alert.status = "Action Required"
                alert.final_relevance = "Relevant"
            elif relevance == "Auto-Not-Relevant":
                alert.status = "Closed"
                alert.final_relevance = "Not-Relevant"
            else:
                alert.status = "New"
            
            # Extract product details if possible
            product_details = self.triage_service.extract_product_details(entry_data)
            alert.product_name = product_details.get("product_name")
            alert.batch_numbers = product_details.get("batch_numbers")
            alert.manufacturer = product_details.get("manufacturer")
            
            # Add to database
            db.add(alert)
            
            logger.info(f"Created alert from feed: {alert.title} [{alert.alert_category}]")
            return alert
            
        except Exception as e:
            logger.error(f"Error processing feed entry: {e}")
            return None
    
    async def poll_all_feeds(self) -> Dict[str, int]:
        """
        Poll all configured feeds and process new entries
        
        Returns:
            Dictionary with counts of new alerts per feed
        """
        results = {}
        
        db = SessionLocal()
        try:
            for feed_name, feed_config in self.FEEDS.items():
                logger.info(f"Polling feed: {feed_name}")
                
                feed = await self.fetch_feed(feed_config)
                if not feed:
                    results[feed_name] = 0
                    continue
                
                new_count = 0
                for entry in feed.entries[:50]:  # Process max 50 entries
                    entry_data = self.parse_atom_entry(entry, feed_config['source'])
                    alert = await self.process_feed_entry(entry_data, db)
                    if alert:
                        new_count += 1
                
                db.commit()
                results[feed_name] = new_count
                logger.info(f"Processed {new_count} entries from {feed_name}")
            
        finally:
            db.close()
        
        return results
    
    async def check_feed_health(self) -> Dict[str, bool]:
        """
        Check if feeds are accessible
        
        Returns:
            Dictionary with feed health status
        """
        health = {}
        
        for feed_name, feed_config in self.FEEDS.items():
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.head(feed_config['url'])
                    health[feed_name] = response.status_code == 200
            except:
                health[feed_name] = False
        
        return health
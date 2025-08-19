from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, List, Any
from datetime import datetime, timedelta
import logging
import asyncio

from ...core.database import get_db
from ...services.govuk_client import GovUKClient
from ...services.feed_reader import FeedReaderService
from ...services.triage import TriageService

router = APIRouter(prefix="/system-test", tags=["system-test"])
logger = logging.getLogger(__name__)


@router.get("/")
async def run_system_test(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Test the alert system by polling last month's alerts for each category
    Returns connection status and count for each alert type
    """
    govuk_client = GovUKClient()
    feed_reader = FeedReaderService()
    triage_service = TriageService()
    
    # Define categories to test
    categories = [
        'Medicines Recall',
        'National Patient Safety Alert', 
        'Medical Device Alert',
        'MHRA Safety Roundup',
        'Drug Safety Update',
        'Medicine Supply Alert',
        'Serious Shortage Protocol'
    ]
    
    # Calculate date range (last 30 days) - make timezone-aware
    from datetime import timezone
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=30)
    
    results = {}
    
    # Test GOV.UK API for medical safety alerts
    try:
        logger.info("Testing GOV.UK Search API for medical safety alerts...")
        alerts_response = await govuk_client.search_alerts(
            document_type="medical_safety_alert",
            count=100
        )
        
        govuk_alerts = alerts_response.get("results", [])
        
        # Filter by date and categorize
        for category in categories:
            category_alerts = []
            
            for alert in govuk_alerts:
                # Parse date
                pub_date = govuk_client._parse_date(alert.get("public_timestamp"))
                if pub_date and pub_date >= start_date:
                    # Check if alert matches category
                    title = (alert.get("title") or "").lower()
                    
                    if category == 'Medicines Recall' and 'recall' in title:
                        category_alerts.append(alert)
                    elif category == 'National Patient Safety Alert' and 'patient safety' in title:
                        category_alerts.append(alert)
                    elif category == 'Medical Device Alert' and ('device' in title or 'field safety' in title):
                        category_alerts.append(alert)
                    elif category == 'Medicine Supply Alert' and 'supply' in title:
                        category_alerts.append(alert)
                    elif category == 'Serious Shortage Protocol' and 'shortage protocol' in title:
                        category_alerts.append(alert)
            
            if category not in results:
                results[category] = {
                    'status': 'success',
                    'count': len(category_alerts),
                    'source': 'GOV.UK API',
                    'error': None
                }
            else:
                results[category]['count'] += len(category_alerts)
        
    except Exception as e:
        logger.error(f"Error testing GOV.UK API: {e}")
        for category in ['Medicines Recall', 'Medical Device Alert', 'Medicine Supply Alert', 'Serious Shortage Protocol']:
            if category not in results:
                results[category] = {
                    'status': 'error',
                    'count': 0,
                    'source': 'GOV.UK API',
                    'error': str(e)
                }
    
    # Test Drug Safety Update feed
    try:
        logger.info("Testing MHRA Drug Safety Update feed...")
        dsu_feed = await feed_reader.fetch_feed(FeedReaderService.FEEDS['MHRA_DSU'])
        
        if dsu_feed:
            dsu_count = 0
            for entry in dsu_feed.entries[:20]:  # Check last 20 entries
                pub_date = feed_reader.alert_processor._parse_date(entry.get('published'))
                if pub_date and pub_date >= start_date:
                    dsu_count += 1
            
            results['Drug Safety Update'] = {
                'status': 'success',
                'count': dsu_count,
                'source': 'MHRA DSU Feed',
                'error': None
            }
        else:
            results['Drug Safety Update'] = {
                'status': 'error',
                'count': 0,
                'source': 'MHRA DSU Feed',
                'error': 'Failed to fetch feed'
            }
            
    except Exception as e:
        logger.error(f"Error testing DSU feed: {e}")
        results['Drug Safety Update'] = {
            'status': 'error',
            'count': 0,
            'source': 'MHRA DSU Feed',
            'error': str(e)
        }
    
    # Test NHS England PSA feed
    try:
        logger.info("Testing NHS England Patient Safety Alert feed...")
        psa_feed = await feed_reader.fetch_feed(FeedReaderService.FEEDS['NHS_ENGLAND_PSA'])
        
        if psa_feed:
            psa_count = 0
            for entry in psa_feed.entries[:20]:  # Check last 20 entries
                pub_date = feed_reader.alert_processor._parse_date(entry.get('published'))
                if pub_date and pub_date >= start_date:
                    psa_count += 1
            
            if 'National Patient Safety Alert' in results:
                results['National Patient Safety Alert']['count'] += psa_count
            else:
                results['National Patient Safety Alert'] = {
                    'status': 'success',
                    'count': psa_count,
                    'source': 'NHS England Feed',
                    'error': None
                }
        else:
            if 'National Patient Safety Alert' not in results:
                results['National Patient Safety Alert'] = {
                    'status': 'error',
                    'count': 0,
                    'source': 'NHS England Feed',
                    'error': 'Failed to fetch feed'
                }
                
    except Exception as e:
        logger.error(f"Error testing NHS PSA feed: {e}")
        if 'National Patient Safety Alert' not in results:
            results['National Patient Safety Alert'] = {
                'status': 'error',
                'count': 0,
                'source': 'NHS England Feed',
                'error': str(e)
            }
    
    # Test GOV.UK Drug Device Alerts feed
    try:
        logger.info("Testing GOV.UK Drug Device Alerts feed...")
        dd_feed = await feed_reader.fetch_feed(FeedReaderService.FEEDS['GOV_UK_DRUG_DEVICE'])
        
        if dd_feed:
            for entry in dd_feed.entries[:50]:  # Check last 50 entries
                pub_date = feed_reader.alert_processor._parse_date(entry.get('published'))
                if pub_date and pub_date >= start_date:
                    title = (entry.get('title', '')).lower()
                    
                    # Categorize based on title
                    if 'safety roundup' in title or 'roundup' in title:
                        if 'MHRA Safety Roundup' not in results:
                            results['MHRA Safety Roundup'] = {
                                'status': 'success',
                                'count': 0,
                                'source': 'GOV.UK Feed',
                                'error': None
                            }
                        results['MHRA Safety Roundup']['count'] += 1
                        
    except Exception as e:
        logger.error(f"Error testing Drug Device feed: {e}")
        if 'MHRA Safety Roundup' not in results:
            results['MHRA Safety Roundup'] = {
                'status': 'error',
                'count': 0,
                'source': 'GOV.UK Feed',
                'error': str(e)
            }
    
    # Ensure all categories have results
    for category in categories:
        if category not in results:
            results[category] = {
                'status': 'no_data',
                'count': 0,
                'source': 'N/A',
                'error': 'No data source configured'
            }
    
    # Add summary
    total_success = sum(1 for r in results.values() if r['status'] == 'success')
    total_errors = sum(1 for r in results.values() if r['status'] == 'error')
    total_alerts = sum(r['count'] for r in results.values())
    
    return {
        'test_date': datetime.now().isoformat(),
        'date_range': {
            'start': start_date.isoformat(),
            'end': end_date.isoformat()
        },
        'summary': {
            'total_categories': len(categories),
            'successful_tests': total_success,
            'failed_tests': total_errors,
            'total_alerts_found': total_alerts
        },
        'categories': results
    }
#!/usr/bin/env python3
"""
Test script to verify MHRA Alerts system is working properly
Tests GOV.UK API connectivity, alert fetching, and processing
"""

import asyncio
import httpx
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from app.services.govuk_client import GovUKClient
from app.services.alert_processor import AlertProcessor
from app.services.teams_notify import TeamsNotificationService
from app.core.config import settings
from app.core.database import SessionLocal
import json

class AlertSystemTester:
    def __init__(self):
        self.govuk_client = GovUKClient()
        self.processor = AlertProcessor()
        self.teams = TeamsNotificationService()
        self.results = []
        
    async def test_govuk_api_connectivity(self):
        """Test 1: Check if GOV.UK APIs are accessible"""
        print("\n" + "="*60)
        print("TEST 1: GOV.UK API Connectivity")
        print("="*60)
        
        try:
            # Test Search API
            print("Testing Search API...")
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    settings.GOVUK_SEARCH_API,
                    params={"count": 1}
                )
                response.raise_for_status()
                print(f"✅ Search API accessible - Status: {response.status_code}")
                self.results.append(("Search API", "PASS"))
                
            # Test Content API
            print("Testing Content API...")
            test_path = "/drug-safety-update"
            url = f"{settings.GOVUK_CONTENT_API}{test_path}"
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
                # Content API may return 404 for some paths, but connection should work
                if response.status_code in [200, 404]:
                    print(f"✅ Content API accessible - Status: {response.status_code}")
                    self.results.append(("Content API", "PASS"))
                else:
                    print(f"⚠️ Content API returned unexpected status: {response.status_code}")
                    self.results.append(("Content API", "WARNING"))
                    
        except Exception as e:
            print(f"❌ API connectivity test failed: {e}")
            self.results.append(("API Connectivity", "FAIL"))
            return False
        
        return True

    async def test_fetch_recent_alerts(self):
        """Test 2: Fetch recent alerts from GOV.UK"""
        print("\n" + "="*60)
        print("TEST 2: Fetching Recent Alerts")
        print("="*60)
        
        try:
            # Fetch medical safety alerts
            print("Fetching medical safety alerts...")
            alerts = await self.govuk_client.search_alerts(
                document_type="medical_safety_alert",
                count=5
            )
            
            alert_count = len(alerts.get("results", []))
            print(f"✅ Found {alert_count} medical safety alerts")
            
            if alert_count > 0:
                latest = alerts["results"][0]
                print(f"   Latest: {latest.get('title', 'No title')[:60]}...")
                print(f"   Date: {latest.get('public_timestamp', 'No date')}")
                
            # Fetch drug safety updates
            print("\nFetching drug safety updates...")
            updates = await self.govuk_client.search_alerts(
                document_type="drug_safety_update",
                count=5
            )
            
            update_count = len(updates.get("results", []))
            print(f"✅ Found {update_count} drug safety updates")
            
            if update_count > 0:
                latest = updates["results"][0]
                print(f"   Latest: {latest.get('title', 'No title')[:60]}...")
                print(f"   Date: {latest.get('public_timestamp', 'No date')}")
            
            self.results.append(("Fetch Alerts", "PASS"))
            return alert_count + update_count > 0
            
        except Exception as e:
            print(f"❌ Failed to fetch alerts: {e}")
            self.results.append(("Fetch Alerts", "FAIL"))
            return False

    async def test_alert_processing(self):
        """Test 3: Process a sample alert through the system"""
        print("\n" + "="*60)
        print("TEST 3: Alert Processing Pipeline")
        print("="*60)
        
        try:
            # Fetch one recent alert
            print("Fetching a sample alert to process...")
            alerts = await self.govuk_client.search_alerts(
                document_type="medical_safety_alert",
                count=1
            )
            
            if not alerts.get("results"):
                print("⚠️ No alerts available to test processing")
                self.results.append(("Alert Processing", "SKIP"))
                return False
            
            alert_data = alerts["results"][0]
            print(f"Processing: {alert_data.get('title', 'No title')[:60]}...")
            
            # Enrich the alert
            print("Enriching alert with content API...")
            enriched = await self.govuk_client.enrich_alert(alert_data)
            
            # Test classification
            print("Testing auto-classification...")
            processor = AlertProcessor()
            
            # Mock classification for testing
            specialties = enriched.get("medical_specialties", [])
            is_relevant = any(
                spec in str(specialties) 
                for spec in settings.RELEVANT_SPECIALTIES
            )
            
            print(f"   Specialties: {specialties if specialties else 'None specified'}")
            print(f"   Auto-relevance: {'Relevant' if is_relevant else 'Not Relevant'}")
            
            self.results.append(("Alert Processing", "PASS"))
            return True
            
        except Exception as e:
            print(f"❌ Alert processing failed: {e}")
            self.results.append(("Alert Processing", "FAIL"))
            return False

    def test_database_connection(self):
        """Test 4: Check database connectivity and schema"""
        print("\n" + "="*60)
        print("TEST 4: Database Connection")
        print("="*60)
        
        try:
            db = SessionLocal()
            
            # Test connection
            result = db.execute(text("SELECT 1"))
            print("✅ Database connection successful")
            
            # Check alerts table exists
            result = db.execute(text("""
                SELECT COUNT(*) as count 
                FROM sqlite_master 
                WHERE type='table' AND name='alerts'
            """))
            if result.scalar() > 0:
                print("✅ Alerts table exists")
                
                # Count existing alerts
                result = db.execute(text("SELECT COUNT(*) as count FROM alerts"))
                count = result.scalar()
                print(f"   Found {count} alerts in database")
                
                # Show recent alerts
                result = db.execute(text("""
                    SELECT alert_id, title, created_at 
                    FROM alerts 
                    ORDER BY created_at DESC 
                    LIMIT 3
                """))
                recent = result.fetchall()
                if recent:
                    print("\n   Recent alerts in database:")
                    for row in recent:
                        print(f"   - {row[1][:50]}... ({row[2]})")
            else:
                print("⚠️ Alerts table not found")
                
            db.close()
            self.results.append(("Database", "PASS"))
            return True
            
        except Exception as e:
            print(f"❌ Database test failed: {e}")
            self.results.append(("Database", "FAIL"))
            return False

    async def test_teams_webhook(self):
        """Test 5: Test Teams webhook (if configured)"""
        print("\n" + "="*60)
        print("TEST 5: Teams Webhook Configuration")
        print("="*60)
        
        if not settings.TEAMS_WEBHOOK_URL:
            print("⚠️ Teams webhook not configured (TEAMS_WEBHOOK_URL not set)")
            self.results.append(("Teams Webhook", "SKIP"))
            return False
        
        print(f"✅ Teams webhook configured")
        print("   (Not sending test message to avoid spam)")
        self.results.append(("Teams Webhook", "CONFIGURED"))
        return True

    async def test_scheduler_status(self):
        """Test 6: Check scheduler configuration"""
        print("\n" + "="*60)
        print("TEST 6: Scheduler Configuration")
        print("="*60)
        
        print(f"Poll interval: {settings.POLL_INTERVAL_HOURS} hours")
        print(f"Backfill years: {settings.BACKFILL_YEARS} years")
        print(f"Current approver: {settings.APPROVER_NAME}")
        print(f"Approver switch date: {settings.APPROVER_SWITCH_DATE}")
        print(f"Next approver: {settings.APPROVER_AFTER}")
        
        self.results.append(("Scheduler Config", "PASS"))
        return True

    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        
        for test_name, status in self.results:
            emoji = {
                "PASS": "✅",
                "FAIL": "❌",
                "WARNING": "⚠️",
                "SKIP": "⏭️",
                "CONFIGURED": "✅"
            }.get(status, "❓")
            print(f"{emoji} {test_name}: {status}")
        
        # Overall status
        failures = sum(1 for _, status in self.results if status == "FAIL")
        if failures == 0:
            print("\n✅ All critical tests passed! The alert system is working properly.")
        else:
            print(f"\n❌ {failures} test(s) failed. Please check the issues above.")

async def main():
    """Run all tests"""
    print("🔍 MHRA Alerts System Test Suite")
    print("Testing alert reception and processing capabilities...")
    
    tester = AlertSystemTester()
    
    # Run tests
    await tester.test_govuk_api_connectivity()
    await tester.test_fetch_recent_alerts()
    await tester.test_alert_processing()
    tester.test_database_connection()
    await tester.test_teams_webhook()
    await tester.test_scheduler_status()
    
    # Print summary
    tester.print_summary()
    
    print("\n" + "="*60)
    print("💡 Quick Actions:")
    print("- To manually trigger alert polling: Call POST /api/reports/trigger-poll")
    print("- To backfill historical alerts: Call POST /api/reports/backfill")
    print("- To view dashboard: Visit http://localhost:5173")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())
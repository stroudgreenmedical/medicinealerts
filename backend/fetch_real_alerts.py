#!/usr/bin/env python3
"""
Script to manually fetch real alerts from GOV.UK and add them to the database
"""

import asyncio
import sys
from datetime import datetime, timedelta
from app.services.scheduler import SchedulerService
from app.core.database import SessionLocal
from sqlalchemy import text
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    """Fetch real alerts from GOV.UK"""
    print("=" * 60)
    print("FETCHING REAL ALERTS FROM GOV.UK")
    print("=" * 60)
    
    # Check current database state
    db = SessionLocal()
    try:
        result = db.execute(text("SELECT COUNT(*) FROM alerts"))
        current_count = result.scalar()
        print(f"\nCurrent alerts in database: {current_count}")
        
        # Show sample of existing alerts
        result = db.execute(text("""
            SELECT alert_id, title 
            FROM alerts 
            ORDER BY created_at DESC 
            LIMIT 3
        """))
        print("\nSample of existing alerts:")
        for row in result.fetchall():
            print(f"  - {row[0]}: {row[1][:50]}...")
            
    finally:
        db.close()
    
    # Ask user to proceed
    print("\n" + "=" * 60)
    response = input("Do you want to fetch real alerts from GOV.UK? (y/n): ")
    if response.lower() != 'y':
        print("Cancelled.")
        return
    
    # Initialize scheduler service
    scheduler = SchedulerService()
    
    # Option 1: Poll for recent alerts (last 7 days)
    print("\nOption 1: Fetch recent alerts (last 7 days)")
    print("Option 2: Backfill historical alerts (last 1 year)")
    choice = input("Choose option (1 or 2): ")
    
    try:
        if choice == "1":
            print("\nFetching recent alerts from the last 7 days...")
            await scheduler.poll_for_alerts()
            
        elif choice == "2":
            print("\nBackfilling alerts from the last year...")
            await scheduler.run_backfill(years=1)
            
        else:
            print("Invalid choice")
            return
            
    except Exception as e:
        print(f"\n❌ Error fetching alerts: {e}")
        logger.error(f"Failed to fetch alerts: {e}", exc_info=True)
        return
    
    # Check results
    db = SessionLocal()
    try:
        result = db.execute(text("SELECT COUNT(*) FROM alerts"))
        new_count = result.scalar()
        print(f"\n✅ Complete! New total alerts in database: {new_count}")
        print(f"   Added {new_count - current_count} new alerts")
        
        # Show newly added real alerts
        result = db.execute(text("""
            SELECT alert_id, title, published_date 
            FROM alerts 
            WHERE alert_id NOT LIKE 'MHRA-2024-%'
            ORDER BY created_at DESC 
            LIMIT 5
        """))
        
        real_alerts = result.fetchall()
        if real_alerts:
            print("\nNewly added REAL alerts from GOV.UK:")
            for row in real_alerts:
                print(f"  - {row[0]}: {row[1][:50]}... ({row[2]})")
        else:
            print("\n⚠️ No real alerts found. There may be an issue with fetching.")
            
    finally:
        db.close()
    
    print("\n" + "=" * 60)
    print("You can now check the dashboard at http://localhost:5173")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
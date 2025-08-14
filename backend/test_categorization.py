#!/usr/bin/env python3
"""
Test script to apply new categorization to existing alerts
"""

import sys
from app.services.triage import TriageService
from app.core.database import SessionLocal
from sqlalchemy import text
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Test categorization on existing alerts"""
    print("=" * 60)
    print("TESTING ALERT CATEGORIZATION")
    print("=" * 60)
    
    triage_service = TriageService()
    db = SessionLocal()
    
    try:
        # Get sample alerts from database
        result = db.execute(text("""
            SELECT id, title, message_type, alert_type, govuk_reference 
            FROM alerts 
            WHERE govuk_reference IS NOT NULL
            LIMIT 20
        """))
        
        alerts = result.fetchall()
        print(f"\nTesting categorization on {len(alerts)} alerts:\n")
        
        # Category counters
        categories = {}
        
        for alert in alerts:
            alert_id, title, message_type, alert_type, ref = alert
            
            # Create alert data dict
            alert_data = {
                'title': title or '',
                'message_type': message_type or '',
                'alert_type': alert_type or '',
                'content_id': ref or '',
                'medical_specialties': []
            }
            
            # Get category
            relevance, reason, severity, priority, category = triage_service.triage_alert(alert_data)
            
            # Count categories
            categories[category] = categories.get(category, 0) + 1
            
            # Print result
            print(f"Alert: {title[:60]}...")
            print(f"  Category: {category}")
            print(f"  Priority: {priority}")
            print(f"  Severity: {severity}")
            print("-" * 60)
            
            # Update database with category
            db.execute(text("""
                UPDATE alerts 
                SET alert_category = :category
                WHERE id = :id
            """), {'category': category, 'id': alert_id})
        
        db.commit()
        
        # Print summary
        print("\n" + "=" * 60)
        print("CATEGORY SUMMARY:")
        for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
            print(f"  {cat}: {count}")
        
        # Update all alerts with categories
        print("\nUpdating all alerts with categories...")
        
        # Get all alerts without a category
        result = db.execute(text("""
            SELECT COUNT(*) FROM alerts 
            WHERE alert_category IS NULL
        """))
        uncategorized = result.scalar()
        
        if uncategorized > 0:
            print(f"Found {uncategorized} uncategorized alerts. Categorizing...")
            
            # Process in batches
            batch_size = 100
            offset = 0
            
            while offset < uncategorized:
                result = db.execute(text("""
                    SELECT id, title, message_type, alert_type, content_id
                    FROM alerts 
                    WHERE alert_category IS NULL
                    LIMIT :limit OFFSET :offset
                """), {'limit': batch_size, 'offset': offset})
                
                batch = result.fetchall()
                
                for alert in batch:
                    alert_id, title, message_type, alert_type, content_id = alert
                    
                    alert_data = {
                        'title': title or '',
                        'message_type': message_type or '',
                        'alert_type': alert_type or '',
                        'content_id': content_id or '',
                        'medical_specialties': []
                    }
                    
                    _, _, _, _, category = triage_service.triage_alert(alert_data)
                    
                    db.execute(text("""
                        UPDATE alerts 
                        SET alert_category = :category
                        WHERE id = :id
                    """), {'category': category, 'id': alert_id})
                
                db.commit()
                offset += batch_size
                print(f"  Processed {min(offset, uncategorized)}/{uncategorized}")
        
        # Final category distribution
        result = db.execute(text("""
            SELECT alert_category, COUNT(*) as count
            FROM alerts
            GROUP BY alert_category
            ORDER BY count DESC
        """))
        
        print("\n" + "=" * 60)
        print("FINAL CATEGORY DISTRIBUTION:")
        for row in result.fetchall():
            cat, count = row
            print(f"  {cat or 'None'}: {count}")
        
    finally:
        db.close()
    
    print("\n✅ Categorization complete!")

if __name__ == "__main__":
    main()
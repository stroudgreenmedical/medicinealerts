#!/usr/bin/env python3
"""
Check dashboard stats directly from database
"""

import sqlite3
import json
from pathlib import Path

def get_dashboard_stats():
    """Get dashboard stats directly from database"""
    
    db_path = Path("data/alerts.db")
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return False
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        # Total alerts
        cursor.execute("SELECT COUNT(*) FROM alerts")
        total = cursor.fetchone()[0]
        
        # Status counts
        cursor.execute("SELECT status, COUNT(*) FROM alerts GROUP BY status")
        status_counts = dict(cursor.fetchall())
        
        # Priority counts
        cursor.execute("SELECT priority, COUNT(*) FROM alerts GROUP BY priority")
        priority_counts = dict(cursor.fetchall())
        
        # Alert types
        cursor.execute("SELECT alert_type, COUNT(*) FROM alerts GROUP BY alert_type")
        type_counts = dict(cursor.fetchall())
        
        # New (unreviewed) alerts
        cursor.execute("SELECT COUNT(*) FROM alerts WHERE status = 'New'")
        new_alerts = cursor.fetchone()[0]
        
        # Completed alerts
        cursor.execute("SELECT COUNT(*) FROM alerts WHERE status = 'Completed'")
        completed = cursor.fetchone()[0]
        
        print("\n📊 Dashboard Statistics")
        print("=" * 40)
        print(f"Total Alerts: {total}")
        print(f"New/Unreviewed: {new_alerts}")
        print(f"Completed: {completed}")
        
        print("\n📈 By Status:")
        for status, count in status_counts.items():
            print(f"  {status}: {count}")
        
        print("\n⚡ By Priority:")
        for priority, count in priority_counts.items():
            priority_str = priority if priority else "Unassigned"
            print(f"  {priority_str}: {count}")
        
        print("\n📋 By Type:")
        for alert_type, count in type_counts.items():
            type_str = alert_type if alert_type else "Unknown"
            print(f"  {type_str}: {count}")
        
        # Sample alerts
        print("\n🔍 Sample Alerts (first 5):")
        cursor.execute("""
            SELECT id, title, status, date_first_reviewed, patients_affected_count 
            FROM alerts 
            LIMIT 5
        """)
        for row in cursor.fetchall():
            id, title, status, reviewed, patients = row
            reviewed_str = "Yes" if reviewed else "No"
            patients_str = str(patients) if patients is not None else "N/A"
            print(f"  [{id}] {title[:50]}...")
            print(f"       Status: {status}, Reviewed: {reviewed_str}, Patients: {patients_str}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    get_dashboard_stats()
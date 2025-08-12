#!/usr/bin/env python3
"""
Script to reset all alerts to unreviewed state for testing
"""

import sqlite3
from pathlib import Path

def reset_alerts():
    """Reset all alerts to initial state"""
    
    db_path = Path("data/alerts.db")
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return False
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        # Reset all alerts to NEW status and clear review fields
        cursor.execute("""
            UPDATE alerts 
            SET 
                status = 'New',
                date_first_reviewed = NULL,
                emis_search_completed = NULL,
                emis_search_date = NULL,
                emis_search_reason = NULL,
                patients_affected_count = NULL,
                emergency_drugs_check = NULL,
                emergency_drugs_affected = NULL,
                practice_team_notified = NULL,
                practice_team_notified_date = NULL,
                team_notification_method = NULL,
                patients_contacted = NULL,
                contact_method = NULL,
                medication_stopped = NULL,
                medication_stopped_date = NULL,
                medication_alternative_provided = NULL,
                medication_not_stopped_reason = NULL,
                patient_harm_assessed = NULL,
                harm_assessment_planned_date = NULL,
                patient_harm_occurred = NULL,
                harm_severity = NULL,
                patient_harm_details = NULL,
                action_completed_date = NULL,
                notes = NULL
        """)
        
        affected_rows = cursor.rowcount
        conn.commit()
        
        print(f"✅ Reset {affected_rows} alerts to unreviewed state")
        print("All alerts are now:")
        print("  - Status: New")
        print("  - Not reviewed")
        print("  - No actions completed")
        print("  - Ready for testing the full workflow")
        
        return True
        
    except Exception as e:
        print(f"❌ Reset failed: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    reset_alerts()
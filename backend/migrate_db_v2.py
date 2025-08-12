#!/usr/bin/env python3
"""
Database migration script v2 - Add new fields for improved Yes/No workflow
"""

import sqlite3
import sys
from pathlib import Path

def migrate_database():
    """Add new columns for better Yes/No tracking"""
    
    db_path = Path("data/alerts.db")
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return False
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        # Get current schema
        cursor.execute("PRAGMA table_info(alerts)")
        columns = {row[1] for row in cursor.fetchall()}
        
        # Add new columns if they don't exist
        new_columns = [
            ("emis_search_reason", "TEXT"),
            ("team_notification_method", "TEXT"),
            ("medication_alternative_provided", "BOOLEAN DEFAULT 0"),
            ("medication_not_stopped_reason", "TEXT"),
            ("harm_assessment_planned_date", "DATETIME"),
            ("harm_severity", "TEXT")
        ]
        
        for col_name, col_type in new_columns:
            if col_name not in columns:
                print(f"Adding column: {col_name}")
                cursor.execute(f"ALTER TABLE alerts ADD COLUMN {col_name} {col_type}")
            else:
                print(f"Column {col_name} already exists, skipping")
        
        conn.commit()
        print("✅ Database migration v2 completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    success = migrate_database()
    sys.exit(0 if success else 1)
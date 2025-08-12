#!/usr/bin/env python3
"""
Database migration script to update schema for GP practice workflow
"""

import sqlite3
import sys
from pathlib import Path

def migrate_database():
    """Add new columns and remove old ones from the alerts table"""
    
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
            ("emergency_drugs_check", "BOOLEAN DEFAULT 0"),
            ("emergency_drugs_affected", "TEXT"),
            ("medication_stopped", "BOOLEAN DEFAULT 0"),
            ("medication_stopped_date", "DATETIME"),
            ("patient_harm_assessed", "BOOLEAN DEFAULT 0"),
            ("patient_harm_occurred", "BOOLEAN DEFAULT 0"),
            ("patient_harm_details", "TEXT")
        ]
        
        for col_name, col_type in new_columns:
            if col_name not in columns:
                print(f"Adding column: {col_name}")
                cursor.execute(f"ALTER TABLE alerts ADD COLUMN {col_name} {col_type}")
        
        # Note: SQLite doesn't support dropping columns directly
        # The old columns (formulary_check, stock_check, stock_action) will remain but unused
        print("Note: Old columns (formulary_check, stock_check, stock_action) will remain in the database but are no longer used")
        
        conn.commit()
        print("✅ Database migration completed successfully")
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
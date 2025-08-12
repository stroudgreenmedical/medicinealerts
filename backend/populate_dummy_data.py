#!/usr/bin/env python3
"""
Script to populate the database with dummy data for testing
"""

import random
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.alert import Alert, AlertStatus, Priority, Severity, Base

# Database connection
DATABASE_URL = "sqlite:///./data/alerts.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Sample data
PRODUCTS = [
    "Amlodipine 5mg tablets",
    "Metformin 500mg tablets", 
    "Omeprazole 20mg capsules",
    "Atorvastatin 20mg tablets",
    "Ramipril 5mg capsules",
    "Salbutamol 100mcg inhaler",
    "Sertraline 50mg tablets",
    "Levothyroxine 100mcg tablets",
    "Bisoprolol 5mg tablets",
    "Lansoprazole 30mg capsules",
    "Paracetamol 500mg tablets",
    "Ibuprofen 400mg tablets",
    "Simvastatin 40mg tablets",
    "Lisinopril 10mg tablets",
    "Citalopram 20mg tablets"
]

MANUFACTURERS = [
    "Pfizer Ltd",
    "AstraZeneca UK Ltd",
    "GlaxoSmithKline UK",
    "Teva UK Ltd",
    "Accord Healthcare Ltd",
    "Sandoz Ltd",
    "Mylan",
    "Zentiva",
    "Bristol-Myers Squibb",
    "Actavis UK Ltd"
]

ALERT_TYPES = [
    "Drug Alert",
    "Medical Device Alert",
    "Class 2 Medicines Recall",
    "Class 1 Medicines Recall",
    "Patient Safety Alert",
    "Supply Disruption Alert"
]

ISSUES = [
    "potential contamination with foreign particles",
    "incorrect labeling of strength",
    "stability issues affecting shelf life",
    "packaging defect allowing moisture ingress",
    "potential for incorrect dosing",
    "manufacturing deviation from specifications",
    "incorrect patient information leaflet",
    "potential allergenic substance not declared",
    "batch fails dissolution testing",
    "potential glass particles in vials"
]

ACTIONS = [
    "Quarantine and return affected stock immediately",
    "Check all stock and remove affected batches",
    "Review all patients who may have received affected product",
    "Contact all patients currently using this medication",
    "Implement additional checks before dispensing",
    "Return to supplier for credit",
    "Destroy affected stock according to waste regulations",
    "Monitor patients for adverse effects",
    "Switch patients to alternative preparation",
    "Urgent: Stop dispensing immediately"
]

def create_dummy_alerts(num_alerts=50):
    """Create dummy alert records"""
    db = SessionLocal()
    
    # Clear existing alerts (optional)
    db.query(Alert).delete()
    db.commit()
    
    alerts = []
    base_date = datetime.now()
    
    for i in range(num_alerts):
        # Random dates within last 3 months
        days_ago = random.randint(0, 90)
        published_date = base_date - timedelta(days=days_ago)
        
        # Determine status based on age
        if days_ago < 7:
            status = random.choice([AlertStatus.NEW, AlertStatus.UNDER_REVIEW, AlertStatus.ACTION_REQUIRED])
            priority = random.choice([Priority.P1_IMMEDIATE, Priority.P2_48H, Priority.P2_48H])
            severity = random.choice([Severity.CRITICAL, Severity.HIGH, Severity.HIGH])
        elif days_ago < 30:
            status = random.choice([AlertStatus.IN_PROGRESS, AlertStatus.ACTION_REQUIRED, AlertStatus.UNDER_REVIEW])
            priority = random.choice([Priority.P2_48H, Priority.P3_WEEK])
            severity = random.choice([Severity.HIGH, Severity.MEDIUM])
        else:
            status = random.choice([AlertStatus.COMPLETED, AlertStatus.CLOSED, AlertStatus.IN_PROGRESS])
            priority = random.choice([Priority.P3_WEEK, Priority.P4_ROUTINE])
            severity = random.choice([Severity.MEDIUM, Severity.LOW])
        
        # Some alerts should be marked as reviewed/actioned
        date_first_reviewed = None
        action_completed_date = None
        emis_search_completed = False
        emergency_drugs_check = False
        emergency_drugs_affected = None
        practice_team_notified = False
        patients_affected_count = None
        medication_stopped = False
        medication_stopped_date = None
        patient_harm_assessed = False
        patient_harm_occurred = False
        patient_harm_details = None
        
        if status in [AlertStatus.IN_PROGRESS, AlertStatus.COMPLETED, AlertStatus.CLOSED]:
            date_first_reviewed = published_date + timedelta(hours=random.randint(1, 48))
            emis_search_completed = random.choice([True, False])
            emergency_drugs_check = random.choice([True, False])
            if emergency_drugs_check and random.choice([True, False]):
                emergency_drugs_affected = random.choice(["Adrenaline 1:1000", "Glucagon", "Salbutamol inhaler", "None"])
            practice_team_notified = random.choice([True, False])
            
            if emis_search_completed:
                patients_affected_count = random.choice([0, 0, 1, 2, 3, 5, 8, 12, 20])  # Include 0 patients
                
                if patients_affected_count > 0:
                    medication_stopped = random.choice([True, False])
                    if medication_stopped:
                        medication_stopped_date = date_first_reviewed + timedelta(days=random.randint(0, 2))
                    
                    patient_harm_assessed = random.choice([True, False])
                    if patient_harm_assessed:
                        patient_harm_occurred = random.choice([False, False, False, True])  # 25% chance of harm
                        if patient_harm_occurred:
                            patient_harm_details = random.choice([
                                "Minor GI upset reported by 2 patients",
                                "One patient experienced allergic reaction - treated and recovered",
                                "Temporary elevated blood pressure in one patient"
                            ])
        
        if status == AlertStatus.COMPLETED:
            action_completed_date = date_first_reviewed + timedelta(days=random.randint(1, 7))
            emis_search_completed = True
            emergency_drugs_check = True
            practice_team_notified = True
            if patients_affected_count and patients_affected_count > 0:
                patient_harm_assessed = True
        
        product = random.choice(PRODUCTS)
        manufacturer = random.choice(MANUFACTURERS)
        
        alert = Alert(
            alert_id=f"MHRA-{2024+i//50}-{str(i+1).zfill(4)}",
            govuk_reference=f"MDR-{str(2024)}-{str(i+1).zfill(3)}",
            content_id=f"content-{str(i+1).zfill(6)}",
            title=f"{random.choice(ALERT_TYPES)}: {product} - {random.choice(ISSUES)}",
            url=f"https://www.gov.uk/drug-device-alerts/mhra-{2024}-{str(i+1).zfill(4)}",
            
            # Status fields
            status=status,
            priority=priority,
            severity=severity,
            final_relevance=random.choice(["Relevant", "Relevant", "Relevant", "Not-Relevant"]),  # 75% relevant
            
            # Product details
            product_name=product,
            manufacturer=manufacturer,
            batch_numbers=f"Batch {random.randint(1000, 9999)}, {random.randint(1000, 9999)}",
            expiry_dates=f"{(base_date + timedelta(days=random.randint(180, 730))).strftime('%m/%Y')}",
            
            # Alert metadata
            alert_type=random.choice(ALERT_TYPES),
            issued_date=published_date,
            published_date=published_date,
            
            # Action tracking
            date_first_reviewed=date_first_reviewed,
            action_completed_date=action_completed_date,
            emis_search_completed=emis_search_completed,
            emergency_drugs_check=emergency_drugs_check,
            emergency_drugs_affected=emergency_drugs_affected,
            practice_team_notified=practice_team_notified,
            patients_affected_count=patients_affected_count,
            medication_stopped=medication_stopped,
            medication_stopped_date=medication_stopped_date,
            patient_harm_assessed=patient_harm_assessed,
            patient_harm_occurred=patient_harm_occurred,
            patient_harm_details=patient_harm_details,
            
            # Additional details
            action_required=random.choice(ACTIONS),
            emis_search_terms=f'"{product.split()[0]}" AND {manufacturer.split()[0]}',
            notes="Test data for dashboard demonstration" if status == AlertStatus.COMPLETED else None
        )
        
        alerts.append(alert)
    
    # Add alerts to database
    db.add_all(alerts)
    db.commit()
    
    # Print summary
    print(f"✅ Created {len(alerts)} dummy alerts")
    
    # Count by status
    status_counts = {}
    for alert in alerts:
        status_counts[alert.status.value] = status_counts.get(alert.status.value, 0) + 1
    
    print("\nAlerts by Status:")
    for status, count in status_counts.items():
        print(f"  {status}: {count}")
    
    # Count by priority
    priority_counts = {}
    for alert in alerts:
        if alert.priority:
            priority_counts[alert.priority.value] = priority_counts.get(alert.priority.value, 0) + 1
    
    print("\nAlerts by Priority:")
    for priority, count in priority_counts.items():
        print(f"  {priority}: {count}")
    
    db.close()

if __name__ == "__main__":
    print("Populating database with dummy data...")
    create_dummy_alerts(50)
    print("\n✅ Dummy data population complete!")
    print("You can now view the alerts in the dashboard at http://localhost:5173")
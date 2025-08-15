# Alert Data Sources Strategy Document
## Medicines Alerts Manager - Data Acquisition for Missing Categories

### Current Status (as of August 2025)

#### Categories WITH Data (103 alerts):
1. **Medicines Recall** (48 alerts) - ✅ Active
2. **Medical Device Alert** (50 alerts) - ✅ Active  
3. **MHRA Safety Roundup** (5 alerts) - ✅ Active

#### Categories WITHOUT Data (0 alerts):
1. **National Patient Safety Alert (NatPSA)** - ❌ No data
2. **Drug Safety Update (DSU)** - ❌ No data
3. **Medicine Supply Alert** - ❌ No data
4. **Serious Shortage Protocol (SSP)** - ❌ No data
5. **CAS Distribution** - ❌ No data (see analysis below)

---

## Data Source Strategy for Missing Categories

### 1. National Patient Safety Alert (NatPSA)
**What it is:** Critical safety alerts issued by NHS England about significant patient safety risks requiring urgent action.

**Primary Data Source:**
- **URL:** https://www.england.nhs.uk/patient-safety-alerts/
- **Feed:** RSS available at https://www.england.nhs.uk/feed/?post_type=psa
- **API:** No official API, but RSS feed provides structured data

**Implementation Strategy:**
```python
FEEDS['NHS_ENGLAND_PSA'] = {
    'url': 'https://www.england.nhs.uk/feed/?post_type=psa',
    'source': 'NHS England PSA',
    'type': 'rss',
    'category': 'National Patient Safety Alert'
}
```

**Alternative Sources:**
- CAS (Central Alerting System) - see CAS section below
- Direct email subscriptions from NHS England

---

### 2. Drug Safety Update (DSU)
**What it is:** Monthly bulletin from MHRA providing healthcare professionals with the latest advice on medicine safety.

**Primary Data Source:**
- **URL:** https://www.gov.uk/drug-safety-update
- **Feed:** RSS available at https://www.gov.uk/drug-safety-update.atom
- **API:** GOV.UK Content API with document_type filter

**Implementation Strategy:**
```python
# Add to GOV.UK search parameters
document_types = ["drug_safety_update", "medical_safety_alert"]

# Or add dedicated RSS feed
FEEDS['MHRA_DSU'] = {
    'url': 'https://www.gov.uk/drug-safety-update.atom',
    'source': 'MHRA DSU',
    'type': 'atom',
    'category': 'Drug Safety Update'
}
```

**Key Considerations:**
- DSUs are monthly publications with multiple articles
- Each article may need separate alert entry
- Requires parsing of bulletin structure

---

### 3. Medicine Supply Alert
**What it is:** Notifications about medicine supply disruptions, shortages, and discontinuations.

**Primary Data Sources:**

**Option 1: DHSC Medicine Supply Notifications**
- **URL:** https://www.gov.uk/government/collections/medicine-supply-notifications
- **Feed:** No dedicated feed, requires web scraping or API polling
- **Document Type:** "medicine_supply_notification"

**Option 2: NHS England Supply Disruption Alerts**
- **URL:** https://www.england.nhs.uk/publications/
- **Filter:** Medicine supply disruptions category

**Implementation Strategy:**
```python
# Extend GOV.UK API search
async def search_supply_alerts():
    params = {
        "filter_content_store_document_type": "medicine_supply_notification",
        "filter_organisations": ["department-of-health-and-social-care"],
        "order": "-public_timestamp"
    }
```

---

### 4. Serious Shortage Protocol (SSP)
**What it is:** Protocols allowing pharmacists to supply alternative medicines during serious shortages without GP prescription changes.

**Primary Data Sources:**

**Option 1: DHSC SSP Notifications**
- **URL:** https://www.gov.uk/government/collections/serious-shortage-protocols-ssps
- **Feed:** No dedicated feed
- **Identification:** Title contains "SSP" or "Serious Shortage Protocol"

**Option 2: PSNC (Pharmaceutical Services Negotiating Committee)**
- **URL:** https://psnc.org.uk/dispensing-supply/supply-chain/shortage-protocols/
- **Note:** Third-party source but often faster than official channels

**Implementation Strategy:**
```python
# Search for SSP in titles
async def identify_ssp_alerts(alerts):
    ssp_keywords = ['SSP', 'Serious Shortage Protocol', 'shortage protocol']
    for alert in alerts:
        if any(keyword in alert.title for keyword in ssp_keywords):
            alert.category = 'Serious Shortage Protocol'
```

**Key Considerations:**
- SSPs are time-limited (usually 2-3 months)
- Require tracking of expiry dates
- Often issued alongside Supply Alerts

---

### 5. CAS Distribution (Central Alerting System)
**Analysis:** CAS is NOT a distinct category of alerts but rather a **distribution mechanism** for various alert types.

**What CAS Actually Is:**
- A system operated by MHRA for distributing alerts from multiple organizations
- Distributes NatPSAs, MHRA alerts, NHS England alerts, etc.
- Acts as a central hub rather than an originator of alerts

**Recommendation:** 
**REMOVE CAS as a separate category** and instead:
1. Tag alerts with "CAS-distributed: true/false" metadata
2. Track CAS reference numbers separately
3. Use CAS as a fallback data source for missed alerts

**CAS Data Access:**
- **Web Interface:** https://www.cas.mhra.gov.uk/ (requires login)
- **Email Distribution:** Subscription-based
- **API:** No public API available

**Alternative Implementation:**
If CAS must remain as a category, interpret it as "Other Safety Alerts" for alerts that don't fit other categories:
```python
# Catch-all for uncategorized CAS alerts
if not alert.category and alert.source == 'CAS':
    alert.category = 'CAS Distribution'  # or 'Other Safety Alert'
```

---

## Implementation Priority Order

### Phase 1 (Immediate - High Impact)
1. **Drug Safety Update** - Monthly critical updates, RSS feed available
2. **National Patient Safety Alert** - Urgent safety alerts, RSS feed available

### Phase 2 (Short-term - Medium Impact)
3. **Medicine Supply Alert** - Important for stock management
4. **Serious Shortage Protocol** - Critical for dispensing practices

### Phase 3 (Reconsideration)
5. **CAS Distribution** - Recommend removal or redefinition

---

## Technical Implementation Steps

### 1. Update Feed Reader Service
```python
# backend/app/services/feed_reader.py
FEEDS = {
    'GOV_UK_DRUG_DEVICE': {...},  # Existing
    'NHS_ENGLAND_PSA': {
        'url': 'https://www.england.nhs.uk/feed/?post_type=psa',
        'source': 'NHS England',
        'type': 'rss',
        'category': 'National Patient Safety Alert'
    },
    'MHRA_DSU': {
        'url': 'https://www.gov.uk/drug-safety-update.atom',
        'source': 'MHRA DSU',
        'type': 'atom',
        'category': 'Drug Safety Update'
    }
}
```

### 2. Extend GOV.UK Client
```python
# backend/app/services/govuk_client.py
DOCUMENT_TYPES = [
    "medical_safety_alert",
    "drug_safety_update",
    "medicine_supply_notification"
]
```

### 3. Add Category Detection Logic
```python
# backend/app/services/triage.py
def detect_category_from_content(alert):
    # SSP detection
    if 'serious shortage protocol' in alert.title.lower():
        return 'Serious Shortage Protocol'
    # Supply alert detection
    if 'supply' in alert.title.lower() and 'disruption' in alert.content.lower():
        return 'Medicine Supply Alert'
```

### 4. Create Scheduled Tasks
```python
# backend/app/services/scheduler.py
# Add new scheduled tasks for each feed
scheduler.add_job(
    fetch_nhs_england_psa,
    'interval',
    hours=6,
    id='fetch_psa_alerts'
)
```

---

## Data Quality Considerations

### Deduplication Strategy
- Use content_id/guid as primary key
- Check title similarity for cross-source duplicates
- Maintain source_urls field to track all sources

### Categorization Accuracy
- Implement fallback rules for uncategorized alerts
- Log categorization failures for manual review
- Consider ML-based categorization for ambiguous cases

### Historical Data
- Backfill last 6 months of alerts for new categories
- Maintain consistent date handling across sources
- Archive old alerts after 12 months

---

## Monitoring & Maintenance

### Health Checks
- Monitor each feed endpoint availability
- Alert on parsing failures
- Track new alert detection rates

### Regular Reviews
- Monthly review of uncategorized alerts
- Quarterly assessment of category definitions
- Annual review of data source effectiveness

---

## Conclusion

The missing alert categories can be populated through a combination of:
1. RSS/ATOM feeds (NatPSA, DSU)
2. Extended GOV.UK API queries (Supply Alerts, SSP)
3. Content-based categorization (SSP identification)

**Key Recommendation:** Remove CAS as a separate category since it's a distribution mechanism, not an alert type. Replace with "Other Safety Alerts" if needed for uncategorized alerts.

**Timeline:** Full implementation can be completed in 2-3 sprints with Phase 1 RSS feeds implementable immediately.
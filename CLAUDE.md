# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MHRA Alerts Automator - An automated system for monitoring and managing MHRA medicine safety alerts for GP practices. It polls GOV.UK APIs, auto-classifies alerts for GP relevance, sends Teams notifications, and provides a web dashboard for pharmacists to track responses.

## Tech Stack

- **Backend**: FastAPI (Python 3.11), SQLAlchemy, SQLite
- **Frontend**: React (TypeScript), Material-UI, Vite
- **APIs**: GOV.UK Search/Content APIs, Microsoft Teams webhooks
- **Deployment**: Docker on Synology NAS

## Common Development Commands

### Backend
```bash
# Start backend server
cd backend && python main.py

# Run with uvicorn (alternative)
cd backend && python -m uvicorn app.main:app --reload --port 8080

# Install dependencies
cd backend && pip install -r requirements.txt

# Run tests
cd backend && pytest

# Fetch real alerts from GOV.UK
cd backend && python fetch_real_alerts.py

# Test alert system functionality
cd backend && python test_alerts_system.py
```

### Frontend
```bash
# Start development server
cd frontend && npm run dev

# Build for production
cd frontend && npm run build

# Run linting
cd frontend && npm run lint

# Install dependencies
cd frontend && npm install
```

### Database Operations
```bash
# Check alerts in database
sqlite3 backend/data/alerts.db "SELECT * FROM alerts ORDER BY created_at DESC LIMIT 10;"

# Reset dummy data
cd backend && python populate_dummy_data.py
```

## Architecture & Key Components

### Backend Structure
- **app/api/routes/**: API endpoints (alerts, auth, dashboard, reports)
- **app/services/**:
  - `govuk_client.py`: Fetches alerts from GOV.UK APIs (medical_safety_alert, drug_safety_update)
  - `triage.py`: Auto-classifies alerts for GP relevance using medical specialties
  - `scheduler.py`: Polls GOV.UK every 4 hours, handles backfills
  - `teams_notify.py`: Sends adaptive cards to Teams webhook
  - `alert_processor.py`: Processes and stores alerts with classification
- **app/models/alert.py**: SQLAlchemy Alert model with comprehensive tracking fields
- **app/core/**: Configuration, database setup, JWT authentication

### Frontend Structure
- **src/pages/**: AlertDetail, AlertsList, Dashboard, Login
- **src/services/api.ts**: Axios client with JWT token handling (stored as 'token' in localStorage)
- **src/components/Layout.tsx**: Main app layout with navigation

### Alert Classification Logic
Alerts are auto-classified as "Relevant" if:
- Medical specialties include "General practice" or "Dispensing GP practices"
- Alert type matches GP-relevant patterns (see triage.py)

Priority levels: P1-Immediate, P2-Within 48h, P3-Within 1 week, P4-Routine

### API Authentication
- Login: POST /api/auth/login with username/password
- Token stored in localStorage as 'token'
- Backend expects "Bearer {token}" in Authorization header

## Key Configuration

### Environment Variables (.env)
```
ADMIN_EMAIL=anjan.chakraborty@nhs.net
ADMIN_PASSWORD=MHRAAlerts2024Secure!
TEAMS_WEBHOOK_URL=<teams_webhook>
DATABASE_URL=sqlite:///./data/alerts.db
POLL_INTERVAL_HOURS=4
```

### Database Location
- Development: `backend/data/alerts.db`
- Docker: `/app/data/alerts.db`

## Known Issues & Fixes

### Datetime Comparison Error
Fixed in `govuk_client.py` - use timezone-aware datetimes:
```python
from datetime import timezone
cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
```

### NoneType .lower() Error
Fixed in `triage.py` - handle None values:
```python
title = (alert_data.get("title") or "").lower()
```

### Mark Complete Button Not Working
Debug logging added to `AlertDetail.tsx` and `alerts.py` routes. Check console and backend logs for update failures.

## Testing & Debugging

### Test Alert Fetching
```bash
cd backend && python test_alerts_system.py
```

### Manual Poll for Alerts
```bash
cd backend && echo -e "y\n1" | python fetch_real_alerts.py  # Recent alerts
cd backend && echo -e "y\n2" | python fetch_real_alerts.py  # 1-year backfill
```

### Playwright Testing
```bash
node test-complete-button.js  # Test Mark Complete functionality
```

## Deployment

### Deploy to Synology
```bash
./deployment/pre-deploy-check.sh
./deployment/deploy-synology.sh
```

### Monitor Logs
```bash
ssh anjan@synology.local 'cd /volume1/docker/mhra-alerts && docker-compose logs -f'
```

## Alert Types from GOV.UK

1. **Medical Safety Alerts** (medical_safety_alert) - Urgent safety communications
2. **Drug Safety Updates** (drug_safety_update) - Regular medicine safety updates

Both filtered by MHRA organization and processed through the triage system.
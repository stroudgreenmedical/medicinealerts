# MHRA Alerts Automator

An automated system for monitoring, triaging, and managing MHRA (Medicines and Healthcare products Regulatory Agency) alerts for GP practices. The system polls GOV.UK APIs, automatically classifies alerts for GP relevance, sends Teams notifications, and provides a web dashboard for pharmacists to track and manage their response to alerts.

## Features

- **Automated Alert Monitoring**: Polls GOV.UK APIs every 4 hours for new MHRA alerts
- **Intelligent Triage**: Automatically classifies alerts as relevant/not relevant for GP practices
- **Teams Integration**: Sends notifications to Microsoft Teams for relevant alerts
- **Web Dashboard**: Full-featured web interface for managing alerts and tracking actions
- **Excel Export**: Generate comprehensive reports in Excel format
- **Audit Trail**: Complete tracking of all actions taken on alerts
- **8-Year Backfill**: Import historical alerts for comprehensive record keeping

## Architecture

- **Backend**: FastAPI (Python 3.11)
- **Database**: SQLite
- **Frontend**: React (coming soon)
- **Deployment**: Docker on Synology NAS
- **Notifications**: Microsoft Teams webhooks

## Quick Start

### Prerequisites

- Synology NAS with Docker installed
- SSH access to Synology
- Microsoft Teams webhook URL
- Python 3.11+ (for local development)

### Configuration

1. Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

2. Update `.env` with your configuration:
- Set `TEAMS_WEBHOOK_URL` to your Teams incoming webhook
- Set `ADMIN_PASSWORD` to a secure password
- Adjust other settings as needed

### Deployment to Synology

1. Run pre-deployment checks:
```bash
./deployment/pre-deploy-check.sh
```

2. Deploy to Synology:
```bash
./deployment/deploy-synology.sh
```

3. Access the application:
- API: http://synology.local:8080
- Dashboard: http://synology.local:3000 (when frontend is ready)

### Local Development

1. Install backend dependencies:
```bash
cd backend
pip install -r requirements.txt
```

2. Run the backend:
```bash
python main.py
```

3. Access the API at http://localhost:8080

## API Endpoints

### Authentication
- `POST /api/auth/login` - Login with email/password
- `GET /api/auth/me` - Get current user info
- `POST /api/auth/logout` - Logout

### Alerts
- `GET /api/alerts` - List alerts with filtering
- `GET /api/alerts/{id}` - Get single alert
- `PUT /api/alerts/{id}` - Update alert
- `GET /api/alerts/overdue/list` - List overdue alerts
- `POST /api/alerts/{id}/mark-reviewed` - Mark as reviewed

### Dashboard
- `GET /api/dashboard/stats` - Get dashboard statistics

### Reports
- `GET /api/reports/export/excel` - Export to Excel
- `GET /api/reports/summary/monthly` - Monthly summary
- `GET /api/reports/summary/annual` - Annual summary

## Alert Classification Rules

Alerts are automatically classified as **relevant** if:
- Medical specialties include "General practice" or "Dispensing GP practices"
- National Patient Safety Alert with GP specialties
- MHRA Safety Roundup with GP specialties

Priority levels:
- **P1-Immediate**: Class 1 recalls, National Patient Safety Alerts
- **P2-Within 48h**: Class 2 recalls
- **P3-Within 1 week**: Class 3 recalls, Field Safety Notices
- **P4-Routine**: Class 4 recalls, general updates

## Workflow

1. **Automatic Detection**: System polls GOV.UK every 4 hours
2. **Triage**: Alerts are automatically classified for relevance
3. **Notification**: Relevant alerts trigger Teams notifications
4. **Review**: Pharmacist reviews alert in web dashboard
5. **Action**: Pharmacist performs required actions (EMIS searches, stock checks, etc.)
6. **Documentation**: Actions are recorded in the system
7. **Reporting**: Generate Excel reports for compliance

## Database Schema

The system tracks comprehensive information for each alert:
- Alert identification (ID, reference, URL)
- Classification (type, severity, priority)
- Product details (name, batches, expiry dates)
- Action management (status, assigned to, dates)
- Implementation tracking (EMIS searches, patient counts)
- Communication records (team notified, patients contacted)
- Compliance metrics (response times, evidence)

## Monitoring

View logs:
```bash
ssh anjan@synology.local 'cd /volume1/docker/mhra-alerts && docker-compose logs -f'
```

Check service status:
```bash
ssh anjan@synology.local 'cd /volume1/docker/mhra-alerts && docker-compose ps'
```

## Troubleshooting

### Cannot connect to Synology
- Check SSH is enabled on Synology
- Verify IP address and credentials
- Check firewall settings

### Port conflicts
- The deployment script automatically frees ports 8080 and 3000
- If issues persist, manually stop conflicting services

### Teams notifications not working
- Verify webhook URL in `.env`
- Check Synology can reach Teams (firewall/proxy)
- Review logs for error messages

## Security

- JWT-based authentication
- Password hashing with bcrypt
- Environment-based configuration
- No patient data stored
- Audit trail for all actions

## License

Internal use only - NHS North Central London ICB

## Support

For issues or questions, contact:
- Dr Anjan Chakraborty (anjan.chakraborty@nhs.net)

## Roadmap

- [x] Backend API implementation
- [x] GOV.UK integration
- [x] Teams notifications
- [x] Database and models
- [x] Authentication
- [x] Excel export
- [x] Docker deployment
- [ ] React frontend dashboard
- [ ] SharePoint integration (future)
- [ ] Email digest option
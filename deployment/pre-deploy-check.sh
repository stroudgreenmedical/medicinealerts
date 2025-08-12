#!/bin/bash

# Pre-deployment checks for MHRA Alerts Automator

set -e

# Configuration
SYNOLOGY_HOST="${SYNOLOGY_HOST:-192.168.0.32}"
SYNOLOGY_USER="${SYNOLOGY_USER:-anjan}"
REQUIRED_DISK_SPACE_MB=1000  # 1GB minimum

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Counters
WARNINGS=0
ERRORS=0

log_pass() {
    echo -e "${GREEN}✓${NC} $1"
}

log_fail() {
    echo -e "${RED}✗${NC} $1"
    ((ERRORS++))
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
    ((WARNINGS++))
}

echo "======================================"
echo "MHRA Alerts Pre-Deployment Check"
echo "======================================"
echo ""

# Check local environment
echo "Checking local environment..."

# Check if .env file exists
if [ -f ".env" ]; then
    log_pass ".env file exists"
    
    # Check for required variables
    if grep -q "TEAMS_WEBHOOK_URL=" .env && grep -q "ADMIN_PASSWORD=" .env; then
        log_pass "Required environment variables present"
    else
        log_warning "Some environment variables may be missing"
    fi
else
    log_warning ".env file not found (will use .env.example)"
fi

# Check if Docker is installed locally
if command -v docker &> /dev/null; then
    log_pass "Docker installed locally"
else
    log_warning "Docker not installed locally (not required for deployment)"
fi

# Check backend files
if [ -f "backend/main.py" ] && [ -f "backend/requirements.txt" ]; then
    log_pass "Backend files present"
else
    log_fail "Backend files missing"
fi

# Check if frontend exists (optional)
if [ -d "frontend" ]; then
    log_pass "Frontend directory exists"
else
    log_warning "Frontend not yet implemented"
fi

echo ""
echo "Checking Synology connectivity..."

# Check SSH connection
if ssh -o ConnectTimeout=5 ${SYNOLOGY_USER}@${SYNOLOGY_HOST} "echo 'connected'" > /dev/null 2>&1; then
    log_pass "SSH connection to Synology successful"
else
    log_fail "Cannot connect to Synology via SSH"
    echo "  Please check:"
    echo "  - Synology host: ${SYNOLOGY_HOST}"
    echo "  - Username: ${SYNOLOGY_USER}"
    echo "  - SSH is enabled on Synology"
fi

echo ""
echo "Checking Synology environment..."

# Check Docker on Synology
if ssh ${SYNOLOGY_USER}@${SYNOLOGY_HOST} "which docker" > /dev/null 2>&1; then
    log_pass "Docker installed on Synology"
    
    # Check Docker version
    DOCKER_VERSION=$(ssh ${SYNOLOGY_USER}@${SYNOLOGY_HOST} "docker --version" 2>/dev/null | cut -d' ' -f3 | cut -d',' -f1)
    echo "  Docker version: ${DOCKER_VERSION}"
else
    log_fail "Docker not found on Synology"
fi

# Check docker-compose on Synology
if ssh ${SYNOLOGY_USER}@${SYNOLOGY_HOST} "which docker-compose || test -f /usr/local/bin/docker-compose" > /dev/null 2>&1; then
    log_pass "docker-compose available on Synology"
else
    log_fail "docker-compose not found on Synology"
fi

# Check disk space
AVAILABLE_SPACE=$(ssh ${SYNOLOGY_USER}@${SYNOLOGY_HOST} "df -m /volume1 | tail -1 | awk '{print \$4}'" 2>/dev/null)
if [ -n "$AVAILABLE_SPACE" ] && [ "$AVAILABLE_SPACE" -gt "$REQUIRED_DISK_SPACE_MB" ]; then
    log_pass "Sufficient disk space (${AVAILABLE_SPACE}MB available)"
else
    log_fail "Insufficient disk space (${AVAILABLE_SPACE}MB available, need ${REQUIRED_DISK_SPACE_MB}MB)"
fi

# Check ports
echo ""
echo "Checking port availability on Synology..."

# Check port 8080
if ssh ${SYNOLOGY_USER}@${SYNOLOGY_HOST} "lsof -i:8080" > /dev/null 2>&1; then
    log_warning "Port 8080 is in use (will be freed during deployment)"
else
    log_pass "Port 8080 is available"
fi

# Check port 3000
if ssh ${SYNOLOGY_USER}@${SYNOLOGY_HOST} "lsof -i:3000" > /dev/null 2>&1; then
    log_warning "Port 3000 is in use (will be freed during deployment)"
else
    log_pass "Port 3000 is available"
fi

# Check architecture
echo ""
echo "Checking system architecture..."

LOCAL_ARCH=$(uname -m)
REMOTE_ARCH=$(ssh ${SYNOLOGY_USER}@${SYNOLOGY_HOST} "uname -m" 2>/dev/null)

echo "  Local architecture: ${LOCAL_ARCH}"
echo "  Synology architecture: ${REMOTE_ARCH}"

if [[ "$LOCAL_ARCH" == "arm64" ]] && [[ "$REMOTE_ARCH" == "x86_64" ]]; then
    log_warning "Architecture mismatch - will build on Synology (recommended)"
elif [[ "$LOCAL_ARCH" == "$REMOTE_ARCH" ]]; then
    log_pass "Architecture match"
else
    log_warning "Architecture mismatch detected"
fi

# Check network connectivity from Synology
echo ""
echo "Checking external connectivity from Synology..."

# Check GOV.UK API
if ssh ${SYNOLOGY_USER}@${SYNOLOGY_HOST} "curl -s -o /dev/null -w '%{http_code}' https://www.gov.uk/api/search.json" 2>/dev/null | grep -q "200"; then
    log_pass "Can reach GOV.UK API"
else
    log_fail "Cannot reach GOV.UK API from Synology"
fi

# Check Teams webhook (just DNS resolution)
if ssh ${SYNOLOGY_USER}@${SYNOLOGY_HOST} "nslookup nhs.webhook.office.com" > /dev/null 2>&1; then
    log_pass "Can resolve Teams webhook domain"
else
    log_warning "Cannot resolve Teams webhook domain (check firewall)"
fi

# Summary
echo ""
echo "======================================"
echo "Pre-deployment Check Summary"
echo "======================================"
echo -e "Errors: ${RED}${ERRORS}${NC}"
echo -e "Warnings: ${YELLOW}${WARNINGS}${NC}"

if [ $ERRORS -gt 0 ]; then
    echo ""
    echo -e "${RED}Pre-deployment check failed with ${ERRORS} error(s)${NC}"
    echo "Please fix the errors before proceeding with deployment"
    exit 1
elif [ $WARNINGS -gt 0 ]; then
    echo ""
    echo -e "${YELLOW}Pre-deployment check passed with ${WARNINGS} warning(s)${NC}"
    echo "You can proceed with deployment, but review the warnings"
    exit 0
else
    echo ""
    echo -e "${GREEN}All pre-deployment checks passed!${NC}"
    echo "Ready for deployment"
    exit 0
fi
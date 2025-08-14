#!/bin/bash

# MHRA Alerts Manager - Synology Deployment Script
# Based on lessons learned from RAG Practice App deployment

set -e  # Exit on any error

# Configuration
SYNOLOGY_HOST="192.168.0.32"
SYNOLOGY_USER="anjan"
APP_NAME="mhra-alerts"
REMOTE_DIR="/volume1/docker/${APP_NAME}"
DOCKER_COMPOSE="/usr/local/bin/docker-compose"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

# Step 1: Pre-deployment validation
log "Step 1/10: Running pre-deployment checks..."

# Check SSH connectivity
if ! ssh -o ConnectTimeout=5 "${SYNOLOGY_USER}@${SYNOLOGY_HOST}" "echo 'SSH connection successful'" > /dev/null 2>&1; then
    error "Cannot connect to Synology NAS at ${SYNOLOGY_HOST}"
    exit 1
fi

# Check if ports are available
log "Checking port availability..."
BACKEND_PORT_CHECK=$(ssh "${SYNOLOGY_USER}@${SYNOLOGY_HOST}" "netstat -tln | grep :8081 || echo 'PORT_FREE'")
FRONTEND_PORT_CHECK=$(ssh "${SYNOLOGY_USER}@${SYNOLOGY_HOST}" "netstat -tln | grep :3000 || echo 'PORT_FREE'")

if [[ "$BACKEND_PORT_CHECK" != "PORT_FREE" ]]; then
    error "Port 8081 is already in use on Synology"
    exit 1
fi

if [[ "$FRONTEND_PORT_CHECK" != "PORT_FREE" ]]; then
    warn "Port 3000 is in use, but continuing (might be okay if it's our previous deployment)"
fi

# Step 2: Create backup if app exists
log "Step 2/10: Creating backup of existing deployment..."
ssh "${SYNOLOGY_USER}@${SYNOLOGY_HOST}" "
    if [ -d '${REMOTE_DIR}' ]; then
        BACKUP_DIR='${REMOTE_DIR}-backup-$(date +%Y%m%d_%H%M%S)'
        echo 'Creating backup at: \$BACKUP_DIR'
        cp -r '${REMOTE_DIR}' '\$BACKUP_DIR'
        echo 'Backup created successfully'
    else
        echo 'No existing deployment found, skipping backup'
    fi
"

# Step 3: Stop existing containers if running
log "Step 3/10: Stopping existing containers..."
ssh "${SYNOLOGY_USER}@${SYNOLOGY_HOST}" "
    if [ -d '${REMOTE_DIR}' ]; then
        cd '${REMOTE_DIR}'
        ${DOCKER_COMPOSE} down || echo 'No containers were running'
    fi
"

# Step 4: Clean up old Docker resources
log "Step 4/10: Cleaning up old Docker resources..."
ssh "${SYNOLOGY_USER}@${SYNOLOGY_HOST}" "
    /usr/local/bin/docker system prune -f
    /usr/local/bin/docker image prune -f
"

# Step 5: Transfer application files
log "Step 5/10: Transferring application files..."

# Create exclude file for transfer
cat > /tmp/rsync-exclude << EOF
node_modules
.git
*.log
.env
.DS_Store
__pycache__
*.pyc
.pytest_cache
dist
build
coverage
.coverage
*.db
logs/*
data/*
.vscode
.idea
EOF

# Use tar over SSH for reliable transfer (learned from deployment notes)
log "Transferring files using tar over SSH..."
tar czf - --exclude-from=/tmp/rsync-exclude . | ssh "${SYNOLOGY_USER}@${SYNOLOGY_HOST}" "
    mkdir -p '${REMOTE_DIR}' && 
    cd '${REMOTE_DIR}' && 
    tar xzf -
"

# Clean up
rm /tmp/rsync-exclude

# Step 6: Set up environment file
log "Step 6/10: Setting up environment file..."
ssh "${SYNOLOGY_USER}@${SYNOLOGY_HOST}" "
    cd '${REMOTE_DIR}'
    if [ -f '.env.production' ]; then
        cp .env.production .env
        echo 'Environment file configured from .env.production'
    else
        echo 'Warning: No .env.production file found'
    fi
"

# Step 7: Fix permissions
log "Step 7/10: Setting proper permissions..."
ssh "${SYNOLOGY_USER}@${SYNOLOGY_HOST}" "
    chown -R 1026:100 '${REMOTE_DIR}'
    chmod -R 755 '${REMOTE_DIR}'
    chmod +x '${REMOTE_DIR}'/deploy-*.sh || true
"

# Step 8: Build Docker images on Synology
log "Step 8/10: Building Docker images on Synology (this may take several minutes)..."
ssh "${SYNOLOGY_USER}@${SYNOLOGY_HOST}" "
    cd '${REMOTE_DIR}'
    ${DOCKER_COMPOSE} build --no-cache --pull
"

# Step 9: Start services with proper sequence
log "Step 9/10: Starting services..."
ssh "${SYNOLOGY_USER}@${SYNOLOGY_HOST}" "
    cd '${REMOTE_DIR}'
    
    # Start backend first
    ${DOCKER_COMPOSE} up -d backend
    
    # Wait for backend to be healthy
    echo 'Waiting for backend to be healthy...'
    timeout=60
    while [ \$timeout -gt 0 ]; do
        if ${DOCKER_COMPOSE} ps backend | grep -q 'healthy'; then
            echo 'Backend is healthy'
            break
        fi
        sleep 5
        timeout=\$((timeout - 5))
    done
    
    if [ \$timeout -le 0 ]; then
        echo 'Backend health check timed out'
        ${DOCKER_COMPOSE} logs backend
        exit 1
    fi
    
    # Start frontend
    ${DOCKER_COMPOSE} up -d frontend
"

# Step 10: Final health checks
log "Step 10/10: Running final health checks..."

sleep 10  # Give services time to start

# Check container status
log "Checking container status..."
ssh "${SYNOLOGY_USER}@${SYNOLOGY_HOST}" "
    cd '${REMOTE_DIR}'
    ${DOCKER_COMPOSE} ps
"

# Test backend endpoint
log "Testing backend health endpoint..."
BACKEND_HEALTH=$(ssh "${SYNOLOGY_USER}@${SYNOLOGY_HOST}" "curl -s -f http://localhost:8081/health || echo 'FAILED'")
if [[ "$BACKEND_HEALTH" == "FAILED" ]]; then
    error "Backend health check failed"
    ssh "${SYNOLOGY_USER}@${SYNOLOGY_HOST}" "cd '${REMOTE_DIR}' && ${DOCKER_COMPOSE} logs backend"
    exit 1
fi

# Test frontend
log "Testing frontend..."
FRONTEND_HEALTH=$(ssh "${SYNOLOGY_USER}@${SYNOLOGY_HOST}" "curl -s -f http://localhost:3000/health || echo 'FAILED'")
if [[ "$FRONTEND_HEALTH" == "FAILED" ]]; then
    warn "Frontend health check failed, but this might be expected if no /health endpoint exists"
fi

# Final status
success "Deployment completed successfully!"
echo ""
echo "🎉 MHRA Alerts Manager is now running on Synology!"
echo ""
echo "📋 Access Information:"
echo "   • Backend API: http://${SYNOLOGY_HOST}:8081"
echo "   • Frontend Web App: http://${SYNOLOGY_HOST}:3000"
echo "   • Health Check: http://${SYNOLOGY_HOST}:8081/health"
echo ""
echo "🔍 Management Commands:"
echo "   • View logs: ssh ${SYNOLOGY_USER}@${SYNOLOGY_HOST} 'cd ${REMOTE_DIR} && ${DOCKER_COMPOSE} logs -f'"
echo "   • Restart: ssh ${SYNOLOGY_USER}@${SYNOLOGY_HOST} 'cd ${REMOTE_DIR} && ${DOCKER_COMPOSE} restart'"
echo "   • Stop: ssh ${SYNOLOGY_USER}@${SYNOLOGY_HOST} 'cd ${REMOTE_DIR} && ${DOCKER_COMPOSE} down'"
echo ""

# Show final container status
log "Final container status:"
ssh "${SYNOLOGY_USER}@${SYNOLOGY_HOST}" "cd '${REMOTE_DIR}' && ${DOCKER_COMPOSE} ps"
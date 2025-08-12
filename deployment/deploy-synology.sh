#!/bin/bash

# MHRA Alerts Automator - Synology Deployment Script
# Builds and deploys the application on Synology NAS

set -e

# Configuration
SYNOLOGY_HOST="${SYNOLOGY_HOST:-192.168.0.32}"
SYNOLOGY_USER="${SYNOLOGY_USER:-anjan}"
SYNOLOGY_PATH="/volume1/docker/mhra-alerts"
PROJECT_NAME="mhra-alerts"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check SSH connectivity
    if ! ssh -o ConnectTimeout=5 ${SYNOLOGY_USER}@${SYNOLOGY_HOST} "echo 'SSH connection successful'" > /dev/null 2>&1; then
        log_error "Cannot connect to Synology via SSH"
        exit 1
    fi
    
    # Check if Docker is available on Synology
    if ! ssh ${SYNOLOGY_USER}@${SYNOLOGY_HOST} "which docker" > /dev/null 2>&1; then
        log_error "Docker not found on Synology"
        exit 1
    fi
    
    # Check if docker-compose is available
    if ! ssh ${SYNOLOGY_USER}@${SYNOLOGY_HOST} "which docker-compose" > /dev/null 2>&1; then
        log_warning "docker-compose not found, trying /usr/local/bin/docker-compose"
        DOCKER_COMPOSE="/usr/local/bin/docker-compose"
    else
        DOCKER_COMPOSE="docker-compose"
    fi
    
    log_info "Prerequisites check passed"
}

# Clean up old containers and processes
cleanup_old_deployment() {
    log_info "Cleaning up old deployment..."
    
    ssh ${SYNOLOGY_USER}@${SYNOLOGY_HOST} <<EOF
        cd ${SYNOLOGY_PATH} 2>/dev/null || true
        
        # Stop and remove old containers
        ${DOCKER_COMPOSE} down --remove-orphans 2>/dev/null || true
        
        # Kill any lingering processes on our ports
        lsof -ti:8080 | xargs kill -9 2>/dev/null || true
        lsof -ti:3000 | xargs kill -9 2>/dev/null || true
        
        # Clean up old images
        docker image prune -f
EOF
    
    log_info "Cleanup completed"
}

# Create directory structure on Synology
create_directories() {
    log_info "Creating directory structure on Synology..."
    
    ssh ${SYNOLOGY_USER}@${SYNOLOGY_HOST} <<EOF
        mkdir -p ${SYNOLOGY_PATH}/data
        mkdir -p ${SYNOLOGY_PATH}/logs
        mkdir -p ${SYNOLOGY_PATH}/backend
        mkdir -p ${SYNOLOGY_PATH}/frontend
        chmod -R 755 ${SYNOLOGY_PATH}
EOF
    
    log_info "Directories created"
}

# Transfer files to Synology
transfer_files() {
    log_info "Transferring files to Synology..."
    
    # Create tar archive and transfer
    tar czf - \
        --exclude='.git' \
        --exclude='*.pyc' \
        --exclude='__pycache__' \
        --exclude='node_modules' \
        --exclude='.env' \
        --exclude='data' \
        --exclude='logs' \
        . | ssh ${SYNOLOGY_USER}@${SYNOLOGY_HOST} \
        "cd ${SYNOLOGY_PATH} && tar xzf -"
    
    # Copy .env file if it exists
    if [ -f .env ]; then
        log_info "Copying .env file..."
        scp .env ${SYNOLOGY_USER}@${SYNOLOGY_HOST}:${SYNOLOGY_PATH}/.env
    else
        log_warning ".env file not found. Using .env.example as template"
        scp .env.example ${SYNOLOGY_USER}@${SYNOLOGY_HOST}:${SYNOLOGY_PATH}/.env
        log_warning "Please update ${SYNOLOGY_PATH}/.env with your actual values"
    fi
    
    log_info "File transfer completed"
}

# Build Docker images on Synology
build_on_synology() {
    log_info "Building Docker images on Synology (this may take a while)..."
    
    ssh ${SYNOLOGY_USER}@${SYNOLOGY_HOST} <<EOF
        cd ${SYNOLOGY_PATH}
        
        # Update docker-compose.yml paths for Synology
        sed -i "s|/volume1/docker/mhra-alerts|${SYNOLOGY_PATH}|g" docker-compose.yml
        
        # Build images
        ${DOCKER_COMPOSE} build --no-cache
EOF
    
    log_info "Docker images built successfully"
}

# Start services
start_services() {
    log_info "Starting services..."
    
    ssh ${SYNOLOGY_USER}@${SYNOLOGY_HOST} <<EOF
        cd ${SYNOLOGY_PATH}
        
        # Start backend first
        ${DOCKER_COMPOSE} up -d backend
        
        # Wait for backend to be healthy
        echo "Waiting for backend to be ready..."
        sleep 10
        
        # Check backend health
        if curl -f http://localhost:8080/health > /dev/null 2>&1; then
            echo "Backend is healthy"
        else
            echo "Backend health check failed"
            ${DOCKER_COMPOSE} logs backend
            exit 1
        fi
        
        # Start frontend (if it exists)
        if [ -d "frontend" ]; then
            ${DOCKER_COMPOSE} up -d frontend
        fi
EOF
    
    log_info "Services started successfully"
}

# Verify deployment
verify_deployment() {
    log_info "Verifying deployment..."
    
    # Check if backend is responding
    if ssh ${SYNOLOGY_USER}@${SYNOLOGY_HOST} "curl -s http://localhost:8080/health | grep -q healthy"; then
        log_info "✅ Backend is running and healthy"
    else
        log_error "❌ Backend health check failed"
        ssh ${SYNOLOGY_USER}@${SYNOLOGY_HOST} "${DOCKER_COMPOSE} logs backend | tail -20"
        exit 1
    fi
    
    # Display service status
    ssh ${SYNOLOGY_USER}@${SYNOLOGY_HOST} <<EOF
        cd ${SYNOLOGY_PATH}
        echo ""
        echo "Service Status:"
        ${DOCKER_COMPOSE} ps
        echo ""
        echo "Container Resource Usage:"
        docker stats --no-stream
EOF
    
    log_info "Deployment verification completed"
}

# Run initial database setup
initialize_database() {
    log_info "Initializing database (if needed)..."
    
    ssh ${SYNOLOGY_USER}@${SYNOLOGY_HOST} <<EOF
        cd ${SYNOLOGY_PATH}
        
        # Check if database exists
        if [ ! -f "${SYNOLOGY_PATH}/data/alerts.db" ]; then
            echo "Database not found, will be created on first run"
        else
            echo "Database already exists"
        fi
EOF
}

# Main deployment flow
main() {
    echo "======================================"
    echo "MHRA Alerts Automator - Synology Deployment"
    echo "======================================"
    echo "Target: ${SYNOLOGY_USER}@${SYNOLOGY_HOST}"
    echo "Path: ${SYNOLOGY_PATH}"
    echo ""
    
    # Confirm deployment
    read -p "Do you want to proceed with deployment? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Deployment cancelled"
        exit 0
    fi
    
    # Run deployment steps
    check_prerequisites
    cleanup_old_deployment
    create_directories
    transfer_files
    build_on_synology
    initialize_database
    start_services
    verify_deployment
    
    echo ""
    echo "======================================"
    echo "Deployment completed successfully!"
    echo "======================================"
    echo ""
    echo "Access the application at:"
    echo "  Backend API: http://${SYNOLOGY_HOST}:8080"
    echo "  Frontend: http://${SYNOLOGY_HOST}:3000 (when available)"
    echo ""
    echo "Default login:"
    echo "  Email: anjan.chakraborty@nhs.net"
    echo "  Password: (as configured in .env)"
    echo ""
    echo "To view logs:"
    echo "  ssh ${SYNOLOGY_USER}@${SYNOLOGY_HOST} 'cd ${SYNOLOGY_PATH} && docker-compose logs -f'"
    echo ""
}

# Run main function
main "$@"
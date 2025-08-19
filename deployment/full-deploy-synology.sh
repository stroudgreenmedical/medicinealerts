#!/bin/bash

# Full deployment script for Synology NAS with complete rebuild
# This ensures no cache issues and clean deployment

set -e

echo "🚀 Full Deployment to Synology NAS (192.168.0.32)"
echo "================================================"

# Configuration
SYNOLOGY_USER="anjan"
SYNOLOGY_HOST="192.168.0.32"
DEPLOY_PATH="/volume1/docker/mhra-alerts"
LOCAL_PATH="/Users/anjan/Programs/Cursor/MHRA Alerts Automator"

echo ""
echo "📦 Step 1: Preparing deployment package..."
cd "$LOCAL_PATH"

# Create deployment archive with all necessary files
echo "Creating deployment archive..."
tar -czf deployment-package.tar.gz \
    --exclude='backend/__pycache__' \
    --exclude='backend/*.pyc' \
    --exclude='backend/data/*.db' \
    --exclude='frontend/node_modules' \
    --exclude='frontend/dist' \
    --exclude='.git' \
    backend/ \
    frontend/ \
    docker-compose.yml \
    .env

echo "✅ Deployment package created"

echo ""
echo "📤 Step 2: Uploading to Synology..."
scp deployment-package.tar.gz ${SYNOLOGY_USER}@${SYNOLOGY_HOST}:~/deployment-package.tar.gz

echo ""
echo "🔧 Step 3: Deploying on Synology..."
ssh ${SYNOLOGY_USER}@${SYNOLOGY_HOST} << 'ENDSSH'
set -e

echo "Extracting deployment package..."
cd /volume1/docker/mhra-alerts

# Backup existing data
echo "Backing up database..."
if [ -f backend/data/alerts.db ]; then
    cp backend/data/alerts.db backend/data/alerts.db.backup.$(date +%Y%m%d_%H%M%S)
fi

# Stop existing containers
echo "Stopping existing containers..."
sudo /usr/local/bin/docker-compose down || true

# Clean up old images to prevent cache issues
echo "Cleaning up old Docker images..."
sudo docker image prune -f
sudo docker images | grep mhra-alerts | awk '{print $3}' | xargs -r sudo docker rmi -f || true

# Extract new code
echo "Extracting new code..."
tar -xzf ~/deployment-package.tar.gz

# Restore database if it exists
if [ -f backend/data/alerts.db.backup.* ]; then
    echo "Restoring database..."
    cp backend/data/alerts.db.backup.$(ls -t backend/data/alerts.db.backup.* | head -1 | cut -d. -f4-) backend/data/alerts.db
fi

# Build fresh images with no cache
echo "Building Docker images (no cache)..."
sudo /usr/local/bin/docker-compose build --no-cache --pull

# Start containers
echo "Starting containers..."
sudo /usr/local/bin/docker-compose up -d

# Wait for services to be ready
echo "Waiting for services to start..."
sleep 10

# Check health
echo "Checking service health..."
curl -f http://localhost:8080/health || echo "Backend health check failed"
curl -f http://localhost:3000 || echo "Frontend health check failed"

# Show running containers
echo ""
echo "Running containers:"
sudo docker ps | grep mhra

# Clean up
rm /tmp/deployment-package.tar.gz

echo "✅ Deployment complete on Synology!"
ENDSSH

# Clean up local package
rm deployment-package.tar.gz

echo ""
echo "🎉 Full deployment completed successfully!"
echo ""
echo "Access the application at:"
echo "  📍 Local Network: http://192.168.0.32:3000"
echo "  🌐 Via Cloudflare: https://meds.stroudgreenmedical.co.uk"
echo ""
echo "New System Test feature available at:"
echo "  📍 Local: http://192.168.0.32:3000/system-test"
echo "  🌐 Cloudflare: https://meds.stroudgreenmedical.co.uk/system-test"
echo ""
echo "Backend API: http://192.168.0.32:8081"
echo ""

# Test the new endpoint
echo "Testing system-test endpoint..."
curl -s http://192.168.0.32:8081/api/system-test/ | python3 -m json.tool | head -20 || echo "System test endpoint not yet available"
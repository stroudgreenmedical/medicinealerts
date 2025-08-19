#!/bin/bash

# Deploy script for MHRA Alerts to Synology NAS
# Uses nginx reverse proxy for API calls to avoid mixed content issues

echo "🚀 Starting deployment to Synology..."

echo "📦 Building Docker images with nginx proxy configuration..."

# Build the images (VITE_API_URL is empty to use relative paths)
docker-compose build

echo "🔄 Stopping existing containers..."
docker-compose down

echo "🎯 Starting new containers..."
docker-compose up -d

echo "✅ Deployment complete!"
echo ""
echo "Access the application at:"
echo "  - Direct: http://192.168.0.32:3000"
echo "  - Via Cloudflare: https://meds.stroudgreenmedical.co.uk"
echo ""
echo "Backend API is available at: http://192.168.0.32:8081"
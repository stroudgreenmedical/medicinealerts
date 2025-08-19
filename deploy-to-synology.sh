#!/bin/bash

# Deploy script for MHRA Alerts to Synology NAS
# This ensures the frontend is built with the correct API URL

echo "🚀 Starting deployment to Synology..."

# Set the API URL for your Synology environment
export VITE_API_URL="http://192.168.0.32:8081"

echo "📦 Building Docker images with API URL: $VITE_API_URL"

# Build the images with the correct build args
docker-compose build --build-arg VITE_API_URL=$VITE_API_URL

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
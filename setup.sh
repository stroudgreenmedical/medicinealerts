#!/bin/bash

# MHRA Alerts Automator - Initial Setup Script

set -e

echo "======================================"
echo "MHRA Alerts Automator - Setup"
echo "======================================"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "✓ .env file created"
    echo ""
    echo "⚠ IMPORTANT: Please edit .env and update:"
    echo "  - ADMIN_PASSWORD (set a secure password)"
    echo "  - SECRET_KEY (generate with: openssl rand -hex 32)"
    echo "  - TEAMS_WEBHOOK_URL (already set from your input)"
    echo ""
else
    echo "✓ .env file already exists"
fi

# Generate secret key if needed
if grep -q "your-secret-key-here" .env; then
    echo ""
    echo "Generating secret key..."
    SECRET_KEY=$(openssl rand -hex 32)
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s/your-secret-key-here-generate-with-openssl-rand-hex-32/${SECRET_KEY}/" .env
    else
        # Linux
        sed -i "s/your-secret-key-here-generate-with-openssl-rand-hex-32/${SECRET_KEY}/" .env
    fi
    echo "✓ Secret key generated and saved"
fi

# Make scripts executable
echo "Making scripts executable..."
chmod +x deployment/*.sh
echo "✓ Scripts are executable"

# Create local directories for testing
echo "Creating local directories..."
mkdir -p data logs
echo "✓ Local directories created"

echo ""
echo "======================================"
echo "Setup Complete!"
echo "======================================"
echo ""
echo "Next steps:"
echo "1. Edit .env to set your ADMIN_PASSWORD"
echo "2. Run pre-deployment check:"
echo "   ./deployment/pre-deploy-check.sh"
echo "3. Deploy to Synology:"
echo "   ./deployment/deploy-synology.sh"
echo ""
echo "For local testing:"
echo "   cd backend"
echo "   pip install -r requirements.txt"
echo "   python main.py"
echo ""
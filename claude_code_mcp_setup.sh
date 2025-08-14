#!/bin/bash

# Script to set up Playwright MCP for Claude Code CLI

echo "Setting up Playwright MCP for Claude Code..."

# Option 1: Global install (most reliable for CLI)
echo "Installing @playwright/mcp globally..."
npm install -g @playwright/mcp

# Option 2: Check/create Claude Code config directory
CONFIG_DIR="$HOME/.config/claude"
if [ ! -d "$CONFIG_DIR" ]; then
    echo "Creating Claude Code config directory..."
    mkdir -p "$CONFIG_DIR"
fi

# Option 3: Create a claude_code_config.json if needed
CONFIG_FILE="$CONFIG_DIR/claude_code_config.json"
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Creating Claude Code config file..."
    cat > "$CONFIG_FILE" << 'EOF'
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": [
        "-y",
        "@playwright/mcp",
        "--browser", "chromium"
      ]
    }
  }
}
EOF
    echo "Config file created at: $CONFIG_FILE"
else
    echo "Config file already exists at: $CONFIG_FILE"
fi

# Option 4: Check environment variables
echo ""
echo "You may also need to set environment variables:"
echo "export CLAUDE_MCP_PLAYWRIGHT=true"
echo ""
echo "To verify Playwright MCP is available:"
echo "1. Restart your terminal"
echo "2. Run 'claude' command"
echo "3. Use '/mcp' to check loaded MCPs"

# Show current npm global packages
echo ""
echo "Currently installed global npm packages:"
npm list -g --depth=0 | grep playwright || echo "No playwright packages found globally"
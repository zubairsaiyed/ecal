#!/bin/bash

# Compute Pi Installation Script
# This script sets up the calendar server for automatic startup
# Note: The calendar sync service runs on the Display Pi, not here

set -e

echo "=== ECAL Compute Pi Installation Script ==="
echo "This will install:"
echo "  - Calendar Server (web application with /image endpoint for screenshots)"
echo ""
echo "Note: Calendar sync service runs on the Display Pi, not the Compute Pi"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run this script with sudo"
    exit 1
fi

# Get the project root directory (parent of scripts directory)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
echo "Script directory: $SCRIPT_DIR"
echo "Project directory: $PROJECT_DIR"

# Get the current user
CURRENT_USER=$(whoami)
echo "Current user: $CURRENT_USER"

# Check if virtual environment exists
if [ ! -d "$PROJECT_DIR/venv" ]; then
    echo "Warning: Virtual environment not found at $PROJECT_DIR/venv"
    echo "Please create it first with:"
    echo "  cd $PROJECT_DIR"
    echo "  python3 -m venv venv"
    echo "  source venv/bin/activate"
    echo "  pip install -r requirements.txt"
    echo ""
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Installation cancelled."
        exit 1
    fi
fi

# Prompt for configuration
echo ""
echo "=== Calendar Server Configuration ==="
echo ""
read -p "Calendar server port [5000]: " CALENDAR_PORT
CALENDAR_PORT=${CALENDAR_PORT:-5000}

CALENDAR_URL="http://localhost:$CALENDAR_PORT"

echo ""
echo "Configuration Summary:"
echo "  Calendar URL: $CALENDAR_URL"
echo ""

# Install system dependencies
echo "Installing system dependencies..."
apt update
apt install -y chromium-browser
echo "Note: Chromium is used by calendar_server.py for rendering screenshots"

# Create log directory
mkdir -p /var/log/ecal
chown $CURRENT_USER:$CURRENT_USER /var/log/ecal

# Create calendar server systemd service file
cat > /etc/systemd/system/ecal-calendar-server.service << EOF
[Unit]
Description=ECAL Calendar Server
After=network.target
Wants=network.target

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$PROJECT_DIR
Environment=PATH=$PROJECT_DIR/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
Environment=PYTHONPATH=$PROJECT_DIR
ExecStart=$PROJECT_DIR/venv/bin/python3 $PROJECT_DIR/calendar_server.py
Restart=always
RestartSec=10
StandardOutput=append:/var/log/ecal/calendar-server.log
StandardError=append:/var/log/ecal/calendar-server.log

[Install]
WantedBy=multi-user.target
EOF

echo "Created systemd service file"

# Set proper permissions
chmod 644 /etc/systemd/system/ecal-calendar-server.service

# Reload systemd
systemctl daemon-reload

# Enable the service
systemctl enable ecal-calendar-server.service

echo ""
echo "=== Installation Complete ==="
echo ""
echo "Services installed:"
echo "  - ecal-calendar-server (Calendar web server)"
echo "Status: Enabled (will start on boot)"
echo ""
echo "Configuration:"
echo "  Calendar URL: $CALENDAR_URL"
echo ""
echo "=== Service Management ==="
echo "To start the service now:"
echo "  sudo systemctl start ecal-calendar-server"
echo ""
echo "To check status:"
echo "  sudo systemctl status ecal-calendar-server"
echo ""
echo "To view logs:"
echo "  sudo journalctl -u ecal-calendar-server -f"
echo "  tail -f /var/log/ecal/calendar-server.log"
echo ""
echo "=== Important Notes ==="
echo "1. Make sure your virtual environment is set up with:"
echo "     python3 -m venv venv"
echo "     source venv/bin/activate"
echo "     pip install -r requirements.txt"
echo ""
echo "2. Ensure you have:"
echo "     - service-account-key.json for Google Calendar access"
echo ""
echo "3. Test the calendar server:"
echo "     curl $CALENDAR_URL"
echo "     curl $CALENDAR_URL/image/hash"
echo ""
echo "4. The calendar sync service runs on the Display Pi, not here"
echo "   Configure it on the Display Pi using its web interface or config.json"
echo ""
echo "For more information, see:"
echo "  - ARCHITECTURE.md (system architecture)"
echo "  - QUICK_START.md (quick setup guide)"
echo "  - scripts/README.md (installation details)" 
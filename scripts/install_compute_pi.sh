#!/bin/bash

# Compute Pi Installation Script
# This script sets up the calendar server and sync service for automatic startup

set -e

echo "=== Compute Pi Installation Script ==="
echo "This will install the calendar server and sync service as systemd services"
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

# Install system dependencies
echo "Installing system dependencies..."
apt update
apt install -y chromium-browser

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
Environment=PATH=$PROJECT_DIR/venv/bin
ExecStart=$PROJECT_DIR/venv/bin/python3 $PROJECT_DIR/calendar_server.py
Restart=always
RestartSec=10
StandardOutput=append:/var/log/ecal/calendar-server.log
StandardError=append:/var/log/ecal/calendar-server.log

[Install]
WantedBy=multi-user.target
EOF

# Create calendar sync service systemd service file
cat > /etc/systemd/system/ecal-calendar-sync.service << EOF
[Unit]
Description=ECAL Calendar Sync Service
After=ecal-calendar-server.service
Wants=ecal-calendar-server.service

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$PROJECT_DIR
Environment=PATH=$PROJECT_DIR/venv/bin
ExecStart=$PROJECT_DIR/venv/bin/python3 $PROJECT_DIR/calendar_sync_service.py --scheduled
Restart=always
RestartSec=30
StandardOutput=append:/var/log/ecal/calendar-sync.log
StandardError=append:/var/log/ecal/calendar-sync.log

[Install]
WantedBy=multi-user.target
EOF

echo "Created systemd service files"

# Set proper permissions
chmod 644 /etc/systemd/system/ecal-calendar-server.service
chmod 644 /etc/systemd/system/ecal-calendar-sync.service

# Reload systemd
systemctl daemon-reload

# Enable the services
systemctl enable ecal-calendar-server.service
systemctl enable ecal-calendar-sync.service

echo ""
echo "=== Installation Complete ==="
echo "Services:"
echo "  - ecal-calendar-server (Calendar web server)"
echo "  - ecal-calendar-sync (Calendar sync service)"
echo "Status: Enabled (will start on boot)"
echo ""
echo "To start the services now:"
echo "  sudo systemctl start ecal-calendar-server"
echo "  sudo systemctl start ecal-calendar-sync"
echo ""
echo "To check status:"
echo "  sudo systemctl status ecal-calendar-server"
echo "  sudo systemctl status ecal-calendar-sync"
echo ""
echo "To view logs:"
echo "  sudo journalctl -u ecal-calendar-server -f"
echo "  sudo journalctl -u ecal-calendar-sync -f"
echo "  tail -f /var/log/ecal/calendar-server.log"
echo "  tail -f /var/log/ecal/calendar-sync.log"
echo ""
echo "The calendar server will run on port 5000"
echo "The sync service will upload screenshots to the Display Pi on port 8000"
echo ""
echo "Make sure your virtual environment is set up with:"
echo "  python3 -m venv venv"
echo "  source venv/bin/activate"
echo "  pip install -r requirements.txt"
echo ""
echo "Also ensure you have:"
echo "  - service-account-key.json for Google Calendar access"
echo "  - Display Pi accessible at the configured ENDPOINT_URL" 
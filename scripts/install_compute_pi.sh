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

# Get the current directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Installing from: $SCRIPT_DIR"

# Install system dependencies
echo "Installing system dependencies..."
apt update
apt install -y chromium-browser

# Create calendar server systemd service file
cat > /etc/systemd/system/ecal-calendar-server.service << EOF
[Unit]
Description=ECAL Calendar Server
After=network.target
Wants=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=$SCRIPT_DIR
Environment=PATH=$SCRIPT_DIR/venv/bin
ExecStart=$SCRIPT_DIR/venv/bin/python3 $SCRIPT_DIR/calendar_server.py
Restart=always
RestartSec=10

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
User=pi
WorkingDirectory=$SCRIPT_DIR
Environment=PATH=$SCRIPT_DIR/venv/bin
Environment=DEV_MODE=0
ExecStart=$SCRIPT_DIR/venv/bin/python3 $SCRIPT_DIR/calendar_sync_service.py
Restart=always
RestartSec=30

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
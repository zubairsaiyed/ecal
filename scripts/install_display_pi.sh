#!/bin/bash

# Display Pi Installation Script
# This script sets up the ECAL Display service with mode switching support

set -e

echo "=== ECAL Display Pi Installation Script ==="
echo "This will install the ECAL Display service with dual-mode support:"
echo "  - Image Receiver Mode: Manual image uploads via web interface"
echo "  - Calendar Sync Mode: Automatic calendar synchronization"
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

# Create log directory
mkdir -p /var/log/ecal
chown $CURRENT_USER:$CURRENT_USER /var/log/ecal

# Prompt for calendar server URL if config doesn't exist
if [ ! -f "$PROJECT_DIR/config.json" ]; then
    echo ""
    echo "=== Calendar Server Configuration ==="
    echo "Enter the calendar server URL (where calendar_server.py is running)"
    echo "Examples:"
    echo "  - http://192.168.1.100:5000 (remote server)"
    echo "  - http://compute-pi.local:5000 (hostname)"
    echo "  - http://localhost:5000 (same machine)"
    echo ""
    read -p "Calendar server URL [http://localhost:5000]: " CALENDAR_URL
    CALENDAR_URL=${CALENDAR_URL:-http://localhost:5000}
    
    echo "Creating configuration file..."
    cat > "$PROJECT_DIR/config.json" << CONFIGEOF
{
  "mode": "image_receiver",
  "calendar_sync": {
    "calendar_url": "$CALENDAR_URL"
  },
  "image_receiver": {
    "host": "0.0.0.0",
    "port": 8000
  }
}
CONFIGEOF
    chown $CURRENT_USER:$CURRENT_USER "$PROJECT_DIR/config.json"
    echo "Created config.json with calendar_url: $CALENDAR_URL"
else
    echo "Config file already exists, keeping existing configuration"
    echo ""
    echo "Current calendar_url: $(grep -o '"calendar_url": "[^"]*"' "$PROJECT_DIR/config.json" | cut -d'"' -f4)"
    echo ""
    echo "To update the calendar server URL, either:"
    echo "  1. Edit $PROJECT_DIR/config.json directly"
    echo "  2. Use the web interface when switching to calendar_sync mode"
    echo "  3. Use the /config API endpoint"
fi

# Make service_manager.py executable
chmod +x "$PROJECT_DIR/service_manager.py"
echo "Made service_manager.py executable"

# Create systemd service file with service manager
cat > /etc/systemd/system/ecal-display.service << EOF
[Unit]
Description=ECAL Display Service (Image Receiver / Calendar Sync)
After=network.target
Wants=network.target

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$PROJECT_DIR
Environment=PATH=$PROJECT_DIR/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
Environment=PYTHONPATH=$PROJECT_DIR
ExecStart=$PROJECT_DIR/venv/bin/python3 $PROJECT_DIR/image_receiver_server.py
ExecStop=/bin/kill -s TERM $MAINPID
Restart=on-failure
RestartSec=10
StandardOutput=append:/var/log/ecal/ecal-display.log
StandardError=append:/var/log/ecal/ecal-display.log

[Install]
WantedBy=multi-user.target
EOF

echo "Created systemd service file"

# Set proper permissions
chmod 644 /etc/systemd/system/ecal-display.service

# Reload systemd
systemctl daemon-reload

# Enable the service
systemctl enable ecal-display.service

echo ""
echo "=== Installation Complete ==="
echo "Service: ecal-display"
echo "Status: Enabled (will start on boot)"
echo ""
echo "Current Mode: $(cat $PROJECT_DIR/config.json | grep -o '\"mode\": \"[^\"]*\"' | cut -d'"' -f4)"
echo ""
echo "=== Service Management ==="
echo "To start the service now:"
echo "  sudo systemctl start ecal-display"
echo ""
echo "To check status:"
echo "  sudo systemctl status ecal-display"
echo ""
echo "To view logs:"
echo "  sudo journalctl -u ecal-display -f"
echo "  tail -f /var/log/ecal/ecal-display.log"
echo ""
echo "=== Mode Management ==="
echo "Switch between modes using the service manager:"
echo "  cd $PROJECT_DIR"
echo "  python3 service_manager.py status          # Check current mode"
echo "  python3 service_manager.py switch image_receiver"
echo "  python3 service_manager.py switch calendar_sync"
echo ""
echo "Or use the web interface (when in Image Receiver mode):"
echo "  http://localhost:8000/upload_form"
echo ""
echo "=== Configuration ==="
echo "Edit config.json to customize settings for each mode:"
echo "  nano $PROJECT_DIR/config.json"
echo ""
echo "Default port: 8000 (Image Receiver mode)"
echo "Logs: /var/log/ecal/ecal-display.log"
echo ""
echo "For detailed mode switching guide, see:"
echo "  $PROJECT_DIR/MODE_SWITCHING_GUIDE.md"
echo ""
echo "Make sure your virtual environment is set up with:"
echo "  python3 -m venv venv"
echo "  source venv/bin/activate"
echo "  pip install -r requirements.txt" 
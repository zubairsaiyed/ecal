#!/bin/bash

# Display Pi Installation Script
# This script sets up the image receiver server for automatic startup

set -e

echo "=== Display Pi Installation Script ==="
echo "This will install the image receiver server as a systemd service"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run this script with sudo"
    exit 1
fi

# Get the current directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Installing from: $SCRIPT_DIR"

# Get the current user
CURRENT_USER=$(whoami)
echo "Current user: $CURRENT_USER"

# Check if virtual environment exists
if [ ! -d "$SCRIPT_DIR/venv" ]; then
    echo "Warning: Virtual environment not found at $SCRIPT_DIR/venv"
    echo "Please create it first with:"
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

# Create systemd service file
cat > /etc/systemd/system/ecal-image-server.service << EOF
[Unit]
Description=ECAL Image Receiver Server
After=network.target
Wants=network.target

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$SCRIPT_DIR
Environment=PATH=$SCRIPT_DIR/venv/bin
ExecStart=$SCRIPT_DIR/venv/bin/python3 $SCRIPT_DIR/image_receiver_server.py
Restart=always
RestartSec=10
StandardOutput=append:/var/log/ecal/image-server.log
StandardError=append:/var/log/ecal/image-server.log

[Install]
WantedBy=multi-user.target
EOF

echo "Created systemd service file"

# Set proper permissions
chmod 644 /etc/systemd/system/ecal-image-server.service

# Reload systemd
systemctl daemon-reload

# Enable the service
systemctl enable ecal-image-server.service

echo ""
echo "=== Installation Complete ==="
echo "Service: ecal-image-server"
echo "Status: Enabled (will start on boot)"
echo ""
echo "To start the service now:"
echo "  sudo systemctl start ecal-image-server"
echo ""
echo "To check status:"
echo "  sudo systemctl status ecal-image-server"
echo ""
echo "To view logs:"
echo "  sudo journalctl -u ecal-image-server -f"
echo "  tail -f /var/log/ecal/image-server.log"
echo ""
echo "The image server will run on port 8000"
echo "Logs will be written to: /var/log/ecal/image-server.log"
echo "Make sure your virtual environment is set up with:"
echo "  python3 -m venv venv"
echo "  source venv/bin/activate"
echo "  pip install -r requirements.txt" 
#!/bin/bash

# Display Pi Uninstallation Script
# This script removes the ECAL Display service

set -e

echo "=== ECAL Display Pi Uninstallation Script ==="
echo "This will remove the ECAL Display service"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run this script with sudo"
    exit 1
fi

# Get the project root directory (parent of scripts directory)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "Project directory: $PROJECT_DIR"
echo ""

# Confirm uninstallation
read -p "Are you sure you want to uninstall the ECAL Display service? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Uninstallation cancelled."
    exit 1
fi

# Stop the service if running
if systemctl is-active --quiet ecal-display.service; then
    echo "Stopping ecal-display service..."
    systemctl stop ecal-display.service
fi

# Disable the service
if systemctl is-enabled --quiet ecal-display.service 2>/dev/null; then
    echo "Disabling ecal-display service..."
    systemctl disable ecal-display.service
fi

# Remove systemd service file
if [ -f /etc/systemd/system/ecal-display.service ]; then
    echo "Removing systemd service file..."
    rm /etc/systemd/system/ecal-display.service
fi

# Reload systemd
systemctl daemon-reload

# Optionally remove log directory
read -p "Remove log directory (/var/log/ecal)? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if [ -d /var/log/ecal ]; then
        echo "Removing log directory..."
        rm -rf /var/log/ecal
    fi
fi

# Optionally remove config and PID files
read -p "Remove configuration and PID files? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if [ -f "$PROJECT_DIR/config.json" ]; then
        echo "Removing config.json..."
        rm "$PROJECT_DIR/config.json"
    fi
    if [ -f "$PROJECT_DIR/service.pid" ]; then
        echo "Removing service.pid..."
        rm "$PROJECT_DIR/service.pid"
    fi
fi

echo ""
echo "=== Uninstallation Complete ==="
echo "The ECAL Display service has been removed."
echo ""
echo "Note: The following were NOT removed:"
echo "  - Python virtual environment ($PROJECT_DIR/venv)"
echo "  - Project files and scripts"
echo "  - Python packages"
echo ""
echo "To completely remove the project:"
echo "  rm -rf $PROJECT_DIR"


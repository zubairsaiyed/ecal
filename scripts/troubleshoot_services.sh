#!/bin/bash

# ECAL Service Troubleshooting Script
# This script helps diagnose and fix common service issues

set -e

echo "=== ECAL Service Troubleshooting ==="
echo ""

# Get current user and directory
CURRENT_USER=$(whoami)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Current user: $CURRENT_USER"
echo "Script directory: $SCRIPT_DIR"
echo ""

# Function to check service status
check_service() {
    local service_name=$1
    echo "=== Checking $service_name ==="
    
    if systemctl is-active --quiet $service_name; then
        echo "✅ $service_name is running"
    else
        echo "❌ $service_name is not running"
    fi
    
    if systemctl is-enabled --quiet $service_name; then
        echo "✅ $service_name is enabled (will start on boot)"
    else
        echo "❌ $service_name is not enabled"
    fi
    
    echo "Recent logs:"
    sudo journalctl -u $service_name -n 10 --no-pager
    echo ""
    
    # Check for log files
    case $service_name in
        "ecal-image-server")
            log_file="/var/log/ecal/image-server.log"
            ;;
        "ecal-calendar-server")
            log_file="/var/log/ecal/calendar-server.log"
            ;;
        "ecal-calendar-sync")
            log_file="/var/log/ecal/calendar-sync.log"
            ;;
        *)
            log_file=""
            ;;
    esac
    
    if [ -n "$log_file" ] && [ -f "$log_file" ]; then
        echo "Recent log file entries:"
        tail -n 10 "$log_file"
    elif [ -n "$log_file" ]; then
        echo "Log file not found: $log_file"
    fi
    echo ""
}

# Function to check virtual environment
check_venv() {
    echo "=== Checking Virtual Environment ==="
    
    if [ -d "$SCRIPT_DIR/venv" ]; then
        echo "✅ Virtual environment exists at $SCRIPT_DIR/venv"
        
        if [ -f "$SCRIPT_DIR/venv/bin/python3" ]; then
            echo "✅ Python executable found"
        else
            echo "❌ Python executable not found in venv"
        fi
        
        if [ -f "$SCRIPT_DIR/venv/bin/activate" ]; then
            echo "✅ Virtual environment is properly configured"
        else
            echo "❌ Virtual environment activation script not found"
        fi
    else
        echo "❌ Virtual environment not found at $SCRIPT_DIR/venv"
        echo "   Create it with: python3 -m venv venv"
    fi
    echo ""
}

# Function to check Python dependencies
check_dependencies() {
    echo "=== Checking Python Dependencies ==="
    
    if [ -f "$SCRIPT_DIR/requirements.txt" ]; then
        echo "✅ requirements.txt found"
        
        # Check if key packages are installed
        if [ -d "$SCRIPT_DIR/venv" ]; then
            source $SCRIPT_DIR/venv/bin/activate
            if python3 -c "import flask" 2>/dev/null; then
                echo "✅ Flask is installed"
            else
                echo "❌ Flask is not installed"
            fi
            
            if python3 -c "import requests" 2>/dev/null; then
                echo "✅ Requests is installed"
            else
                echo "❌ Requests is not installed"
            fi
            
            if python3 -c "import PIL" 2>/dev/null; then
                echo "✅ Pillow is installed"
            else
                echo "❌ Pillow is not installed"
            fi
        fi
    else
        echo "❌ requirements.txt not found"
    fi
    echo ""
}

# Function to check file permissions
check_permissions() {
    echo "=== Checking File Permissions ==="
    
    # Check if user owns the directory
    if [ "$(stat -c '%U' $SCRIPT_DIR)" = "$CURRENT_USER" ]; then
        echo "✅ User $CURRENT_USER owns the script directory"
    else
        echo "❌ User $CURRENT_USER does not own the script directory"
        echo "   Current owner: $(stat -c '%U' $SCRIPT_DIR)"
    fi
    
    # Check if key files are executable
    if [ -x "$SCRIPT_DIR/image_receiver_server.py" ]; then
        echo "✅ image_receiver_server.py is executable"
    else
        echo "❌ image_receiver_server.py is not executable"
    fi
    
    if [ -x "$SCRIPT_DIR/calendar_server.py" ]; then
        echo "✅ calendar_server.py is executable"
    else
        echo "❌ calendar_server.py is not executable"
    fi
    
    if [ -x "$SCRIPT_DIR/calendar_sync_service.py" ]; then
        echo "✅ calendar_sync_service.py is executable"
    else
        echo "❌ calendar_sync_service.py is not executable"
    fi
    echo ""
}

# Function to provide fix suggestions
suggest_fixes() {
    echo "=== Suggested Fixes ==="
    
    # Check if virtual environment needs to be created
    if [ ! -d "$SCRIPT_DIR/venv" ]; then
        echo "🔧 Create virtual environment:"
        echo "   cd $SCRIPT_DIR"
        echo "   python3 -m venv venv"
        echo "   source venv/bin/activate"
        echo "   pip install -r requirements.txt"
        echo ""
    fi
    
    # Check if services need to be reinstalled
    if ! systemctl is-enabled --quiet ecal-image-server 2>/dev/null; then
        echo "🔧 Reinstall Display Pi services:"
        echo "   sudo ./scripts/install_display_pi.sh"
        echo ""
    fi
    
    if ! systemctl is-enabled --quiet ecal-calendar-server 2>/dev/null; then
        echo "🔧 Reinstall Compute Pi services:"
        echo "   sudo ./scripts/install_compute_pi.sh"
        echo ""
    fi
    
    # Check if services need to be restarted
    if ! systemctl is-active --quiet ecal-image-server 2>/dev/null; then
        echo "🔧 Restart Display Pi service:"
        echo "   sudo systemctl restart ecal-image-server"
        echo ""
    fi
    
    if ! systemctl is-active --quiet ecal-calendar-server 2>/dev/null; then
        echo "🔧 Restart Compute Pi services:"
        echo "   sudo systemctl restart ecal-calendar-server"
        echo "   sudo systemctl restart ecal-calendar-sync"
        echo ""
    fi
    
    echo "🔧 View service logs:"
    echo "   sudo journalctl -u ecal-image-server -f"
    echo "   sudo journalctl -u ecal-calendar-server -f"
    echo "   sudo journalctl -u ecal-calendar-sync -f"
    echo "   tail -f /var/log/ecal/image-server.log"
    echo "   tail -f /var/log/ecal/calendar-server.log"
    echo "   tail -f /var/log/ecal/calendar-sync.log"
    echo ""
}

# Main execution
echo "Checking for Display Pi services..."
if systemctl list-unit-files | grep -q ecal-image-server; then
    check_service ecal-image-server
fi

echo "Checking for Compute Pi services..."
if systemctl list-unit-files | grep -q ecal-calendar-server; then
    check_service ecal-calendar-server
fi

if systemctl list-unit-files | grep -q ecal-calendar-sync; then
    check_service ecal-calendar-sync
fi

check_venv
check_dependencies
check_permissions
suggest_fixes

echo "=== Troubleshooting Complete ==="
echo "If issues persist, check the service logs for specific error messages." 
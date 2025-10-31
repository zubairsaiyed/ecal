#!/bin/bash

# Calendar Sync Server Script
# Run this on your SERVER/COMPUTE machine (NOT on the display client)
#
# This script polls the calendar server for changes and uploads screenshots to the display client.
# Note: The calendar server (calendar_server.py) handles screenshot generation via its /image endpoint.
# Note: The service always polls every 5 seconds for changes.

set -e

# Default configuration
CALENDAR_URL="http://localhost:5000"
DISPLAY_CLIENT_IP="raspberrypi.local"  # Change to your display Pi's IP/hostname
DISPLAY_PORT="8000"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=== ECAL Calendar Sync Server ==="
echo ""
echo "This script runs the calendar sync service on the SERVER side."
echo "It polls the calendar server for changes and uploads screenshots to your display client."
echo ""
echo "Note: Make sure calendar_server.py is running first!"
echo ""

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if calendar_sync_service.py exists
if [ ! -f "calendar_sync_service.py" ]; then
    echo -e "${RED}Error: calendar_sync_service.py not found${NC}"
    echo "Make sure you're running this from the ecal project directory"
    exit 1
fi

# Check if calendar server is accessible
echo "Testing connection to calendar server..."
if curl -s --connect-timeout 5 "${CALENDAR_URL}/image/hash" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Calendar server is reachable${NC}"
else
    echo -e "${YELLOW}⚠ Warning: Cannot reach calendar server at ${CALENDAR_URL}/image/hash${NC}"
    echo "Make sure calendar_server.py is running first!"
    echo ""
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Parse command line arguments or prompt for configuration
echo "Configuration:"
echo "--------------"
echo ""

read -p "Calendar URL [$CALENDAR_URL]: " input
CALENDAR_URL=${input:-$CALENDAR_URL}

read -p "Display Client IP/Hostname [$DISPLAY_CLIENT_IP]: " input
DISPLAY_CLIENT_IP=${input:-$DISPLAY_CLIENT_IP}

read -p "Display Client Port [$DISPLAY_PORT]: " input
DISPLAY_PORT=${input:-$DISPLAY_PORT}

# Construct endpoint URL
ENDPOINT_URL="http://${DISPLAY_CLIENT_IP}:${DISPLAY_PORT}/upload"

# Test connection to display client
echo ""
echo "Testing connection to display client..."
if curl -s --connect-timeout 5 "http://${DISPLAY_CLIENT_IP}:${DISPLAY_PORT}/" > /dev/null; then
    echo -e "${GREEN}✓ Display client is reachable${NC}"
else
    echo -e "${YELLOW}⚠ Warning: Cannot reach display client at http://${DISPLAY_CLIENT_IP}:${DISPLAY_PORT}${NC}"
    echo "Make sure:"
    echo "  1. Display client is powered on"
    echo "  2. Image receiver service is running on display client"
    echo "  3. IP address/hostname is correct"
    echo "  4. Firewall allows connections"
    echo ""
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Build command - always polls every 5 seconds
CMD="python3 calendar_sync_service.py"
CMD="$CMD --calendar-url $CALENDAR_URL"
CMD="$CMD --endpoint-url $ENDPOINT_URL"

# Summary
echo ""
echo "=== Starting Calendar Sync Server ==="
echo "Calendar URL: $CALENDAR_URL"
echo "Display Client: $ENDPOINT_URL"
echo "Poll Interval: 5 seconds (fixed)"
echo ""
echo "Press Ctrl+C to stop"
echo ""
echo "Command: $CMD"
echo ""

# Run the service
exec $CMD


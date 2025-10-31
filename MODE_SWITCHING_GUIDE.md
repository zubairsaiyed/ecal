# ECAL Display Mode Switching Guide

## Overview

Your ECAL e-paper display now supports **two operating modes**:

1. **📸 Image Receiver Mode** - Accept manual image uploads via web interface
2. **📅 Calendar Sync Mode** - Automatically sync and display calendar screenshots

You can easily switch between these modes using either the command line or the web interface.

---

## Quick Start

### Start the Service

```bash
cd /home/zuperzz/code/ecal
python3 service_manager.py start
```

Or using systemd:
```bash
sudo systemctl start ecal-display
```

The service will start `image_receiver_server.py`, which will:
- Always run the Flask server on port 8000
- Automatically start the calendar sync subprocess if mode is `calendar_sync`
- Default mode is `image_receiver`

### View Service Status

```bash
python3 service_manager.py status
```

This shows:
- Current operating mode
- Service status (running/stopped)
- Current configuration

### Stop the Service

```bash
python3 service_manager.py stop
```

---

## Switching Modes

### Method 1: Command Line

#### Set mode without restarting:
```bash
python3 service_manager.py set-mode image_receiver
# or
python3 service_manager.py set-mode calendar_sync
```

#### Switch mode and restart service:
```bash
python3 service_manager.py switch calendar_sync
# or
python3 service_manager.py switch image_receiver
```

### Method 2: Web Interface

1. Open the web interface: `http://localhost:8000/upload_form`
2. Look for the mode selector at the top of the page
3. Click "🔄 Switch to Calendar Sync" (or "Switch to Image Receiver")
4. Confirm the switch
5. The mode will switch without restarting the service (calendar sync subprocess will start/stop automatically)

---

## Mode Descriptions

### 📸 Image Receiver Mode

**Purpose:** Accept manual image uploads through the web interface

**What runs:**
- `image_receiver_server.py` (Flask server on port 8000)
- No calendar sync subprocess

**Features:**
- Web-based upload form at `http://localhost:8000/upload_form`
- Image optimization for memory efficiency
- Auto-rotation to maximize screen usage
- Auto-zoom to fill display after rotation
- Memory status monitoring

**Configuration** (`config.json`):
```json
{
  "mode": "image_receiver",
  "image_receiver": {
    "host": "0.0.0.0",
    "port": 8000
  }
}
```

**When to use:**
- Manual photo display
- Ad-hoc image sharing
- Testing different images
- Custom image display control

---

### 📅 Calendar Sync Mode

**Purpose:** Automatically monitor a calendar server and update the display when changes occur

**Features:**
- Server-side calendar rendering (calendar_server.py generates screenshots)
- Change detection via hash polling (only updates when calendar changes)
- Fixed 5-second polling interval for optimal responsiveness
- Automatic upload to display
- Separation of concerns: calendar server handles rendering, client handles sync
- Manual sync trigger via web interface
- Real-time status display in web UI

**Configuration** (`config.json`):
```json
{
  "mode": "calendar_sync",
  "calendar_sync": {
    "calendar_url": "http://localhost:5000"
  }
}
```

**Configuration Options:**
- `calendar_url`: URL of the calendar server (should point to calendar_server.py)

**Note:** The polling interval is fixed at 5 seconds. The calendar sync service automatically starts when switching to `calendar_sync` mode.

**When to use:**
- Family calendar display
- Event schedule monitoring
- Automated daily calendar updates
- Hands-free operation

---

## Configuration File

The configuration is stored in `config.json`:

```json
{
  "mode": "image_receiver",
  "calendar_sync": {
    "calendar_url": "http://localhost:5000"
  },
  "image_receiver": {
    "host": "0.0.0.0",
    "port": 8000
  }
}
```

### Editing Configuration

You can manually edit `config.json` or use the API endpoints:

**Get current config:**
```bash
curl http://localhost:8000/mode/config
```

**Update calendar sync settings:**
```bash
curl -X POST http://localhost:8000/mode/config \
  -H "Content-Type: application/json" \
  -d '{
    "mode_type": "calendar_sync",
    "calendar_url": "http://example.com/calendar"
  }'
```

---

## API Endpoints

### Get Current Mode
```bash
GET /mode
```

**Response:**
```json
{
  "mode": "image_receiver",
  "available_modes": ["image_receiver", "calendar_sync"]
}
```

### Set Mode (without restart)
```bash
POST /mode
Content-Type: application/json

{
  "mode": "calendar_sync"
}
```

### Switch Mode (with restart)
```bash
POST /mode/switch
Content-Type: application/json

{
  "mode": "calendar_sync"
}
```

### Get/Update Configuration
```bash
GET /mode/config
POST /mode/config
```

---

## Running as a System Service

To run the service automatically on boot, you can create a systemd service:

1. Create `/etc/systemd/system/ecal-display.service`:
```ini
[Unit]
Description=ECAL Display Service
After=network.target

[Service]
Type=forking
User=zuperzz
WorkingDirectory=/home/zuperzz/code/ecal
ExecStart=/usr/bin/python3 /home/zuperzz/code/ecal/service_manager.py start
ExecStop=/usr/bin/python3 /home/zuperzz/code/ecal/service_manager.py stop
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

2. Enable and start:
```bash
sudo systemctl enable ecal-display
sudo systemctl start ecal-display
```

3. Check status:
```bash
sudo systemctl status ecal-display
```

---

## Troubleshooting

### Service won't start
```bash
# Check if another service is already running
python3 service_manager.py status

# Stop any existing service
python3 service_manager.py stop

# Try starting again
python3 service_manager.py start
```

### Mode switch doesn't work
```bash
# Check config file exists and is valid
cat config.json

# Manually set mode and restart
python3 service_manager.py set-mode image_receiver
python3 service_manager.py restart
```

### Can't access web interface
- Check the service is running in `image_receiver` mode
- Verify the port in `config.json` (default: 8000)
- Check firewall settings if accessing remotely

### Calendar sync not updating
- Verify calendar server is running: `curl <calendar_url>/image/hash`
- Check that `image_receiver_server.py` is running (the calendar sync subprocess is managed by it)
- Verify the mode is set to `calendar_sync` in `config.json`
- Look at service logs for errors: `tail -f /var/log/ecal/ecal-display.log`
- Ensure `calendar_server.py` is running and accessible at the configured URL
- Check calendar sync status in the web interface: `http://localhost:8000/upload_form`

---

## Examples

### Daily Calendar Display

Set up automatic calendar updates (polls every 5 seconds):

```json
{
  "mode": "calendar_sync",
  "calendar_sync": {
    "calendar_url": "http://localhost:5000"
  }
}
```

```bash
python3 service_manager.py switch calendar_sync
```

Or switch via web interface at `http://localhost:8000/upload_form`

### Manual Photo Display

Switch to image receiver for manual control:

```bash
python3 service_manager.py switch image_receiver
```

Then open `http://localhost:8000/upload_form` to upload images.

### Calendar Sync Mode

The calendar sync service automatically polls every 5 seconds:

```json
{
  "mode": "calendar_sync",
  "calendar_sync": {
    "calendar_url": "http://localhost:5000"
  }
}
```

The polling interval is fixed at 5 seconds for optimal responsiveness.

---

## Support

For more information:
- Image optimization: See `MEMORY_OPTIMIZATION.md`
- Display features: Check `display_image.py --help`
- Calendar sync: Check `calendar_sync_service.py --help`


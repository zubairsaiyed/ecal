# ECAL Display Installation Scripts

This directory contains scripts for setting up and managing the ECAL Display system on Raspberry Pi and compute machines.

## Scripts Overview

### For Display Client: `install_display_pi.sh`
### For Compute Server: `install_compute_pi.sh`
### For Cleanup: `uninstall_display_pi.sh`

---

## `install_display_pi.sh`

**Purpose:** Installs the ECAL Display service as a systemd service with dual-mode support.

**What it does:**
- Creates default `config.json` configuration file
- Makes `service_manager.py` executable
- Creates log directory at `/var/log/ecal`
- Installs systemd service file as `ecal-display.service`
- Enables automatic startup on boot

**Usage:**
```bash
sudo ./scripts/install_display_pi.sh
```

**Requirements:**
- Must be run with sudo
- Virtual environment should be set up (will warn if missing)
- Running from the project root directory

**After installation:**
```bash
# Start the service
sudo systemctl start ecal-display

# Check status
sudo systemctl status ecal-display

# View logs
sudo journalctl -u ecal-display -f
```

---

## `install_compute_pi.sh`

**Purpose:** Installs the calendar server on a compute/server machine.

**What it does:**
- Installs chromium-browser (used by calendar_server.py for rendering screenshots)
- Creates log directory at `/var/log/ecal`
- Prompts for calendar server port
- Installs systemd service:
  - `ecal-calendar-server.service` - Calendar web application with /image endpoint
- Enables automatic startup on boot

**Note:** The calendar sync service runs on the Display Pi (as a subprocess), not on the Compute Pi.

**Usage:**
```bash
sudo ./scripts/install_compute_pi.sh
```

**Interactive Prompts:**
- Calendar server port (default: `5000`)

**Requirements:**
- Must be run with sudo
- Virtual environment should be set up
- Chromium-browser will be installed automatically

**After installation:**
```bash
# Start the calendar server
sudo systemctl start ecal-calendar-server

# Check status
sudo systemctl status ecal-calendar-server

# View logs
sudo journalctl -u ecal-calendar-server -f
tail -f /var/log/ecal/calendar-server.log
```

**Test the calendar server:**
```bash
curl http://localhost:5000
curl http://localhost:5000/image/hash
```

---

### `uninstall_display_pi.sh`

**Purpose:** Removes the ECAL Display service from the system.

**What it does:**
- Stops the running service
- Disables the service from auto-start
- Removes the systemd service file
- Optionally removes logs and configuration files

**Usage:**
```bash
sudo ./scripts/uninstall_display_pi.sh
```

**Requirements:**
- Must be run with sudo

**Interactive prompts:**
- Confirms uninstallation
- Asks whether to remove log directory
- Asks whether to remove config.json and PID files

---

## Two-Machine Deployment (Recommended)

This is the recommended architecture: one machine generates calendar screenshots, another displays them.

### Machine 1: Compute/Server Pi

**Setup:**
```bash
# 1. Navigate to project
cd /path/to/ecal

# 2. Set up virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Install calendar server and sync service
sudo ./scripts/install_compute_pi.sh
```

**The script will prompt for:**
- Display Pi IP/hostname
- Ports and update intervals
- Mode (dev or scheduled)

**Start services:**
```bash
sudo systemctl start ecal-calendar-server
sudo systemctl start ecal-calendar-sync
```

### Machine 2: Display Pi

**Setup:**
```bash
# 1. Navigate to project
cd /home/zuperzz/code/ecal

# 2. Set up virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Install display service
sudo ./scripts/install_display_pi.sh

# 4. Start service
sudo systemctl start ecal-display
```

**Verify:**
- Access upload form: `http://DISPLAY_PI_IP:8000/upload_form`
- Upload a test image
- Check e-paper display updates

**Architecture:**
```
┌─────────────────────┐          ┌─────────────────────┐
│   Compute/Server    │          │   Display Pi        │
│                     │  HTTP    │                     │
│  Calendar Server ───┼─────────>│  Image Receiver     │
│  (/image endpoint)  │  Upload  │  (Port 8000)        │
│  Calendar Sync ─────┼─> Polls  │                     │
│  (No Chromium)      │  Server  │                     │
└─────────────────────┘          └─────────────────────┘
```

---

## Installation Flow

### 1. Initial Setup

Before running the installation script, set up your environment:

```bash
# Clone/navigate to the project
cd /home/zuperzz/code/ecal

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Run Installation

```bash
sudo ./scripts/install_display_pi.sh
```

The script will:
1. ✅ Check for virtual environment
2. ✅ Create log directory
3. ✅ Create default config.json (if not exists)
4. ✅ Make service_manager.py executable
5. ✅ Install systemd service
6. ✅ Enable auto-start on boot

### 3. Start the Service

```bash
sudo systemctl start ecal-display
```

The service will start in the mode specified in `config.json` (default: `image_receiver`).

---

## Service Management

### Using systemd

```bash
# Start service
sudo systemctl start ecal-display

# Stop service
sudo systemctl stop ecal-display

# Restart service
sudo systemctl restart ecal-display

# Check status
sudo systemctl status ecal-display

# View logs
sudo journalctl -u ecal-display -f

# Disable auto-start
sudo systemctl disable ecal-display

# Re-enable auto-start
sudo systemctl enable ecal-display
```

### Using Service Manager

```bash
cd /home/zuperzz/code/ecal

# Check current mode and status
python3 service_manager.py status

# Switch modes
python3 service_manager.py switch image_receiver
python3 service_manager.py switch calendar_sync

# Manual start/stop (if not using systemd)
python3 service_manager.py start
python3 service_manager.py stop
python3 service_manager.py restart
```

---

## Mode Configuration

The service operates in two modes:

### 📸 Image Receiver Mode
- Web interface at `http://localhost:8000/upload_form`
- Manual image uploads
- Auto-rotation and zoom features

### 📅 Calendar Sync Mode
- Polls calendar server for changes (server handles rendering)
- Change detection via hash polling
- Configurable polling intervals

Edit `config.json` to configure mode-specific settings:

```bash
nano /home/zuperzz/code/ecal/config.json
```

After editing, restart the service:
```bash
sudo systemctl restart ecal-display
```

---

## Troubleshooting

### Service won't start

```bash
# Check service status
sudo systemctl status ecal-display

# View full logs
sudo journalctl -u ecal-display -n 50

# Check if virtual environment exists
ls -la /home/zuperzz/code/ecal/venv

# Verify config.json is valid
cat /home/zuperzz/code/ecal/config.json | python3 -m json.tool
```

### Permission issues

```bash
# Check log directory permissions
ls -la /var/log/ecal

# Fix if needed
sudo chown -R $USER:$USER /var/log/ecal
```

### Port already in use

```bash
# Check what's using port 8000
sudo lsof -i :8000

# Kill the process if needed
sudo kill <PID>
```

---

## File Locations

After installation:

| File/Directory | Location | Purpose |
|---------------|----------|---------|
| Service file | `/etc/systemd/system/ecal-display.service` | Systemd service definition |
| Config file | `/home/zuperzz/code/ecal/config.json` | Mode and settings configuration |
| Logs | `/var/log/ecal/ecal-display.log` | Service logs |
| PID file | `/home/zuperzz/code/ecal/service.pid` | Process ID tracking |

---

## Updating After Changes

If you update the code or scripts:

```bash
# Reload systemd if service file changed
sudo systemctl daemon-reload

# Restart the service
sudo systemctl restart ecal-display
```

---

## Complete Removal

To completely remove the service and all files:

```bash
# 1. Uninstall the service
sudo ./scripts/uninstall_display_pi.sh

# 2. Remove project directory (optional)
rm -rf /home/zuperzz/code/ecal
```

---

## Additional Resources

- **Mode Switching Guide:** `../MODE_SWITCHING_GUIDE.md`
- **Memory Optimization:** `../MEMORY_OPTIMIZATION.md`
- **Service Manager:** `../service_manager.py --help`

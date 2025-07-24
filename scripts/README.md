# Installation Scripts

This directory contains installation scripts for setting up the ECAL system on Raspberry Pis.

## Scripts

### `install_display_pi.sh`
**Purpose**: Sets up the Display Pi (low-memory Pi connected to e-paper display)

**What it does**:
- Creates a systemd service for `image_receiver_server.py`
- Enables automatic startup on boot
- Configures the service to run on port 8000
- Sets up proper logging and error handling

**Usage**:
```bash
sudo ./scripts/install_display_pi.sh
```

### `install_compute_pi.sh`
**Purpose**: Sets up the Compute Pi (higher-memory Pi for calendar processing)

**What it does**:
- Installs system dependencies (chromium-browser)
- Creates systemd services for both `calendar_server.py` and `calendar_sync_service.py`
- Enables automatic startup on boot
- Configures proper service dependencies (sync service waits for calendar server)
- Sets up the calendar server on port 5000
- Configures the sync service to upload to Display Pi on port 8000

**Usage**:
```bash
sudo ./scripts/install_compute_pi.sh
```

## Service Management

After installation, you can manage the services using systemctl:

**Display Pi Services**:
- `ecal-image-server` - Image receiver server

**Compute Pi Services**:
- `ecal-calendar-server` - Calendar web server
- `ecal-calendar-sync` - Calendar sync service

**Common Commands**:
```bash
# Check service status
sudo systemctl status ecal-image-server
sudo systemctl status ecal-calendar-server
sudo systemctl status ecal-calendar-sync

# View logs
sudo journalctl -u ecal-image-server -f
sudo journalctl -u ecal-calendar-server -f
sudo journalctl -u ecal-calendar-sync -f

# Restart services
sudo systemctl restart ecal-image-server
sudo systemctl restart ecal-calendar-server
sudo systemctl restart ecal-calendar-sync
```

## Prerequisites

Before running the installation scripts, ensure:

1. **Virtual Environment**: Set up and activated
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Google Calendar Setup**: 
   - `service-account-key.json` file present (for Compute Pi)

3. **Network Configuration**:
   - Display Pi accessible from Compute Pi
   - Proper firewall settings for ports 5000 and 8000

## Uninstalling

To remove the services, see the main README.md file for uninstallation instructions. 
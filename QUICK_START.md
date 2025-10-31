# ECAL Display Quick Start Guide

## 🎯 TL;DR

**Display Client (Raspberry Pi with e-paper):**
```bash
sudo ./scripts/install_display_pi.sh
sudo systemctl start ecal-display
```
Access: `http://DISPLAY_PI_IP:8000/upload_form`

**Server (Desktop/Compute Pi - for calendar sync):**
```bash
./run_calendar_sync_server.sh
```

---

## 📦 Two-Machine Setup (Recommended)

### Machine 1: Display Client (Raspberry Pi)

**What it does:** Displays images on e-paper screen

**Setup:**
```bash
cd /home/zuperzz/code/ecal

# Install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Install as service
sudo ./scripts/install_display_pi.sh

# Start service
sudo systemctl start ecal-display
```

**That's it!** The display client is now ready to receive images.

**Test it:**
- Open browser: `http://DISPLAY_PI_IP:8000/upload_form`
- Upload an image
- Watch it appear on the e-paper display

---

### Machine 2: Server (Desktop/Compute Pi)

**What it does:** Runs calendar server with screenshot generation; sync service polls and uploads to display

**Setup:**
```bash
cd /path/to/ecal  # Copy the ecal folder to your server

# Install dependencies
pip install requests pillow  # Lightweight, no display drivers needed

# Install chromium for screenshots
sudo apt-get install chromium-browser
```

**Start calendar server:**
```bash
# Terminal 1: Start calendar server (generates screenshots via /image endpoint)
python3 calendar_server.py
```

**Run calendar sync:**
```bash
# Terminal 2: Start sync service (polls server and uploads to display)
./run_calendar_sync_server.sh
```

This will:
1. Ask for your calendar server URL (e.g., `http://localhost:5000`)
2. Ask for display client IP (e.g., `192.168.1.100`)
3. Ask for polling interval
4. Start syncing!

**Or run manually:**
```bash
# Calendar server (in one terminal)
python3 calendar_server.py

# Sync service (in another terminal)
python3 calendar_sync_service.py \
  --calendar-url http://localhost:5000 \
  --endpoint-url http://192.168.1.100:8000/upload \
  --poll-interval 10
```

---

## 🖥️ One-Machine Setup (Testing Only)

If you want to test everything on one machine:

```bash
# Terminal 1: Start image receiver
python3 image_receiver_server.py

# Terminal 2: Start calendar server (generates screenshots)
python3 calendar_server.py

# Terminal 3: Start calendar sync (polls server and uploads)
python3 calendar_sync_service.py \
  --calendar-url http://localhost:5000 \
  --endpoint-url http://localhost:8000/upload \
  --poll-interval 10
```

**Note:** This is resource-intensive and not recommended for Raspberry Pi Zero/lightweight devices.

---

## 🎨 Manual Image Upload (No Calendar)

Just want to upload images manually?

**Display Client:**
```bash
sudo systemctl start ecal-display
```

**Your Computer:**
- Open browser to `http://DISPLAY_PI_IP:8000/upload_form`
- Upload images
- Configure auto-rotation and zoom options
- Click upload

---

## 📊 Architecture Summary

```
┌──────────────────┐                    ┌──────────────────┐
│  Server/Compute  │                    │  Display Client  │
│                  │                    │   (Raspberry Pi) │
├──────────────────┤                    ├──────────────────┤
│                  │                    │                  │
│  Calendar Server │                    │  Image Receiver  │
│  (Port 5000)     │                    │  (Port 8000)     │
│  /image endpoint │                    │                  │
│  (Chromium)      │                    │                  │
│                  │                    │                  │
│  Calendar Sync ──┼─── Polls Server ────┼─> E-paper Display│
│  Service         │   Downloads/Uploads│                  │
│  (No Chromium)   │                    │                  │
│                  │                    │                  │
└──────────────────┘                    └──────────────────┘
  Heavy Resources                        Light Resources
```

**Key Point:** Calendar sync runs on SERVER, not on display client!

---

## ✅ Checklist

### Display Client
- [ ] Raspberry Pi with e-paper connected
- [ ] Python virtual environment set up
- [ ] Installed via `install_display_pi.sh`
- [ ] Service running: `sudo systemctl status ecal-display`
- [ ] Can access web interface: `http://DISPLAY_PI_IP:8000/upload_form`
- [ ] Test image displays on e-paper

### Server (for Calendar Sync)
- [ ] Chromium browser installed
- [ ] Calendar app running
- [ ] Can access calendar URL
- [ ] Display client IP address known
- [ ] Run `run_calendar_sync_server.sh`
- [ ] Images appear on display

---

## 🔧 Common Issues

### "Can't reach display client"

**Check:**
```bash
# From server, test connection
curl http://DISPLAY_PI_IP:8000

# On display client, verify service
sudo systemctl status ecal-display
```

### "Screenshot generation fails"

**Check:**
```bash
# Chromium installed? (needed by calendar_server.py)
which chromium-browser

# Calendar server running?
curl http://localhost:5000

# Calendar server /image endpoint working?
curl http://localhost:5000/image/hash
```

### "Images not updating"

**Check logs:**
```bash
# On server (calendar sync)
# Logs appear in terminal

# On display client
sudo journalctl -u ecal-display -f
```

---

## 📝 Configuration Files

### Display Client: `config.json`
```json
{
  "mode": "image_receiver",
  "image_receiver": {
    "host": "0.0.0.0",
    "port": 8000
  }
}
```

**Important:** Keep mode as `image_receiver`!

### Server: Command line arguments

No config file needed. Use command line arguments:
```bash
# Start calendar server first
python3 calendar_server.py

# Then start sync service
python3 calendar_sync_service.py \
  --calendar-url http://localhost:5000 \
  --endpoint-url http://DISPLAY_IP:8000/upload \
  --poll-interval 30
```

---

## 🚀 Production Setup

### Systemd Services on Server (Recommended)

**1. Calendar Server Service**

Create `/etc/systemd/system/ecal-calendar-server.service`:
```ini
[Unit]
Description=ECAL Calendar Server
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/ecal
ExecStart=/path/to/venv/bin/python3 calendar_server.py
Restart=always

[Install]
WantedBy=multi-user.target
```

**2. Calendar Sync Service**

Create `/etc/systemd/system/ecal-calendar-sync.service`:
```ini
[Unit]
Description=ECAL Calendar Sync Service
After=ecal-calendar-server.service network.target
Requires=ecal-calendar-server.service

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/ecal
ExecStart=/path/to/venv/bin/python3 calendar_sync_service.py \
  --calendar-url http://localhost:5000 \
  --endpoint-url http://192.168.1.100:8000/upload \
  --scheduled --sleep-hours 12
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable both services:
```bash
sudo systemctl enable ecal-calendar-server
sudo systemctl enable ecal-calendar-sync
sudo systemctl start ecal-calendar-server
sudo systemctl start ecal-calendar-sync
```

**Or use the installation script:**
```bash
sudo ./scripts/install_compute_pi.sh
```

---

## 📚 More Information

- **Architecture Details:** `ARCHITECTURE.md`
- **Mode Switching:** `MODE_SWITCHING_GUIDE.md` (for advanced use)
- **Memory Optimization:** `MEMORY_OPTIMIZATION.md`
- **Installation Scripts:** `scripts/README.md`

---

## 💡 Tips

1. **Use scheduled mode for calendars** - Updates every N hours instead of constant polling
2. **Enable auto-rotation/zoom** - Maximizes use of display
3. **Monitor resources** - Check `/memory_status` endpoint on display
4. **Test connectivity first** - Make sure server can reach display client
5. **Use hostnames** - Easier than IP addresses (e.g., `raspberrypi.local`)


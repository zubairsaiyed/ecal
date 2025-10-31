# ECAL Display System Architecture

## 🏗️ System Overview

The ECAL Display system uses a **client-server architecture** where resource-intensive tasks run on powerful machines and the display client is lightweight.

```
┌─────────────────────┐          ┌─────────────────────┐
│   Server/Compute    │          │   Display Client    │
│   (Desktop/Pi)      │          │   (Raspberry Pi)    │
├─────────────────────┤          ├─────────────────────┤
│                     │          │                     │
│ - Calendar Server   │          │ - Image Receiver    │
│ - Screenshot Gen    │  HTTP    │   (Port 8000)       │
│ - Calendar Sync ────┼─────────>│                     │
│   Service           │  Upload  │ - Display Driver    │
│                     │  Images  │ - E-paper Control   │
│                     │          │                     │
└─────────────────────┘          └─────────────────────┘
      (Heavy)                          (Lightweight)
```

---

## 📦 Component Roles

### **Server/Compute Machine** (Desktop or Compute Pi)

**What runs here:**
- `calendar_server.py` - Calendar web application with screenshot generation endpoint
- `calendar_sync_service.py` - Polls server for changes and uploads screenshots
- Image processing/generation

**Resources:**
- `calendar_server.py` uses chromium-browser for screenshot rendering
- `calendar_sync_service.py` only polls server endpoints (no rendering)
- Can be any computer with Python and chromium
- Higher CPU/memory available

**Installation:**
```bash
cd /home/zuperzz/code/ecal

# Just the calendar sync service (no systemd needed)
python3 calendar_sync_service.py \
  --calendar-url http://localhost:5000 \
  --endpoint-url http://DISPLAY_PI_IP:8000/upload \
  --poll-interval 10
```

---

### **Display Client** (Raspberry Pi with E-paper)

**What runs here:**
- `image_receiver_server.py` - Web server accepting image uploads
- `display_image.py` - E-paper display driver
- Auto-rotation and image optimization

**Resources:**
- Minimal CPU/memory usage
- Only displays images, doesn't generate them
- Always in **image_receiver mode ONLY**

**Installation:**
```bash
cd /home/zuperzz/code/ecal
sudo ./scripts/install_display_pi.sh

# The service runs image_receiver mode by default
sudo systemctl start ecal-display
```

**DO NOT run calendar sync on the display client!**

---

## 🔄 Data Flow

### Manual Image Upload
```
User Browser → Upload Form (Display Client:8000) → Image Receiver → E-paper Display
```

### Calendar Sync (Automated)
```
1. Server: Calendar Web App generates calendar HTML
2. Server: calendar_server.py generates screenshot via /image endpoint
3. Server: Calendar Sync Service polls /image/hash for changes
4. Server: When hash changes, downloads image from /image endpoint
5. Server: Uploads screenshot to Display Client:8000/upload
6. Display Client: Receives image, optimizes, displays on e-paper
```

---

## ⚙️ Configuration

### **Display Client Configuration** (`config.json`)

The display client should ALWAYS be in `image_receiver` mode:

```json
{
  "mode": "image_receiver",
  "image_receiver": {
    "host": "0.0.0.0",
    "port": 8000
  }
}
```

**DO NOT set mode to `calendar_sync` on the display client!**

### **Server Configuration** (Command line arguments)

Run `calendar_sync_service.py` with appropriate arguments:

```bash
python3 calendar_sync_service.py \
  --calendar-url http://localhost:5000 \
  --endpoint-url http://192.168.1.100:8000/upload \
  --poll-interval 10
```

Where:
- `calendar-url`: Your local calendar server
- `endpoint-url`: The display client's IP address
- `poll-interval`: How often to check for changes (seconds)

---

## 🚀 Deployment Scenarios

### Scenario 1: Desktop Server + Display Client

**Server (Desktop/Laptop):**
```bash
# Terminal 1: Run calendar server
cd calendar-app
python3 app.py

# Terminal 2: Run calendar sync
cd /path/to/ecal
python3 calendar_sync_service.py \
  --calendar-url http://localhost:5000 \
  --endpoint-url http://192.168.1.100:8000/upload \
  --poll-interval 10
```

**Display Client (Raspberry Pi):**
```bash
# Installed as systemd service
sudo systemctl start ecal-display

# Or manually
cd /home/zuperzz/code/ecal
python3 image_receiver_server.py
```

### Scenario 2: Compute Pi + Display Pi

**Compute Pi (More powerful Pi):**
```bash
# Run calendar sync service
python3 calendar_sync_service.py \
  --calendar-url http://localhost:5000 \
  --endpoint-url http://display-pi.local:8000/upload \
  --scheduled  # Use scheduled mode for less frequent updates
  --sleep-hours 12
```

**Display Pi (Pi Zero or lightweight):**
```bash
# Just the image receiver
sudo systemctl start ecal-display
```

### Scenario 3: Manual Image Upload Only

**Display Client:**
```bash
# Just run the image receiver
sudo systemctl start ecal-display

# Access upload form at:
# http://DISPLAY_PI_IP:8000/upload_form
```

Upload images manually via web browser.

---

## 🎛️ Mode Management (Display Client Only)

The display client doesn't actually need mode switching. It should always run in `image_receiver` mode.

The original dual-mode design was intended for:
- Running everything on one device (for testing)
- Switching between manual uploads and automated calendar

**Recommended for production:**
- Display Client: Always `image_receiver` mode
- Server: Run `calendar_sync_service.py` separately

---

## 📝 Setup Checklist

### Display Client Setup
- [ ] Install service with `install_display_pi.sh`
- [ ] Verify mode is `image_receiver` in `config.json`
- [ ] Start service: `sudo systemctl start ecal-display`
- [ ] Test upload form: `http://DISPLAY_PI_IP:8000/upload_form`
- [ ] Verify e-paper displays images correctly

### Server Setup (for Calendar Sync)
- [ ] Install Python dependencies
- [ ] Install chromium-browser: `sudo apt-get install chromium-browser`
- [ ] Configure calendar URL
- [ ] Configure endpoint URL (display client IP)
- [ ] Test screenshot generation
- [ ] Run calendar_sync_service.py
- [ ] Verify images appear on display

---

## 🔧 Troubleshooting

### "Calendar sync not updating display"

**Problem:** Running calendar sync ON the display client
**Solution:** Run calendar sync on the server, display client only receives

### "Resource usage too high on display Pi"

**Problem:** Chromium running on display client
**Solution:** Move calendar sync to server

### "Can't access display from server"

**Problem:** Network/firewall issues
**Solution:** 
```bash
# On display client, check service is running
sudo systemctl status ecal-display

# From server, test connectivity
curl http://DISPLAY_PI_IP:8000

# Check firewall
sudo ufw status
```

---

## 📊 Resource Usage Comparison

| Task | Display Client | Server |
|------|----------------|--------|
| Chromium Screenshot | ❌ Not Recommended | ✅ Runs Here |
| Calendar Generation | ❌ Not Here | ✅ Runs Here |
| Image Receiver | ✅ Runs Here | ❌ Not Needed |
| E-paper Display | ✅ Runs Here | ❌ Not Available |
| Image Optimization | ✅ Minimal | N/A |

---

## 🎯 Best Practices

1. **Keep display client lightweight** - Only run image receiver
2. **Run heavy tasks on server** - Screenshot generation, calendar rendering
3. **Use scheduled mode for calendars** - Reduce network traffic
4. **Monitor resource usage** - Check `/memory_status` endpoint
5. **Use auto-rotation/zoom** - Maximize display usage
6. **Set appropriate poll intervals** - Balance freshness vs. resources

---

## 🔗 Related Documentation

- **Mode Switching Guide:** `MODE_SWITCHING_GUIDE.md` (mainly for testing)
- **Memory Optimization:** `MEMORY_OPTIMIZATION.md`
- **Installation Scripts:** `scripts/README.md`
- **Service Manager:** For advanced use cases only


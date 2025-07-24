# ECAL - E-Paper Calendar and Image Display System

A Python-based system for displaying images and calendars on e-paper displays, with web-based image upload capabilities.

## Applications

This project contains four main applications:

### 1. Image Receiver Server (`image_receiver_server.py`)
A Flask web server that receives uploaded images and processes them for display on e-paper.

### 2. E-Paper Image Display (`display_image.py`)
A standalone script for displaying images on a 13.3-inch e-paper display with automatic scaling and rotation.

### 3. Calendar Web Application (`calendar_server.py`)
A Flask web application for displaying Google Calendar events with customizable themes and settings.

### 4. Calendar Sync Service (`calendar_sync_service.py`)
A background service that monitors calendar changes, takes screenshots of the calendar web interface, and uploads them to an endpoint for display on e-paper.

## Features

- **Web-based image upload** via HTTP POST requests
- **Automatic image processing** with EXIF orientation correction
- **E-paper display support** for 13.3-inch displays
- **Smart image scaling** with rotation optimization
- **Virtual environment support** for clean dependency management
- **Google Calendar integration** with customizable themes
- **Web-based settings management** for calendar preferences

## Hardware Requirements

- **E-paper display**: 13.3-inch e-paper display (compatible with epd13in3E library)
- **Two Raspberry Pis**: Recommended for distributed deployment
  - **Display Pi**: Low-memory Pi connected to e-paper display
  - **Compute Pi**: Higher-memory Pi for calendar processing
- **Required libraries**: Custom e-paper display libraries in `/lib` directory

## Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd ecal
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Linux/Mac
   # or
   venv\Scripts\activate     # On Windows
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Verify hardware libraries:**
   Ensure the `/lib` directory contains the required e-paper display libraries:
   - `epd13in3E.py`
   - `epdconfig.py`
   - `DEV_Config_*.so` files

5. **Set up Google Calendar integration (optional):**
   - Create a Google Cloud project and enable Calendar API
   - Download service account key as `service-account-key.json`
   - The app will automatically create `settings.json` on first run

## Deployment Configuration

This system is designed for deployment across two Raspberry Pis:

### Display Pi (Low Memory)
- **Purpose**: Connected to e-paper display, runs lightweight image server
- **Applications**: `image_receiver_server.py` only
- **Network**: Receives image uploads from Compute Pi
- **Hardware**: E-paper display, minimal RAM requirements

### Compute Pi (Higher Memory)
- **Purpose**: Calendar processing and web interface
- **Applications**: `calendar_server.py`, `calendar_sync_service.py`
- **Network**: Sends screenshots to Display Pi
- **Hardware**: More RAM for calendar processing and web serving

### Network Configuration
- **Display Pi**: Runs image server on port 8000
- **Compute Pi**: Runs calendar server on port 5000
- **Communication**: Compute Pi uploads screenshots to Display Pi's image server

### Automatic Startup Installation
Use the provided installation scripts to set up automatic startup:

**On Display Pi:**
```bash
sudo ./scripts/install_display_pi.sh
```

**On Compute Pi:**
```bash
sudo ./scripts/install_compute_pi.sh
```

These scripts will:
- Install required system dependencies
- Set up systemd services for automatic startup
- Configure network settings
- Enable services to start on boot

### Uninstalling Services
To remove the automatic startup services:

**On Display Pi:**
```bash
sudo systemctl stop ecal-image-server
sudo systemctl disable ecal-image-server
sudo rm /etc/systemd/system/ecal-image-server.service
sudo systemctl daemon-reload
```

**On Compute Pi:**
```bash
sudo systemctl stop ecal-calendar-server ecal-calendar-sync
sudo systemctl disable ecal-calendar-server ecal-calendar-sync
sudo rm /etc/systemd/system/ecal-calendar-server.service
sudo rm /etc/systemd/system/ecal-calendar-sync.service
sudo systemctl daemon-reload
```

### Troubleshooting Services
If services are not starting properly, use the troubleshooting script:

```bash
sudo ./scripts/troubleshoot_services.sh
```

This script will:
- Check service status and recent logs
- Verify virtual environment setup
- Check Python dependencies
- Verify file permissions
- Suggest specific fixes for common issues

## Usage

### Image Receiver Server

The web server provides an HTTP interface for uploading and processing images.

**Start the server:**
```bash
python3 image_receiver_server.py
```

**Server endpoints:**
- `POST /upload` - Upload an image file
- `GET /upload_form` - Simple HTML form for testing uploads

**Example usage:**
```bash
# Test with curl
curl -X POST -F "file=@your_image.png" http://localhost:8000/upload

# Or visit in browser
http://localhost:8000/upload_form
```

### E-Paper Image Display

The standalone script for displaying images on e-paper displays.

**Basic usage:**
```bash
python3 display_image.py path/to/your/image.png
```

**Advanced options:**
```bash
# Display with zoom-to-fit (may crop image)
python3 display_image.py image.png --zoom-to-fit

# Display for 10 seconds
python3 display_image.py image.png --sleep-time 10
```

**Command line arguments:**
- `image_path` - Path to the image file to display
- `--sleep-time` - Time to display the image in seconds (default: 3)
- `--zoom-to-fit` - Scale to fill display (may crop). Default is to fit without cropping.

### Calendar Web Application

The web application provides a customizable calendar interface with Google Calendar integration.

**Start the calendar app:**
```bash
python3 calendar_server.py
```

**Access the application:**
- Main calendar: `http://localhost:5000`
- Settings page: `http://localhost:5000/settings`

**Features:**
- Multiple calendar support with color coding
- Customizable themes and display options
- Web-based settings management
- Automatic settings file creation

### Calendar Sync Service

The background service that automatically syncs calendar changes to the e-paper display.

**Start the sync service:**
```bash
python3 calendar_sync_service.py
```

**Configuration:**
- **Default Mode**: Dev mode with 10-second polling (change detection)
- **Scheduled Mode**: Use `--scheduled` flag for production mode with configurable intervals
- **Polling Interval**: `--poll-interval` for dev mode (default: 10 seconds)
- **Sleep Hours**: `--sleep-hours` for scheduled mode (default: 12 hours)
- **Calendar URL**: `--calendar-url` to specify calendar web app URL
- **Endpoint URL**: `--endpoint-url` to specify upload endpoint
- **Screenshot Path**: `--screenshot-path` to specify screenshot file location

**Usage Examples:**
```bash
# Dev mode (default) - 10-second polling with change detection
python3 calendar_sync_service.py

# Dev mode with custom polling interval
python3 calendar_sync_service.py --poll-interval 30

# Scheduled mode - 12-hour intervals
python3 calendar_sync_service.py --scheduled

# Scheduled mode with custom interval
python3 calendar_sync_service.py --scheduled --sleep-hours 6

# Custom configuration
python3 calendar_sync_service.py --calendar-url http://192.168.1.100:5000 --endpoint-url http://192.168.1.101:8000/upload
```

**Features:**
- Automatic screenshot capture of calendar web interface
- Change detection with hash comparison (dev mode)
- Configurable update intervals for both modes
- Command-line configuration for all settings
- Error handling and logging

## Configuration

### Image Processing
- **EXIF orientation**: Automatically corrected during upload
- **Image scaling**: Smart scaling with rotation optimization
- **Display modes**: Fit-without-crop (default) or zoom-to-fit

### Calendar Configuration
The application automatically creates a `settings.json` file on first run with sensible defaults. You can customize:

- **Calendar IDs**: Add your Google Calendar IDs (comma-separated)
- **Theme**: Choose from available calendar themes
- **Display options**: Weekends, zoom level, row height, etc.
- **Calendar colors**: Customize colors for each calendar

**Example settings.json:**
```json
{
  "theme": "spectra6",
  "show_weekends": true,
  "first_day": 0,
  "zoom": 150,
  "calendar_ids": "your-email@gmail.com, calendar-id@group.calendar.google.com",
  "calendar_colors": {
    "your-email@gmail.com": "vivid-blue",
    "calendar-id@group.calendar.google.com": "vivid-red"
  }
}
```

### Hardware Configuration
The e-paper display configuration is handled by the libraries in `/lib`:
- Pin assignments in `epdconfig.py`
- Display dimensions: 1200x1600 pixels
- Supported colors: Black, White, Yellow, Red, Blue, Green

## Dependencies

### Python Packages
- **Flask==2.3.3** - Web framework
- **Pillow==10.0.1** - Image processing
- **requests==2.31.0** - HTTP library
- **google-auth==2.23.4** - Google authentication
- **google-auth-oauthlib==1.1.0** - OAuth library
- **google-auth-httplib2==0.1.1** - HTTP transport
- **google-api-python-client==2.108.0** - Google API client

### System Dependencies
- **chromium-browser** - Required for calendar screenshot functionality in `calendar_sync_service.py`
  ```bash
  sudo apt update
  sudo apt install chromium-browser
  ```

### Hardware Libraries
- **epd13in3E.py** - E-paper display interface
- **epdconfig.py** - Hardware configuration
- **DEV_Config_*.so** - Binary libraries for different architectures

## File Structure

```
ecal/
├── calendar_server.py         # Calendar web application
├── calendar_sync_service.py  # Calendar sync and screenshot service
├── display_image.py           # E-paper image display script
├── image_receiver_server.py   # Flask web server
├── requirements.txt           # Python dependencies
├── README.md                 # This file
├── .gitignore                # Git ignore rules
├── scripts/                  # Installation and utility scripts
│   ├── install_display_pi.sh # Display Pi installation script
│   ├── install_compute_pi.sh # Compute Pi installation script
│   └── troubleshoot_services.sh # Service troubleshooting script
├── settings.json             # Calendar settings (auto-created)
├── service-account-key.json  # Google API credentials (user-provided)
├── templates/                # HTML templates
│   ├── calendar.html         # Calendar display template
│   └── settings.html         # Settings page template
└── lib/                      # Hardware libraries
    ├── epd13in3E.py         # E-paper display interface
    ├── epdconfig.py         # Hardware configuration
    ├── DEV_Config_*.so      # Binary libraries
    └── __init__.py          # Package initialization
```

## Development

### Virtual Environment
Always use a virtual environment to ensure dependency isolation:
```bash
source venv/bin/activate  # Activate before running
python3 image_receiver_server.py
python3 calendar_server.py
```

### Testing
- Test image upload: `curl -X POST -F "file=@test.png" http://localhost:8000/upload`
- Test e-paper display: `python3 display_image.py test.png`
- Test calendar app: Visit `http://localhost:5000` after starting `calendar_server.py`
- Test calendar sync: `python3 calendar_sync_service.py` (dev mode) or `python3 calendar_sync_service.py --scheduled` (scheduled mode)

## Troubleshooting

### Common Issues

1. **Import errors for epd13in3E:**
   - Ensure `/lib` directory contains all required files
   - Check that `sys.path.append(libdir)` is working in `display_image.py`

2. **Permission errors with hardware:**
   - Run with appropriate permissions for GPIO access
   - Ensure hardware libraries are compatible with your system

3. **Image display issues:**
   - Check image format (PNG, JPG supported)
   - Verify image file exists and is readable
   - Check e-paper display connections

### Debug Mode
Enable debug output by checking console messages for detailed information about image processing and display operations.

### Calendar Issues
- **No events showing**: Check that `service-account-key.json` exists and has proper permissions
- **Settings not saving**: Ensure `settings.json` is writable and not corrupted
- **Authentication errors**: Verify Google Cloud project has Calendar API enabled

## License

This project uses hardware libraries from Waveshare Electronics. See individual library files for specific license information.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## Support

For issues related to:
- **Hardware**: Check Waveshare documentation for your specific e-paper display
- **Software**: Check the console output for error messages
- **Dependencies**: Ensure virtual environment is activated and all packages are installed 
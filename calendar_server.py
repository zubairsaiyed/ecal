#!/usr/bin/env python3
# -*- coding:utf-8 -*-

from flask import Flask, render_template, request, jsonify, send_file
from google.oauth2 import service_account
from googleapiclient.discovery import build
import os
import json
from datetime import datetime, timedelta, date
import threading
import subprocess
import hashlib
import tempfile
import sys
import logging

app = Flask(__name__)

# Configure logging to go to stderr (which systemd/journald captures)
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stderr)
    ],
    force=True  # Override any existing configuration
)
logger = logging.getLogger(__name__)

# Configure Flask's logger to also use stderr
app.logger.setLevel(logging.INFO)
app.logger.handlers = [logging.StreamHandler(sys.stderr)]

# Helper function for compatibility with existing print() calls
def log_info(message):
    """Log to stderr (which systemd captures)"""
    logger.info(message)

# Google Calendar API configuration
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
SERVICE_ACCOUNT_FILE = 'service-account-key.json'

# Settings storage
SETTINGS_FILE = 'settings.json'
SETTINGS_DEFAULTS = {
    'theme': 'spectra6',
    'show_weekends': True,
    'first_day': 0,
    'zoom': 150,
    'hide_past_weeks': True,
    'week_count': 4,
    'equal_row_height': True,
    'wrap_event_titles': True,
    'color_event_text': True,
    'calendar_ids': '',
    'calendar_colors': {}
}
settings_lock = threading.Lock()

# Screenshot cache
screenshot_cache = {
    'path': None,
    'hash': None,
    'lock': threading.Lock()
}

def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        log_info(f"Creating default settings file: {SETTINGS_FILE}")
        log_info("Please edit this file to add your calendar IDs and customize your preferences.")
        save_settings(SETTINGS_DEFAULTS)
        return SETTINGS_DEFAULTS.copy()
    
    with open(SETTINGS_FILE, 'r') as f:
        settings = json.load(f)
    
    # MIGRATION: Remove legacy 'max_rows' if present
    if 'max_rows' in settings:
        del settings['max_rows']
        save_settings(settings)
    
    return settings

def save_settings(settings):
    with settings_lock:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=2)

def generate_calendar_screenshot(width=1600, height=1200):
    """Generate a screenshot of the calendar page using headless chromium"""
    log_info(f"Generating calendar screenshot...")
    
    # Create a temporary file for the screenshot
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
    temp_file.close()
    screenshot_path = temp_file.name
    
    try:
        # Use headless chromium to take screenshot
        cmd = [
            "chromium-browser",
            "http://localhost:5000",  # Self-referencing URL
            "--headless",
            f"--screenshot={screenshot_path}",
            f"--window-size={width},{height}",
            "--disable-gpu",
            "--no-sandbox",
            "--virtual-time-budget=3000",  # Wait 3 seconds for rendering
            "--hide-scrollbars"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            log_info(f"Screenshot failed: {result.stderr}")
            return None
        
        # Calculate hash of the image
        with open(screenshot_path, 'rb') as f:
            image_hash = hashlib.sha256(f.read()).hexdigest()
        
        log_info(f"Screenshot generated: {screenshot_path} (hash: {image_hash[:16]}...)")
        return screenshot_path, image_hash
        
    except subprocess.TimeoutExpired:
        log_info("Screenshot generation timed out")
        return None
    except Exception as e:
        log_info(f"Error generating screenshot: {e}")
        return None

def get_google_calendar_service():
    """Get authenticated Google Calendar service using service account"""
    try:
        if not os.path.exists(SERVICE_ACCOUNT_FILE):
            return None, "service-account-key.json file not found. Please create a service account and download the key."
        
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        
        service = build('calendar', 'v3', credentials=credentials)
        return service, None
    except Exception as e:
        return None, f"Error building service: {str(e)}"

def fetch_calendar_events(service, calendar_ids=None, max_results=50):
    """Fetch events from one or more Google Calendars for 6 weeks from the start of the current week"""
    try:
        settings = load_settings()
        theme = settings.get('theme', 'standard')
        calendar_colors = settings.get('calendar_colors', {})
        # Theme palettes
        spectra_palette = {
            'vivid-red': '#e60000',
            'vivid-yellow': '#ffd600',
            'vivid-blue': '#0057e7',
            'vivid-black': '#000000'
        }
        default_palette = [
            '#1E90FF', '#e60000', '#ffd600', '#28a745', '#6f42c1', '#000000'
        ]
        # Determine the first day of the week (0=Sunday, 1=Monday)
        first_day = settings.get('first_day', 1)
        today = date.today()
        # Calculate the start of the current week
        weekday = today.weekday()  # Monday=0, Sunday=6
        if first_day == 0:  # Sunday
            days_since_week_start = (today.weekday() + 1) % 7
        else:  # Monday
            days_since_week_start = today.weekday()
        week_start = today - timedelta(days=days_since_week_start)
        week_start_dt = datetime.combine(week_start, datetime.min.time())
        # Calculate the end date (6 weeks from week_start)
        week_end = week_start + timedelta(weeks=6)
        week_end_dt = datetime.combine(week_end, datetime.max.time())
        now = week_start_dt.isoformat() + 'Z'
        end_date = week_end_dt.isoformat() + 'Z'
        # Get calendar IDs from settings if not provided
        if calendar_ids is None:
            calendar_ids_str = settings.get('calendar_ids', '').strip()
            if calendar_ids_str:
                calendar_ids = [cid.strip() for cid in calendar_ids_str.split(',') if cid.strip()]
            else:
                # No calendars configured - return empty events with helpful message
                return [], "No calendars configured. Please add calendar IDs to settings."
        all_events = []
        for calendar_id in calendar_ids:
            events_result = service.events().list(
                calendarId=calendar_id,
                timeMin=now,
                timeMax=end_date,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            events = events_result.get('items', [])
            # Determine color for this calendar
            color = None
            if calendar_id in calendar_colors:
                color_key = calendar_colors[calendar_id]
                if theme == 'spectra6' and color_key in spectra_palette:
                    color = spectra_palette[color_key]
                elif theme != 'spectra6' and (color_key.startswith('#') and len(color_key) in (7, 4)):
                    color = color_key
            # Fallback to palette
            if not color:
                if theme == 'spectra6':
                    vivid_keys = list(spectra_palette.keys())
                    idx = abs(hash(calendar_id)) % len(vivid_keys)
                    color = spectra_palette[vivid_keys[idx]]
                else:
                    idx = abs(hash(calendar_id)) % len(default_palette)
                    color = default_palette[idx]
            # Convert to FullCalendar format
            for event in events:
                start_raw = event['start']
                end_raw = event['end']
                is_all_day = 'date' in start_raw and 'date' in end_raw
                if is_all_day:
                    start = start_raw['date']
                    end = end_raw['date']
                else:
                    start = start_raw.get('dateTime', start_raw.get('date'))
                    end = end_raw.get('dateTime', end_raw.get('date'))
                calendar_event = {
                    'title': event.get('summary', 'No Title'),
                    'start': start,
                    'end': end,
                    'backgroundColor': color,
                    'borderColor': color,
                    'description': event.get('description', ''),
                    'location': event.get('location', ''),
                    'calendarId': calendar_id
                }
                all_events.append(calendar_event)
        # Optionally, sort all_events by start time
        all_events.sort(key=lambda e: e['start'])
        return all_events, None
    except Exception as e:
        return [], f"Error fetching events: {str(e)}"

@app.route('/')
def index():
    """Main route - serve the calendar page"""
    settings = load_settings()
    return render_template('calendar.html', settings=settings)

@app.route('/api/events')
def get_events():
    service, error = get_google_calendar_service()
    if error:
        log_info(f'Service error: {error}')
        return jsonify({'error': error}), 500

    events, error = fetch_calendar_events(service)
    if error:
        log_info(f'Fetch error: {error}')
        return jsonify({'error': error}), 500

    log_info(f'Returning {len(events)} events')
    return jsonify(events)

@app.route('/api/calendar_list')
def api_calendar_list():
    service, error = get_google_calendar_service()
    if error:
        return jsonify({'error': error}), 500
    try:
        calendar_list = service.calendarList().list().execute()
        calendars = [
            {'id': cal['id'], 'summary': cal.get('summary', cal['id'])}
            for cal in calendar_list.get('items', [])
        ]
        return jsonify({'calendars': calendars})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/settings', methods=['GET'])
def settings_page():
    settings = load_settings()
    return render_template('settings.html', settings=settings)

@app.route('/api/settings', methods=['GET', 'POST'])
def api_settings():
    if request.method == 'GET':
        return jsonify(load_settings())
    data = request.get_json(force=True)
    settings = load_settings()
    # Only allow known keys
    for key in SETTINGS_DEFAULTS:
        if key in data:
            settings[key] = data[key]
    # Also allow calendar_colors
    if 'calendar_colors' in data:
        try:
            if isinstance(data['calendar_colors'], str):
                settings['calendar_colors'] = json.loads(data['calendar_colors'])
            else:
                settings['calendar_colors'] = data['calendar_colors']
        except Exception:
            settings['calendar_colors'] = {}
    save_settings(settings)
    return jsonify({'success': True, 'settings': settings})

@app.route('/image')
def get_calendar_image():
    """Generate and serve a screenshot of the calendar"""
    with screenshot_cache['lock']:
        # Generate new screenshot
        result = generate_calendar_screenshot()
        if not result:
            return jsonify({'error': 'Failed to generate screenshot'}), 500
        
        screenshot_path, image_hash = result
        
        # Clean up old cached screenshot if exists
        if screenshot_cache['path'] and os.path.exists(screenshot_cache['path']):
            try:
                os.remove(screenshot_cache['path'])
            except Exception as e:
                log_info(f"Warning: Could not remove old screenshot: {e}")
        
        # Update cache
        screenshot_cache['path'] = screenshot_path
        screenshot_cache['hash'] = image_hash
        
        # Send the image
        return send_file(screenshot_path, mimetype='image/png')

@app.route('/image/hash')
def get_calendar_image_hash():
    """Get the hash of the current calendar image without generating a new one"""
    with screenshot_cache['lock']:
        if screenshot_cache['hash']:
            return jsonify({'hash': screenshot_cache['hash']})
        else:
            # Generate a new screenshot to get a hash
            result = generate_calendar_screenshot()
            if not result:
                return jsonify({'error': 'Failed to generate screenshot'}), 500
            
            screenshot_path, image_hash = result
            screenshot_cache['path'] = screenshot_path
            screenshot_cache['hash'] = image_hash
            
            return jsonify({'hash': image_hash})

@app.route('/setup')
def setup():
    """Setup page with instructions"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Google Calendar Setup (Service Account)</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .step { margin: 20px 0; padding: 15px; background: #f5f5f5; border-radius: 5px; }
            .code { background: #e0e0e0; padding: 10px; border-radius: 3px; font-family: monospace; }
        </style>
    </head>
    <body>
        <h1>Google Calendar Setup (Service Account)</h1>
        
        <div class="step">
            <h2>Step 1: Create Service Account</h2>
            <ol>
                <li>Go to <a href="https://console.cloud.google.com/" target="_blank">Google Cloud Console</a></li>
                <li>Select your project</li>
                <li>Go to "IAM & Admin" > "Service Accounts"</li>
                <li>Click "Create Service Account"</li>
                <li>Name it "Calendar Display App"</li>
                <li>Click "Create and Continue"</li>
                <li>Skip role assignment, click "Done"</li>
            </ol>
        </div>
        
        <div class="step">
            <h2>Step 2: Create and Download Key</h2>
            <ol>
                <li>Click on your service account</li>
                <li>Go to "Keys" tab</li>
                <li>Click "Add Key" > "Create new key"</li>
                <li>Choose "JSON" format</li>
                <li>Download the file</li>
                <li>Rename it to <span class="code">service-account-key.json</span> and place it in this directory</li>
            </ol>
        </div>
        
        <div class="step">
            <h2>Step 3: Share Calendar</h2>
            <ol>
                <li>Go to <a href="https://calendar.google.com/" target="_blank">Google Calendar</a></li>
                <li>Find your calendar in the left sidebar</li>
                <li>Click the three dots next to it</li>
                <li>Select "Settings and sharing"</li>
                <li>Scroll down to "Share with specific people"</li>
                <li>Click "Add people"</li>
                <li>Add the service account email (found in the JSON file)</li>
                <li>Give it "Make changes to events" permission</li>
                <li>Click "Send"</li>
            </ol>
        </div>
        
        <div class="step">
            <h2>Step 4: Run the Application</h2>
            <ol>
                <li>Install required packages: <span class="code">pip install flask google-auth google-api-python-client</span></li>
                <li>Run the server: <span class="code">python app.py</span></li>
                <li>Open <a href="/" target="_blank">http://localhost:5000</a></li>
            </ol>
        </div>
        
        <div class="step">
            <h2>Current Status</h2>
            <p>Service account key: {'✅ Found' if os.path.exists('service-account-key.json') else '❌ Missing'}</p>
        </div>
    </body>
    </html>
    """

if __name__ == '__main__':
    # Move calendar.html to templates directory
    if not os.path.exists('templates'):
        os.makedirs('templates')
    
    if os.path.exists('calendar.html') and not os.path.exists('templates/calendar.html'):
        import shutil
        shutil.copy('calendar.html', 'templates/calendar.html')
    
    log_info("Flask server starting...")
    log_info("Visit http://localhost:5000 to view the calendar")
    log_info("Visit http://localhost:5000/setup for setup instructions")
    # Run with use_reloader=False to avoid double logging in systemd
    app.run(debug=False, host='0.0.0.0', port=5000, use_reloader=False) 
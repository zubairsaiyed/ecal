#!/usr/bin/env python3
# -*- coding:utf-8 -*-

from flask import Flask, render_template, request, jsonify, send_file, Response, stream_with_context
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
import time
import queue

app = Flask(__name__)

# Log buffer for streaming logs via HTTP
class LogBuffer:
    """In-memory ring buffer for storing recent logs"""
    def __init__(self, max_size=1000):
        self.max_size = max_size
        self.logs = []
        self.lock = threading.Lock()
        self.subscribers = []  # For SSE streaming
    
    def add_log(self, level, message, timestamp=None):
        """Add a log entry"""
        if timestamp is None:
            timestamp = datetime.now().isoformat()
        
        log_entry = {
            'timestamp': timestamp,
            'level': level,
            'message': message
        }
        
        with self.lock:
            self.logs.append(log_entry)
            if len(self.logs) > self.max_size:
                self.logs.pop(0)
            
            # Notify SSE subscribers
            for subscriber_queue in self.subscribers[:]:  # Copy list to avoid modification during iteration
                try:
                    subscriber_queue.put(log_entry, block=False)
                except queue.Full:
                    # Remove subscriber if queue is full (client disconnected)
                    self.subscribers.remove(subscriber_queue)
    
    def get_logs(self, limit=100):
        """Get recent logs"""
        with self.lock:
            return self.logs[-limit:]
    
    def subscribe(self):
        """Subscribe to new logs (returns a queue for SSE streaming)"""
        subscriber_queue = queue.Queue(maxsize=100)
        with self.lock:
            self.subscribers.append(subscriber_queue)
        return subscriber_queue
    
    def unsubscribe(self, subscriber_queue):
        """Unsubscribe from log updates"""
        with self.lock:
            if subscriber_queue in self.subscribers:
                self.subscribers.remove(subscriber_queue)

# Global log buffer
log_buffer = LogBuffer(max_size=1000)

# Custom log handler that writes to both stderr and log buffer
class LogBufferHandler(logging.Handler):
    """Log handler that writes to both stderr and log buffer"""
    def emit(self, record):
        try:
            msg = self.format(record)
            # Write to stderr (original behavior)
            print(msg, file=sys.stderr)
            sys.stderr.flush()
            # Also add to buffer
            log_buffer.add_log(record.levelname, msg, datetime.fromtimestamp(record.created).isoformat())
        except Exception:
            self.handleError(record)

# Configure logging to go to stderr (which systemd/journald captures) and log buffer
log_format = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
buffer_handler = LogBufferHandler()
buffer_handler.setFormatter(log_format)

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stderr),
        buffer_handler
    ],
    force=True  # Override any existing configuration
)
logger = logging.getLogger(__name__)

# Configure Flask's logger to also use stderr and buffer
app.logger.setLevel(logging.INFO)
app.logger.handlers = [logging.StreamHandler(sys.stderr), buffer_handler]

# Helper function for compatibility with existing print() calls
def log_info(message):
    """Log to stderr (which systemd captures) and log buffer"""
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
    'calendar_colors': {},
    'calendar_view': 'fullcalendar',  # 'fullcalendar' or 'grid'
    'grid_weeks': 2  # Number of weeks to display in grid view (1-4)
}
settings_lock = threading.Lock()

# Screenshot cache
screenshot_cache = {
    'path': None,
    'hash': None,
    'events_hash': None,  # Hash of calendar events to detect changes
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
        # Use --window-size to set viewport, and ensure full page capture
        # Note: --screenshot captures the viewport, so window-size must match exactly
        # Use --screenshot-full-page=false to capture only viewport (which is what we want)
        cmd = [
            "chromium-browser",
            "http://localhost:5000",  # Self-referencing URL
            "--headless=new",
            f"--screenshot={screenshot_path}",
            f"--window-size={width},{height}",
            f"--viewport-size={width},{height}",
            f"--force-device-scale-factor=1",
            "--disable-gpu",
            "--no-sandbox",
            "--virtual-time-budget=8000",  # Wait 8 seconds for rendering and JS to complete
            "--hide-scrollbars",
            "--disable-web-security",
            "--run-all-compositor-stages-before-draw",
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding",
            "--disable-features=TranslateUI",
            "--disable-ipc-flooding-protection",
            "--disable-extensions"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            log_info(f"Screenshot failed: {result.stderr}")
            return None
        
        # Verify and fix screenshot dimensions, and crop whitespace if needed
        try:
            from PIL import Image as PILImage
            img = PILImage.open(screenshot_path)
            actual_width, actual_height = img.size
            log_info(f"Screenshot dimensions: {actual_width}x{actual_height} (expected: {width}x{height})")
            
            # Convert to RGB if needed for processing
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # If screenshot is taller than expected, crop from bottom to exact height
            if actual_height > height:
                log_info(f"Screenshot is taller than expected ({actual_height} > {height}), cropping from bottom")
                img = img.crop((0, 0, actual_width, height))
                actual_height = height
                log_info(f"After height crop: {img.size[0]}x{img.size[1]}")
            
            # Detect and crop whitespace from bottom using PIL (no numpy required)
            # Strategy: Find the last row with significant content (non-white pixels)
            white_threshold = 240  # Consider pixels with RGB > 240 as white
            content_threshold = 0.02  # Need at least 2% non-white pixels to be considered content
            pixels = img.load()
            sample_step = max(1, actual_width // 50)  # Sample every Nth pixel for performance
            
            log_info(f"Scanning for last content row (checking last {min(400, actual_height)} rows)")
            rows_to_check = min(400, actual_height)  # Check last 400 rows
            
            # Find the last row with significant content
            last_content_row = None
            for y in range(actual_height - 1, max(-1, actual_height - rows_to_check - 1), -1):
                non_white_count = 0
                sampled_pixels = 0
                
                for x in range(0, actual_width, sample_step):
                    r, g, b = pixels[x, y]
                    # Count non-white pixels
                    if not (r > white_threshold and g > white_threshold and b > white_threshold):
                        non_white_count += 1
                    sampled_pixels += 1
                
                non_white_ratio = non_white_count / sampled_pixels if sampled_pixels > 0 else 0
                
                if non_white_ratio >= content_threshold:
                    last_content_row = y
                    log_info(f"Found last content row at y={y} (non-white ratio: {non_white_ratio:.2%})")
                    break
            
            # Also check for consecutive white rows as a fallback
            bottom_crop = actual_height
            consecutive_white_rows = 0
            required_white_rows = 3  # Reduced to 3 for more aggressive detection
            
            for y in range(actual_height - 1, max(-1, actual_height - rows_to_check - 1), -1):
                white_pixel_count = 0
                sampled_pixels = 0
                for x in range(0, actual_width, sample_step):
                    r, g, b = pixels[x, y]
                    if r > white_threshold and g > white_threshold and b > white_threshold:
                        white_pixel_count += 1
                    sampled_pixels += 1
                
                white_ratio = white_pixel_count / sampled_pixels if sampled_pixels > 0 else 0
                if white_ratio > 0.90:  # 90% white pixels
                    consecutive_white_rows += 1
                    if consecutive_white_rows >= required_white_rows:
                        bottom_crop = y + 1  # Crop just before the white rows start
                        log_info(f"Found {consecutive_white_rows} consecutive white rows starting at y={y}, will crop to {bottom_crop}")
                        break
                else:
                    consecutive_white_rows = 0
            
            # Use the more aggressive of the two methods
            if last_content_row is not None:
                # Add a small buffer (5 pixels) to ensure we don't cut off content
                suggested_crop = last_content_row + 6
                if suggested_crop < bottom_crop:
                    bottom_crop = suggested_crop
                    log_info(f"Using content-based detection: cropping to y={bottom_crop}")
            else:
                log_info(f"Using white-row detection: cropping to y={bottom_crop}")
            
            # Check top for whitespace (less likely but check anyway)
            top_crop = 0
            consecutive_white_rows = 0
            for y in range(0, min(100, actual_height)):  # Only check first 100 rows
                white_pixel_count = 0
                sampled_pixels = 0
                for x in range(0, actual_width, sample_step):
                    r, g, b = pixels[x, y]
                    if r > white_threshold and g > white_threshold and b > white_threshold:
                        white_pixel_count += 1
                    sampled_pixels += 1
                
                white_ratio = white_pixel_count / sampled_pixels if sampled_pixels > 0 else 0
                if white_ratio > 0.90:
                    consecutive_white_rows += 1
                    if consecutive_white_rows >= required_white_rows:
                        top_crop = y
                        log_info(f"Found whitespace at top, will crop from row {top_crop}")
                        break
                else:
                    consecutive_white_rows = 0
                    top_crop = y
                    break
            
            # Crop if whitespace detected
            if top_crop > 0 or bottom_crop < actual_height:
                log_info(f"Cropping whitespace: top={top_crop}, bottom={bottom_crop} (original height={actual_height})")
                img = img.crop((0, max(0, top_crop), actual_width, min(actual_height, bottom_crop)))
                actual_height = img.size[1]
                log_info(f"After whitespace crop: {img.size[0]}x{img.size[1]}")
            
            # If dimensions don't match expected, resize to exact expected size
            if img.size[0] != width or img.size[1] != height:
                log_info(f"Resizing screenshot from {img.size[0]}x{img.size[1]} to {width}x{height}")
                # Use high-quality resampling for better results
                img = img.resize((width, height), PILImage.Resampling.LANCZOS)
                img.save(screenshot_path, 'PNG', optimize=False)
                log_info(f"Screenshot resized to exact dimensions: {width}x{height}")
            else:
                img.save(screenshot_path, 'PNG', optimize=False)
                log_info(f"Screenshot dimensions match expected: {width}x{height}")
        except Exception as e:
            log_info(f"Warning: Could not verify/resize screenshot: {e}")
            import traceback
            log_info(f"Traceback: {traceback.format_exc()}")
        
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

def compute_events_hash(events):
    """Compute a hash of calendar events to detect changes"""
    # Create a deterministic representation of events for hashing
    # Sort by start time to ensure consistent ordering
    events_data = []
    for event in sorted(events, key=lambda e: (e.get('start', ''), e.get('title', ''))):
        events_data.append({
            'title': event.get('title', ''),
            'start': event.get('start', ''),
            'end': event.get('end', ''),
            'description': event.get('description', ''),
            'location': event.get('location', ''),
            'calendarId': event.get('calendarId', '')
        })
    # Serialize to JSON string and hash it
    events_json = json.dumps(events_data, sort_keys=True)
    return hashlib.sha256(events_json.encode('utf-8')).hexdigest()

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
        
        # Deduplicate events across calendars
        # Events are considered duplicates if they have the same title, start, and end time
        seen_events = {}
        deduplicated_events = []
        
        for event in all_events:
            # Create a unique key based on title, start, and end
            event_key = (
                event.get('title', '').strip().lower(),
                event.get('start', ''),
                event.get('end', '')
            )
            
            # If we haven't seen this event before, add it
            if event_key not in seen_events:
                seen_events[event_key] = True
                deduplicated_events.append(event)
            # If we have seen it, keep the first occurrence (which may have better color/calendar info)
            # Optionally, we could merge calendar IDs if needed
        
        # Sort deduplicated events by start time
        deduplicated_events.sort(key=lambda e: e['start'])
        return deduplicated_events, None
    except Exception as e:
        return [], f"Error fetching events: {str(e)}"

@app.route('/')
def index():
    """Main route - serve the calendar page"""
    settings = load_settings()
    calendar_view = settings.get('calendar_view', 'fullcalendar')
    
    if calendar_view == 'grid':
        return render_template('calendar_grid.html', settings=settings)
    else:
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
    # Validate grid_weeks
    if 'grid_weeks' in settings:
        settings['grid_weeks'] = max(1, min(4, int(settings['grid_weeks'])))
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
        
        # Update events hash when generating screenshot
        service, error = get_google_calendar_service()
        if not error and service:
            events, _ = fetch_calendar_events(service)
            if events:
                screenshot_cache['events_hash'] = compute_events_hash(events)
        
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
    """Get the hash of the current calendar image - only regenerates if events changed"""
    with screenshot_cache['lock']:
        # Check if calendar events have changed by comparing event hashes
        service, error = get_google_calendar_service()
        if error or not service:
            # If we can't get the service, return cached hash if available
            if screenshot_cache['hash']:
                return jsonify({'hash': screenshot_cache['hash']})
            return jsonify({'error': 'Failed to get calendar service'}), 500
        
        # Fetch current events and compute their hash
        events, fetch_error = fetch_calendar_events(service)
        if fetch_error:
            # If fetch fails, return cached hash if available
            if screenshot_cache['hash']:
                log_info(f"Warning: Failed to fetch events: {fetch_error}, using cached hash")
                return jsonify({'hash': screenshot_cache['hash']})
            return jsonify({'error': fetch_error}), 500
        
        current_events_hash = compute_events_hash(events)
        
        # Only regenerate screenshot if events have changed
        if screenshot_cache['events_hash'] == current_events_hash:
            # Events haven't changed, return cached hash
            if screenshot_cache['hash']:
                return jsonify({'hash': screenshot_cache['hash']})
            # No cached hash, need to generate one
            log_info("No cached hash available, generating screenshot...")
        else:
            # Events have changed, regenerate screenshot
            log_info(f"Calendar events changed (old hash: {screenshot_cache['events_hash'][:16] if screenshot_cache['events_hash'] else 'none'}..., new hash: {current_events_hash[:16]}...), regenerating screenshot...")
        
        # Generate new screenshot
        result = generate_calendar_screenshot()
        if not result:
            # If generation fails, return cached hash if available
            if screenshot_cache['hash']:
                log_info("Warning: Screenshot generation failed, using cached hash")
                return jsonify({'hash': screenshot_cache['hash']})
            return jsonify({'error': 'Failed to generate screenshot'}), 500
        
        screenshot_path, image_hash = result
        
        # Clean up old cached screenshot if exists
        if screenshot_cache['path'] and os.path.exists(screenshot_cache['path']):
            try:
                os.remove(screenshot_cache['path'])
            except Exception as e:
                log_info(f"Warning: Could not remove old screenshot: {e}")
        
        # Update cache with new screenshot and events hash
        screenshot_cache['path'] = screenshot_path
        screenshot_cache['hash'] = image_hash
        screenshot_cache['events_hash'] = current_events_hash
        
        return jsonify({'hash': image_hash})

@app.route('/logs')
def get_logs():
    """Get recent logs as JSON"""
    limit = request.args.get('limit', 100, type=int)
    logs = log_buffer.get_logs(limit=min(limit, 1000))  # Cap at 1000
    return jsonify({
        'logs': logs,
        'count': len(logs),
        'total_buffered': len(log_buffer.logs)
    })

@app.route('/logs/stream')
def stream_logs():
    """Stream logs in real-time using Server-Sent Events (SSE)"""
    def generate():
        subscriber_queue = log_buffer.subscribe()
        try:
            # Send initial message
            yield f"data: {json.dumps({'type': 'connected', 'message': 'Log stream connected'})}\n\n"
            
            # Send recent logs first
            recent_logs = log_buffer.get_logs(limit=50)
            for log_entry in recent_logs:
                yield f"data: {json.dumps({'type': 'log', 'data': log_entry})}\n\n"
            
            # Stream new logs as they arrive
            while True:
                try:
                    log_entry = subscriber_queue.get(timeout=30)
                    yield f"data: {json.dumps({'type': 'log', 'data': log_entry})}\n\n"
                except queue.Empty:
                    # Send keepalive every 30 seconds
                    yield f"data: {json.dumps({'type': 'keepalive', 'timestamp': datetime.now().isoformat()})}\n\n"
        except GeneratorExit:
            pass
        finally:
            log_buffer.unsubscribe(subscriber_queue)
    
    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'  # Disable nginx buffering
        }
    )

@app.route('/logs/viewer')
def logs_viewer():
    """HTML page for viewing logs"""
    return render_template('logs.html')

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
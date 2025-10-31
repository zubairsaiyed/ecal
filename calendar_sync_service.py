#!/usr/bin/env python3
import time
import os
from datetime import datetime
import requests
import sys
import argparse
import tempfile

# Helper function to log to stderr (which is typically visible in service logs)
def log_info(message):
    """Log to stderr for visibility in service logs"""
    print(message, file=sys.stderr)
    sys.stderr.flush()

# Configuration
CALENDAR_URL = "http://localhost:5000"
IMAGE_ENDPOINT = f"{CALENDAR_URL}/image"
HASH_ENDPOINT = f"{CALENDAR_URL}/image/hash"

# ENDPOINT_URL is a placeholder; replace with your actual endpoint
ENDPOINT_URL = "http://raspberrypi.local:8000/upload"

def update_status(status_endpoint, fetching=None, uploading=None, error=None):
    """Update status on the image receiver server"""
    try:
        data = {}
        if fetching is not None:
            data['fetching'] = fetching
        if uploading is not None:
            data['uploading'] = uploading
        if error is not None:
            data['error'] = error
        
        if data:
            requests.post(status_endpoint, json=data, timeout=2)
    except Exception:
        # Silently fail - status updates are not critical
        pass

def download_image(image_url, local_path, status_endpoint=None):
    """Download image from the calendar server"""
    log_info(f"[{datetime.now()}] Downloading image from {image_url}...")
    update_status(status_endpoint, fetching=True, uploading=False)
    try:
        response = requests.get(image_url, timeout=30)
        if response.status_code == 200:
            with open(local_path, 'wb') as f:
                f.write(response.content)
            log_info(f"[{datetime.now()}] Image downloaded to {local_path}")
            update_status(status_endpoint, fetching=False, error=None)  # Clear any previous errors
            return True
        else:
            error_msg = f"Failed to download image: HTTP {response.status_code}"
            log_info(f"[{datetime.now()}] ERROR: {error_msg}")
            update_status(status_endpoint, fetching=False, error=error_msg)
            return False
    except requests.exceptions.ConnectionError as e:
        error_msg = f"Connection error: Calendar server unreachable at {image_url}. Is calendar_server.py running?"
        log_info(f"[{datetime.now()}] ERROR: {error_msg}")
        log_info(f"[{datetime.now()}] Full error: {e}")
        update_status(status_endpoint, fetching=False, error=error_msg)
        return False
    except Exception as e:
        error_msg = f"Error downloading image: {e}"
        log_info(f"[{datetime.now()}] ERROR: {error_msg}")
        update_status(status_endpoint, fetching=False, error=error_msg)
        return False

def upload_image_to_endpoint(image_path, endpoint_url, status_endpoint=None):
    log_info(f"[{datetime.now()}] Uploading {image_path} to endpoint {endpoint_url}...")
    update_status(status_endpoint, fetching=False, uploading=True)
    try:
        with open(image_path, 'rb') as img_file:
            files = {'file': (os.path.basename(image_path), img_file, 'image/png')}
            response = requests.post(endpoint_url, files=files)
        if response.status_code == 200:
            log_info(f"[{datetime.now()}] Image uploaded successfully.")
            update_status(status_endpoint, uploading=False, error=None)  # Clear any previous errors
        else:
            error_msg = f"Failed to upload image: HTTP {response.status_code} - {response.text[:100]}"
            log_info(f"[{datetime.now()}] ERROR: {error_msg}")
            update_status(status_endpoint, uploading=False, error=error_msg)
    except Exception as e:
        error_msg = f"Error uploading image: {e}"
        log_info(f"[{datetime.now()}] ERROR: {error_msg}")
        update_status(status_endpoint, uploading=False, error=error_msg)

def refresh_display(image_url, endpoint_url, temp_dir, status_endpoint=None):
    """Download image and upload to display endpoint"""
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png', dir=temp_dir)
    temp_file.close()
    temp_path = temp_file.name
    
    if download_image(image_url, temp_path, status_endpoint):
        upload_image_to_endpoint(temp_path, endpoint_url, status_endpoint)
    
    # Clean up temp file
    try:
        os.remove(temp_path)
    except Exception:
        pass

def get_image_hash(hash_url):
    """Get the hash of the current calendar image from the server"""
    try:
        resp = requests.get(hash_url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return data.get('hash')
        else:
            print(f"Failed to fetch hash: {resp.status_code}")
            return None
    except Exception as e:
        print(f"Error fetching hash: {e}")
        return None

def main():
    # Store original values for help text and defaults
    original_calendar_url = CALENDAR_URL
    original_endpoint_url = ENDPOINT_URL
    
    parser = argparse.ArgumentParser(description='Calendar Sync Service - Monitors calendar changes and uploads screenshots')
    parser.add_argument('--calendar-url', type=str, default=original_calendar_url,
                       help=f'Calendar server URL (default: {original_calendar_url})')
    parser.add_argument('--endpoint-url', type=str, default=original_endpoint_url,
                       help=f'Upload endpoint URL (default: {original_endpoint_url})')
    
    args = parser.parse_args()
    
    # Update configuration based on arguments
    calendar_url = args.calendar_url
    endpoint_url = args.endpoint_url
    image_endpoint = f"{calendar_url}/image"
    hash_endpoint = f"{calendar_url}/image/hash"
    
    # Fixed polling interval - always poll every 5 seconds
    poll_interval = 5
    
    # Determine status endpoint from endpoint URL (assumes same host/port)
    # Convert endpoint_url from http://host:port/upload to http://host:port/calendar_sync/status
    status_endpoint = endpoint_url.replace('/upload', '/calendar_sync/status')
    trigger_check_endpoint = status_endpoint.replace('/calendar_sync/status', '/calendar_sync/check_trigger')
    
    # Create temp directory for downloaded images
    temp_dir = tempfile.mkdtemp()
    log_info(f"[{datetime.now()}] Using temp directory: {temp_dir}")
    
    try:
        # Always do an immediate refresh when starting calendar sync mode
        log_info(f"[{datetime.now()}] ===== STARTING CALENDAR SYNC MODE =====")
        log_info(f"[{datetime.now()}] Calendar URL: {calendar_url}")
        log_info(f"[{datetime.now()}] Image endpoint: {image_endpoint}")
        log_info(f"[{datetime.now()}] Upload endpoint: {endpoint_url}")
        log_info(f"[{datetime.now()}] Status endpoint: {status_endpoint}")
        log_info(f"[{datetime.now()}] Poll interval: {poll_interval} seconds")
        log_info(f"[{datetime.now()}] Fetching latest calendar image immediately...")
        refresh_display(image_endpoint, endpoint_url, temp_dir, status_endpoint)
        log_info(f"[{datetime.now()}] ===== INITIAL IMAGE FETCHED AND DISPLAYED =====")
        
        # Get initial hash after the refresh
        last_hash = get_image_hash(hash_endpoint)
        
        log_info(f"[{datetime.now()}] Watching for calendar changes with {poll_interval}-second polling...")
        
        while True:
            time.sleep(poll_interval)
            
            # Check if manual sync was triggered
            try:
                trigger_resp = requests.get(trigger_check_endpoint, timeout=2)
                if trigger_resp.status_code == 200:
                    trigger_data = trigger_resp.json()
                    if trigger_data.get('trigger', False):
                        log_info(f"[{datetime.now()}] Manual sync triggered! Refreshing immediately...")
                        refresh_display(image_endpoint, endpoint_url, temp_dir, status_endpoint)
                        last_hash = get_image_hash(hash_endpoint)
                        continue  # Skip the normal change detection for this cycle
            except Exception:
                # Silently fail - trigger check is optional
                pass
            
            # Poll for hash changes
            new_hash = get_image_hash(hash_endpoint)
            if new_hash and new_hash != last_hash:
                log_info(f"[{datetime.now()}] Change detected! Refreshing...")
                refresh_display(image_endpoint, endpoint_url, temp_dir, status_endpoint)
                last_hash = new_hash
            elif new_hash is None:
                # Hash fetch failed - log warning but keep polling (recoverable)
                log_info(f"[{datetime.now()}] WARNING: Failed to fetch hash, will retry in {poll_interval}s")
    finally:
        # Clean up temp directory
        try:
            os.rmdir(temp_dir)
        except Exception as e:
            log_info(f"[{datetime.now()}] Warning: Could not remove temp directory: {e}")

if __name__ == "__main__":
    main() 
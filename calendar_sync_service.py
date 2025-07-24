#!/usr/bin/env python3
import subprocess
import time
import os
from datetime import datetime
import hashlib
import requests
import sys
import argparse

# Configuration
CALENDAR_URL = "http://localhost:5000"
SCREENSHOT_PATH = "cal.png"  # You can change this path/filename
WINDOW_SIZE = "1600,1200"
IMAGE_SCRIPT = "display_image.py"    # Path to your display_image.py script
SLEEP_HOURS = 12

# ENDPOINT_URL is a placeholder; replace with your actual endpoint
ENDPOINT_URL = "http://raspberrypi.local:8000/upload"

def take_screenshot(calendar_url, screenshot_path):
    cmd = [
        "chromium-browser",
        calendar_url,
        "--headless",
        f"--screenshot={screenshot_path}",
        f"--window-size={WINDOW_SIZE}",
        "--disable-gpu",
        "--no-sandbox",
        "--virtual-time-budget=2000",
        "--hide-scrollbars"
    ]
    print(f"[{datetime.now()}] Taking screenshot...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Screenshot failed: {result.stderr}")
    else:
        print(f"Screenshot saved to {screenshot_path}")

def upload_image_to_endpoint(image_path, endpoint_url):
    print(f"[{datetime.now()}] Uploading {image_path} to endpoint {endpoint_url}...")
    try:
        with open(image_path, 'rb') as img_file:
            files = {'file': (os.path.basename(image_path), img_file, 'image/png')}
            response = requests.post(endpoint_url, files=files)
        if response.status_code == 200:
            print("Image uploaded successfully.")
        else:
            print(f"Failed to upload image: {response.status_code} {response.text}")
    except Exception as e:
        print(f"Error uploading image: {e}")

def refresh_display(screenshot_path, endpoint_url):
    upload_image_to_endpoint(screenshot_path, endpoint_url)

def get_calendar_hash(calendar_url):
    try:
        resp = requests.get(calendar_url)
        if resp.status_code == 200:
            return hashlib.sha256(resp.content).hexdigest()
        else:
            print(f"Failed to fetch calendar: {resp.status_code}")
            return None
    except Exception as e:
        print(f"Error fetching calendar: {e}")
        return None

def get_image_hash(screenshot_path):
    try:
        with open(screenshot_path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
    except Exception as e:
        print(f"Error hashing screenshot: {e}")
        return None

def main():
    # Declare globals at the very beginning
    global CALENDAR_URL, ENDPOINT_URL, SCREENSHOT_PATH, SLEEP_HOURS
    
    # Store original values for help text and defaults
    original_calendar_url = CALENDAR_URL
    original_endpoint_url = ENDPOINT_URL
    original_screenshot_path = SCREENSHOT_PATH
    
    parser = argparse.ArgumentParser(description='Calendar Sync Service - Monitors calendar changes and uploads screenshots')
    parser.add_argument('--scheduled', action='store_true', 
                       help='Run in scheduled mode (default: dev mode with 10-second polling)')
    parser.add_argument('--poll-interval', type=int, default=10,
                       help='Polling interval in seconds for dev mode (default: 10)')
    parser.add_argument('--sleep-hours', type=int, default=12,
                       help='Sleep interval in hours for scheduled mode (default: 12)')
    parser.add_argument('--calendar-url', type=str, default=original_calendar_url,
                       help=f'Calendar URL to monitor (default: {original_calendar_url})')
    parser.add_argument('--endpoint-url', type=str, default=original_endpoint_url,
                       help=f'Upload endpoint URL (default: {original_endpoint_url})')
    parser.add_argument('--screenshot-path', type=str, default=original_screenshot_path,
                       help=f'Screenshot file path (default: {original_screenshot_path})')
    
    args = parser.parse_args()
    
    # Update configuration based on arguments
    CALENDAR_URL = args.calendar_url
    ENDPOINT_URL = args.endpoint_url
    SCREENSHOT_PATH = args.screenshot_path
    SLEEP_HOURS = args.sleep_hours
    
    if args.scheduled:
        print(f"[SCHEDULED MODE] Running with {SLEEP_HOURS}-hour intervals...")
        while True:
            take_screenshot(CALENDAR_URL, SCREENSHOT_PATH)
            refresh_display(SCREENSHOT_PATH, ENDPOINT_URL)
            print(f"[{datetime.now()}] Sleeping for {SLEEP_HOURS} hours...")
            time.sleep(SLEEP_HOURS * 3600)
    else:
        # Default: DEV MODE
        poll_interval = args.poll_interval
        print(f"[DEV MODE] Watching for calendar changes with {poll_interval}-second polling...")
        take_screenshot(CALENDAR_URL, SCREENSHOT_PATH)
        refresh_display(SCREENSHOT_PATH, ENDPOINT_URL)
        last_hash = get_image_hash(SCREENSHOT_PATH)
        while True:
            time.sleep(poll_interval)
            take_screenshot(CALENDAR_URL, SCREENSHOT_PATH)
            new_hash = get_image_hash(SCREENSHOT_PATH)
            if new_hash and new_hash != last_hash:
                print(f"[DEV MODE] Change detected at {datetime.now()}! Refreshing...")
                refresh_display(SCREENSHOT_PATH, ENDPOINT_URL)
                last_hash = new_hash

if __name__ == "__main__":
    main() 
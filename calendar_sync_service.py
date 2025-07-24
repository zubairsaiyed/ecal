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

def take_screenshot():
    cmd = [
        "chromium-browser",
        CALENDAR_URL,
        "--headless",
        f"--screenshot={SCREENSHOT_PATH}",
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
        print(f"Screenshot saved to {SCREENSHOT_PATH}")

def upload_image_to_endpoint(image_path):
    print(f"[{datetime.now()}] Uploading {image_path} to endpoint {ENDPOINT_URL}...")
    try:
        with open(image_path, 'rb') as img_file:
            files = {'file': (os.path.basename(image_path), img_file, 'image/png')}
            response = requests.post(ENDPOINT_URL, files=files)
        if response.status_code == 200:
            print("Image uploaded successfully.")
        else:
            print(f"Failed to upload image: {response.status_code} {response.text}")
    except Exception as e:
        print(f"Error uploading image: {e}")

def refresh_display():
    upload_image_to_endpoint(SCREENSHOT_PATH)

def get_calendar_hash():
    try:
        resp = requests.get(CALENDAR_URL)
        if resp.status_code == 200:
            return hashlib.sha256(resp.content).hexdigest()
        else:
            print(f"Failed to fetch calendar: {resp.status_code}")
            return None
    except Exception as e:
        print(f"Error fetching calendar: {e}")
        return None

def get_image_hash():
    try:
        with open(SCREENSHOT_PATH, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
    except Exception as e:
        print(f"Error hashing screenshot: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description='Calendar Sync Service - Monitors calendar changes and uploads screenshots')
    parser.add_argument('--scheduled', action='store_true', 
                       help='Run in scheduled mode (default: dev mode with 10-second polling)')
    parser.add_argument('--poll-interval', type=int, default=10,
                       help='Polling interval in seconds for dev mode (default: 10)')
    parser.add_argument('--sleep-hours', type=int, default=12,
                       help='Sleep interval in hours for scheduled mode (default: 12)')
    parser.add_argument('--calendar-url', type=str, default=CALENDAR_URL,
                       help=f'Calendar URL to monitor (default: {CALENDAR_URL})')
    parser.add_argument('--endpoint-url', type=str, default=ENDPOINT_URL,
                       help=f'Upload endpoint URL (default: {ENDPOINT_URL})')
    parser.add_argument('--screenshot-path', type=str, default=SCREENSHOT_PATH,
                       help=f'Screenshot file path (default: {SCREENSHOT_PATH})')
    
    args = parser.parse_args()
    
    # Update configuration based on arguments
    global CALENDAR_URL, ENDPOINT_URL, SCREENSHOT_PATH, SLEEP_HOURS
    CALENDAR_URL = args.calendar_url
    ENDPOINT_URL = args.endpoint_url
    SCREENSHOT_PATH = args.screenshot_path
    SLEEP_HOURS = args.sleep_hours
    
    if args.scheduled:
        print(f"[SCHEDULED MODE] Running with {SLEEP_HOURS}-hour intervals...")
        while True:
            take_screenshot()
            refresh_display()
            print(f"[{datetime.now()}] Sleeping for {SLEEP_HOURS} hours...")
            time.sleep(SLEEP_HOURS * 3600)
    else:
        # Default: DEV MODE
        poll_interval = args.poll_interval
        print(f"[DEV MODE] Watching for calendar changes with {poll_interval}-second polling...")
        take_screenshot()
        refresh_display()
        last_hash = get_image_hash()
        while True:
            time.sleep(poll_interval)
            take_screenshot()
            new_hash = get_image_hash()
            if new_hash and new_hash != last_hash:
                print(f"[DEV MODE] Change detected at {datetime.now()}! Refreshing...")
                refresh_display()
                last_hash = new_hash

if __name__ == "__main__":
    main() 
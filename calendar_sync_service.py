#!/usr/bin/env python3
import subprocess
import time
import os
from datetime import datetime
import hashlib
import requests
import sys

# Configuration
CALENDAR_URL = "http://localhost:5000"
SCREENSHOT_PATH = "cal.png"  # You can change this path/filename
WINDOW_SIZE = "1600,1200"
IMAGE_SCRIPT = "display_image.py"    # Path to your display_image.py script
SLEEP_HOURS = 12

DEV_MODE = os.environ.get('DEV_MODE', '0') == '1' or '--dev' in sys.argv
POLL_INTERVAL = 10  # seconds for dev mode

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
    if DEV_MODE:
        print("[DEV MODE] Watching for calendar changes...")
        take_screenshot()
        refresh_display()
        last_hash = get_image_hash()
        while True:
            time.sleep(POLL_INTERVAL)
            take_screenshot()
            new_hash = get_image_hash()
            if new_hash and new_hash != last_hash:
                print(f"[DEV MODE] Change detected at {datetime.now()}! Refreshing...")
                refresh_display()
                last_hash = new_hash
    else:
        while True:
            take_screenshot()
            refresh_display()
            print(f"[{datetime.now()}] Sleeping for {SLEEP_HOURS} hours...")
            time.sleep(SLEEP_HOURS * 3600)

if __name__ == "__main__":
    main() 
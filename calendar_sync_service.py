#!/usr/bin/env python3
import time
import os
from datetime import datetime
import requests
import sys
import argparse
import tempfile

# Configuration
CALENDAR_URL = "http://localhost:5000"
IMAGE_ENDPOINT = f"{CALENDAR_URL}/image"
HASH_ENDPOINT = f"{CALENDAR_URL}/image/hash"
SLEEP_HOURS = 12

# ENDPOINT_URL is a placeholder; replace with your actual endpoint
ENDPOINT_URL = "http://raspberrypi.local:8000/upload"

def download_image(image_url, local_path):
    """Download image from the calendar server"""
    print(f"[{datetime.now()}] Downloading image from {image_url}...")
    try:
        response = requests.get(image_url, timeout=30)
        if response.status_code == 200:
            with open(local_path, 'wb') as f:
                f.write(response.content)
            print(f"Image downloaded to {local_path}")
            return True
        else:
            print(f"Failed to download image: {response.status_code}")
            return False
    except Exception as e:
        print(f"Error downloading image: {e}")
        return False

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

def refresh_display(image_url, endpoint_url, temp_dir):
    """Download image and upload to display endpoint"""
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png', dir=temp_dir)
    temp_file.close()
    temp_path = temp_file.name
    
    if download_image(image_url, temp_path):
        upload_image_to_endpoint(temp_path, endpoint_url)
    
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
    parser.add_argument('--scheduled', action='store_true', 
                       help='Run in scheduled mode (default: dev mode with 10-second polling)')
    parser.add_argument('--poll-interval', type=int, default=10,
                       help='Polling interval in seconds for dev mode (default: 10)')
    parser.add_argument('--sleep-hours', type=int, default=12,
                       help='Sleep interval in hours for scheduled mode (default: 12)')
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
    sleep_hours = args.sleep_hours
    
    # Create temp directory for downloaded images
    temp_dir = tempfile.mkdtemp()
    print(f"Using temp directory: {temp_dir}")
    
    try:
        # Always do an immediate refresh when starting calendar sync mode
        print(f"[{datetime.now()}] Starting calendar sync - fetching latest image immediately...")
        refresh_display(image_endpoint, endpoint_url, temp_dir)
        print(f"[{datetime.now()}] Initial image fetched and displayed")
        
        if args.scheduled:
            print(f"[SCHEDULED MODE] Running with {sleep_hours}-hour intervals...")
            while True:
                print(f"[{datetime.now()}] Sleeping for {sleep_hours} hours...")
                time.sleep(sleep_hours * 3600)
                refresh_display(image_endpoint, endpoint_url, temp_dir)
        else:
            # Default: DEV MODE
            poll_interval = args.poll_interval
            print(f"[DEV MODE] Watching for calendar changes with {poll_interval}-second polling...")
            
            # Get initial hash after the refresh
            last_hash = get_image_hash(hash_endpoint)
            
            while True:
                time.sleep(poll_interval)
                
                # Poll for hash changes
                new_hash = get_image_hash(hash_endpoint)
                if new_hash and new_hash != last_hash:
                    print(f"[DEV MODE] Change detected at {datetime.now()}! Refreshing...")
                    refresh_display(image_endpoint, endpoint_url, temp_dir)
                    last_hash = new_hash
    finally:
        # Clean up temp directory
        try:
            os.rmdir(temp_dir)
        except Exception as e:
            print(f"Warning: Could not remove temp directory: {e}")

if __name__ == "__main__":
    main() 
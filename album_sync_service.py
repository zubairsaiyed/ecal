#!/usr/bin/env python3
import time
import os
from datetime import datetime
import requests
import sys
import argparse
import tempfile
import random
import xml.etree.ElementTree as ET
from urllib.parse import urlparse, urljoin

# Helper function to log to stderr (which is typically visible in service logs)
def log_info(message):
    """Log to stderr for visibility in service logs"""
    print(message, file=sys.stderr)
    sys.stderr.flush()

# Configuration defaults
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

def parse_rss_feed(rss_url, album_token=None):
    """Parse RSS feed from iCloud shared album and extract image URLs"""
    log_info(f"[{datetime.now()}] Fetching RSS feed from {rss_url}...")
    
    try:
        headers = {}
        if album_token:
            headers['Cookie'] = f'albumToken={album_token}'
        
        response = requests.get(rss_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Parse XML
        root = ET.fromstring(response.content)
        
        # Find namespace (RSS feeds may have namespaces)
        namespaces = {
            'atom': 'http://www.w3.org/2005/Atom',
            'media': 'http://search.yahoo.com/mrss/',
            'dc': 'http://purl.org/dc/elements/1.1/'
        }
        
        # Try to find items (handle different RSS formats)
        items = []
        if root.tag.endswith('feed'):  # Atom feed
            items = root.findall('atom:entry', namespaces) or root.findall('entry')
        else:  # RSS feed
            channel = root.find('channel')
            if channel is not None:
                items = channel.findall('item')
        
        image_urls = []
        for item in items:
            # Try to find image URL in various possible locations
            image_url = None
            
            # Check for media:content (Media RSS)
            media_content = item.find('media:content', namespaces)
            if media_content is not None:
                image_url = media_content.get('url')
            
            # Check for enclosure
            if not image_url:
                enclosure = item.find('enclosure')
                if enclosure is not None:
                    image_url = enclosure.get('url')
            
            # Check for link
            if not image_url:
                link = item.find('link')
                if link is not None:
                    image_url = link.text if link.text else link.get('href')
            
            # Check for content with image
            if not image_url:
                content = item.find('content', namespaces) or item.find('description')
                if content is not None and content.text:
                    # Try to extract image URL from HTML content
                    import re
                    img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', content.text)
                    if img_match:
                        image_url = img_match.group(1)
            
            if image_url:
                # Make URL absolute if relative
                if not image_url.startswith('http'):
                    image_url = urljoin(rss_url, image_url)
                image_urls.append(image_url)
        
        log_info(f"[{datetime.now()}] Found {len(image_urls)} images in album")
        return image_urls
        
    except requests.exceptions.RequestException as e:
        error_msg = f"Failed to fetch RSS feed: {e}"
        log_info(f"[{datetime.now()}] ERROR: {error_msg}")
        return []
    except ET.ParseError as e:
        error_msg = f"Failed to parse RSS feed: {e}"
        log_info(f"[{datetime.now()}] ERROR: {error_msg}")
        return []
    except Exception as e:
        error_msg = f"Error parsing RSS feed: {e}"
        log_info(f"[{datetime.now()}] ERROR: {error_msg}")
        return []

def get_rss_url(album_url):
    """Convert iCloud shared album URL to RSS feed URL"""
    # iCloud shared albums can have different URL formats
    # Try common RSS feed patterns
    
    # If already an RSS feed, return as-is
    if album_url.endswith('.xml') or album_url.endswith('/feed') or '/feed.xml' in album_url:
        return album_url
    
    # Try common RSS feed URL patterns
    rss_urls = [
        f"{album_url}/feed.xml",
        f"{album_url}/feed",
        f"{album_url}.xml",
        album_url.replace('/sharedalbum/', '/sharedalbum/feed.xml'),
    ]
    
    # Also try if it's a public website URL, convert to RSS
    if 'icloud.com/sharedalbum' in album_url:
        # Extract album ID if possible
        if '#' in album_url:
            album_id = album_url.split('#')[-1]
            rss_urls.insert(0, f"https://www.icloud.com/sharedalbum/{album_id}/feed.xml")
    
    # Try each URL until one works
    for rss_url in rss_urls:
        try:
            response = requests.head(rss_url, timeout=5, allow_redirects=True)
            if response.status_code == 200:
                log_info(f"[{datetime.now()}] Found RSS feed at: {rss_url}")
                return rss_url
        except Exception:
            continue
    
    # If none work, return the first one (will try to fetch and see what happens)
    log_info(f"[{datetime.now()}] Using RSS feed URL: {rss_urls[0]}")
    return rss_urls[0]

def download_image(image_url, local_path, status_endpoint=None, album_token=None):
    """Download image from URL"""
    log_info(f"[{datetime.now()}] Downloading image from {image_url}...")
    update_status(status_endpoint, fetching=True, uploading=False)
    
    try:
        headers = {}
        if album_token:
            headers['Cookie'] = f'albumToken={album_token}'
        
        response = requests.get(image_url, headers=headers, timeout=90, stream=True)
        response.raise_for_status()
        
        # Check if it's actually an image
        content_type = response.headers.get('content-type', '')
        if not content_type.startswith('image/'):
            error_msg = f"URL does not point to an image (content-type: {content_type})"
            log_info(f"[{datetime.now()}] ERROR: {error_msg}")
            update_status(status_endpoint, fetching=False, error=error_msg)
            return False
        
        with open(local_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        log_info(f"[{datetime.now()}] Image downloaded to {local_path}")
        update_status(status_endpoint, fetching=False, error=None)
        return True
        
    except requests.exceptions.RequestException as e:
        error_msg = f"Failed to download image: {e}"
        log_info(f"[{datetime.now()}] ERROR: {error_msg}")
        update_status(status_endpoint, fetching=False, error=error_msg)
        return False
    except Exception as e:
        error_msg = f"Error downloading image: {e}"
        log_info(f"[{datetime.now()}] ERROR: {error_msg}")
        update_status(status_endpoint, fetching=False, error=error_msg)
        return False

def upload_image_to_endpoint(image_path, endpoint_url, status_endpoint=None, max_retries=3, retry_delay=2):
    """Upload image with retry logic for connection refused errors"""
    log_info(f"[{datetime.now()}] Uploading {image_path} to endpoint {endpoint_url}...")
    update_status(status_endpoint, fetching=False, uploading=True)
    
    for attempt in range(max_retries):
        try:
            with open(image_path, 'rb') as img_file:
                files = {'file': (os.path.basename(image_path), img_file, 'image/png')}
                # Use auto rotation and zoom for album images
                data = {
                    'rotation_mode': 'auto',
                    'auto_zoom': 'true'
                }
                # Add a custom header to identify this upload as coming from album sync
                headers = {'X-Album-Sync-Upload': 'true'}
                response = requests.post(endpoint_url, files=files, data=data, headers=headers, timeout=90)
            if response.status_code == 200:
                log_info(f"[{datetime.now()}] Image uploaded successfully.")
                update_status(status_endpoint, uploading=False, error=None)
                return True
            else:
                error_msg = f"Failed to upload image: HTTP {response.status_code} - {response.text[:100]}"
                log_info(f"[{datetime.now()}] ERROR: {error_msg}")
                update_status(status_endpoint, uploading=False, error=error_msg)
                return False
        except requests.exceptions.ConnectionError as e:
            if attempt < max_retries - 1:
                wait_time = retry_delay * (attempt + 1)
                log_info(f"[{datetime.now()}] Connection refused, retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait_time)
                continue
            else:
                error_msg = f"Error uploading image: Connection refused after {max_retries} attempts. Is image_receiver_server.py running?"
                log_info(f"[{datetime.now()}] ERROR: {error_msg}")
                log_info(f"[{datetime.now()}] Full error: {e}")
                update_status(status_endpoint, uploading=False, error=error_msg)
                return False
        except Exception as e:
            error_msg = f"Error uploading image: {e}"
            log_info(f"[{datetime.now()}] ERROR: {error_msg}")
            update_status(status_endpoint, uploading=False, error=error_msg)
            return False
    
    return False

def display_image(image_url, endpoint_url, temp_dir, status_endpoint=None, album_token=None):
    """Download image and upload to display endpoint"""
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg', dir=temp_dir)
    temp_file.close()
    temp_path = temp_file.name
    
    if download_image(image_url, temp_path, status_endpoint, album_token):
        upload_image_to_endpoint(temp_path, endpoint_url, status_endpoint)
    
    # Clean up temp file
    try:
        os.remove(temp_path)
    except Exception:
        pass

def main():
    parser = argparse.ArgumentParser(description='Album Sync Service - Displays images from iPhone shared albums')
    parser.add_argument('--album-url', type=str, required=True,
                       help='iCloud shared album URL or RSS feed URL')
    parser.add_argument('--album-token', type=str, default=None,
                       help='Optional token for private albums')
    parser.add_argument('--endpoint-url', type=str, default=ENDPOINT_URL,
                       help=f'Upload endpoint URL (default: {ENDPOINT_URL})')
    parser.add_argument('--poll-interval', type=int, default=300,
                       help='Poll interval in seconds (default: 300)')
    parser.add_argument('--display-duration', type=int, default=30,
                       help='Display duration per image in seconds (default: 30)')
    parser.add_argument('--shuffle', action='store_true',
                       help='Shuffle images instead of sequential display')
    
    args = parser.parse_args()
    
    album_url = args.album_url
    album_token = args.album_token
    endpoint_url = args.endpoint_url
    poll_interval = args.poll_interval
    display_duration = args.display_duration
    shuffle = args.shuffle
    
    # Determine status endpoint from endpoint URL
    status_endpoint = endpoint_url.replace('/upload', '/album_sync/status')
    
    # Get RSS feed URL
    rss_url = get_rss_url(album_url)
    
    # Create temp directory for downloaded images
    temp_dir = tempfile.mkdtemp()
    log_info(f"[{datetime.now()}] Using temp directory: {temp_dir}")
    
    try:
        log_info(f"[{datetime.now()}] ===== STARTING ALBUM SYNC MODE =====")
        log_info(f"[{datetime.now()}] Album URL: {album_url}")
        log_info(f"[{datetime.now()}] RSS Feed URL: {rss_url}")
        log_info(f"[{datetime.now()}] Upload endpoint: {endpoint_url}")
        log_info(f"[{datetime.now()}] Status endpoint: {status_endpoint}")
        log_info(f"[{datetime.now()}] Poll interval: {poll_interval} seconds")
        log_info(f"[{datetime.now()}] Display duration: {display_duration} seconds")
        log_info(f"[{datetime.now()}] Shuffle: {shuffle}")
        
        displayed_images = []  # Track displayed images to avoid immediate repeats
        current_index = 0
        
        while True:
            # Fetch album images
            image_urls = parse_rss_feed(rss_url, album_token)
            
            if not image_urls:
                log_info(f"[{datetime.now()}] No images found in album, retrying in {poll_interval}s...")
                time.sleep(poll_interval)
                continue
            
            # Filter out already displayed images (unless shuffle is enabled)
            if not shuffle and displayed_images:
                available_images = [url for url in image_urls if url not in displayed_images]
                if not available_images:
                    # All images displayed, reset
                    log_info(f"[{datetime.now()}] All images displayed, resetting...")
                    displayed_images = []
                    available_images = image_urls
            else:
                available_images = image_urls
            
            # Select next image
            if shuffle:
                if available_images:
                    selected_url = random.choice(available_images)
                else:
                    selected_url = random.choice(image_urls)
            else:
                if current_index >= len(image_urls):
                    current_index = 0
                    displayed_images = []
                selected_url = image_urls[current_index]
                current_index += 1
            
            # Display the image
            log_info(f"[{datetime.now()}] Displaying image {selected_url}...")
            display_image(selected_url, endpoint_url, temp_dir, status_endpoint, album_token)
            
            # Track displayed image
            if selected_url not in displayed_images:
                displayed_images.append(selected_url)
            
            # Wait for display duration before next image
            log_info(f"[{datetime.now()}] Waiting {display_duration} seconds before next image...")
            time.sleep(display_duration)
            
            # Check for new images periodically (every poll_interval)
            # This allows the album to update without waiting for full cycle
            if len(displayed_images) % max(1, poll_interval // display_duration) == 0:
                log_info(f"[{datetime.now()}] Checking for new images in album...")
                
    finally:
        # Clean up temp directory
        try:
            os.rmdir(temp_dir)
        except Exception as e:
            log_info(f"[{datetime.now()}] Warning: Could not remove temp directory: {e}")

if __name__ == "__main__":
    main()


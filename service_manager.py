#!/usr/bin/env python3
"""
Service Manager for ECAL Display
Manages switching between Image Receiver mode and Calendar Sync mode
"""
import json
import os
import sys
import subprocess
import signal
import time
from pathlib import Path

CONFIG_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config.json')
PID_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'service.pid')

def load_config():
    """Load configuration from JSON file"""
    if not os.path.exists(CONFIG_FILE):
        print(f"Error: Config file not found at {CONFIG_FILE}")
        sys.exit(1)
    
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

def save_config(config):
    """Save configuration to JSON file"""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)
    print(f"Configuration saved to {CONFIG_FILE}")

def get_current_mode():
    """Get the current mode from config"""
    config = load_config()
    return config.get('mode', 'image_receiver')

def set_mode(mode):
    """Set the operating mode"""
    if mode not in ['image_receiver', 'calendar_sync']:
        print(f"Error: Invalid mode '{mode}'. Must be 'image_receiver' or 'calendar_sync'")
        sys.exit(1)
    
    config = load_config()
    config['mode'] = mode
    save_config(config)
    print(f"Mode set to: {mode}")

def is_service_running():
    """Check if a service is currently running"""
    if not os.path.exists(PID_FILE):
        return False
    
    try:
        with open(PID_FILE, 'r') as f:
            pid = int(f.read().strip())
        
        # Check if process is still running
        os.kill(pid, 0)
        return True
    except (OSError, ValueError):
        # Process not running or invalid PID
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
        return False

def stop_service():
    """Stop the currently running service"""
    if not is_service_running():
        print("No service is currently running")
        return
    
    try:
        with open(PID_FILE, 'r') as f:
            pid = int(f.read().strip())
        
        print(f"Stopping service (PID: {pid})...")
        os.kill(pid, signal.SIGTERM)
        
        # Wait for process to terminate
        for _ in range(10):
            try:
                os.kill(pid, 0)
                time.sleep(0.5)
            except OSError:
                break
        
        # Force kill if still running
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError:
            pass
        
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
        
        print("Service stopped")
    except Exception as e:
        print(f"Error stopping service: {e}")

def start_image_receiver():
    """Start the image receiver server"""
    config = load_config()
    receiver_config = config.get('image_receiver', {})
    
    script_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'image_receiver_server.py')
    
    print("Starting Image Receiver Server...")
    print(f"  Host: {receiver_config.get('host', '0.0.0.0')}")
    print(f"  Port: {receiver_config.get('port', 8000)}")
    
    # Start the Flask server
    process = subprocess.Popen(
        [sys.executable, script_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True
    )
    
    # Save PID
    with open(PID_FILE, 'w') as f:
        f.write(str(process.pid))
    
    print(f"Image Receiver Server started (PID: {process.pid})")
    print(f"Access the web interface at http://localhost:{receiver_config.get('port', 8000)}/upload_form")

def start_calendar_sync():
    """Start the calendar sync service"""
    config = load_config()
    sync_config = config.get('calendar_sync', {})
    receiver_config = config.get('image_receiver', {})
    
    script_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'calendar_sync_service.py')
    
    # Determine endpoint URL from image_receiver config (for local uploads)
    receiver_host = receiver_config.get('host', '0.0.0.0')
    receiver_port = receiver_config.get('port', 8000)
    
    # If host is 0.0.0.0, use localhost for the endpoint URL
    if receiver_host == '0.0.0.0':
        endpoint_host = 'localhost'
    else:
        endpoint_host = receiver_host
    
    endpoint_url = f"http://{endpoint_host}:{receiver_port}/upload"
    
    print("Starting Calendar Sync Service...")
    print(f"  Calendar URL: {sync_config.get('calendar_url', 'http://localhost:5000')}")
    print(f"  Endpoint URL: {endpoint_url}")
    print(f"  Poll Interval: 5 seconds (fixed)")
    
    # Build command arguments - always polls every 5 seconds
    cmd = [sys.executable, script_path]
    cmd.extend(['--calendar-url', sync_config.get('calendar_url', 'http://localhost:5000')])
    cmd.extend(['--endpoint-url', endpoint_url])
    
    # Start the calendar sync service with output visible (not piped)
    # This allows us to see the immediate fetch logs
    process = subprocess.Popen(
        cmd,
        stdout=None,  # Don't pipe - let stdout go to parent's stdout
        stderr=None,  # Don't pipe - let stderr go to parent's stderr
        start_new_session=True
    )
    
    # Save PID
    with open(PID_FILE, 'w') as f:
        f.write(str(process.pid))
    
    print(f"Calendar Sync Service started (PID: {process.pid})")

def start_service():
    """Start the service based on current mode"""
    if is_service_running():
        print("A service is already running. Stop it first with 'stop' command.")
        return
    
    mode = get_current_mode()
    print(f"Starting service in '{mode}' mode...")
    
    # Always start image_receiver_server.py - it manages calendar sync as a subprocess
    # when in calendar_sync mode
    start_image_receiver()

def restart_service():
    """Restart the service"""
    print("Restarting service...")
    stop_service()
    time.sleep(1)
    start_service()

def status():
    """Show service status"""
    config = load_config()
    mode = config.get('mode', 'unknown')
    
    print(f"Current Mode: {mode}")
    
    if is_service_running():
        with open(PID_FILE, 'r') as f:
            pid = int(f.read().strip())
        print(f"Service Status: Running (PID: {pid})")
    else:
        print("Service Status: Stopped")
    
    print("\nConfiguration:")
    if mode == 'image_receiver':
        receiver_config = config.get('image_receiver', {})
        print(f"  Host: {receiver_config.get('host', '0.0.0.0')}")
        print(f"  Port: {receiver_config.get('port', 8000)}")
    elif mode == 'calendar_sync':
        sync_config = config.get('calendar_sync', {})
        print(f"  Calendar URL: {sync_config.get('calendar_url', 'http://localhost:5000')}")
        print(f"  Poll Interval: 5 seconds (fixed)")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='ECAL Display Service Manager')
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Start command
    subparsers.add_parser('start', help='Start the service based on current mode')
    
    # Stop command
    subparsers.add_parser('stop', help='Stop the currently running service')
    
    # Restart command
    subparsers.add_parser('restart', help='Restart the service')
    
    # Status command
    subparsers.add_parser('status', help='Show service status')
    
    # Set mode command
    mode_parser = subparsers.add_parser('set-mode', help='Set the operating mode')
    mode_parser.add_argument('mode', choices=['image_receiver', 'calendar_sync'],
                            help='Mode to set')
    
    # Switch mode and restart
    switch_parser = subparsers.add_parser('switch', help='Switch mode and restart service')
    switch_parser.add_argument('mode', choices=['image_receiver', 'calendar_sync'],
                               help='Mode to switch to')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    if args.command == 'start':
        start_service()
    elif args.command == 'stop':
        stop_service()
    elif args.command == 'restart':
        restart_service()
    elif args.command == 'status':
        status()
    elif args.command == 'set-mode':
        set_mode(args.mode)
    elif args.command == 'switch':
        set_mode(args.mode)
        restart_service()

if __name__ == '__main__':
    main()


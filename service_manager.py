#!/usr/bin/env python3
"""
Service Manager for ECAL Display
Manages switching between Image Receiver mode and Calendar Sync mode
"""
import json
import os
import sys
import subprocess

CONFIG_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config.json')
SERVICE_NAME = 'ecal-display'

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

def run_systemctl(command):
    """Run a systemctl command"""
    try:
        result = subprocess.run(
            ['sudo', 'systemctl', command, SERVICE_NAME],
            capture_output=True,
            text=True
        )
        print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        return result.returncode == 0
    except Exception as e:
        print(f"Error running systemctl: {e}")
        return False

def start_service():
    """Start the systemd service"""
    mode = get_current_mode()
    print(f"Starting service in '{mode}' mode...")
    return run_systemctl('start')

def stop_service():
    """Stop the systemd service"""
    print(f"Stopping service...")
    return run_systemctl('stop')

def restart_service():
    """Restart the systemd service"""
    print("Restarting service...")
    return run_systemctl('restart')

def service_status():
    """Get systemd service status"""
    try:
        result = subprocess.run(
            ['sudo', 'systemctl', 'is-active', SERVICE_NAME],
            capture_output=True,
            text=True
        )
        return result.stdout.strip()
    except:
        return 'unknown'

def status():
    """Show service status"""
    config = load_config()
    mode = config.get('mode', 'unknown')
    
    print(f"Current Mode: {mode}")
    
    active_status = service_status()
    if active_status == 'active':
        print(f"Service Status: Running")
    else:
        print(f"Service Status: {active_status}")
    
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
    subparsers.add_parser('start', help='Start the systemd service')
    
    # Stop command
    subparsers.add_parser('stop', help='Stop the systemd service')
    
    # Restart command
    subparsers.add_parser('restart', help='Restart the systemd service')
    
    # Status command
    subparsers.add_parser('status', help='Show service status')
    
    # Set mode command
    mode_parser = subparsers.add_parser('set-mode', help='Set the operating mode (no restart)')
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

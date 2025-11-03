#!/usr/bin/env python3
from flask import Flask, request, jsonify, render_template
import os
import tempfile
import subprocess
import sys
import gc
import json
import threading
import time
import signal
import atexit
from datetime import datetime
from PIL import Image

app = Flask(__name__)

# Force Flask to reload templates on every request (disable template caching)
app.config['TEMPLATES_AUTO_RELOAD'] = True

# Global calendar sync process and status
_calendar_sync_process = None
_calendar_sync_lock = threading.Lock()
_calendar_sync_status = {
    'active': False,
    'last_fetch_time': None,
    'last_upload_time': None,
    'last_error': None,
    'fetching': False,
    'uploading': False
}
_manual_sync_trigger = False  # Flag to trigger manual sync

# Helper function to log to stderr (which Flask shows) for important messages
def log_info(message):
    """Log to stderr (which Flask shows in logs)"""
    print(message, file=sys.stderr)
    sys.stderr.flush()

IMAGE_SCRIPT = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'display_image.py')
CONFIG_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config.json')
SERVICE_MANAGER = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'service_manager.py')
CALENDAR_SYNC_SCRIPT = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'calendar_sync_service.py')

# Memory optimization settings
MAX_IMAGE_DIMENSION = 2000  # Maximum dimension for large images
COMPRESSION_QUALITY = 6      # PNG compression level (0-9, lower = smaller file)
ENABLE_MEMORY_OPTIMIZATION = True

def load_config():
    """Load configuration from JSON file"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    # Return default config if file doesn't exist
    return {
        'mode': 'image_receiver',
        'calendar_sync': {
            'calendar_url': 'http://localhost:5000'
        },
        'image_receiver': {
            'host': '0.0.0.0',
            'port': 8000
        }
    }

def save_config(config):
    """Save configuration to JSON file"""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

def start_calendar_sync_process():
    """Start calendar sync service as a background process"""
    global _calendar_sync_process
    
    with _calendar_sync_lock:
        if _calendar_sync_process and _calendar_sync_process.poll() is None:
            log_info(f"[{datetime.now()}] Calendar sync process already running (PID: {_calendar_sync_process.pid})")
            return True
        
        config = load_config()
        sync_config = config.get('calendar_sync', {})
        receiver_config = config.get('image_receiver', {})
        
        # Determine endpoint URL from image_receiver config
        receiver_host = receiver_config.get('host', '0.0.0.0')
        receiver_port = receiver_config.get('port', 8000)
        
        if receiver_host == '0.0.0.0':
            endpoint_host = 'localhost'
        else:
            endpoint_host = receiver_host
        
        endpoint_url = f"http://{endpoint_host}:{receiver_port}/upload"
        calendar_url = sync_config.get('calendar_url', 'http://localhost:5000')
        
        # Build command - always polls every 5 seconds
        cmd = [sys.executable, CALENDAR_SYNC_SCRIPT]
        cmd.extend(['--calendar-url', calendar_url])
        cmd.extend(['--endpoint-url', endpoint_url])
        
        log_info(f"[{datetime.now()}] Starting calendar sync process...")
        log_info(f"[{datetime.now()}] Command: {' '.join(cmd)}")
        
        # Verify the upload endpoint is accessible before starting the sync service
        try:
            import requests
            test_response = requests.get(endpoint_url.replace('/upload', '/'), timeout=2)
            log_info(f"[{datetime.now()}] Verified upload endpoint is accessible")
        except Exception as e:
            log_info(f"[{datetime.now()}] WARNING: Could not verify upload endpoint: {e}")
            log_info(f"[{datetime.now()}] Continuing anyway - sync service will retry connection...")
        
        try:
            _calendar_sync_process = subprocess.Popen(
                cmd,
                stdout=None,  # Let output go to stderr/stdout
                stderr=None,
                start_new_session=True
            )
            log_info(f"[{datetime.now()}] Calendar sync process started (PID: {_calendar_sync_process.pid})")
            _calendar_sync_status['active'] = True
            _calendar_sync_status['process_pid'] = _calendar_sync_process.pid
            return True
        except Exception as e:
            log_info(f"[{datetime.now()}] Failed to start calendar sync process: {e}")
            _calendar_sync_status['active'] = False
            _calendar_sync_status['last_error'] = str(e)
            return False

def stop_calendar_sync_process():
    """Stop calendar sync service process"""
    global _calendar_sync_process, _calendar_sync_status
    
    with _calendar_sync_lock:
        if not _calendar_sync_process:
            log_info(f"[{datetime.now()}] No calendar sync process to stop")
            _calendar_sync_status['active'] = False
            return True
        
        if _calendar_sync_process.poll() is not None:
            log_info(f"[{datetime.now()}] Calendar sync process already stopped")
            _calendar_sync_process = None
            _calendar_sync_status['active'] = False
            return True
        
        log_info(f"[{datetime.now()}] Stopping calendar sync process (PID: {_calendar_sync_process.pid})...")
        
        try:
            # Kill the entire process group to ensure child processes are also terminated
            import os
            try:
                os.killpg(os.getpgid(_calendar_sync_process.pid), signal.SIGTERM)
                log_info(f"[{datetime.now()}] Sent SIGTERM to process group {os.getpgid(_calendar_sync_process.pid)}")
            except (ProcessLookupError, PermissionError):
                # Process group doesn't exist or permission denied, try direct termination
                _calendar_sync_process.terminate()
            
            # Wait up to 5 seconds for termination
            try:
                _calendar_sync_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                log_info(f"[{datetime.now()}] Process didn't terminate, forcing kill...")
                try:
                    os.killpg(os.getpgid(_calendar_sync_process.pid), signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    _calendar_sync_process.kill()
                _calendar_sync_process.wait()
            
            log_info(f"[{datetime.now()}] Calendar sync process stopped")
            _calendar_sync_process = None
            _calendar_sync_status['active'] = False
            _calendar_sync_status['fetching'] = False
            _calendar_sync_status['uploading'] = False
            return True
        except Exception as e:
            log_info(f"[{datetime.now()}] Error stopping calendar sync process: {e}")
            _calendar_sync_process = None
            _calendar_sync_status['active'] = False
            return False

def update_calendar_sync_status(fetching=False, uploading=False, error=None):
    """Update calendar sync status"""
    global _calendar_sync_status
    with _calendar_sync_lock:
        if fetching is not None:
            _calendar_sync_status['fetching'] = fetching
            if fetching:
                _calendar_sync_status['last_fetch_time'] = datetime.now().isoformat()
        if uploading is not None:
            _calendar_sync_status['uploading'] = uploading
            if uploading:
                _calendar_sync_status['last_upload_time'] = datetime.now().isoformat()
        if error is not None:
            _calendar_sync_status['last_error'] = error
            if error:
                _calendar_sync_status['last_error_time'] = datetime.now().isoformat()
            else:
                _calendar_sync_status['last_error'] = None
                _calendar_sync_status['last_error_time'] = None

def optimize_image_memory(img):
    """Optimize image for memory usage"""
    if not ENABLE_MEMORY_OPTIMIZATION:
        return img
    
    # Check if image is very large and needs resizing
    max_dim = max(img.size)
    if max_dim > MAX_IMAGE_DIMENSION:
        # Calculate new size maintaining aspect ratio
        ratio = MAX_IMAGE_DIMENSION / max_dim
        new_size = tuple(int(dim * ratio) for dim in img.size)
        print(f"[{datetime.now()}] Resizing large image from {img.size} to {new_size} for memory optimization")
        img = img.resize(new_size, Image.Resampling.LANCZOS)
    
    return img

@app.route('/upload', methods=['POST'])
def upload_image():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in the request'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    # Check current mode and switch to image_receiver if in calendar_sync mode
    config = load_config()
    current_mode = config.get('mode', 'image_receiver')
    mode_switched = False
    
    log_info(f"[{datetime.now()}] Upload request received. Current mode: {current_mode}")
    
    # Check if this upload is from the calendar sync service itself (should not trigger mode switch)
    is_sync_upload = request.headers.get('X-Calendar-Sync-Upload') == 'true'
    if is_sync_upload:
        log_info(f"[{datetime.now()}] Calendar sync upload detected - skipping mode switch")
    
    if current_mode == 'calendar_sync' and not is_sync_upload:
        log_info(f"[{datetime.now()}] ===== MODE SWITCH: Upload detected while in calendar_sync mode ======")
        log_info(f"[{datetime.now()}] Switching to image_receiver mode...")
        try:
            # Switch to image_receiver mode using service manager
            result = subprocess.run(
                [sys.executable, SERVICE_MANAGER, 'set-mode', 'image_receiver'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            # Log the full output
            if result.stdout:
                log_info(f"[{datetime.now()}] set-mode stdout: {result.stdout}")
            if result.stderr:
                log_info(f"[{datetime.now()}] set-mode stderr: {result.stderr}")
            
            if result.returncode == 0:
                # Verify the mode was actually changed
                new_config = load_config()
                new_mode = new_config.get('mode', 'unknown')
                log_info(f"[{datetime.now()}] Mode changed from calendar_sync to {new_mode}")
                
                if new_mode == 'image_receiver':
                    mode_switched = True
                    log_info(f"[{datetime.now()}] ===== MODE SWITCH SUCCESSFUL ======")
                    
                    # Restart service to apply the mode change
                    # Use longer timeout to allow for service restart
                    log_info(f"[{datetime.now()}] Restarting service to apply mode change...")
                    restart_result = subprocess.run(
                        [sys.executable, SERVICE_MANAGER, 'restart'],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    
                    if restart_result.stdout:
                        log_info(f"[{datetime.now()}] restart stdout: {restart_result.stdout}")
                    if restart_result.stderr:
                        log_info(f"[{datetime.now()}] restart stderr: {restart_result.stderr}")
                    
                    if restart_result.returncode == 0:
                        log_info(f"[{datetime.now()}] ===== SERVICE RESTARTED IN IMAGE_RECEIVER MODE ======")
                    else:
                        log_info(f"[{datetime.now()}] Warning: Service restart returned non-zero exit code: {restart_result.returncode}")
                else:
                    log_info(f"[{datetime.now()}] ERROR: Mode verification failed. Expected 'image_receiver', got '{new_mode}'")
            else:
                log_info(f"[{datetime.now()}] ===== MODE SWITCH FAILED ======")
                log_info(f"[{datetime.now()}] Exit code: {result.returncode}")
                log_info(f"[{datetime.now()}] Error: {result.stderr}")
        except subprocess.TimeoutExpired as e:
            log_info(f"[{datetime.now()}] ===== MODE SWITCH TIMEOUT ======")
            log_info(f"[{datetime.now()}] Error: Command timed out: {e}")
        except Exception as e:
            log_info(f"[{datetime.now()}] ===== MODE SWITCH EXCEPTION ======")
            log_info(f"[{datetime.now()}] Error: {e}")
            import traceback
            traceback.print_exc(file=sys.stderr)
    
    # Get display options
    rotation_mode = request.form.get('rotation_mode', 'landscape')  # landscape, portrait, or auto
    auto_zoom = request.form.get('auto_zoom', 'true').lower() == 'true'
    print(f"[{datetime.now()}] Display options - Rotation mode: {rotation_mode}, Auto-zoom: {auto_zoom}")
    
    tmp_path = None
    img = None
    
    try:
        # Save to a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp:
            file.save(tmp)
            tmp_path = tmp.name
        print(f"[{datetime.now()}] Received file saved to {tmp_path}")
        
        # Apply memory optimization if image is very large
        try:
            img = Image.open(tmp_path)
            print(f"[{datetime.now()}] Original image size: {img.size}")
            
            # Apply memory optimization
            optimized_img = optimize_image_memory(img)
            
            # If image was optimized (resized), save it
            if optimized_img.size != img.size:
                print(f"[{datetime.now()}] Image size after optimization: {optimized_img.size}")
                print(f"[{datetime.now()}] Saving optimized image...")
                optimized_img.save(tmp_path, format='PNG', optimize=True, compress_level=COMPRESSION_QUALITY)
                print(f"[{datetime.now()}] Image optimization completed and saved")
            else:
                print(f"[{datetime.now()}] No optimization needed")
            
            # Clean up image objects
            img.close()
            optimized_img.close()
            img = None
            
            # Force garbage collection
            gc.collect()
            
        except Exception as e:
            print(f"Error optimizing image: {e}")
            if img:
                img.close()
                img = None
            import traceback
            traceback.print_exc()
        
        # Call the display_image.py script with display options
        cmd = [sys.executable, IMAGE_SCRIPT, tmp_path]
        cmd.extend(['--rotation-mode', rotation_mode])
        if not auto_zoom:
            cmd.append('--no-auto-zoom')
        
        print(f"[{datetime.now()}] Running display command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"display_image.py failed: {result.stderr}")
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)
            return jsonify({'error': 'display_image.py failed', 'details': result.stderr}), 500
        print("display_image.py executed successfully.")
        
        # Clean up temporary file
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)
        
        # Final garbage collection
        gc.collect()
        
        response_data = {'status': 'success'}
        if mode_switched:
            response_data['message'] = 'Image uploaded successfully. Switched to image_receiver mode.'
            response_data['mode_switched'] = True
        
        return jsonify(response_data), 200
        
    except Exception as e:
        print(f"Error processing file: {e}")
        # Clean up on error
        if img:
            img.close()
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)
        gc.collect()
        return jsonify({'error': str(e)}), 500

@app.route('/config', methods=['GET', 'POST'])
def config():
    global MAX_IMAGE_DIMENSION, COMPRESSION_QUALITY, ENABLE_MEMORY_OPTIMIZATION
    
    if request.method == 'POST':
        try:
            data = request.get_json()
            if 'max_image_dimension' in data:
                MAX_IMAGE_DIMENSION = int(data['max_image_dimension'])
            if 'compression_quality' in data:
                COMPRESSION_QUALITY = int(data['compression_quality'])
            if 'enable_memory_optimization' in data:
                ENABLE_MEMORY_OPTIMIZATION = bool(data['enable_memory_optimization'])
            
            return jsonify({
                'status': 'success',
                'message': 'Configuration updated',
                'config': {
                    'max_image_dimension': MAX_IMAGE_DIMENSION,
                    'compression_quality': COMPRESSION_QUALITY,
                    'enable_memory_optimization': ENABLE_MEMORY_OPTIMIZATION
                }
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 400
    
    # GET request - return current configuration
    return jsonify({
        'max_image_dimension': MAX_IMAGE_DIMENSION,
        'compression_quality': COMPRESSION_QUALITY,
        'enable_memory_optimization': ENABLE_MEMORY_OPTIMIZATION
    })

@app.route('/memory_status')
def memory_status():
    """Get current memory usage information"""
    try:
        import psutil
        process = psutil.Process()
        memory_info = process.memory_info()
        
        return jsonify({
            'memory_rss_mb': round(memory_info.rss / 1024 / 1024, 2),
            'memory_vms_mb': round(memory_info.vms / 1024 / 1024, 2),
            'cpu_percent': process.cpu_percent(),
            'config': {
                'max_image_dimension': MAX_IMAGE_DIMENSION,
                'compression_quality': COMPRESSION_QUALITY,
                'enable_memory_optimization': ENABLE_MEMORY_OPTIMIZATION
            }
        })
    except ImportError:
        return jsonify({'error': 'psutil not available'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/')
def index():
    return """
    <h1>ECAL Image Receiver Server</h1>
    <p>Server is running with memory optimizations!</p>
    <ul>
        <li><a href='/upload_form'>Upload Form</a></li>
        <li><a href='/config'>Configuration</a></li>
        <li><a href='/memory_status'>Memory Status</a></li>
    </ul>
    <p><strong>Memory Optimization Settings:</strong></p>
    <ul>
        <li>Max Image Dimension: {max_dim}px</li>
        <li>Compression Quality: {comp_qual}</li>
        <li>Memory Optimization: {mem_opt}</li>
    </ul>
    """.format(
        max_dim=MAX_IMAGE_DIMENSION,
        comp_qual=COMPRESSION_QUALITY,
        mem_opt="Enabled" if ENABLE_MEMORY_OPTIMIZATION else "Disabled"
    )

@app.route('/upload_form', methods=['GET'])
def upload_form():
    try:
        return render_template('upload.html')
    except Exception as e:
        print(f"Error rendering template: {e}")
        return f"Template error: {e}", 500

@app.route('/mode', methods=['GET', 'POST'])
def mode():
    """Get or set the operating mode"""
    if request.method == 'POST':
        try:
            data = request.get_json()
            new_mode = data.get('mode')
            
            if new_mode not in ['image_receiver', 'calendar_sync']:
                return jsonify({'error': 'Invalid mode. Must be image_receiver or calendar_sync'}), 400
            
            config = load_config()
            config['mode'] = new_mode
            save_config(config)
            
            return jsonify({
                'status': 'success',
                'message': f'Mode set to {new_mode}',
                'mode': new_mode,
                'note': 'Restart the service for changes to take effect'
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 400
    
    # GET request - return current mode
    config = load_config()
    return jsonify({
        'mode': config.get('mode', 'image_receiver'),
        'available_modes': ['image_receiver', 'calendar_sync']
    })

@app.route('/mode/switch', methods=['POST'])
def switch_mode():
    """Switch mode without restarting the main service"""
    try:
        data = request.get_json()
        new_mode = data.get('mode')
        
        # Get current mode for logging
        config = load_config()
        current_mode = config.get('mode', 'image_receiver')
        
        log_info(f"[{datetime.now()}] ===== MODE SWITCH REQUEST (NO RESTART) =====")
        log_info(f"[{datetime.now()}] Current mode: {current_mode}")
        log_info(f"[{datetime.now()}] Requested mode: {new_mode}")
        
        if new_mode not in ['image_receiver', 'calendar_sync']:
            log_info(f"[{datetime.now()}] ERROR: Invalid mode requested")
            return jsonify({'error': 'Invalid mode. Must be image_receiver or calendar_sync'}), 400
        
        if current_mode == new_mode:
            log_info(f"[{datetime.now()}] Already in {new_mode} mode, no switch needed")
            return jsonify({
                'status': 'success',
                'message': f'Already in {new_mode} mode',
                'mode': new_mode
            })
        
        # Update config mode
        config['mode'] = new_mode
        save_config(config)
        log_info(f"[{datetime.now()}] Config updated to {new_mode} mode")
        
        # Control calendar sync process based on mode
        if new_mode == 'calendar_sync':
            # Stop calendar sync if running (shouldn't be, but just in case)
            stop_calendar_sync_process()
            # Start calendar sync process
            if start_calendar_sync_process():
                log_info(f"[{datetime.now()}] ===== MODE SWITCH SUCCESSFUL: {current_mode} -> {new_mode} =====")
                log_info(f"[{datetime.now()}] Calendar sync process started - will fetch initial image shortly")
                return jsonify({
                    'status': 'success',
                    'message': f'Switched to {new_mode} mode. Calendar sync started.',
                    'mode': new_mode
                })
            else:
                log_info(f"[{datetime.now()}] ===== MODE SWITCH FAILED: Could not start calendar sync =====")
                return jsonify({
                    'error': 'Failed to start calendar sync process',
                    'details': 'Check logs for details'
                }), 500
        else:  # image_receiver mode
            # Stop calendar sync process if running
            if stop_calendar_sync_process():
                log_info(f"[{datetime.now()}] ===== MODE SWITCH SUCCESSFUL: {current_mode} -> {new_mode} =====")
                log_info(f"[{datetime.now()}] Calendar sync process stopped")
                return jsonify({
                    'status': 'success',
                    'message': f'Switched to {new_mode} mode. Calendar sync stopped.',
                    'mode': new_mode
                })
            else:
                # Still succeeded even if stop failed (maybe it wasn't running)
                log_info(f"[{datetime.now()}] ===== MODE SWITCH SUCCESSFUL: {current_mode} -> {new_mode} =====")
                return jsonify({
                    'status': 'success',
                    'message': f'Switched to {new_mode} mode',
                    'mode': new_mode
                })
        
    except Exception as e:
        log_info(f"[{datetime.now()}] ===== MODE SWITCH EXCEPTION ======")
        log_info(f"[{datetime.now()}] Error: {e}")
        import traceback
        traceback.print_exc(file=sys.stderr)
        return jsonify({'error': str(e)}), 500

@app.route('/calendar_sync/status', methods=['GET', 'POST'])
def calendar_sync_status():
    """Get or update calendar sync status"""
    if request.method == 'POST':
        # Calendar sync service updates its status here
        try:
            data = request.get_json()
            
            with _calendar_sync_lock:
                if 'fetching' in data:
                    _calendar_sync_status['fetching'] = bool(data['fetching'])
                    if data['fetching']:
                        _calendar_sync_status['last_fetch_time'] = datetime.now().isoformat()
                
                if 'uploading' in data:
                    _calendar_sync_status['uploading'] = bool(data['uploading'])
                    if data['uploading']:
                        _calendar_sync_status['last_upload_time'] = datetime.now().isoformat()
                
                if 'error' in data:
                    error = data['error']
                    _calendar_sync_status['last_error'] = error if error else None
                    if error:
                        _calendar_sync_status['last_error_time'] = datetime.now().isoformat()
                    else:
                        _calendar_sync_status['last_error_time'] = None
            
            return jsonify({'status': 'success'})
        except Exception as e:
            return jsonify({'error': str(e)}), 400
    
    # GET request - return current status
    with _calendar_sync_lock:
        status = _calendar_sync_status.copy()
        
        # Check if process is actually running
        if _calendar_sync_process:
            if _calendar_sync_process.poll() is None:
                status['active'] = True
                status['process_pid'] = _calendar_sync_process.pid
            else:
                status['active'] = False
                status['process_pid'] = None
        else:
            status['active'] = False
            status['process_pid'] = None
        
        return jsonify(status)

@app.route('/calendar_sync/trigger', methods=['POST', 'GET'])
def trigger_calendar_sync():
    """Trigger a manual calendar sync"""
    global _manual_sync_trigger
    
    with _calendar_sync_lock:
        # Check if calendar sync is active
        if not _calendar_sync_process or _calendar_sync_process.poll() is not None:
            return jsonify({
                'error': 'Calendar sync is not active',
                'message': 'Please switch to calendar sync mode first'
            }), 400
        
        # Set the trigger flag
        _manual_sync_trigger = True
        log_info(f"[{datetime.now()}] Manual calendar sync triggered")
        
        return jsonify({
            'status': 'success',
            'message': 'Manual sync triggered. Calendar sync service will refresh shortly.'
        })

@app.route('/calendar_sync/check_trigger', methods=['GET'])
def check_manual_sync_trigger():
    """Check if manual sync was triggered (used by calendar sync service)"""
    global _manual_sync_trigger
    
    with _calendar_sync_lock:
        if _manual_sync_trigger:
            _manual_sync_trigger = False  # Clear the flag after reading
            return jsonify({'trigger': True})
        else:
            return jsonify({'trigger': False})

@app.route('/mode/config', methods=['GET', 'POST'])
def mode_config():
    """Get or update mode-specific configuration"""
    config = load_config()
    
    if request.method == 'POST':
        try:
            data = request.get_json()
            mode_type = data.get('mode_type')
            
            if mode_type == 'calendar_sync':
                if 'calendar_url' in data:
                    config['calendar_sync']['calendar_url'] = data['calendar_url']
            elif mode_type == 'image_receiver':
                if 'host' in data:
                    config['image_receiver']['host'] = data['host']
                if 'port' in data:
                    config['image_receiver']['port'] = int(data['port'])
            
            save_config(config)
            
            return jsonify({
                'status': 'success',
                'message': 'Configuration updated',
                'config': config
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 400
    
    # GET request
    return jsonify(config)

def cleanup_on_exit():
    """Cleanup function called on exit to ensure subprocesses are terminated"""
    log_info(f"[{datetime.now()}] Cleanup on exit: stopping calendar sync process...")
    stop_calendar_sync_process()

def signal_handler(signum, frame):
    """Handle termination signals to ensure clean shutdown"""
    log_info(f"[{datetime.now()}] Received signal {signum}, cleaning up...")
    cleanup_on_exit()
    sys.exit(0)

# Register cleanup handlers
atexit.register(cleanup_on_exit)
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

if __name__ == '__main__':
    # Check mode on startup and start calendar sync if needed
    config = load_config()
    current_mode = config.get('mode', 'image_receiver')
    log_info(f"[{datetime.now()}] Starting image_receiver_server.py in {current_mode} mode...")
    
    if current_mode == 'calendar_sync':
        # Wait a moment for Flask to start, then start calendar sync process
        def start_sync_delayed():
            time.sleep(2)  # Give Flask time to start
            log_info(f"[{datetime.now()}] Auto-starting calendar sync process (mode is calendar_sync)...")
            start_calendar_sync_process()
        
        thread = threading.Thread(target=start_sync_delayed, daemon=True)
        thread.start()
    
    app.run(host='0.0.0.0', port=8000, threaded=True, use_reloader=False)

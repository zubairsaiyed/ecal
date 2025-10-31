#!/usr/bin/env python3
from flask import Flask, request, jsonify, render_template
import os
import tempfile
import subprocess
import sys
import gc
import json
import threading
from datetime import datetime
from PIL import Image

app = Flask(__name__)

# Global calendar sync process
_calendar_sync_process = None
_calendar_sync_lock = threading.Lock()

# Helper function to log to stderr (which Flask shows) for important messages
def log_info(message):
    """Log to both print (for stdout) and stderr (for Flask logs)"""
    print(message, file=sys.stderr)
    print(message)
    sys.stderr.flush()
    sys.stdout.flush()

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
            'calendar_url': 'http://localhost:5000',
            'poll_interval': 10,
            'scheduled': False
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
        
        # Build command
        cmd = [sys.executable, CALENDAR_SYNC_SCRIPT]
        
        if sync_config.get('scheduled', False):
            cmd.append('--scheduled')
            cmd.extend(['--sleep-hours', str(sync_config.get('sleep_hours', 12))])
        else:
            cmd.extend(['--poll-interval', str(sync_config.get('poll_interval', 10))])
        
        cmd.extend(['--calendar-url', calendar_url])
        cmd.extend(['--endpoint-url', endpoint_url])
        
        log_info(f"[{datetime.now()}] Starting calendar sync process...")
        log_info(f"[{datetime.now()}] Command: {' '.join(cmd)}")
        
        try:
            _calendar_sync_process = subprocess.Popen(
                cmd,
                stdout=None,  # Let output go to stderr/stdout
                stderr=None,
                start_new_session=True
            )
            log_info(f"[{datetime.now()}] Calendar sync process started (PID: {_calendar_sync_process.pid})")
            return True
        except Exception as e:
            log_info(f"[{datetime.now()}] Failed to start calendar sync process: {e}")
            return False

def stop_calendar_sync_process():
    """Stop calendar sync service process"""
    global _calendar_sync_process
    
    with _calendar_sync_lock:
        if not _calendar_sync_process:
            log_info(f"[{datetime.now()}] No calendar sync process to stop")
            return True
        
        if _calendar_sync_process.poll() is not None:
            log_info(f"[{datetime.now()}] Calendar sync process already stopped")
            _calendar_sync_process = None
            return True
        
        log_info(f"[{datetime.now()}] Stopping calendar sync process (PID: {_calendar_sync_process.pid})...")
        
        try:
            # Try graceful termination first
            _calendar_sync_process.terminate()
            
            # Wait up to 5 seconds for termination
            try:
                _calendar_sync_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                log_info(f"[{datetime.now()}] Process didn't terminate, forcing kill...")
                _calendar_sync_process.kill()
                _calendar_sync_process.wait()
            
            log_info(f"[{datetime.now()}] Calendar sync process stopped")
            _calendar_sync_process = None
            return True
        except Exception as e:
            log_info(f"[{datetime.now()}] Error stopping calendar sync process: {e}")
            _calendar_sync_process = None
            return False

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
    
    if current_mode == 'calendar_sync':
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
    auto_rotate = request.form.get('auto_rotate', 'true').lower() == 'true'
    auto_zoom = request.form.get('auto_zoom', 'true').lower() == 'true'
    print(f"[{datetime.now()}] Display options - Auto-rotate: {auto_rotate}, Auto-zoom: {auto_zoom}")
    
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
        if not auto_rotate:
            cmd.append('--no-auto-rotate')
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
                if 'poll_interval' in data:
                    config['calendar_sync']['poll_interval'] = int(data['poll_interval'])
                if 'scheduled' in data:
                    config['calendar_sync']['scheduled'] = bool(data['scheduled'])
                if 'sleep_hours' in data:
                    config['calendar_sync']['sleep_hours'] = int(data['sleep_hours'])
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)

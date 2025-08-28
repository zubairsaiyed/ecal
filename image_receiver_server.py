#!/usr/bin/env python3
from flask import Flask, request, jsonify, render_template
import os
import tempfile
import subprocess
import sys
import gc
from datetime import datetime
from PIL import Image, ExifTags

app = Flask(__name__)

IMAGE_SCRIPT = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'display_image.py')

# Memory optimization settings
MAX_IMAGE_DIMENSION = 2000  # Maximum dimension for large images
COMPRESSION_QUALITY = 6      # PNG compression level (0-9, lower = smaller file)
ENABLE_MEMORY_OPTIMIZATION = True

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
    
    # Get auto-rotate preference
    auto_rotate = request.form.get('auto_rotate', 'true').lower() == 'true'
    print(f"[{datetime.now()}] Auto-rotate setting: {auto_rotate}")
    
    tmp_path = None
    img = None
    
    try:
        # Save to a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp:
            file.save(tmp)
            tmp_path = tmp.name
        print(f"[{datetime.now()}] Received file saved to {tmp_path}")
        
        # Auto-orient the image using Pillow (only if enabled)
        if auto_rotate:
            try:
                # Load image with memory optimization
                img = Image.open(tmp_path)
                print(f"[{datetime.now()}] Original image size: {img.size}")
                
                # Apply memory optimization
                img = optimize_image_memory(img)
                print(f"[{datetime.now()}] Image size after optimization: {img.size}")
                
                # Process EXIF orientation more efficiently
                orientation_value = None
                try:
                    exif = img.getexif()
                    if exif is not None:
                        # Use direct tag lookup instead of iterating through all tags
                        orientation_value = exif.get(274, None)  # 274 is the standard orientation tag
                        if orientation_value is None:
                            orientation_value = exif.get(0x0112, None)  # Alternative hex format
                        
                        print(f"[{datetime.now()}] EXIF orientation value: {orientation_value}")
                except Exception as e:
                    print(f"EXIF processing error: {e}")
                
                # Apply rotation if needed
                if orientation_value in [3, 6, 8]:
                    original_size = img.size
                    
                    if orientation_value == 3:
                        img = img.rotate(180, expand=True)
                        print(f"[{datetime.now()}] Rotated image 180°")
                    elif orientation_value == 6:
                        img = img.rotate(90, expand=True)
                        print(f"[{datetime.now()}] Rotated image 90°")
                    elif orientation_value == 8:
                        img = img.rotate(270, expand=True)
                        print(f"[{datetime.now()}] Rotated image 270°")
                    
                    print(f"[{datetime.now()}] Image size after rotation: {img.size}")
                    
                    # Save rotated image with memory optimization
                    print(f"[{datetime.now()}] Saving rotated image...")
                    img.save(tmp_path, format='PNG', optimize=True, compress_level=6)
                    print(f"[{datetime.now()}] Image auto-orientation completed and saved")
                    
                    # Clean up the rotated image object
                    img.close()
                    img = None
                    
                    # Force garbage collection
                    gc.collect()
                    
                else:
                    print(f"[{datetime.now()}] No rotation needed for orientation {orientation_value}")
                    # Close image if no rotation needed
                    img.close()
                    img = None
                    
            except Exception as e:
                print(f"Error auto-orienting image: {e}")
                if img:
                    img.close()
                    img = None
                import traceback
                traceback.print_exc()
        else:
            print(f"[{datetime.now()}] Auto-rotation disabled, keeping original orientation")
        
        # Call the display_image.py script
        print(f"[{datetime.now()}] Running display command: {' '.join([sys.executable, IMAGE_SCRIPT, tmp_path])}")
        result = subprocess.run([sys.executable, IMAGE_SCRIPT, tmp_path], capture_output=True, text=True)
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
        
        return jsonify({'status': 'success'}), 200
        
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)

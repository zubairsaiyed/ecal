#!/usr/bin/env python3
from flask import Flask, request, jsonify, render_template
import os
import tempfile
import subprocess
import sys
from datetime import datetime
from PIL import Image, ExifTags

app = Flask(__name__)

IMAGE_SCRIPT = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'display_image.py')

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
    
    try:
        # Save to a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp:
            file.save(tmp)
            tmp_path = tmp.name
        print(f"[{datetime.now()}] Received file saved to {tmp_path}")
        
        # Auto-orient the image using Pillow (only if enabled)
        if auto_rotate:
            try:
                img = Image.open(tmp_path)
                print(f"[{datetime.now()}] Original image size: {img.size}")
                print(f"[{datetime.now()}] Original image mode: {img.mode}")
                print(f"[{datetime.now()}] Original image format: {img.format}")
                print(f"[{datetime.now()}] Original image info: {img.info}")
                
                try:
                    exif = img.getexif()
                    print(f"[{datetime.now()}] EXIF data found: {exif is not None}")
                    if exif is not None:
                        print(f"[{datetime.now()}] EXIF tags: {list(exif.keys())}")
                    
                    orientation = None
                    for tag, value in ExifTags.TAGS.items():
                        if value == 'Orientation':
                            orientation = tag
                            break
                    print(f"[{datetime.now()}] Orientation tag ID: {orientation}")
                    
                    # Alternative method: try common orientation tag IDs
                    if orientation is None:
                        print(f"[{datetime.now()}] Trying alternative orientation detection...")
                        # Common orientation tag IDs: 274, 0x0112
                        for alt_tag in [274, 0x0112]:
                            if alt_tag in exif:
                                orientation = alt_tag
                                print(f"[{datetime.now()}] Found orientation using alternative tag: {alt_tag}")
                                break
                    
                    if exif is not None and orientation is not None:
                        orientation_value = exif.get(orientation, None)
                        print(f"[{datetime.now()}] EXIF orientation value: {orientation_value}")
                        
                        # Store original dimensions
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
                        else:
                            print(f"[{datetime.now()}] No rotation needed for orientation {orientation_value}")
                        
                        print(f"[{datetime.now()}] Image size after rotation: {img.size}")
                        print(f"[{datetime.now()}] Size change: {original_size} -> {img.size}")
                        
                        # Verify rotation actually happened
                        if img.size != original_size:
                            print(f"[{datetime.now()}] ✅ Rotation confirmed - image size changed")
                        else:
                            print(f"[{datetime.now()}] ⚠️  Warning - image size unchanged, rotation may not have worked")
                            
                        # Test rotation functionality with a simple 90-degree rotation
                        print(f"[{datetime.now()}] Testing rotation functionality...")
                        test_img = img.copy()
                        test_img = test_img.rotate(90, expand=True)
                        print(f"[{datetime.now()}] Test rotation result: {img.size} -> {test_img.size}")
                        
                    else:
                        print(f"[{datetime.now()}] No EXIF orientation data found")
                except Exception as e:
                    print(f"No EXIF orientation or error: {e}")
                
                # Save with explicit format and quality
                print(f"[{datetime.now()}] Saving rotated image...")
                img.save(tmp_path, format='PNG', optimize=True)
                print(f"[{datetime.now()}] Image auto-orientation completed and saved")
                
                # Verify the saved file
                if os.path.exists(tmp_path):
                    file_size = os.path.getsize(tmp_path)
                    print(f"[{datetime.now()}] Saved file size: {file_size} bytes")
                    
                    # Open and check the saved image
                    saved_img = Image.open(tmp_path)
                    print(f"[{datetime.now()}] Saved image size: {saved_img.size}")
                    print(f"[{datetime.now()}] Saved image mode: {saved_img.mode}")
                else:
                    print(f"[{datetime.now()}] ⚠️  Warning - saved file not found!")
                    
            except Exception as e:
                print(f"Error auto-orienting image: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"[{datetime.now()}] Auto-rotation disabled, keeping original orientation")
        
        # Call the display_image.py script
        print(f"[{datetime.now()}] Running display command: {' '.join([sys.executable, IMAGE_SCRIPT, tmp_path])}")
        result = subprocess.run([sys.executable, IMAGE_SCRIPT, tmp_path], capture_output=True, text=True)
        if result.returncode != 0:
            print(f"display_image.py failed: {result.stderr}")
            os.remove(tmp_path)
            return jsonify({'error': 'display_image.py failed', 'details': result.stderr}), 500
        print("display_image.py executed successfully.")
        os.remove(tmp_path)
        return jsonify({'status': 'success'}), 200
    except Exception as e:
        print(f"Error processing file: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/')
def index():
    return "ECAL Image Receiver Server is running! <a href='/upload_form'>Go to upload form</a>"

@app.route('/upload_form', methods=['GET'])
def upload_form():
    try:
        return render_template('upload.html')
    except Exception as e:
        print(f"Error rendering template: {e}")
        return f"Template error: {e}", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)

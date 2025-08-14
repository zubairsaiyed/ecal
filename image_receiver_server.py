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
                try:
                    exif = img.getexif()
                    orientation = None
                    for tag, value in ExifTags.TAGS.items():
                        if value == 'Orientation':
                            orientation = tag
                            break
                    if exif is not None and orientation is not None:
                        orientation_value = exif.get(orientation, None)
                        if orientation_value == 3:
                            img = img.rotate(180, expand=True)
                            print(f"[{datetime.now()}] Rotated image 180°")
                        elif orientation_value == 6:
                            img = img.rotate(270, expand=True)
                            print(f"[{datetime.now()}] Rotated image 270°")
                        elif orientation_value == 8:
                            img = img.rotate(90, expand=True)
                            print(f"[{datetime.now()}] Rotated image 90°")
                except Exception as e:
                    print(f"No EXIF orientation or error: {e}")
                img.save(tmp_path)
                print(f"[{datetime.now()}] Image auto-orientation completed")
            except Exception as e:
                print(f"Error auto-orienting image: {e}")
        else:
            print(f"[{datetime.now()}] Auto-rotation disabled, keeping original orientation")
        
        # Call the display_image.py script
        # Pass the disable_rotation parameter
        cmd = [sys.executable, IMAGE_SCRIPT, tmp_path]
        if not auto_rotate:
            cmd.append('--disable-rotation')
        
        print(f"[{datetime.now()}] Running display command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
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

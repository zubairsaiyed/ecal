#!/usr/bin/env python3
from flask import Flask, request, jsonify, render_template_string
import os
import tempfile
import subprocess
import sys
from datetime import datetime
from PIL import Image, ExifTags

app = Flask(__name__)

IMAGE_SCRIPT = os.path.join(os.path.dirname(__file__), 'display_image.py')

@app.route('/upload', methods=['POST'])
def upload_image():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in the request'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    try:
        # Save to a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp:
            file.save(tmp)
            tmp_path = tmp.name
        print(f"[{datetime.now()}] Received file saved to {tmp_path}")
        # Auto-orient the image using Pillow
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
                    elif orientation_value == 6:
                        img = img.rotate(270, expand=True)
                    elif orientation_value == 8:
                        img = img.rotate(90, expand=True)
            except Exception as e:
                print(f"No EXIF orientation or error: {e}")
            img.save(tmp_path)
        except Exception as e:
            print(f"Error auto-orienting image: {e}")
        # Call the display_image.py script
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

@app.route('/upload_form', methods=['GET'])
def upload_form():
    html = '''
    <!doctype html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>ECAL Image Upload</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }
            
            .container {
                max-width: 600px;
                margin: 0 auto;
                background: white;
                border-radius: 20px;
                box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                overflow: hidden;
            }
            
            .header {
                background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
                color: white;
                padding: 30px;
                text-align: center;
            }
            
            .header h1 {
                font-size: 2rem;
                margin-bottom: 10px;
                font-weight: 600;
            }
            
            .header p {
                opacity: 0.9;
                font-size: 1.1rem;
            }
            
            .content {
                padding: 30px;
            }
            
            .upload-section {
                margin-bottom: 30px;
            }
            
            .upload-section h2 {
                color: #333;
                margin-bottom: 20px;
                font-size: 1.5rem;
                text-align: center;
            }
            
            .file-input-wrapper {
                position: relative;
                margin-bottom: 20px;
            }
            
            .file-input {
                width: 100%;
                padding: 15px;
                border: 2px dashed #ddd;
                border-radius: 10px;
                text-align: center;
                cursor: pointer;
                transition: all 0.3s ease;
                background: #f8f9fa;
            }
            
            .file-input:hover {
                border-color: #4facfe;
                background: #f0f8ff;
            }
            
            .file-input input[type="file"] {
                position: absolute;
                opacity: 0;
                width: 100%;
                height: 100%;
                cursor: pointer;
            }
            
            .camera-section {
                margin-bottom: 30px;
                text-align: center;
            }
            
            .camera-section h2 {
                color: #333;
                margin-bottom: 20px;
                font-size: 1.5rem;
            }
            
            .camera-button {
                background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%);
                color: white;
                border: none;
                padding: 15px 30px;
                border-radius: 25px;
                font-size: 1.1rem;
                cursor: pointer;
                transition: all 0.3s ease;
                box-shadow: 0 5px 15px rgba(238, 90, 36, 0.3);
            }
            
            .camera-button:hover {
                transform: translateY(-2px);
                box-shadow: 0 8px 20px rgba(238, 90, 36, 0.4);
            }
            
            .camera-button:disabled {
                opacity: 0.6;
                cursor: not-allowed;
                transform: none;
            }
            
            .camera-preview {
                margin-top: 20px;
                display: none;
            }
            
            .camera-preview video {
                width: 100%;
                max-width: 400px;
                border-radius: 10px;
                box-shadow: 0 5px 15px rgba(0,0,0,0.2);
            }
            
            .camera-preview canvas {
                display: none;
                width: 100%;
                max-width: 400px;
                border-radius: 10px;
            }
            
            .capture-button {
                background: linear-gradient(135deg, #00b894 0%, #00a085 100%);
                color: white;
                border: none;
                padding: 12px 25px;
                border-radius: 20px;
                font-size: 1rem;
                cursor: pointer;
                margin: 10px;
                transition: all 0.3s ease;
            }
            
            .capture-button:hover {
                transform: translateY(-1px);
                box-shadow: 0 5px 15px rgba(0, 184, 148, 0.3);
            }
            
            .upload-button {
                background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
                color: white;
                border: none;
                padding: 15px 30px;
                border-radius: 25px;
                font-size: 1.1rem;
                cursor: pointer;
                width: 100%;
                transition: all 0.3s ease;
                box-shadow: 0 5px 15px rgba(79, 172, 254, 0.3);
            }
            
            .upload-button:hover {
                transform: translateY(-2px);
                box-shadow: 0 8px 20px rgba(79, 172, 254, 0.4);
            }
            
            .upload-button:disabled {
                opacity: 0.6;
                cursor: not-allowed;
                transform: none;
            }
            
            .status {
                margin-top: 20px;
                padding: 15px;
                border-radius: 10px;
                text-align: center;
                display: none;
            }
            
            .status.success {
                background: #d4edda;
                color: #155724;
                border: 1px solid #c3e6cb;
            }
            
            .status.error {
                background: #f8d7da;
                color: #721c24;
                border: 1px solid #f5c6cb;
            }
            
            .loading {
                display: none;
                text-align: center;
                margin: 20px 0;
            }
            
            .spinner {
                border: 3px solid #f3f3f3;
                border-top: 3px solid #4facfe;
                border-radius: 50%;
                width: 30px;
                height: 30px;
                animation: spin 1s linear infinite;
                margin: 0 auto 10px;
            }
            
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            
            @media (max-width: 768px) {
                body {
                    padding: 10px;
                }
                
                .header {
                    padding: 20px;
                }
                
                .header h1 {
                    font-size: 1.5rem;
                }
                
                .content {
                    padding: 20px;
                }
                
                .camera-button, .upload-button {
                    padding: 12px 25px;
                    font-size: 1rem;
                }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📸 ECAL Image Upload</h1>
                <p>Upload images to display on your e-paper screen</p>
            </div>
            
            <div class="content">
                <div class="upload-section">
                    <h2>📁 Upload Image File</h2>
                    <div class="file-input-wrapper">
                        <div class="file-input">
                            <span>📁 Click to select an image file</span>
                            <input type="file" name="file" accept="image/*" id="fileInput">
                        </div>
                    </div>
                    <button type="button" class="upload-button" id="uploadBtn" disabled>Upload Image</button>
                </div>
                
                <div class="camera-section">
                    <h2>📷 Take Live Photo</h2>
                    <button type="button" class="camera-button" id="cameraBtn">📷 Open Camera</button>
                    
                    <div class="camera-preview" id="cameraPreview">
                        <video id="video" autoplay playsinline></video>
                        <canvas id="canvas"></canvas>
                        <div style="margin-top: 15px;">
                            <button type="button" class="capture-button" id="captureBtn">📸 Capture Photo</button>
                            <button type="button" class="capture-button" id="retakeBtn" style="display: none;">🔄 Retake</button>
                        </div>
                    </div>
                </div>
                
                <div class="status" id="status"></div>
                <div class="loading" id="loading">
                    <div class="spinner"></div>
                    <p>Processing image...</p>
                </div>
            </div>
        </div>
        
        <script>
            let stream = null;
            let capturedImage = null;
            
            // File input handling
            const fileInput = document.getElementById('fileInput');
            const uploadBtn = document.getElementById('uploadBtn');
            
            fileInput.addEventListener('change', function() {
                uploadBtn.disabled = !this.files.length;
            });
            
            // Camera functionality
            const cameraBtn = document.getElementById('cameraBtn');
            const cameraPreview = document.getElementById('cameraPreview');
            const video = document.getElementById('video');
            const canvas = document.getElementById('canvas');
            const captureBtn = document.getElementById('captureBtn');
            const retakeBtn = document.getElementById('retakeBtn');
            
            cameraBtn.addEventListener('click', async function() {
                try {
                    stream = await navigator.mediaDevices.getUserMedia({ 
                        video: { 
                            facingMode: 'environment',
                            width: { ideal: 1920 },
                            height: { ideal: 1080 }
                        } 
                    });
                    video.srcObject = stream;
                    cameraPreview.style.display = 'block';
                    cameraBtn.textContent = '📷 Camera Active';
                    cameraBtn.disabled = true;
                } catch (err) {
                    alert('Camera access denied: ' + err.message);
                }
            });
            
            captureBtn.addEventListener('click', function() {
                const context = canvas.getContext('2d');
                canvas.width = video.videoWidth;
                canvas.height = video.videoHeight;
                context.drawImage(video, 0, 0);
                
                capturedImage = canvas.toBlob(function(blob) {
                    // Create a file from the blob
                    const file = new File([blob], 'camera-photo.jpg', { type: 'image/jpeg' });
                    
                    // Set the file input
                    const dataTransfer = new DataTransfer();
                    dataTransfer.items.add(file);
                    fileInput.files = dataTransfer.files;
                    
                    // Enable upload button
                    uploadBtn.disabled = false;
                    
                    // Show retake button
                    captureBtn.style.display = 'none';
                    retakeBtn.style.display = 'inline-block';
                    
                    // Stop the camera stream
                    if (stream) {
                        stream.getTracks().forEach(track => track.stop());
                        stream = null;
                    }
                    
                    // Hide video, show canvas
                    video.style.display = 'none';
                    canvas.style.display = 'block';
                }, 'image/jpeg', 0.8);
            });
            
            retakeBtn.addEventListener('click', function() {
                // Reset camera
                capturedImage = null;
                canvas.style.display = 'none';
                video.style.display = 'block';
                cameraPreview.style.display = 'none';
                cameraBtn.textContent = '📷 Open Camera';
                cameraBtn.disabled = false;
                captureBtn.style.display = 'inline-block';
                retakeBtn.style.display = 'none';
                
                // Clear file input
                fileInput.value = '';
                uploadBtn.disabled = true;
                
                // Restart camera
                cameraBtn.click();
            });
            
            // Upload functionality
            uploadBtn.addEventListener('click', async function() {
                if (!fileInput.files.length) return;
                
                const formData = new FormData();
                formData.append('file', fileInput.files[0]);
                
                const status = document.getElementById('status');
                const loading = document.getElementById('loading');
                
                // Show loading
                loading.style.display = 'block';
                status.style.display = 'none';
                uploadBtn.disabled = true;
                
                try {
                    const response = await fetch('/upload', {
                        method: 'POST',
                        body: formData
                    });
                    
                    const result = await response.json();
                    
                    if (response.ok) {
                        status.textContent = '✅ Image uploaded successfully!';
                        status.className = 'status success';
                        fileInput.value = '';
                        uploadBtn.disabled = true;
                    } else {
                        status.textContent = '❌ Upload failed: ' + (result.error || 'Unknown error');
                        status.className = 'status error';
                    }
                } catch (err) {
                    status.textContent = '❌ Upload failed: ' + err.message;
                    status.className = 'status error';
                } finally {
                    loading.style.display = 'none';
                    status.style.display = 'block';
                    uploadBtn.disabled = false;
                }
            });
        </script>
    </body>
    </html>
    '''
    return render_template_string(html)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000) 
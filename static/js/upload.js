let stream = null;
let capturedImage = null;

// Debug logging
console.log('Upload.js loaded');

// File input handling
const fileInput = document.getElementById('fileInput');
const uploadBtn = document.getElementById('uploadBtn');

console.log('File input element:', fileInput);
console.log('Upload button element:', uploadBtn);

if (fileInput && uploadBtn) {
    fileInput.addEventListener('change', function() {
        console.log('File input changed, files:', this.files);
        uploadBtn.disabled = !this.files.length;
    });
} else {
    console.error('Required elements not found!');
}

// Camera functionality
const cameraBtn = document.getElementById('cameraBtn');
const cameraPreview = document.getElementById('cameraPreview');
const video = document.getElementById('video');
const canvas = document.getElementById('canvas');
const captureBtn = document.getElementById('captureBtn');
const retakeBtn = document.getElementById('retakeBtn');

console.log('Camera elements:', {
    cameraBtn,
    cameraPreview,
    video,
    canvas,
    captureBtn,
    retakeBtn
});

if (cameraBtn) {
    cameraBtn.addEventListener('click', async function() {
        console.log('Camera button clicked');
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
            console.error('Camera error:', err);
            alert('Camera access denied: ' + err.message);
        }
    });
} else {
    console.error('Camera button not found!');
}

if (captureBtn) {
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
} else {
    console.error('Capture button not found!');
}

if (retakeBtn) {
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
} else {
    console.error('Retake button not found!');
}

// Upload functionality
if (uploadBtn) {
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
} else {
    console.error('Upload button not found!');
}

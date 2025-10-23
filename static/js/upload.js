

// Debug logging
console.log('Upload.js loaded');

// Global error handler
window.addEventListener('error', function(e) {
    console.error('Global error:', e.error);
});

// Wait for DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM fully loaded');
    
    // Get all required elements
    const fileInput = document.getElementById('fileInput');
    const uploadBtn = document.getElementById('uploadBtn');
    const fileInputWrapper = document.getElementById('fileInputWrapper');
    const status = document.getElementById('status');
    const loading = document.getElementById('loading');

    console.log('Elements found:', {
        fileInput, uploadBtn, fileInputWrapper, status, loading
    });
    
    // Debug file input specifically
    if (fileInput) {
        console.log('File input details:', {
            type: fileInput.type,
            accept: fileInput.accept,
            style: fileInput.style.cssText,
            computedStyle: window.getComputedStyle(fileInput),
            disabled: fileInput.disabled,
            readonly: fileInput.readOnly
        });
    }

    // File input handling
    if (fileInput && uploadBtn) {
        console.log('Setting up file input and upload button');
        
        // File input change event
        fileInput.addEventListener('change', function(e) {
            console.log('File input change event fired!');
            console.log('Event:', e);
            console.log('Files:', this.files);
            console.log('Files length:', this.files.length);
            console.log('File input value:', this.value);
            console.log('File input element:', this);
            
            if (this.files.length > 0) {
                console.log('File selected:', this.files[0].name, 'Size:', this.files[0].size);
                uploadBtn.disabled = false;
                uploadBtn.style.background = 'linear-gradient(135deg, #00b894 0%, #00a085 100%)';
                uploadBtn.textContent = '📤 Upload Image (' + this.files[0].name + ')';
                console.log('Upload button enabled');
            } else {
                uploadBtn.disabled = true;
                uploadBtn.style.background = 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)';
                uploadBtn.textContent = 'Upload Image';
                console.log('Upload button disabled');
            }
        });
        
        // Also add click event to file input for debugging
        fileInput.addEventListener('click', function(e) {
            console.log('File input clicked directly!');
        });

        // Upload button click event
        uploadBtn.addEventListener('click', async function(e) {
            console.log('Upload button clicked!');
            
            if (!fileInput.files.length) {
                console.log('No files selected');
                return;
            }

            console.log('Starting upload for file:', fileInput.files[0].name);
            
            const formData = new FormData();
            formData.append('file', fileInput.files[0]);
            
            // Add display options
            const autoRotate = document.getElementById('autoRotate').checked;
            const autoZoom = document.getElementById('autoZoom').checked;
            formData.append('auto_rotate', autoRotate);
            formData.append('auto_zoom', autoZoom);
            console.log('Auto-rotate setting:', autoRotate);
            console.log('Auto-zoom setting:', autoZoom);
            
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
                    uploadBtn.style.background = 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)';
                    uploadBtn.textContent = 'Upload Image';
                } else {
                    status.textContent = '❌ Upload failed: ' + (result.error || 'Unknown error');
                    status.className = 'status error';
                }
            } catch (err) {
                console.error('Upload error:', err);
                status.textContent = '❌ Upload failed: ' + err.message;
                status.className = 'status error';
            } finally {
                loading.style.display = 'none';
                status.style.display = 'block';
                uploadBtn.disabled = false;
            }
        });
        
    } else {
        console.error('File input or upload button not found!');
    }

    // File input wrapper click event
    if (fileInputWrapper) {
        fileInputWrapper.addEventListener('click', function(e) {
            console.log('File input wrapper clicked!');
            
            // Create a new file input element and trigger it
            const tempFileInput = document.createElement('input');
            tempFileInput.type = 'file';
            tempFileInput.accept = 'image/*';
            tempFileInput.style.display = 'none';
            
            // Add change event listener to the temp input
            tempFileInput.addEventListener('change', function(e) {
                console.log('Temp file input changed!');
                if (this.files.length > 0) {
                    // Copy the files to the main file input
                    const dataTransfer = new DataTransfer();
                    dataTransfer.items.add(this.files[0]);
                    fileInput.files = dataTransfer.files;
                    
                    // Trigger the change event on the main file input
                    const changeEvent = new Event('change', { bubbles: true });
                    fileInput.dispatchEvent(changeEvent);
                    
                    console.log('Files transferred to main input:', fileInput.files);
                }
                
                // Clean up
                document.body.removeChild(tempFileInput);
            });
            
            // Add to DOM and trigger click
            document.body.appendChild(tempFileInput);
            tempFileInput.click();
        });
    }



    console.log('All event listeners attached successfully');
});

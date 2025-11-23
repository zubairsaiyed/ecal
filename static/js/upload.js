

// Debug logging
console.log('Upload.js loaded');

// Global error handler
window.addEventListener('error', function(e) {
    console.error('Global error:', e.error);
});

// Load current mode
async function loadCurrentMode() {
    try {
        const response = await fetch('/mode');
        const data = await response.json();
        updateModeUI(data.mode);
        
        // Show/hide sync status based on mode
        const calendarStatusDiv = document.getElementById('calendarSyncStatus');
        const albumStatusDiv = document.getElementById('albumSyncStatus');
        const albumConfigDiv = document.getElementById('albumSyncConfig');
        
        if (data.mode === 'calendar_sync') {
            calendarStatusDiv.style.display = 'block';
            albumStatusDiv.style.display = 'none';
            albumConfigDiv.style.display = 'none';
            startCalendarSyncStatusPolling();
            stopAlbumSyncStatusPolling();
        } else if (data.mode === 'album_sync') {
            calendarStatusDiv.style.display = 'none';
            albumStatusDiv.style.display = 'block';
            albumConfigDiv.style.display = 'block';
            stopCalendarSyncStatusPolling();
            startAlbumSyncStatusPolling();
            loadAlbumConfig();
        } else {
            calendarStatusDiv.style.display = 'none';
            albumStatusDiv.style.display = 'none';
            albumConfigDiv.style.display = 'none';
            stopCalendarSyncStatusPolling();
            stopAlbumSyncStatusPolling();
        }
    } catch (error) {
        console.error('Error loading mode:', error);
    }
}

// Calendar sync status polling
let calendarSyncStatusInterval = null;

async function updateCalendarSyncStatus() {
    try {
        const response = await fetch('/calendar_sync/status');
        const status = await response.json();
        
        const statusDiv = document.getElementById('calendarSyncStatus');
        const indicator = document.getElementById('syncActiveIndicator');
        const statusText = document.getElementById('syncStatusText');
        const statusDetails = document.getElementById('syncStatusDetails');
        
        if (!status.active) {
            indicator.className = 'status-indicator inactive';
            statusText.textContent = 'Calendar sync is not active';
            statusDetails.textContent = '';
            return;
        }
        
        // Update indicator based on activity
        if (status.fetching) {
            indicator.className = 'status-indicator fetching';
            statusText.textContent = '🔄 Fetching calendar image...';
        } else if (status.uploading) {
            indicator.className = 'status-indicator uploading';
            statusText.textContent = '📤 Uploading to display...';
        } else if (status.last_error) {
            indicator.className = 'status-indicator error';
            statusText.textContent = '❌ Error: ' + status.last_error;
        } else {
            indicator.className = 'status-indicator active';
            statusText.textContent = '✅ Calendar sync active';
        }
        
        // Update details
        let details = [];
        if (status.last_fetch_time) {
            const fetchTime = new Date(status.last_fetch_time);
            details.push(`Last fetch: ${fetchTime.toLocaleTimeString()}`);
        }
        if (status.last_upload_time) {
            const uploadTime = new Date(status.last_upload_time);
            details.push(`Last upload: ${uploadTime.toLocaleTimeString()}`);
        }
        if (status.process_pid) {
            details.push(`PID: ${status.process_pid}`);
        }
        statusDetails.textContent = details.join(' • ');
        
    } catch (error) {
        console.error('Error fetching calendar sync status:', error);
    }
}

function startCalendarSyncStatusPolling() {
    // Stop any existing polling
    stopCalendarSyncStatusPolling();
    
    // Update immediately
    updateCalendarSyncStatus();
    
    // Then poll every 1 second
    calendarSyncStatusInterval = setInterval(updateCalendarSyncStatus, 1000);
}

function stopCalendarSyncStatusPolling() {
    if (calendarSyncStatusInterval) {
        clearInterval(calendarSyncStatusInterval);
        calendarSyncStatusInterval = null;
    }
}

// Trigger manual calendar sync
async function triggerManualSync() {
    const triggerBtn = document.getElementById('triggerSyncBtn');
    const status = document.getElementById('status');
    
    if (!triggerBtn) return;
    
    triggerBtn.disabled = true;
    triggerBtn.textContent = '⏳ Syncing...';
    
    try {
        const response = await fetch('/calendar_sync/trigger', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const result = await response.json();
        
        if (response.ok) {
            status.textContent = '✅ ' + result.message;
            status.className = 'status success';
            status.style.display = 'block';
            
            // Refresh status display to show the sync happening
            setTimeout(() => {
                updateCalendarSyncStatus();
            }, 500);
        } else {
            status.textContent = '❌ ' + (result.error || 'Failed to trigger sync');
            status.className = 'status error';
            status.style.display = 'block';
        }
    } catch (error) {
        console.error('Trigger sync error:', error);
        status.textContent = '❌ Error triggering sync: ' + error.message;
        status.className = 'status error';
        status.style.display = 'block';
    } finally {
        setTimeout(() => {
            triggerBtn.disabled = false;
            triggerBtn.textContent = '🔄 Force Sync';
        }, 2000);
    }
}

// Update mode UI
function updateModeUI(mode) {
    const modeBadge = document.getElementById('currentMode');
    const modeSelect = document.getElementById('modeSelect');
    const switchBtn = document.getElementById('modeSwitchBtn');
    
    modeBadge.classList.remove('calendar', 'album');
    
    if (mode === 'image_receiver') {
        modeBadge.textContent = '📸 Image Receiver';
        if (modeSelect) {
            modeSelect.value = 'image_receiver';
            // Update switch button text based on selected mode
            updateSwitchButtonText();
        }
    } else if (mode === 'calendar_sync') {
        modeBadge.textContent = '📅 Calendar Sync';
        modeBadge.classList.add('calendar');
        if (modeSelect) {
            modeSelect.value = 'calendar_sync';
            updateSwitchButtonText();
        }
    } else if (mode === 'album_sync') {
        modeBadge.textContent = '📷 Album Sync';
        modeBadge.classList.add('album');
        if (modeSelect) {
            modeSelect.value = 'album_sync';
            updateSwitchButtonText();
        }
    }
}

// Update switch button text to show target mode
function updateSwitchButtonText() {
    const modeSelect = document.getElementById('modeSelect');
    const switchBtn = document.getElementById('modeSwitchBtn');
    const modeBadge = document.getElementById('currentMode');
    
    if (!modeSelect || !switchBtn || !modeBadge) return;
    
    const selectedMode = modeSelect.value;
    
    // Determine current mode from badge
    let currentMode = 'image_receiver';
    if (modeBadge.textContent.includes('Calendar')) {
        currentMode = 'calendar_sync';
    } else if (modeBadge.textContent.includes('Album')) {
        currentMode = 'album_sync';
    }
    
    // If already in selected mode, show "Already Selected"
    if (currentMode === selectedMode) {
        switchBtn.textContent = '✓ Already Selected';
        switchBtn.disabled = true;
    } else {
        // Show which mode will be switched to
        let targetModeName;
        if (selectedMode === 'image_receiver') {
            targetModeName = 'Image Receiver';
        } else if (selectedMode === 'calendar_sync') {
            targetModeName = 'Calendar Sync';
        } else {
            targetModeName = 'Album Sync';
        }
        switchBtn.textContent = `🔄 Switch to ${targetModeName}`;
        switchBtn.disabled = false;
    }
}

// Switch mode
async function switchMode() {
    const modeSelect = document.getElementById('modeSelect');
    const switchBtn = document.getElementById('modeSwitchBtn');
    const status = document.getElementById('status');
    
    // Get selected mode from dropdown
    if (!modeSelect) {
        status.textContent = '❌ Mode selector not found';
        status.className = 'status error';
        status.style.display = 'block';
        return;
    }
    
    const targetMode = modeSelect.value;
    
    // Determine current mode from badge
    const modeBadge = document.getElementById('currentMode');
    let currentMode = 'image_receiver';
    if (modeBadge.textContent.includes('Calendar')) {
        currentMode = 'calendar_sync';
    } else if (modeBadge.textContent.includes('Album')) {
        currentMode = 'album_sync';
    }
    
    // Check if already in target mode
    if (currentMode === targetMode) {
        status.textContent = `✅ Already in ${targetMode === 'image_receiver' ? 'Image Receiver' : targetMode === 'calendar_sync' ? 'Calendar Sync' : 'Album Sync'} mode`;
        status.className = 'status success';
        status.style.display = 'block';
        return;
    }
    
    // Get friendly name for confirmation
    let targetModeName;
    if (targetMode === 'image_receiver') {
        targetModeName = 'Image Receiver';
    } else if (targetMode === 'calendar_sync') {
        targetModeName = 'Calendar Sync';
    } else {
        targetModeName = 'Album Sync';
    }
    
    // Confirm with user
    const confirmed = confirm(`Switch to ${targetModeName} mode?`);
    
    if (!confirmed) return;
    
    switchBtn.disabled = true;
    switchBtn.textContent = '⏳ Switching...';
    
    try {
        const response = await fetch('/mode/switch', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ mode: targetMode })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            status.textContent = `✅ ${result.message}`;
            status.className = 'status success';
            status.style.display = 'block';
            
            updateModeUI(targetMode);
            
            // Show/hide appropriate status sections
            const calendarStatusDiv = document.getElementById('calendarSyncStatus');
            const albumStatusDiv = document.getElementById('albumSyncStatus');
            const albumConfigDiv = document.getElementById('albumSyncConfig');
            
            if (targetMode === 'calendar_sync') {
                if (calendarStatusDiv) {
                    calendarStatusDiv.style.display = 'block';
                    startCalendarSyncStatusPolling();
                }
                if (albumStatusDiv) albumStatusDiv.style.display = 'none';
                if (albumConfigDiv) albumConfigDiv.style.display = 'none';
                stopAlbumSyncStatusPolling();
                setTimeout(() => {
                    status.textContent = '📅 Now in Calendar Sync mode. Calendar sync status shown above.';
                }, 2000);
            } else if (targetMode === 'album_sync') {
                if (calendarStatusDiv) calendarStatusDiv.style.display = 'none';
                if (albumStatusDiv) {
                    albumStatusDiv.style.display = 'block';
                    startAlbumSyncStatusPolling();
                }
                if (albumConfigDiv) {
                    albumConfigDiv.style.display = 'block';
                    loadAlbumConfig();
                }
                stopCalendarSyncStatusPolling();
                setTimeout(() => {
                    status.textContent = '📷 Now in Album Sync mode. Configure your album settings above.';
                }, 2000);
            } else {
                // Switching to image receiver - hide all sync status
                if (calendarStatusDiv) {
                    calendarStatusDiv.style.display = 'none';
                    stopCalendarSyncStatusPolling();
                }
                if (albumStatusDiv) {
                    albumStatusDiv.style.display = 'none';
                    stopAlbumSyncStatusPolling();
                }
                if (albumConfigDiv) albumConfigDiv.style.display = 'none';
            }
        } else {
            status.textContent = `❌ Failed to switch mode: ${result.error}`;
            status.className = 'status error';
            status.style.display = 'block';
        }
    } catch (error) {
        console.error('Mode switch error:', error);
        status.textContent = '❌ Error switching mode: ' + error.message;
        status.className = 'status error';
        status.style.display = 'block';
    } finally {
        switchBtn.disabled = false;
        updateSwitchButtonText(); // Update button text after mode switch
        loadCurrentMode();  // Reload to confirm
    }
}

// Album sync status polling
let albumSyncStatusInterval = null;

async function updateAlbumSyncStatus() {
    try {
        const response = await fetch('/album_sync/status');
        const status = await response.json();
        
        const statusDiv = document.getElementById('albumSyncStatus');
        const indicator = document.getElementById('albumSyncActiveIndicator');
        const statusText = document.getElementById('albumSyncStatusText');
        const statusDetails = document.getElementById('albumSyncStatusDetails');
        
        if (!statusDiv || !indicator || !statusText || !statusDetails) return;
        
        if (!status.active) {
            indicator.className = 'status-indicator inactive';
            statusText.textContent = 'Album sync is not active';
            statusDetails.textContent = '';
            return;
        }
        
        // Update indicator based on activity
        if (status.fetching) {
            indicator.className = 'status-indicator fetching';
            statusText.textContent = '🔄 Fetching album images...';
        } else if (status.uploading) {
            indicator.className = 'status-indicator uploading';
            statusText.textContent = '📤 Uploading to display...';
        } else if (status.last_error) {
            indicator.className = 'status-indicator error';
            statusText.textContent = '❌ Error: ' + status.last_error;
        } else {
            indicator.className = 'status-indicator active';
            statusText.textContent = '✅ Album sync active';
        }
        
        // Update details
        let details = [];
        if (status.last_fetch_time) {
            const fetchTime = new Date(status.last_fetch_time);
            details.push(`Last fetch: ${fetchTime.toLocaleTimeString()}`);
        }
        if (status.last_upload_time) {
            const uploadTime = new Date(status.last_upload_time);
            details.push(`Last upload: ${uploadTime.toLocaleTimeString()}`);
        }
        if (status.process_pid) {
            details.push(`PID: ${status.process_pid}`);
        }
        statusDetails.textContent = details.join(' • ');
        
    } catch (error) {
        console.error('Error fetching album sync status:', error);
    }
}

function startAlbumSyncStatusPolling() {
    // Stop any existing polling
    stopAlbumSyncStatusPolling();
    
    // Update immediately
    updateAlbumSyncStatus();
    
    // Then poll every 1 second
    albumSyncStatusInterval = setInterval(updateAlbumSyncStatus, 1000);
}

function stopAlbumSyncStatusPolling() {
    if (albumSyncStatusInterval) {
        clearInterval(albumSyncStatusInterval);
        albumSyncStatusInterval = null;
    }
}

// Load album configuration
async function loadAlbumConfig() {
    try {
        const response = await fetch('/mode/config');
        const config = await response.json();
        
        const albumConfig = config.album_sync || {};
        
        const albumUrlInput = document.getElementById('albumUrl');
        const albumTokenInput = document.getElementById('albumToken');
        const pollIntervalInput = document.getElementById('pollInterval');
        const displayDurationInput = document.getElementById('displayDuration');
        const shuffleCheckbox = document.getElementById('shuffleImages');
        
        if (albumUrlInput) albumUrlInput.value = albumConfig.album_url || '';
        if (albumTokenInput) albumTokenInput.value = albumConfig.album_token || '';
        if (pollIntervalInput) pollIntervalInput.value = albumConfig.poll_interval || 300;
        if (displayDurationInput) displayDurationInput.value = albumConfig.display_duration || 30;
        if (shuffleCheckbox) shuffleCheckbox.checked = albumConfig.shuffle || false;
    } catch (error) {
        console.error('Error loading album config:', error);
    }
}

// Save album configuration
async function saveAlbumConfig() {
    const status = document.getElementById('status');
    const saveBtn = document.getElementById('saveAlbumConfigBtn');
    
    if (!saveBtn) return;
    
    saveBtn.disabled = true;
    saveBtn.textContent = '⏳ Saving...';
    
    try {
        const albumUrl = document.getElementById('albumUrl').value.trim();
        if (!albumUrl) {
            status.textContent = '❌ Album URL is required';
            status.className = 'status error';
            status.style.display = 'block';
            saveBtn.disabled = false;
            saveBtn.textContent = '💾 Save Configuration';
            return;
        }
        
        const config = {
            mode_type: 'album_sync',
            album_url: albumUrl,
            album_token: document.getElementById('albumToken').value.trim(),
            poll_interval: parseInt(document.getElementById('pollInterval').value) || 300,
            display_duration: parseInt(document.getElementById('displayDuration').value) || 30,
            shuffle: document.getElementById('shuffleImages').checked
        };
        
        const response = await fetch('/mode/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            status.textContent = '✅ Configuration saved! Restart album sync mode to apply changes.';
            status.className = 'status success';
            status.style.display = 'block';
        } else {
            status.textContent = '❌ Failed to save configuration: ' + (result.error || 'Unknown error');
            status.className = 'status error';
            status.style.display = 'block';
        }
    } catch (error) {
        console.error('Save config error:', error);
        status.textContent = '❌ Error saving configuration: ' + error.message;
        status.className = 'status error';
        status.style.display = 'block';
    } finally {
        saveBtn.disabled = false;
        saveBtn.textContent = '💾 Save Configuration';
    }
}

// Wait for DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM fully loaded');
    
    // Load current mode on page load
    loadCurrentMode();
    
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
            const rotationMode = document.getElementById('rotationMode').value;
            const autoZoom = document.getElementById('autoZoom').checked;
            formData.append('rotation_mode', rotationMode);
            formData.append('auto_zoom', autoZoom);
            console.log('Rotation mode:', rotationMode);
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
    
    // Mode switch button click event
    const modeSwitchBtn = document.getElementById('modeSwitchBtn');
    if (modeSwitchBtn) {
        modeSwitchBtn.addEventListener('click', switchMode);
        console.log('Mode switch button listener attached');
    }
    
    // Mode selector change event to update button text
    const modeSelect = document.getElementById('modeSelect');
    if (modeSelect) {
        modeSelect.addEventListener('change', updateSwitchButtonText);
        // Initialize button text
        updateSwitchButtonText();
    }
    
    // Calendar sync trigger button
    const triggerSyncBtn = document.getElementById('triggerSyncBtn');
    if (triggerSyncBtn) {
        triggerSyncBtn.addEventListener('click', triggerManualSync);
        console.log('Trigger sync button listener attached');
    }
    
    // Album sync save config button
    const saveAlbumConfigBtn = document.getElementById('saveAlbumConfigBtn');
    if (saveAlbumConfigBtn) {
        saveAlbumConfigBtn.addEventListener('click', saveAlbumConfig);
        console.log('Save album config button listener attached');
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

/**
 * Test Case Refinement - File Upload Functionality
 * 
 * This script handles file upload for the "Review & Refine Test Case" tab,
 * including drag-and-drop, file selection, preview, and removal functionality.
 */

document.addEventListener('DOMContentLoaded', function() {
    // Cache DOM elements
    const dropArea = document.getElementById('refinement-drop-area');
    const fileInput = document.getElementById('test_case_file');
    const filePreview = document.getElementById('refinement-file-preview');
    const fileName = document.getElementById('refinement-file-name');
    const fileSize = document.getElementById('refinement-file-size');
    const removeFileBtn = document.getElementById('refinement-remove-file');
    const analyzeBtn = document.getElementById('analyzeTestCaseBtn');
    
    // Check if required elements exist
    if (!dropArea || !fileInput) {
        console.error('Required file upload elements not found');
        return;
    }
    
    console.log('Initializing file upload functionality for test case refinement');
    
    // File Input Change Event
    fileInput.addEventListener('change', function() {
        console.log('File input changed');
        if (this.files.length > 0) {
            const file = this.files[0];
            console.log('Selected file:', file.name);
            updateFilePreview(file);
        }
    });
    
    // Click to browse
    dropArea.addEventListener('click', function() {
        console.log('Drop area clicked, triggering file input');
        fileInput.click();
    });
    
    // Prevent default behaviors for drag events
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, function(e) {
            e.preventDefault();
            e.stopPropagation();
        }, false);
    });
    
    // Highlight drop area when file is dragged over
    ['dragenter', 'dragover'].forEach(eventName => {
        dropArea.addEventListener(eventName, function() {
            console.log('File dragged over drop area');
            dropArea.style.borderColor = '#007bff';
            dropArea.style.backgroundColor = 'rgba(0, 123, 255, 0.1)';
        });
    });
    
    // Remove highlight when file leaves drop area
    ['dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, function() {
            console.log('File left drop area');
            dropArea.style.borderColor = '#ced4da';
            dropArea.style.backgroundColor = '';
        });
    });
    
    // Handle file drop
    dropArea.addEventListener('drop', function(e) {
        console.log('File dropped');
        const file = e.dataTransfer.files[0];
        
        if (file) {
            // Check file type
            if (isValidFileType(file)) {
                // Set the file to the file input
                if (fileInput.files instanceof FileList) {
                    // Create a new DataTransfer object
                    const dataTransfer = new DataTransfer();
                    dataTransfer.items.add(file);
                    fileInput.files = dataTransfer.files;
                }
                
                updateFilePreview(file);
            } else {
                // Show error for invalid file type
                showNotification('Invalid file type. Please upload an Excel or Word file.', 'error');
            }
        }
    });
    
    // Handle file removal
    if (removeFileBtn) {
        removeFileBtn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            removeFile();
        });
    }
    
    // Update file preview when a file is selected
    function updateFilePreview(file) {
        if (!filePreview || !fileName || !fileSize) {
            console.error('Required preview elements not found');
            return;
        }
        
        // Update file information
        fileName.textContent = file.name;
        fileSize.textContent = formatFileSize(file.size);
        
        // Show preview, hide drop area
        if (filePreview.classList.contains('d-none')) {
            filePreview.classList.remove('d-none');
        }
        filePreview.style.display = 'flex';
        
        if (!dropArea.classList.contains('d-none')) {
            dropArea.classList.add('d-none');
        }
        dropArea.style.display = 'none';
        
        // Enable analyze button
        if (analyzeBtn) {
            analyzeBtn.disabled = false;
        }
    }
    
    // Remove the selected file
    function removeFile() {
        console.log('Removing file');
        
        if (fileInput) {
            fileInput.value = '';
        }
        
        if (filePreview && dropArea) {
            if (!filePreview.classList.contains('d-none')) {
                filePreview.classList.add('d-none');
            }
            filePreview.style.display = 'none';
            
            if (dropArea.classList.contains('d-none')) {
                dropArea.classList.remove('d-none');
            }
            dropArea.style.display = 'block';
        }
        
        // Disable analyze button
        if (analyzeBtn) {
            analyzeBtn.disabled = true;
        }
    }
    
    // Check if the file type is valid (Excel or Word)
    function isValidFileType(file) {
        const validTypes = [
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        ];
        
        const validExtensions = ['.xlsx', '.xls', '.docx', '.doc'];
        
        // Check by MIME type
        if (validTypes.includes(file.type)) {
            return true;
        }
        
        // Check by file extension as fallback
        const fileName = file.name || '';
        const fileExt = fileName.substring(fileName.lastIndexOf('.')).toLowerCase();
        
        return validExtensions.includes(fileExt);
    }
    
    // Format file size in human-readable format
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    // Show notification
    function showNotification(message, type) {
        // Check if UIUtils is available
        if (window.TestGeneration && TestGeneration.UIUtils && TestGeneration.UIUtils.showNotification) {
            TestGeneration.UIUtils.showNotification(message, type);
        } else {
            alert(message);
        }
    }
    
    console.log('File upload functionality for test case refinement initialized');
});
/**
 * UI Utilities Module for the Test Generation & Refinement interface
 * 
 * This module provides common UI utility functions that can be used across
 * different modules of the test generation and refinement interface.
 */

// Create namespace if it doesn't exist
var TestGeneration = TestGeneration || {};

/**
 * UI utilities for the Test Generation & Refinement interface
 */
TestGeneration.UIUtils = (function() {
    /**
     * Show a notification message to the user
     * @param {string} message - The message to display
     * @param {string} type - The type of notification (success, error, warning, info)
     * @param {number} duration - How long to show the notification in ms (default: 5000ms)
     */
    function showNotification(message, type, duration) {
        console.log(`Notification (${type}): ${message}`);
        
        // Default duration is 5 seconds
        duration = duration || 5000;
        
        // Check if notification container exists, create if not
        let container = document.getElementById('notification-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'notification-container';
            container.style.position = 'fixed';
            container.style.top = '20px';
            container.style.right = '20px';
            container.style.zIndex = '9999';
            document.body.appendChild(container);
        }
        
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} alert-dismissible fade show`;
        notification.role = 'alert';
        
        // Add notification content
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        
        // Add to container
        container.appendChild(notification);
        
        // Remove after duration
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300); // Wait for fade out animation
        }, duration);
        
        // Add click handler to close button
        const closeButton = notification.querySelector('.btn-close');
        if (closeButton) {
            closeButton.addEventListener('click', function() {
                notification.classList.remove('show');
                setTimeout(() => {
                    if (notification.parentNode) {
                        notification.parentNode.removeChild(notification);
                    }
                }, 300); // Wait for fade out animation
            });
        }
    }
    
    /**
     * Format file size in human-readable format
     * @param {number} bytes - File size in bytes
     * @returns {string} Formatted file size
     */
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    /**
     * Format a date in a user-friendly format
     * @param {Date} date - The date to format
     * @returns {string} Formatted date string
     */
    function formatDate(date) {
        if (!(date instanceof Date) || isNaN(date)) {
            return 'Invalid Date';
        }
        
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
    }
    
    /**
     * Check if a file type is allowed
     * @param {File} file - The file to check
     * @param {Array} allowedTypes - Array of allowed file extensions (e.g., ['.xlsx', '.docx'])
     * @returns {boolean} True if the file type is allowed
     */
    function isAllowedFileType(file, allowedTypes) {
        // Check by file extension
        const fileName = file.name || '';
        const fileExt = fileName.substring(fileName.lastIndexOf('.')).toLowerCase();
        
        // Check by MIME type as backup
        const mimeType = file.type;
        
        const mimeMap = {
            '.xlsx': ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'],
            '.xls': ['application/vnd.ms-excel'],
            '.docx': ['application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
            '.doc': ['application/msword']
        };
        
        // Check extension first
        if (allowedTypes.includes(fileExt)) {
            return true;
        }
        
        // Check MIME type as backup
        for (const ext of allowedTypes) {
            if (mimeMap[ext] && mimeMap[ext].includes(mimeType)) {
                return true;
            }
        }
        
        return false;
    }
    
    /**
     * Get CSRF token from cookie
     * @returns {string|null} CSRF token or null if not found
     */
    function getCSRFToken() {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, 10) === 'csrftoken=') {
                    cookieValue = decodeURIComponent(cookie.substring(10));
                    break;
                }
            }
        }
        return cookieValue;
    }
    
    // Return public API
    return {
        showNotification: showNotification,
        formatFileSize: formatFileSize,
        formatDate: formatDate,
        isAllowedFileType: isAllowedFileType,
        getCSRFToken: getCSRFToken
    };
})();

// Log that this module has loaded successfully
console.log('UI Utilities module loaded successfully');
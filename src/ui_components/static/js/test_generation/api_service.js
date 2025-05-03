/**
 * API Service Module for the Test Generation & Refinement interface
 * 
 * This module provides functions for communicating with the backend API,
 * handling file uploads, and processing API responses.
 */

// Create namespace if it doesn't exist
var TestGeneration = TestGeneration || {};

/**
 * API service for the Test Generation & Refinement interface
 */
TestGeneration.API = (function() {
    // Base URL for API requests (empty means relative to current URL)
    const BASE_URL = '';
    
    /**
     * Make a GET request to the API
     * @param {string} url - API endpoint URL
     * @param {Object} params - URL parameters (optional)
     * @returns {Promise} Promise resolving to the API response
     */
    function get(url, params) {
        // Add query parameters if provided
        let queryUrl = url;
        if (params) {
            const queryParams = new URLSearchParams();
            for (const key in params) {
                queryParams.append(key, params[key]);
            }
            queryUrl += '?' + queryParams.toString();
        }
        
        // Make the request
        return fetch(BASE_URL + queryUrl, {
            method: 'GET',
            headers: {
                'Accept': 'application/json'
            },
            credentials: 'same-origin' // Include cookies
        })
        .then(checkResponse)
        .then(response => response.json())
        .catch(handleError);
    }
    
    /**
     * Make a POST request to the API
     * @param {string} url - API endpoint URL
     * @param {Object} data - Data to send in the request body
     * @returns {Promise} Promise resolving to the API response
     */
    function post(url, data) {
        // Get CSRF token
        const csrfToken = TestGeneration.UIUtils.getCSRFToken();
        
        // Make the request
        return fetch(BASE_URL + url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify(data),
            credentials: 'same-origin' // Include cookies
        })
        .then(checkResponse)
        .then(response => response.json())
        .catch(handleError);
    }
    
    /**
     * Make a POST request with form data to the API (for file uploads)
     * @param {string} url - API endpoint URL
     * @param {FormData} formData - Form data to send in the request body
     * @returns {Promise} Promise resolving to the API response
     */
    function postFormData(url, formData) {
        console.log('Posting form data to:', url);
        
        // Get CSRF token
        const csrfToken = TestGeneration.UIUtils.getCSRFToken();
        
        // Add CSRF token to form data if not already present
        if (csrfToken && !formData.has('csrfmiddlewaretoken')) {
            formData.append('csrfmiddlewaretoken', csrfToken);
        }
        
        // Log form data entries (for debugging)
        console.log('Form data entries:');
        for (const pair of formData.entries()) {
            // Don't log file contents, just the file name
            if (pair[1] instanceof File) {
                console.log(pair[0] + ': File - ' + pair[1].name);
            } else {
                console.log(pair[0] + ': ' + pair[1]);
            }
        }
        
        // Make the request
        return fetch(BASE_URL + url, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken
                // Don't set Content-Type, let the browser set it automatically for multipart/form-data
            },
            body: formData,
            credentials: 'same-origin' // Include cookies
        })
        .then(checkResponse)
        .then(response => response.json())
        .catch(handleError);
    }
    
    /**
     * Upload a file to the API
     * @param {string} url - API endpoint URL
     * @param {File} file - File to upload
     * @param {Object} additionalData - Additional data to include with the file
     * @param {Function} progressCallback - Callback for upload progress
     * @returns {Promise} Promise resolving to the API response
     */
    function uploadFile(url, file, additionalData, progressCallback) {
        console.log('Uploading file:', file.name, 'to:', url);
        
        // Create form data
        const formData = new FormData();
        formData.append('test_case_file', file);
        
        // Add additional data if provided
        if (additionalData) {
            for (const key in additionalData) {
                formData.append(key, additionalData[key]);
            }
        }
        
        // Get CSRF token
        const csrfToken = TestGeneration.UIUtils.getCSRFToken();
        
        // Check if browser supports XMLHttpRequest with upload progress
        if (progressCallback && XMLHttpRequest.prototype.hasOwnProperty('upload')) {
            return new Promise((resolve, reject) => {
                const xhr = new XMLHttpRequest();
                
                // Setup progress event
                xhr.upload.addEventListener('progress', function(event) {
                    if (event.lengthComputable) {
                        const percentComplete = (event.loaded / event.total) * 100;
                        progressCallback(percentComplete);
                    }
                });
                
                // Setup complete event
                xhr.addEventListener('load', function() {
                    if (xhr.status >= 200 && xhr.status < 300) {
                        try {
                            const response = JSON.parse(xhr.responseText);
                            resolve(response);
                        } catch (e) {
                            reject(new Error('Invalid JSON response'));
                        }
                    } else {
                        reject(new Error('Upload failed: ' + xhr.status));
                    }
                });
                
                // Setup error event
                xhr.addEventListener('error', function() {
                    reject(new Error('Network error during upload'));
                });
                
                // Open and send the request
                xhr.open('POST', BASE_URL + url, true);
                xhr.setRequestHeader('X-CSRFToken', csrfToken);
                xhr.send(formData);
            });
        } else {
            // Fall back to regular fetch if no progress callback or browser doesn't support it
            return postFormData(url, formData);
        }
    }
    
    /**
     * Check the response status and handle errors
     * @param {Response} response - Fetch API response
     * @returns {Response} The same response if successful
     * @throws {Error} If the response indicates an error
     * @private
     */
    function checkResponse(response) {
        if (!response.ok) {
            // Try to get error details from response
            return response.text().then(text => {
                let errorMessage = 'HTTP error ' + response.status;
                try {
                    // Try to parse as JSON
                    const errorData = JSON.parse(text);
                    if (errorData.message) {
                        errorMessage = errorData.message;
                    } else if (errorData.error) {
                        errorMessage = errorData.error;
                    }
                } catch (e) {
                    // Use text as is if not JSON
                    if (text) {
                        errorMessage += ': ' + text;
                    }
                }
                throw new Error(errorMessage);
            });
        }
        return response;
    }
    
    /**
     * Handle API errors
     * @param {Error} error - The error object
     * @throws {Error} Always rethrows the error after logging
     * @private
     */
    function handleError(error) {
        console.error('API Error:', error);
        
        // Show user-friendly notification
        if (TestGeneration.UIUtils && TestGeneration.UIUtils.showNotification) {
            TestGeneration.UIUtils.showNotification(
                'API Error: ' + error.message,
                'error'
            );
        }
        
        // Rethrow the error for further handling
        throw error;
    }
    
    // Return public API
    return {
        get: get,
        post: post,
        postFormData: postFormData,
        uploadFile: uploadFile
    };
})();

// Log that this module has loaded successfully
console.log('API Service module loaded successfully');
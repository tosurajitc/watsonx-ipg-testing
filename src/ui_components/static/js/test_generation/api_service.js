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
     * @param {boolean} expectBlob - Whether to expect a blob response (for file downloads)
     * @returns {Promise} Promise resolving to the API response
     */
    function post(url, data, expectBlob = false) {
        // Debug logging to trace execution flow
        console.log('API.post called with URL:', url);
        
        // Get CSRF token
        const csrfToken = TestGeneration.UIUtils ? TestGeneration.UIUtils.getCSRFToken() : '';
        
        // Fix for absolute paths - this ensures URLs with leading slash work correctly
        const requestUrl = url.startsWith('/') ? 
            window.location.origin + url : BASE_URL + url;
        
        console.log('Making request to URL:', requestUrl);
        
        // Make the request - use requestUrl instead of BASE_URL + url
        return fetch(requestUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': expectBlob ? '*/*' : 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify(data),
            credentials: 'same-origin' // Include cookies
        })
        .then(response => {
            if (!response.ok) {
                return response.text().then(text => {
                    throw new Error(`Server error (${response.status}): ${text}`);
                });
            }
            
            // Return blob for file downloads or parse JSON otherwise
            if (expectBlob) {
                return response.blob();
            } else {
                return response.json();
            }
        })
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
        const csrfToken = TestGeneration.UIUtils ? TestGeneration.UIUtils.getCSRFToken() : '';
        
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
        const csrfToken = TestGeneration.UIUtils ? TestGeneration.UIUtils.getCSRFToken() : '';
        
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
     * Download a file from the API
     * @param {string} url - API endpoint URL
     * @param {Object} data - Data to send in the request body
     * @param {string} filename - Suggested filename for the download
     * @param {Function} progressCallback - Callback for download progress (optional)
     * @returns {Promise} Promise resolving when the download is complete
     */
    function downloadFile(url, data, filename, progressCallback) {
        console.log('Downloading file from:', url);
        
        // Get CSRF token
        const csrfToken = TestGeneration.UIUtils ? TestGeneration.UIUtils.getCSRFToken() : '';
        
        // Fix for absolute paths - this ensures URLs with leading slash work correctly
        const requestUrl = url.startsWith('/') ? 
            window.location.origin + url : BASE_URL + url;
        
        console.log('Making download request to URL:', requestUrl);
        
        // Check if browser supports Fetch API with download progress
        if (progressCallback && 'ReadableStream' in window) {
            return fetch(requestUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': '*/*',  // Accept any content type
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify(data),
                credentials: 'same-origin' // Include cookies
            })
            .then(response => {
                if (!response.ok) {
                    return response.text().then(text => {
                        let errorMessage = `Server error (${response.status})`;
                        try {
                            // Try to parse as JSON for better error messages
                            const errorData = JSON.parse(text);
                            if (errorData.message) {
                                errorMessage += `: ${errorData.message}`;
                            } else if (errorData.error) {
                                errorMessage += `: ${errorData.error}`;
                            }
                        } catch (e) {
                            // Use the text as is if not JSON
                            if (text) {
                                errorMessage += `: ${text}`;
                            }
                        }
                        throw new Error(errorMessage);
                    });
                }
                
                // Log response headers for debugging
                console.log('Response headers received:', 
                    [...response.headers.entries()].reduce((obj, [key, val]) => {
                        obj[key] = val;
                        return obj;
                    }, {})
                );
                
                // Get content length if available
                const contentLength = response.headers.get('Content-Length');
                let loaded = 0;
                
                // Get filename from Content-Disposition header if available
                const contentDisposition = response.headers.get('Content-Disposition');
                if (contentDisposition) {
                    const filenameMatch = contentDisposition.match(/filename="(.+)"|filename=([^;]+)/);
                    if (filenameMatch) {
                        filename = filenameMatch[1] || filenameMatch[2];
                        console.log('Using filename from Content-Disposition:', filename);
                    }
                }
                
                // Ensure we have a valid filename
                if (!filename || filename.trim() === '') {
                    filename = 'download-' + new Date().toISOString().substring(0, 10);
                    console.log('Using default filename:', filename);
                }
                
                // Check if response body is readable stream
                if (response.body) {
                    console.log('Response body is available as stream');
                    
                    // Create a reader for the response body stream
                    const reader = response.body.getReader();
                    const chunks = [];
                    
                    if (progressCallback) {
                        progressCallback(0); // Initialize progress at 0%
                    }
                    
                    // Process the stream
                    return new Promise((resolve, reject) => {
                        function processStream() {
                            reader.read().then(({done, value}) => {
                                if (done) {
                                    console.log('Download stream complete, preparing file');
                                    
                                    // Combine chunks into a single Blob
                                    const blob = new Blob(chunks);
                                    console.log(`Downloaded file size: ${blob.size} bytes`);
                                    
                                    try {
                                        // Create a download link
                                        const url = window.URL.createObjectURL(blob);
                                        const a = document.createElement('a');
                                        a.style.display = 'none';
                                        a.href = url;
                                        a.download = filename;
                                        document.body.appendChild(a);
                                        
                                        console.log('Triggering file download for:', filename);
                                        a.click();
                                        
                                        // Clean up
                                        setTimeout(() => {
                                            document.body.removeChild(a);
                                            window.URL.revokeObjectURL(url);
                                            console.log('Download cleanup complete');
                                        }, 100);
                                        
                                        if (progressCallback) {
                                            progressCallback(100); // Ensure we end at 100%
                                        }
                                        
                                        // Resolve the promise
                                        resolve();
                                    } catch (downloadError) {
                                        console.error('Error during file download:', downloadError);
                                        reject(new Error(`Download error: ${downloadError.message}`));
                                    }
                                    return;
                                }
                                
                                // Store the chunk
                                chunks.push(value);
                                
                                // Update progress
                                if (progressCallback) {
                                    loaded += value.length;
                                    if (contentLength) {
                                        const percentComplete = Math.min(
                                            99, // Cap at 99% until fully complete
                                            Math.round((loaded / parseInt(contentLength, 10)) * 100)
                                        );
                                        progressCallback(percentComplete);
                                    } else {
                                        // If content length is unknown, use chunk count as a proxy
                                        // This isn't accurate but provides some feedback
                                        progressCallback(Math.min(95, chunks.length * 5));
                                    }
                                }
                                
                                // Continue processing
                                processStream();
                            }).catch(streamError => {
                                console.error('Error reading download stream:', streamError);
                                reject(new Error(`Stream error: ${streamError.message}`));
                            });
                        }
                        
                        processStream();
                    });
                } else {
                    console.warn('Response body stream not available, falling back to blob');
                    
                    // Fallback to blob if streaming isn't working
                    return response.blob().then(blob => {
                        console.log(`Downloaded file size: ${blob.size} bytes`);
                        
                        // Create a download link
                        const url = window.URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.style.display = 'none';
                        a.href = url;
                        a.download = filename;
                        document.body.appendChild(a);
                        a.click();
                        
                        // Clean up
                        setTimeout(() => {
                            document.body.removeChild(a);
                            window.URL.revokeObjectURL(url);
                        }, 100);
                        
                        if (progressCallback) {
                            progressCallback(100); // Complete the progress
                        }
                    });
                }
            })
            .catch(error => {
                console.error('Download failed:', error);
                
                // Show user-friendly notification if available
                if (TestGeneration.UIUtils && TestGeneration.UIUtils.showNotification) {
                    TestGeneration.UIUtils.showNotification(
                        `Download failed: ${error.message}`,
                        'error'
                    );
                }
                
                throw error; // Re-throw for further handling
            });
        } else {
            console.log('Stream API not supported or no progress callback, using basic fetch');
            
            // Fall back to regular post with blob response for browsers without stream support
            return fetch(requestUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': '*/*',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify(data),
                credentials: 'same-origin'
            })
            .then(response => {
                if (!response.ok) {
                    return response.text().then(text => {
                        throw new Error(`Server error (${response.status}): ${text}`);
                    });
                }
                return response.blob();
            })
            .then(blob => {
                console.log(`Downloaded file size: ${blob.size} bytes`);
                
                // Create a download link
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.style.display = 'none';
                a.href = url;
                a.download = filename || 'download';
                document.body.appendChild(a);
                a.click();
                
                // Clean up
                setTimeout(() => {
                    document.body.removeChild(a);
                    window.URL.revokeObjectURL(url);
                }, 100);
                
                // Show success notification
                if (TestGeneration.UIUtils && TestGeneration.UIUtils.showNotification) {
                    TestGeneration.UIUtils.showNotification(
                        `File "${filename}" downloaded successfully.`,
                        'success'
                    );
                }
            })
            .catch(error => {
                console.error('Download failed:', error);
                
                // Show user-friendly notification if available
                if (TestGeneration.UIUtils && TestGeneration.UIUtils.showNotification) {
                    TestGeneration.UIUtils.showNotification(
                        `Download failed: ${error.message}`,
                        'error'
                    );
                }
                
                throw error; // Re-throw for further handling
            });
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
     * @throws {Error} Always rethrows the error after processing
     * @private
     */
    function handleError(error) {
        console.error('API Error:', error);
        
        let processedError = error;
        
        // Try to parse the error response if it's a string
        if (typeof error.message === 'string' && error.message.includes('Server error')) {
            try {
                // Extract the JSON part
                const jsonMatch = error.message.match(/Server error \(\d+\): (.*)/);
                if (jsonMatch && jsonMatch[1]) {
                    const errorData = JSON.parse(jsonMatch[1]);
                    processedError = errorData;
                }
            } catch (e) {
                // If parsing fails, use the original error
                console.warn('Failed to parse error response:', e);
            }
        }
        
        // Show user-friendly notification
        if (TestGeneration.UIUtils && TestGeneration.UIUtils.showNotification) {
            // If we have a structured error
            if (processedError.error && processedError.error.title) {
                TestGeneration.UIUtils.showNotification(
                    processedError.error.title + ': ' + processedError.error.message,
                    'error'
                );
            } else {
                // Fallback to simple error notification
                TestGeneration.UIUtils.showNotification(
                    'API Error: ' + (error.message || 'Unknown error'),
                    'error'
                );
            }
        }
        
        // Rethrow the processed error for further handling
        throw processedError;
    }
    
    // Return public API
    return {
        get: get,
        post: post,
        postFormData: postFormData,
        uploadFile: uploadFile,
        downloadFile: downloadFile
    };
})();

// Log that this module has loaded successfully
console.log('API Service module loaded successfully');
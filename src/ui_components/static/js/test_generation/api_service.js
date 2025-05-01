/**
 * Test Generation & Refinement - API Service Module
 * 
 * This module provides a centralized service for making API calls to the backend.
 * It handles standard HTTP methods, error processing, and authentication.
 */

// Ensure the TestGeneration namespace exists
const TestGeneration = TestGeneration || {};

/**
 * API service for making backend requests
 */
TestGeneration.API = (function() {
    // Private variables
    let initialized = false;
    let baseUrl = ''; // If API is at a different base URL than the frontend
    let defaultHeaders = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    };
    
    /**
     * Initialize the API service
     * @public
     */
    function initialize() {
        if (initialized) return;
        
        console.log('Initializing API Service...');
        
        // Set CSRF token for all requests
        updateCSRFToken();
        
        // Set up global AJAX error handler
        setupGlobalErrorHandler();
        
        // Set initialization flag
        initialized = true;
        
        console.log('API Service initialized');
    }
    
    /**
     * Update the CSRF token in default headers
     * @private
     */
    function updateCSRFToken() {
        const csrfToken = getCSRFToken();
        if (csrfToken) {
            defaultHeaders['X-CSRFToken'] = csrfToken;
        }
    }
    
    /**
     * Get CSRF token from cookie
     * @returns {string|null} CSRF token or null if not found
     * @private
     */
    function getCSRFToken() {
        const name = 'csrftoken';
        let cookieValue = null;
        
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        
        return cookieValue;
    }
    
    /**
     * Set up global error handler for AJAX requests
     * @private
     */
    function setupGlobalErrorHandler() {
        window.addEventListener('unhandledrejection', function(event) {
            if (event.reason && event.reason.isApiError) {
                console.error('Unhandled API error:', event.reason);
                
                // Show error notification if UIUtils is available
                if (TestGeneration.UIUtils && typeof TestGeneration.UIUtils.showNotification === 'function') {
                    TestGeneration.UIUtils.showNotification(
                        'API Error: ' + (event.reason.message || 'Unknown error'),
                        'error'
                    );
                }
            }
        });
    }
    
    /**
     * Create API error object
     * @param {Response} response - Fetch API response
     * @param {string} errorMessage - Error message
     * @returns {Error} Error object with additional API error properties
     * @private
     */
    function createApiError(response, errorMessage) {
        const error = new Error(errorMessage || 'API request failed');
        error.status = response ? response.status : 0;
        error.statusText = response ? response.statusText : '';
        error.isApiError = true;
        return error;
    }
    
    /**
     * Process API response
     * @param {Response} response - Fetch API response
     * @returns {Promise<Object>} Processed response data
     * @private
     */
    async function processResponse(response) {
        // Update CSRF token from response headers if present
        const csrfToken = response.headers.get('X-CSRFToken');
        if (csrfToken) {
            defaultHeaders['X-CSRFToken'] = csrfToken;
        }
        
        // Check if response is ok (status 200-299)
        if (!response.ok) {
            let errorMessage = `API Error: ${response.status} ${response.statusText}`;
            
            // Try to parse error response body
            try {
                const errorData = await response.json();
                if (errorData.message) {
                    errorMessage = errorData.message;
                } else if (errorData.error && errorData.error.message) {
                    errorMessage = errorData.error.message;
                }
            } catch (e) {
                // Ignore parsing errors
            }
            
            throw createApiError(response, errorMessage);
        }
        
        // Check content type
        const contentType = response.headers.get('Content-Type') || '';
        
        // Parse response based on content type
        if (contentType.includes('application/json')) {
            return response.json();
        } else if (contentType.includes('text/')) {
            return response.text();
        } else {
            return response;
        }
    }
    
    /**
     * Make a GET request
     * @param {string} url - API endpoint URL
     * @param {Object} [params=null] - Query parameters
     * @param {Object} [options={}] - Additional fetch options
     * @returns {Promise<Object>} Response data
     * @public
     */
    function get(url, params = null, options = {}) {
        // Build URL with query parameters
        let requestUrl = baseUrl + url;
        if (params) {
            const queryString = new URLSearchParams(params).toString();
            requestUrl += (url.includes('?') ? '&' : '?') + queryString;
        }
        
        // Merge headers
        const headers = { ...defaultHeaders, ...options.headers };
        
        // Make the request
        return fetch(requestUrl, {
            method: 'GET',
            headers,
            credentials: 'same-origin',
            ...options
        })
        .then(processResponse)
        .catch(error => {
            console.error(`GET ${url} failed:`, error);
            throw error.isApiError ? error : createApiError(null, error.message);
        });
    }
    
    /**
     * Make a POST request with JSON data
     * @param {string} url - API endpoint URL
     * @param {Object} data - Request body data
     * @param {Object} [options={}] - Additional fetch options
     * @returns {Promise<Object>} Response data
     * @public
     */
    function post(url, data = {}, options = {}) {
        // Merge headers
        const headers = { ...defaultHeaders, ...options.headers };
        
        // Make the request
        return fetch(baseUrl + url, {
            method: 'POST',
            headers,
            credentials: 'same-origin',
            body: JSON.stringify(data),
            ...options
        })
        .then(processResponse)
        .catch(error => {
            console.error(`POST ${url} failed:`, error);
            throw error.isApiError ? error : createApiError(null, error.message);
        });
    }
    
    /**
     * Make a POST request with FormData
     * @param {string} url - API endpoint URL
     * @param {FormData} formData - Form data
     * @param {Object} [options={}] - Additional fetch options
     * @returns {Promise<Object>} Response data
     * @public
     */
    function postWithFormData(url, formData, options = {}) {
        // Create headers without Content-Type (browser will set it with boundary)
        const headers = { ...defaultHeaders };
        delete headers['Content-Type'];
        
        // Add any additional headers
        if (options.headers) {
            Object.assign(headers, options.headers);
        }
        
        // Make the request
        return fetch(baseUrl + url, {
            method: 'POST',
            headers,
            credentials: 'same-origin',
            body: formData,
            ...options
        })
        .then(processResponse)
        .catch(error => {
            console.error(`POST FormData ${url} failed:`, error);
            throw error.isApiError ? error : createApiError(null, error.message);
        });
    }
    
    /**
     * Make a POST request and get blob response (for file downloads)
     * @param {string} url - API endpoint URL
     * @param {Object} data - Request body data
     * @param {Object} [options={}] - Additional fetch options
     * @returns {Promise<Blob>} Response blob
     * @public
     */
    function postForBlob(url, data = {}, options = {}) {
        // Merge headers
        const headers = { ...defaultHeaders, ...options.headers };
        
        // Make the request
        return fetch(baseUrl + url, {
            method: 'POST',
            headers,
            credentials: 'same-origin',
            body: JSON.stringify(data),
            ...options
        })
        .then(response => {
            // Check for errors but don't process response as JSON
            if (!response.ok) {
                throw createApiError(response, `API Error: ${response.status} ${response.statusText}`);
            }
            
            // Return blob
            return response.blob();
        })
        .catch(error => {
            console.error(`POST for Blob ${url} failed:`, error);
            throw error.isApiError ? error : createApiError(null, error.message);
        });
    }
    
    /**
     * Make a PUT request
     * @param {string} url - API endpoint URL
     * @param {Object} data - Request body data
     * @param {Object} [options={}] - Additional fetch options
     * @returns {Promise<Object>} Response data
     * @public
     */
    function put(url, data = {}, options = {}) {
        // Merge headers
        const headers = { ...defaultHeaders, ...options.headers };
        
        // Make the request
        return fetch(baseUrl + url, {
            method: 'PUT',
            headers,
            credentials: 'same-origin',
            body: JSON.stringify(data),
            ...options
        })
        .then(processResponse)
        .catch(error => {
            console.error(`PUT ${url} failed:`, error);
            throw error.isApiError ? error : createApiError(null, error.message);
        });
    }
    
    /**
     * Make a DELETE request
     * @param {string} url - API endpoint URL
     * @param {Object} [options={}] - Additional fetch options
     * @returns {Promise<Object>} Response data
     * @public
     */
    function del(url, options = {}) {
        // Merge headers
        const headers = { ...defaultHeaders, ...options.headers };
        
        // Make the request
        return fetch(baseUrl + url, {
            method: 'DELETE',
            headers,
            credentials: 'same-origin',
            ...options
        })
        .then(processResponse)
        .catch(error => {
            console.error(`DELETE ${url} failed:`, error);
            throw error.isApiError ? error : createApiError(null, error.message);
        });
    }
    
    /**
     * Make a PATCH request
     * @param {string} url - API endpoint URL
     * @param {Object} data - Request body data
     * @param {Object} [options={}] - Additional fetch options
     * @returns {Promise<Object>} Response data
     * @public
     */
    function patch(url, data = {}, options = {}) {
        // Merge headers
        const headers = { ...defaultHeaders, ...options.headers };
        
        // Make the request
        return fetch(baseUrl + url, {
            method: 'PATCH',
            headers,
            credentials: 'same-origin',
            body: JSON.stringify(data),
            ...options
        })
        .then(processResponse)
        .catch(error => {
            console.error(`PATCH ${url} failed:`, error);
            throw error.isApiError ? error : createApiError(null, error.message);
        });
    }
    
    /**
     * Set base URL for API requests
     * @param {string} url - Base URL
     * @public
     */
    function setBaseUrl(url) {
        baseUrl = url;
    }
    
    /**
     * Set default headers for all requests
     * @param {Object} headers - Headers to set
     * @public
     */
    function setDefaultHeaders(headers) {
        defaultHeaders = { ...defaultHeaders, ...headers };
    }
    
    /**
     * Check if the API service has been initialized
     * @returns {boolean} True if initialized
     * @public
     */
    function isInitialized() {
        return initialized;
    }
    
    // Initialize the service when the script loads
    initialize();
    
    // Return public API
    return {
        initialize: initialize,
        get: get,
        post: post,
        postWithFormData: postWithFormData,
        postForBlob: postForBlob,
        put: put,
        delete: del, // 'delete' is a reserved word, so use 'del' internally
        patch: patch,
        setBaseUrl: setBaseUrl,
        setDefaultHeaders: setDefaultHeaders,
        isInitialized: isInitialized
    };
})();
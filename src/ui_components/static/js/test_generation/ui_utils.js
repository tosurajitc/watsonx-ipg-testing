/**
 * Test Generation & Refinement - UI Utilities Module
 * 
 * This module provides common UI utilities used across the Test Generation & Refinement module,
 * including notification handling, formatting helpers, file utilities, and other UI-related functions.
 */

// Ensure the TestGeneration namespace exists
const TestGeneration = TestGeneration || {};

/**
 * UI Utilities module
 */
TestGeneration.UIUtils = (function() {
    // Private variables
    let initialized = false;
    let notificationContainer = null;
    let notificationTimeout = null;
    
    /**
     * Initialize the UI Utilities module
     * @public
     */
    function initialize() {
        if (initialized) return;
        
        console.log('Initializing UI Utilities...');
        
        // Create notification container if it doesn't exist
        createNotificationContainer();
        
        // Set initialization flag
        initialized = true;
        
        console.log('UI Utilities initialized');
    }
    
    /**
     * Create notification container for displaying notifications
     * @private
     */
    function createNotificationContainer() {
        // Check if container already exists
        notificationContainer = document.getElementById('notification-container');
        if (notificationContainer) return;
        
        // Create container
        notificationContainer = document.createElement('div');
        notificationContainer.id = 'notification-container';
        notificationContainer.className = 'notification-container';
        
        // Apply styles
        const styles = `
            .notification-container {
                position: fixed;
                top: 20px;
                right: 20px;
                max-width: 400px;
                z-index: 9999;
            }
            
            .notification {
                padding: 15px 20px;
                margin-bottom: 10px;
                border-radius: 4px;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
                animation: notification-fadein 0.5s ease-out;
                cursor: pointer;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            
            .notification.success {
                background-color: #d4edda;
                border-color: #c3e6cb;
                color: #155724;
            }
            
            .notification.error {
                background-color: #f8d7da;
                border-color: #f5c6cb;
                color: #721c24;
            }
            
            .notification.warning {
                background-color: #fff3cd;
                border-color: #ffeeba;
                color: #856404;
            }
            
            .notification.info {
                background-color: #d1ecf1;
                border-color: #bee5eb;
                color: #0c5460;
            }
            
            .notification-close {
                margin-left: 10px;
                font-weight: bold;
                font-size: 18px;
                line-height: 1;
                cursor: pointer;
            }
            
            @keyframes notification-fadein {
                from { opacity: 0; transform: translateY(-20px); }
                to { opacity: 1; transform: translateY(0); }
            }
            
            @keyframes notification-fadeout {
                from { opacity: 1; transform: translateY(0); }
                to { opacity: 0; transform: translateY(-20px); }
            }
        `;
        
        // Add styles to the document
        const styleElement = document.createElement('style');
        styleElement.textContent = styles;
        document.head.appendChild(styleElement);
        
        // Add container to the document
        document.body.appendChild(notificationContainer);
    }
    
    /**
     * Show a notification message
     * @param {string} message - The message to display
     * @param {string} [type='info'] - The type of notification ('success', 'error', 'warning', 'info')
     * @param {number} [duration=5000] - Duration in milliseconds to show the notification
     * @public
     */
    function showNotification(message, type = 'info', duration = 5000) {
        if (!notificationContainer) {
            createNotificationContainer();
        }
        
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        
        // Create message element
        const messageElement = document.createElement('div');
        messageElement.className = 'notification-message';
        messageElement.textContent = message;
        
        // Create close button
        const closeButton = document.createElement('span');
        closeButton.className = 'notification-close';
        closeButton.innerHTML = '&times;';
        closeButton.addEventListener('click', function(e) {
            e.stopPropagation();
            removeNotification(notification);
        });
        
        // Add elements to notification
        notification.appendChild(messageElement);
        notification.appendChild(closeButton);
        
        // Add notification to container
        notificationContainer.appendChild(notification);
        
        // Click anywhere on notification to dismiss
        notification.addEventListener('click', function() {
            removeNotification(notification);
        });
        
        // Auto-remove after duration
        if (duration > 0) {
            setTimeout(function() {
                removeNotification(notification);
            }, duration);
        }
        
        return notification;
    }
    
    /**
     * Remove a notification with animation
     * @param {HTMLElement} notification - The notification element
     * @private
     */
    function removeNotification(notification) {
        if (!notification || !notification.parentNode) return;
        
        // Add fadeout animation
        notification.style.animation = 'notification-fadeout 0.5s ease-out';
        
        // Remove after animation completes
        setTimeout(function() {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 500);
    }
    
    /**
     * Format file size in human-readable format
     * @param {number} bytes - File size in bytes
     * @returns {string} Formatted file size
     * @public
     */
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    /**
     * Format a date object to a string
     * @param {Date} date - Date object
     * @param {string} [format='YYYY-MM-DD'] - Date format
     * @returns {string} Formatted date string
     * @public
     */
    function formatDate(date, format = 'YYYY-MM-DD') {
        if (!(date instanceof Date)) {
            return '';
        }
        
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        const hours = String(date.getHours()).padStart(2, '0');
        const minutes = String(date.getMinutes()).padStart(2, '0');
        const seconds = String(date.getSeconds()).padStart(2, '0');
        
        switch (format) {
            case 'YYYY-MM-DD':
                return `${year}-${month}-${day}`;
            case 'MM/DD/YYYY':
                return `${month}/${day}/${year}`;
            case 'DD/MM/YYYY':
                return `${day}/${month}/${year}`;
            case 'YYYY-MM-DD HH:mm':
                return `${year}-${month}-${day} ${hours}:${minutes}`;
            case 'YYYY-MM-DD HH:mm:ss':
                return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
            default:
                return `${year}-${month}-${day}`;
        }
    }
    
    /**
     * Download a blob as a file
     * @param {Blob} blob - The blob to download
     * @param {string} filename - Name for the downloaded file
     * @public
     */
    function downloadBlob(blob, filename) {
        // Create a URL for the blob
        const url = URL.createObjectURL(blob);
        
        // Create a link element
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        link.style.display = 'none';
        
        // Add to document, click, and remove
        document.body.appendChild(link);
        link.click();
        
        // Clean up
        setTimeout(function() {
            document.body.removeChild(link);
            URL.revokeObjectURL(url);
        }, 100);
    }
    
    /**
     * Create a table from data
     * @param {Array} data - Array of objects to display in the table
     * @param {Array} [columns] - Array of column definitions (optional, will use object keys if not provided)
     * @param {Object} [options] - Additional options for the table
     * @returns {HTMLElement} Table element
     * @public
     */
    function createTable(data, columns, options = {}) {
        if (!Array.isArray(data) || data.length === 0) {
            const emptyTable = document.createElement('div');
            emptyTable.className = 'alert alert-info';
            emptyTable.textContent = options.emptyMessage || 'No data available';
            return emptyTable;
        }
        
        // Create table element
        const table = document.createElement('table');
        table.className = options.tableClass || 'table table-bordered table-hover';
        
        // If no columns provided, use object keys from first item
        if (!columns) {
            columns = Object.keys(data[0]).map(key => ({
                key: key,
                header: key.split('_').map(word => 
                    word.charAt(0).toUpperCase() + word.slice(1).toLowerCase()
                ).join(' ')
            }));
        }
        
        // Create table header
        const thead = document.createElement('thead');
        const headerRow = document.createElement('tr');
        
        columns.forEach(column => {
            const th = document.createElement('th');
            
            if (typeof column === 'string') {
                // Simple string column
                th.textContent = column;
            } else {
                // Object column definition
                th.textContent = column.header || column.key;
                
                if (column.width) {
                    th.style.width = column.width;
                }
                
                if (column.className) {
                    th.className = column.className;
                }
            }
            
            headerRow.appendChild(th);
        });
        
        thead.appendChild(headerRow);
        table.appendChild(thead);
        
        // Create table body
        const tbody = document.createElement('tbody');
        
        data.forEach((item, rowIndex) => {
            const row = document.createElement('tr');
            
            // Add row class if provided
            if (options.rowClass) {
                if (typeof options.rowClass === 'function') {
                    const rowClassName = options.rowClass(item, rowIndex);
                    if (rowClassName) {
                        row.className = rowClassName;
                    }
                } else {
                    row.className = options.rowClass;
                }
            }
            
            // Add row click handler if provided
            if (options.onRowClick) {
                row.style.cursor = 'pointer';
                row.addEventListener('click', function() {
                    options.onRowClick(item, rowIndex);
                });
            }
            
            // Add row data cells
            columns.forEach(column => {
                const td = document.createElement('td');
                const key = typeof column === 'string' ? column : column.key;
                
                // Get cell value
                let value = item[key];
                
                // Apply formatter if provided
                if (typeof column === 'object' && column.formatter) {
                    value = column.formatter(value, item, rowIndex);
                }
                
                // Handle different value types
                if (value === undefined || value === null) {
                    td.innerHTML = '<span class="text-muted">--</span>';
                } else if (typeof value === 'object' && !(value instanceof Date)) {
                    td.textContent = JSON.stringify(value);
                } else if (value instanceof Date) {
                    td.textContent = formatDate(value);
                } else if (typeof value === 'boolean') {
                    td.innerHTML = value ? 
                        '<span class="text-success"><i class="fas fa-check"></i></span>' : 
                        '<span class="text-danger"><i class="fas fa-times"></i></span>';
                } else {
                    // String, number, or custom HTML
                    if (typeof column === 'object' && column.html) {
                        td.innerHTML = value;
                    } else {
                        td.textContent = value;
                    }
                }
                
                // Add cell class if provided
                if (typeof column === 'object' && column.cellClass) {
                    if (typeof column.cellClass === 'function') {
                        const cellClassName = column.cellClass(value, item, rowIndex);
                        if (cellClassName) {
                            td.className = cellClassName;
                        }
                    } else {
                        td.className = column.cellClass;
                    }
                }
                
                row.appendChild(td);
            });
            
            tbody.appendChild(row);
        });
        
        table.appendChild(tbody);
        
        return table;
    }
    
    /**
     * Create a modal dialog
     * @param {Object} options - Modal options
     * @param {string} options.title - Modal title
     * @param {string|HTMLElement} options.content - Modal content (string or HTML element)
     * @param {string} [options.size='medium'] - Modal size ('small', 'medium', 'large')
     * @param {boolean} [options.closeButton=true] - Show close button
     * @param {Array} [options.buttons] - Array of button definitions
     * @returns {Object} Modal control object with show, hide, and remove methods
     * @public
     */
    function createModal(options) {
        const modalId = 'modal-' + Math.random().toString(36).substring(2, 9);
        
        // Create modal elements
        const modalWrapper = document.createElement('div');
        modalWrapper.className = 'modal fade';
        modalWrapper.id = modalId;
        modalWrapper.tabIndex = -1;
        modalWrapper.setAttribute('role', 'dialog');
        modalWrapper.setAttribute('aria-hidden', 'true');
        
        // Modal sizes
        const sizeClass = options.size === 'small' ? 'modal-sm' : 
                         options.size === 'large' ? 'modal-lg' : '';
        
        // Create modal HTML structure
        modalWrapper.innerHTML = `
            <div class="modal-dialog ${sizeClass}" role="document">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">${options.title || 'Modal'}</h5>
                        ${options.closeButton !== false ? '<button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>' : ''}
                    </div>
                    <div class="modal-body">
                        ${typeof options.content === 'string' ? options.content : ''}
                    </div>
                    ${options.buttons && options.buttons.length ? '<div class="modal-footer"></div>' : ''}
                </div>
            </div>
        `;
        
        // Add content if it's an HTML element
        if (options.content && typeof options.content !== 'string') {
            const modalBody = modalWrapper.querySelector('.modal-body');
            modalBody.innerHTML = '';
            modalBody.appendChild(options.content);
        }
        
        // Add buttons if provided
        if (options.buttons && options.buttons.length) {
            const modalFooter = modalWrapper.querySelector('.modal-footer');
            
            options.buttons.forEach(button => {
                const btnElement = document.createElement('button');
                btnElement.type = 'button';
                btnElement.className = `btn ${button.className || 'btn-secondary'}`;
                btnElement.textContent = button.text || 'Button';
                
                if (button.dismiss) {
                    btnElement.setAttribute('data-bs-dismiss', 'modal');
                }
                
                if (button.onClick) {
                    btnElement.addEventListener('click', function() {
                        button.onClick(modalControl);
                    });
                }
                
                modalFooter.appendChild(btnElement);
            });
        }
        
        // Add modal to document
        document.body.appendChild(modalWrapper);
        
        // Create Bootstrap modal instance if Bootstrap is available
        let bootstrapModal = null;
        if (typeof bootstrap !== 'undefined' && bootstrap.Modal) {
            bootstrapModal = new bootstrap.Modal(modalWrapper);
        }
        
        // Define modal control object
        const modalControl = {
            show: function() {
                if (bootstrapModal) {
                    bootstrapModal.show();
                } else {
                    // Fallback for when Bootstrap is not available
                    modalWrapper.style.display = 'block';
                    modalWrapper.classList.add('show');
                    document.body.classList.add('modal-open');
                    
                    // Create backdrop
                    const backdrop = document.createElement('div');
                    backdrop.className = 'modal-backdrop fade show';
                    document.body.appendChild(backdrop);
                }
                return modalControl;
            },
            
            hide: function() {
                if (bootstrapModal) {
                    bootstrapModal.hide();
                } else {
                    // Fallback for when Bootstrap is not available
                    modalWrapper.style.display = 'none';
                    modalWrapper.classList.remove('show');
                    document.body.classList.remove('modal-open');
                    
                    // Remove backdrop
                    const backdrop = document.querySelector('.modal-backdrop');
                    if (backdrop) {
                        backdrop.parentNode.removeChild(backdrop);
                    }
                }
                return modalControl;
            },
            
            remove: function() {
                modalControl.hide();
                setTimeout(function() {
                    if (modalWrapper.parentNode) {
                        modalWrapper.parentNode.removeChild(modalWrapper);
                    }
                }, 300);
            },
            
            getElement: function() {
                return modalWrapper;
            },
            
            setContent: function(content) {
                const modalBody = modalWrapper.querySelector('.modal-body');
                if (typeof content === 'string') {
                    modalBody.innerHTML = content;
                } else {
                    modalBody.innerHTML = '';
                    modalBody.appendChild(content);
                }
                return modalControl;
            },
            
            setTitle: function(title) {
                const modalTitle = modalWrapper.querySelector('.modal-title');
                modalTitle.textContent = title;
                return modalControl;
            }
        };
        
        return modalControl;
    }
    
    /**
     * Validate a form
     * @param {HTMLFormElement} form - The form to validate
     * @param {Object} rules - Validation rules
     * @returns {Object} Validation result with isValid flag and errors object
     * @public
     */
    function validateForm(form, rules) {
        const result = {
            isValid: true,
            errors: {}
        };
        
        // Process each rule
        for (const fieldName in rules) {
            if (!rules.hasOwnProperty(fieldName)) continue;
            
            const fieldRules = rules[fieldName];
            const field = form.elements[fieldName];
            
            if (!field) continue;
            
            let fieldValue = field.value;
            
            // Process field value based on type
            if (field.type === 'checkbox') {
                fieldValue = field.checked;
            } else if (field.type === 'select-multiple') {
                fieldValue = Array.from(field.selectedOptions).map(option => option.value);
            }
            
            // Apply validation rules
            for (const rule in fieldRules) {
                if (!fieldRules.hasOwnProperty(rule)) continue;
                
                const ruleValue = fieldRules[rule];
                let isValid = true;
                let errorMessage = '';
                
                switch (rule) {
                    case 'required':
                        if (ruleValue === true) {
                            if (Array.isArray(fieldValue)) {
                                isValid = fieldValue.length > 0;
                            } else {
                                isValid = fieldValue !== '' && fieldValue !== null && fieldValue !== undefined;
                            }
                            errorMessage = field.getAttribute('data-error-required') || 'This field is required.';
                        }
                        break;
                        
                    case 'minLength':
                        isValid = !fieldValue || fieldValue.length >= ruleValue;
                        errorMessage = field.getAttribute('data-error-min-length') || 
                            `Minimum length is ${ruleValue} characters.`;
                        break;
                        
                    case 'maxLength':
                        isValid = !fieldValue || fieldValue.length <= ruleValue;
                        errorMessage = field.getAttribute('data-error-max-length') || 
                            `Maximum length is ${ruleValue} characters.`;
                        break;
                        
                    case 'pattern':
                        isValid = !fieldValue || new RegExp(ruleValue).test(fieldValue);
                        errorMessage = field.getAttribute('data-error-pattern') || 
                            'Invalid format.';
                        break;
                        
                    case 'email':
                        if (ruleValue === true) {
                            const emailPattern = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
                            isValid = !fieldValue || emailPattern.test(fieldValue);
                            errorMessage = field.getAttribute('data-error-email') || 
                                'Please enter a valid email address.';
                        }
                        break;
                        
                    case 'minValue':
                        isValid = !fieldValue || parseFloat(fieldValue) >= ruleValue;
                        errorMessage = field.getAttribute('data-error-min-value') || 
                            `Minimum value is ${ruleValue}.`;
                        break;
                        
                    case 'maxValue':
                        isValid = !fieldValue || parseFloat(fieldValue) <= ruleValue;
                        errorMessage = field.getAttribute('data-error-max-value') || 
                            `Maximum value is ${ruleValue}.`;
                        break;
                        
                    case 'custom':
                        if (typeof ruleValue === 'function') {
                            isValid = ruleValue(fieldValue, form);
                            errorMessage = field.getAttribute('data-error-custom') || 
                                'Invalid value.';
                        }
                        break;
                }
                
                // If rule validation failed
                if (!isValid) {
                    result.isValid = false;
                    result.errors[fieldName] = result.errors[fieldName] || [];
                    result.errors[fieldName].push({
                        rule: rule,
                        message: errorMessage
                    });
                    
                    // Show error on field
                    field.classList.add('is-invalid');
                    
                    // Add or update error message
                    let errorElement = field.parentElement.querySelector('.invalid-feedback');
                    if (!errorElement) {
                        errorElement = document.createElement('div');
                        errorElement.className = 'invalid-feedback';
                        field.parentElement.appendChild(errorElement);
                    }
                    errorElement.textContent = errorMessage;
                    
                    // Only show the first error message
                    break;
                } else {
                    // Remove error highlighting if field is valid
                    field.classList.remove('is-invalid');
                    field.classList.add('is-valid');
                    
                    // Remove error message
                    const errorElement = field.parentElement.querySelector('.invalid-feedback');
                    if (errorElement) {
                        errorElement.parentNode.removeChild(errorElement);
                    }
                }
            }
        }
        
        return result;
    }
    
    /**
     * Check if the UI Utilities module has been initialized
     * @returns {boolean} True if initialized
     * @public
     */
    function isInitialized() {
        return initialized;
    }
    
    // Initialize the module when the script loads
    initialize();
    
    // Return public API
    return {
        initialize: initialize,
        showNotification: showNotification,
        formatFileSize: formatFileSize,
        formatDate: formatDate,
        downloadBlob: downloadBlob,
        createTable: createTable,
        createModal: createModal,
        validateForm: validateForm,
        isInitialized: isInitialized
    };
})();
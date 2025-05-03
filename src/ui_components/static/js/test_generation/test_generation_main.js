/**
 * Test Generation & Refinement - Main Module
 * 
 * This is the main entry point that initializes all sub-modules
 * and handles tab switching and common functionality.
 */

// Create namespace if it doesn't exist
var TestGeneration = TestGeneration || {};

/**
 * Main module for test generation and refinement functionality
 */
TestGeneration.Main = (function() {
    // Private variables
    let activeTab = 'generate'; // Default tab
    let initialized = false;
    
    /**
     * Initialize the Test Generation & Refinement module
     * @public
     */
    function initialize() {
        if (initialized) {
            console.log('Test Generation & Refinement Main module already initialized');
            return;
        }
        
        console.log('Initializing Test Generation & Refinement Main module...');
        
        // Set up tab switching
        setupTabSwitching();
        
        // Initialize sub-modules based on active tab
        initializeActiveModule();
        
        // Handle window resize
        window.addEventListener('resize', handleResize);
        
        // Set initialization flag
        initialized = true;
        
        console.log('Test Generation & Refinement Main module initialized');
    }
    
    /**
     * Set up tab switching functionality
     * @private
     */
    function setupTabSwitching() {
        // Find tab buttons
        const generateTab = document.getElementById('generate-tab');
        const refineTab = document.getElementById('refine-tab');
        
        if (generateTab && refineTab) {
            // Check current window URL to determine active tab
            if (window.location.href.includes('#refine')) {
                setActiveTab('refine');
                // Update UI to match
                generateTab.classList.remove('active');
                generateTab.setAttribute('aria-selected', 'false');
                refineTab.classList.add('active');
                refineTab.setAttribute('aria-selected', 'true');
                
                // Show refine tab content
                const generateContent = document.getElementById('generate');
                const refineContent = document.getElementById('refine');
                
                if (generateContent && refineContent) {
                    generateContent.classList.remove('show', 'active');
                    refineContent.classList.add('show', 'active');
                }
            }
            
            // Add click event listeners
            generateTab.addEventListener('click', function() {
                setActiveTab('generate');
            });
            
            refineTab.addEventListener('click', function() {
                setActiveTab('refine');
            });
            
            console.log('Tab switching event listeners set up');
        } else {
            console.warn('Tab buttons not found in the DOM');
        }
    }
    
    /**
     * Set the active tab
     * @param {string} tabName - Name of the tab to activate
     * @private
     */
    function setActiveTab(tabName) {
        console.log('Setting active tab to:', tabName);
        activeTab = tabName;
        
        // Update URL hash
        window.location.hash = tabName;
        
        // Initialize the appropriate module
        initializeActiveModule();
    }
    
    /**
     * Initialize the currently active module
     * @private
     */
    function initializeActiveModule() {
        if (activeTab === 'generate') {
            // Initialize Generate module if it exists
            if (TestGeneration.Generate && typeof TestGeneration.Generate.initialize === 'function') {
                console.log('Initializing Generate module');
                TestGeneration.Generate.initialize();
            } else {
                console.log('Generate module not found or not properly defined');
            }
        } else if (activeTab === 'refine') {
            // Initialize Refine module if it exists
            if (TestGeneration.Refine && typeof TestGeneration.Refine.initialize === 'function') {
                console.log('Initializing Refine module');
                TestGeneration.Refine.initialize();
            } else {
                console.log('Refine module not found or not properly defined');
            }
        }
    }
    
    /**
     * Handle window resize event
     * @private
     */
    function handleResize() {
        if (activeTab === 'generate') {
            // Call Generate module's resize handler if it exists
            if (TestGeneration.Generate && typeof TestGeneration.Generate.handleResize === 'function') {
                TestGeneration.Generate.handleResize();
            }
        } else if (activeTab === 'refine') {
            // Call Refine module's resize handler if it exists
            if (TestGeneration.Refine && typeof TestGeneration.Refine.handleResize === 'function') {
                TestGeneration.Refine.handleResize();
            }
        }
    }
    
    /**
     * Get the currently active tab
     * @returns {string} Active tab name
     * @public
     */
    function getActiveTab() {
        return activeTab;
    }
    
    /**
     * Show loading spinner for a specific operation
     * @param {string} operation - The operation being performed
     * @param {string} message - Loading message to display
     * @public
     */
    function showLoadingSpinner(operation, message) {
        // Default message if not provided
        message = message || 'Loading...';
        
        // Look for a progress element specific to the operation
        const progressElement = document.getElementById(operation + 'Progress');
        
        if (progressElement) {
            // Update message if there's a status element
            const statusElement = progressElement.querySelector('.progress-status');
            if (statusElement) {
                statusElement.textContent = message;
            }
            
            // Show the progress element
            if (progressElement.classList.contains('d-none')) {
                progressElement.classList.remove('d-none');
            }
            progressElement.style.display = 'block';
        } else {
            // Create a generic loading spinner if no specific one exists
            let loadingContainer = document.getElementById('global-loading-container');
            
            // Create container if it doesn't exist
            if (!loadingContainer) {
                loadingContainer = document.createElement('div');
                loadingContainer.id = 'global-loading-container';
                loadingContainer.className = 'loading-container';
                loadingContainer.style.position = 'fixed';
                loadingContainer.style.top = '0';
                loadingContainer.style.left = '0';
                loadingContainer.style.width = '100%';
                loadingContainer.style.height = '100%';
                loadingContainer.style.display = 'flex';
                loadingContainer.style.justifyContent = 'center';
                loadingContainer.style.alignItems = 'center';
                loadingContainer.style.backgroundColor = 'rgba(0, 0, 0, 0.5)';
                loadingContainer.style.zIndex = '9999';
                
                const spinnerWrapper = document.createElement('div');
                spinnerWrapper.className = 'spinner-wrapper bg-white p-4 rounded';
                
                const spinner = document.createElement('div');
                spinner.className = 'spinner-border text-primary';
                spinner.setAttribute('role', 'status');
                
                const spinnerText = document.createElement('span');
                spinnerText.className = 'sr-only';
                spinnerText.textContent = 'Loading...';
                spinner.appendChild(spinnerText);
                
                const messageElement = document.createElement('div');
                messageElement.className = 'spinner-message mt-2';
                messageElement.textContent = message;
                
                spinnerWrapper.appendChild(spinner);
                spinnerWrapper.appendChild(messageElement);
                loadingContainer.appendChild(spinnerWrapper);
                
                document.body.appendChild(loadingContainer);
            } else {
                // Update existing spinner message
                const messageElement = loadingContainer.querySelector('.spinner-message');
                if (messageElement) {
                    messageElement.textContent = message;
                }
                
                // Show the container
                loadingContainer.style.display = 'flex';
            }
        }
    }
    
    /**
     * Hide loading spinner for a specific operation
     * @param {string} operation - The operation being performed
     * @public
     */
    function hideLoadingSpinner(operation) {
        // Look for a progress element specific to the operation
        const progressElement = document.getElementById(operation + 'Progress');
        
        if (progressElement) {
            // Hide the progress element
            if (!progressElement.classList.contains('d-none')) {
                progressElement.classList.add('d-none');
            }
            progressElement.style.display = 'none';
        } else {
            // Hide the generic loading spinner if no specific one exists
            const loadingContainer = document.getElementById('global-loading-container');
            if (loadingContainer) {
                loadingContainer.style.display = 'none';
            }
        }
    }
    
    // Return public API
    return {
        initialize: initialize,
        getActiveTab: getActiveTab,
        showLoadingSpinner: showLoadingSpinner,
        hideLoadingSpinner: hideLoadingSpinner
    };
})();

// Initialize the main module when the DOM is fully loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, initializing TestGeneration.Main module...');
    TestGeneration.Main.initialize();
});

console.log('Test Generation Main module loaded successfully');
/**
 * Test Generation & Refinement - Main Module
 * 
 * This module serves as the entry point for the Test Generation & Refinement functionality.
 * It handles initialization, tab management, and orchestrates the interaction between
 * the different sub-modules for generating and refining test cases.
 */

// Create namespace for Test Generation modules
const TestGeneration = TestGeneration || {};

/**
 * Main module with initialization and coordination functionality
 */
TestGeneration.Main = (function() {
    // Private variables
    let initialized = false;
    let activeTab = 'generate'; // Default active tab

    /**
     * Initialize the Test Generation module
     * @public
     */
    function initialize() {
        if (initialized) return;

        console.log('Initializing Test Generation & Refinement module...');
        
        // Initialize UI utilities
        TestGeneration.UIUtils.initialize();
        
        // Initialize API service
        TestGeneration.API.initialize();
        
        // Register DOM event listeners
        setupEventListeners();
        
        // Initialize the active tab based on URL or default
        initializeActiveTab();
        
        // Set initialization flag
        initialized = true;
        
        console.log('Test Generation & Refinement module initialized');
    }

    /**
     * Set up event listeners for the main module
     * @private
     */
    function setupEventListeners() {
        // Tab switching event listeners
        const testGenerationTabs = document.getElementById('testGenerationTabs');
        if (testGenerationTabs) {
            const tabs = testGenerationTabs.querySelectorAll('[data-bs-toggle="tab"]');
            
            tabs.forEach(tab => {
                tab.addEventListener('shown.bs.tab', function(event) {
                    handleTabChange(event.target.id);
                });
                
                // Also add click event to ensure tab change is captured even without Bootstrap
                tab.addEventListener('click', function() {
                    const tabId = this.id;
                    if (!tabId.endsWith('-tab')) return;
                    
                    const contentId = tabId.replace('-tab', '');
                    showTabContent(contentId);
                    handleTabChange(tabId);
                });
            });
        }
        
        // Window resize event for responsive adjustments
        window.addEventListener('resize', handleWindowResize);
        
        // Handle beforeunload to warn about unsaved changes
        window.addEventListener('beforeunload', function(event) {
            if (hasUnsavedChanges()) {
                const message = 'You have unsaved changes. Are you sure you want to leave?';
                event.returnValue = message; // Standard for most browsers
                return message; // For older browsers
            }
        });
    }

    /**
     * Show tab content and hide others
     * @param {string} tabId - ID of the tab to show (without '-tab' suffix)
     * @private
     */
    function showTabContent(tabId) {
        // Find all tab panes
        const tabPanes = document.querySelectorAll('.tab-pane');
        
        // Hide all tab panes
        tabPanes.forEach(pane => {
            pane.classList.remove('show', 'active');
        });
        
        // Show the selected tab pane
        const selectedPane = document.getElementById(tabId);
        if (selectedPane) {
            selectedPane.classList.add('show', 'active');
        }
        
        // Update active tab buttons
        const tabButtons = document.querySelectorAll('[data-bs-toggle="tab"]');
        tabButtons.forEach(button => {
            button.classList.remove('active');
            button.setAttribute('aria-selected', 'false');
        });
        
        const activeButton = document.getElementById(`${tabId}-tab`);
        if (activeButton) {
            activeButton.classList.add('active');
            activeButton.setAttribute('aria-selected', 'true');
        }
    }

    /**
     * Handle tab change event
     * @param {string} tabId - ID of the active tab
     * @private
     */
    function handleTabChange(tabId) {
        // Extract tab name without "-tab" suffix
        const tabName = tabId.replace('-tab', '');
        
        // Store current active tab
        activeTab = tabName;
        
        // Reset forms when switching tabs
        resetForms(tabName);
        
        // Initialize the specific tab functionality
        if (tabName === 'generate') {
            TestGeneration.Generate.initialize();
        } else if (tabName === 'refine') {
            TestGeneration.Refine.initialize();
        }
        
        // Update URL hash to persist tab selection
        window.history.replaceState(null, null, `#${tabName}`);
        
        console.log(`Switched to ${tabName} tab`);
    }

    /**
     * Initialize the active tab based on URL hash or default
     * @private
     */
    function initializeActiveTab() {
        let targetTab = 'generate'; // Default tab
        
        // Check URL hash for tab selection
        const hash = window.location.hash.substring(1);
        if (hash === 'generate' || hash === 'refine') {
            targetTab = hash;
        }
        
        // Activate the target tab
        const tabElement = document.getElementById(`${targetTab}-tab`);
        if (tabElement) {
            // If Bootstrap's tab is available, use it
            if (typeof bootstrap !== 'undefined') {
                const tab = new bootstrap.Tab(tabElement);
                tab.show();
            } else {
                // Manual tab activation
                showTabContent(targetTab);
                handleTabChange(`${targetTab}-tab`);
            }
        }
    }

    /**
     * Reset forms when switching tabs
     * @param {string} currentTab - Current active tab
     * @private
     */
    function resetForms(currentTab) {
        if (currentTab === 'generate') {
            // When on generate tab, reset refine tab
            if (TestGeneration.Refine && typeof TestGeneration.Refine.resetForm === 'function') {
                TestGeneration.Refine.resetForm();
            }
        } else if (currentTab === 'refine') {
            // When on refine tab, reset generate tab
            if (TestGeneration.Generate && typeof TestGeneration.Generate.resetForm === 'function') {
                TestGeneration.Generate.resetForm();
            }
        }
    }

    /**
     * Handle window resize event
     * @private
     */
    function handleWindowResize() {
        // Adjust UI elements based on window size
        adjustForScreenSize();
        
        // Notify sub-modules about resize
        if (activeTab === 'generate' && TestGeneration.Generate) {
            TestGeneration.Generate.handleResize();
        } else if (activeTab === 'refine' && TestGeneration.Refine) {
            TestGeneration.Refine.handleResize();
        }
    }

    /**
     * Adjust UI elements based on screen size
     * @private
     */
    function adjustForScreenSize() {
        const isMobile = window.innerWidth < 768;
        
        // Adjust actions button layout
        const actionButtons = document.querySelectorAll('.form-actions, .refinement-actions');
        actionButtons.forEach(actionGroup => {
            if (isMobile) {
                actionGroup.classList.add('flex-column');
            } else {
                actionGroup.classList.remove('flex-column');
            }
        });
        
        // Adjust comparison view
        const comparisonContainer = document.querySelector('.comparison-container .row');
        if (comparisonContainer) {
            if (isMobile) {
                comparisonContainer.classList.remove('row');
                const columns = comparisonContainer.querySelectorAll('.col-md-6');
                columns.forEach(col => {
                    col.classList.remove('col-md-6');
                });
            } else {
                if (!comparisonContainer.classList.contains('row')) {
                    comparisonContainer.classList.add('row');
                    const containers = comparisonContainer.children;
                    for (let i = 0; i < containers.length; i++) {
                        if (!containers[i].classList.contains('col-md-6')) {
                            containers[i].classList.add('col-md-6');
                        }
                    }
                }
            }
        }
    }

    /**
     * Check if there are unsaved changes
     * @returns {boolean} True if there are unsaved changes
     * @private
     */
    function hasUnsavedChanges() {
        if (activeTab === 'generate') {
            return TestGeneration.Generate && 
                   typeof TestGeneration.Generate.hasUnsavedChanges === 'function' && 
                   TestGeneration.Generate.hasUnsavedChanges();
        } else if (activeTab === 'refine') {
            return TestGeneration.Refine && 
                   typeof TestGeneration.Refine.hasUnsavedChanges === 'function' && 
                   TestGeneration.Refine.hasUnsavedChanges();
        }
        
        return false;
    }

    /**
     * Show the loading spinner
     * @param {string} tabId - ID of the tab containing the spinner
     * @param {string} [message] - Optional message to display with the spinner
     * @public
     */
    function showLoadingSpinner(tabId, message) {
        const loadingElement = document.getElementById(`${tabId}Progress`);
        if (loadingElement) {
            loadingElement.classList.remove('hidden');
            
            if (message) {
                const statusElement = loadingElement.querySelector('.progress-status');
                if (statusElement) {
                    statusElement.textContent = message;
                }
            }
        }
    }

    /**
     * Hide the loading spinner
     * @param {string} tabId - ID of the tab containing the spinner
     * @public
     */
    function hideLoadingSpinner(tabId) {
        const loadingElement = document.getElementById(`${tabId}Progress`);
        if (loadingElement) {
            loadingElement.classList.add('hidden');
        }
    }

    /**
     * Get the current active tab
     * @returns {string} ID of the active tab
     * @public
     */
    function getActiveTab() {
        return activeTab;
    }

    /**
     * Check if the module has been initialized
     * @returns {boolean} True if the module has been initialized
     * @public
     */
    function isInitialized() {
        return initialized;
    }

    // Initialize the module when the DOM is loaded
    document.addEventListener('DOMContentLoaded', function() {
        initialize();
    });

    // Return public API
    return {
        initialize: initialize,
        showLoadingSpinner: showLoadingSpinner,
        hideLoadingSpinner: hideLoadingSpinner,
        getActiveTab: getActiveTab,
        isInitialized: isInitialized
    };
})();

/**
 * Stub for UIUtils module - to be implemented in ui_utils.js
 * This ensures the main module can reference it before it's loaded
 */
TestGeneration.UIUtils = TestGeneration.UIUtils || {
    initialize: function() {
        console.warn('UIUtils module not loaded yet');
    }
};

/**
 * Stub for API module - to be implemented in api_service.js
 */
TestGeneration.API = TestGeneration.API || {
    initialize: function() {
        console.warn('API module not loaded yet');
    }
};

/**
 * Stub for Generate module - to be implemented in generate_test_cases.js
 */
TestGeneration.Generate = TestGeneration.Generate || {
    initialize: function() {
        console.warn('Generate module not loaded yet');
    },
    resetForm: function() {
        console.warn('Generate.resetForm not implemented');
    },
    handleResize: function() {},
    hasUnsavedChanges: function() { return false; }
};

/**
 * Stub for Refine module - to be implemented in refine_test_cases.js
 */
TestGeneration.Refine = TestGeneration.Refine || {
    initialize: function() {
        console.warn('Refine module not loaded yet');
    },
    resetForm: function() {
        console.warn('Refine.resetForm not implemented');
    },
    handleResize: function() {},
    hasUnsavedChanges: function() { return false; }
};
/**
 * Test Generation & Refinement - Generate Test Cases Module
 * 
 * This module handles the functionality for generating detailed test cases
 * from requirements or direct prompts. It manages the UI interactions,
 * API calls, and result presentation for the test generation tab.
 */

// Ensure the TestGeneration namespace exists
const TestGeneration = TestGeneration || {};

/**
 * Generate module for test case generation functionality
 */
TestGeneration.Generate = (function() {
    // Private variables
    let initialized = false;
    let requirementsLoaded = false;
    let generatedTestCases = null;
    let hasChanges = false;
    
    // Cache DOM elements for better performance
    const elements = {
        form: null,
        sourceRequirements: null,
        sourcePrompt: null,
        requirementsSection: null,
        promptSection: null,
        requirementSelect: null,
        promptInput: null,
        detailLevel: null,
        includeEdgeCases: null,
        generateBtn: null,
        cancelBtn: null,
        progressArea: null,
        outputArea: null,
        testCasePreview: null,
        exportExcelBtn: null,
        compareRepoBtn: null
    };
    
    /**
     * Initialize the Generate Test Cases module
     * @public
     */
    function initialize() {
        if (initialized && TestGeneration.Main.getActiveTab() === 'generate') return;
        
        console.log('Initializing Generate Test Cases module...');
        
        // Cache DOM elements
        cacheElements();
        
        // Set up event listeners
        setupEventListeners();
        
        // Load requirements if not loaded already
        if (!requirementsLoaded) {
            loadRequirements();
        }
        
        // Set initialization flag
        initialized = true;
        
        console.log('Generate Test Cases module initialized');
    }
    
    /**
     * Cache DOM elements for better performance
     * @private
     */
    function cacheElements() {
        elements.form = document.getElementById('generateTestCaseForm');
        elements.sourceRequirements = document.getElementById('sourceRequirements');
        elements.sourcePrompt = document.getElementById('sourcePrompt');
        elements.requirementsSection = document.getElementById('requirementsSection');
        elements.promptSection = document.getElementById('promptSection');
        elements.requirementSelect = document.getElementById('requirementSelect');
        elements.promptInput = document.getElementById('promptInput');
        elements.detailLevel = document.getElementById('detailLevel');
        elements.includeEdgeCases = document.getElementById('includeEdgeCases');
        elements.generateBtn = document.getElementById('generateTestCaseBtn');
        elements.cancelBtn = document.getElementById('cancelGenerateBtn');
        elements.progressArea = document.getElementById('generationProgress');
        elements.outputArea = document.getElementById('generationOutput');
        elements.testCasePreview = document.getElementById('testCasePreview');
        elements.exportExcelBtn = document.getElementById('exportExcelBtn');
        elements.compareRepoBtn = document.getElementById('compareRepoBtn');
    }
    
    /**
     * Set up event listeners for the Generate module
     * @private
     */
    function setupEventListeners() {
        // Input source selection
        if (elements.sourceRequirements && elements.sourcePrompt) {
            elements.sourceRequirements.addEventListener('change', function() {
                if (this.checked) {
                    elements.requirementsSection.classList.remove('hidden');
                    elements.promptSection.classList.add('hidden');
                }
            });
            
            elements.sourcePrompt.addEventListener('change', function() {
                if (this.checked) {
                    elements.requirementsSection.classList.add('hidden');
                    elements.promptSection.classList.remove('hidden');
                }
            });
        }
        
        // Generate button
        if (elements.generateBtn) {
            elements.generateBtn.addEventListener('click', handleGenerateClick);
        }
        
        // Cancel button
        if (elements.cancelBtn) {
            elements.cancelBtn.addEventListener('click', resetForm);
        }
        
        // Export to Excel button
        if (elements.exportExcelBtn) {
            elements.exportExcelBtn.addEventListener('click', exportToExcel);
        }
        
        // Compare with repository button
        if (elements.compareRepoBtn) {
            elements.compareRepoBtn.addEventListener('click', compareWithRepository);
        }
        
        // Form input change tracking
        if (elements.form) {
            const formInputs = elements.form.querySelectorAll('input, select, textarea');
            formInputs.forEach(input => {
                input.addEventListener('change', function() {
                    hasChanges = true;
                });
                
                if (input.tagName === 'TEXTAREA') {
                    input.addEventListener('input', function() {
                        hasChanges = true;
                    });
                }
            });
        }
    }
    
    /**
     * Handle click on the Generate button
     * @private
     */
    function handleGenerateClick() {
        // Validate form
        if (!validateForm()) {
            return;
        }
        
        // Show progress indicator
        TestGeneration.Main.showLoadingSpinner('generation', 'Generating test cases... This may take a few moments.');
        
        // Get form data
        const formData = getFormData();
        
        // Call API to generate test cases
        generateTestCases(formData);
    }
    
    /**
     * Validate the form before submission
     * @returns {boolean} True if the form is valid
     * @private
     */
    function validateForm() {
        // Get the selected source type
        const sourceType = elements.sourceRequirements.checked ? 'requirements' : 'prompt';
        
        if (sourceType === 'requirements') {
            // Check if requirements are selected
            const selectedRequirements = Array.from(elements.requirementSelect.selectedOptions);
            if (selectedRequirements.length === 0) {
                TestGeneration.UIUtils.showNotification(
                    'Please select at least one requirement.',
                    'warning'
                );
                elements.requirementSelect.focus();
                return false;
            }
        } else {
            // Check if prompt is entered
            if (!elements.promptInput.value.trim()) {
                TestGeneration.UIUtils.showNotification(
                    'Please enter a prompt or keywords.',
                    'warning'
                );
                elements.promptInput.focus();
                return false;
            }
        }
        
        return true;
    }
    
    /**
     * Get form data for API request
     * @returns {Object} Form data as an object
     * @private
     */
    function getFormData() {
        // Get the selected source type
        const sourceType = elements.sourceRequirements.checked ? 'requirements' : 'prompt';
        
        const formData = {
            sourceType: sourceType
        };
        
        if (sourceType === 'requirements') {
            // Get selected requirements
            formData.requirementIds = Array.from(elements.requirementSelect.selectedOptions)
                .map(option => option.value);
        } else {
            // Get direct prompt
            formData.prompt = elements.promptInput.value.trim();
        }
        
        // Get configuration options
        formData.detailLevel = elements.detailLevel.value;
        formData.includeEdgeCases = elements.includeEdgeCases.value === 'include';
        
        return formData;
    }
    
    /**
     * Generate test cases by calling the API
     * @param {Object} formData - Form data for the API request
     * @private
     */
    function generateTestCases(formData) {
        // Prepare the API request data
        let endpoint, requestData;
        
        if (formData.sourceType === 'requirements') {
            endpoint = '/api/test-cases/generate-batch';
            requestData = {
                scenarios: formData.requirementIds.map(id => ({ id })),
                configuration: {
                    detailLevel: formData.detailLevel,
                    includeEdgeCases: formData.includeEdgeCases
                }
            };
        } else {
            endpoint = '/api/test-cases/generate';
            requestData = {
                scenario: {
                    description: formData.prompt
                },
                configuration: {
                    detailLevel: formData.detailLevel,
                    includeEdgeCases: formData.includeEdgeCases
                }
            };
        }
        
        // Call the API
        TestGeneration.API.post(endpoint, requestData)
            .then(response => {
                // Hide progress indicator
                TestGeneration.Main.hideLoadingSpinner('generation');
                
                // Process the response
                if (response.status === 'success') {
                    // Store the generated test cases
                    generatedTestCases = response.data;
                    
                    // Show the output area
                    elements.outputArea.classList.remove('hidden');
                    
                    // Display the test cases
                    displayTestCases(response.data);
                    
                    // Reset the changes flag
                    hasChanges = false;
                    
                    // Show success notification
                    TestGeneration.UIUtils.showNotification(
                        'Test cases generated successfully!',
                        'success'
                    );
                } else {
                    // Show error notification
                    TestGeneration.UIUtils.showNotification(
                        'Failed to generate test cases: ' + (response.message || 'Unknown error'),
                        'error'
                    );
                }
            })
            .catch(error => {
                console.error('Error generating test cases:', error);
                
                // Hide progress indicator
                TestGeneration.Main.hideLoadingSpinner('generation');
                
                // Show error notification
                TestGeneration.UIUtils.showNotification(
                    'Error generating test cases: ' + (error.message || 'Unknown error'),
                    'error'
                );
            });
    }
    
    /**
     * Display generated test cases in the preview area
     * @param {Object} data - Test case data from the API
     * @private
     */
    function displayTestCases(data) {
        if (!elements.testCasePreview) return;
        
        // Clear previous content
        elements.testCasePreview.innerHTML = '';
        
        // Handle different response formats
        if (data.test_case && Array.isArray(data.test_case)) {
            // Single test case with steps
            createTestCaseTable(elements.testCasePreview, data.test_case);
        } else if (data.test_cases && Array.isArray(data.test_cases)) {
            // Multiple test cases
            data.test_cases.forEach((testCase, index) => {
                const testCaseContainer = document.createElement('div');
                testCaseContainer.className = 'test-case-container mb-4';
                
                const header = document.createElement('h5');
                header.textContent = `Test Case ${index + 1}${testCase.title ? ': ' + testCase.title : ''}`;
                testCaseContainer.appendChild(header);
                
                createTestCaseTable(testCaseContainer, testCase.steps || testCase);
                
                if (index < data.test_cases.length - 1) {
                    const divider = document.createElement('hr');
                    testCaseContainer.appendChild(divider);
                }
                
                elements.testCasePreview.appendChild(testCaseContainer);
            });
        } else {
            // Unknown format
            elements.testCasePreview.innerHTML = 
                '<div class="alert alert-info">Test cases generated. Click "Export to Excel" to download.</div>';
        }
    }
    
    /**
     * Create a table to display test case steps
     * @param {HTMLElement} container - Container element
     * @param {Array} steps - Array of test case steps
     * @private
     */
    function createTestCaseTable(container, steps) {
        if (!steps || !steps.length) {
            container.innerHTML += '<div class="alert alert-warning">No test steps available</div>';
            return;
        }
        
        // Create table
        const table = document.createElement('table');
        table.className = 'table table-bordered table-hover';
        
        // Create header
        const thead = document.createElement('thead');
        const headerRow = document.createElement('tr');
        
        // Get column headers from the first step
        const headers = Object.keys(steps[0]);
        
        headers.forEach(header => {
            const th = document.createElement('th');
            th.textContent = formatHeader(header);
            headerRow.appendChild(th);
        });
        
        thead.appendChild(headerRow);
        table.appendChild(thead);
        
        // Create body
        const tbody = document.createElement('tbody');
        
        steps.forEach(step => {
            const row = document.createElement('tr');
            
            headers.forEach(header => {
                const td = document.createElement('td');
                td.textContent = step[header] || '';
                row.appendChild(td);
            });
            
            tbody.appendChild(row);
        });
        
        table.appendChild(tbody);
        container.appendChild(table);
    }
    
    /**
     * Format a header name for display
     * @param {string} header - Header name from API
     * @returns {string} Formatted header name
     * @private
     */
    function formatHeader(header) {
        // Replace underscores with spaces and capitalize words
        return header.split('_')
            .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
            .join(' ');
    }
    
    /**
     * Load requirements from the API
     * @private
     */
    function loadRequirements() {
        if (!elements.requirementSelect) return;
        
        // Show loading state
        elements.requirementSelect.innerHTML = '<option value="" disabled selected>Loading requirements...</option>';
        
        // Call the API
        TestGeneration.API.get('/api/requirements/processed')
            .then(response => {
                // Process the response
                if (response.status === 'success' && response.data && Array.isArray(response.data)) {
                    populateRequirementSelect(response.data);
                } else {
                    elements.requirementSelect.innerHTML = 
                        '<option value="" disabled selected>Error loading requirements</option>';
                    console.error('Invalid response format for requirements:', response);
                }
                
                requirementsLoaded = true;
            })
            .catch(error => {
                console.error('Error loading requirements:', error);
                elements.requirementSelect.innerHTML = 
                    '<option value="" disabled selected>Error loading requirements</option>';
                
                TestGeneration.UIUtils.showNotification(
                    'Failed to load requirements: ' + (error.message || 'Unknown error'),
                    'error'
                );
                
                requirementsLoaded = false;
            });
    }
    
    /**
     * Populate the requirement select dropdown
     * @param {Array} requirements - Requirements data from API
     * @private
     */
    function populateRequirementSelect(requirements) {
        if (!elements.requirementSelect) return;
        
        // Clear previous options
        elements.requirementSelect.innerHTML = '';
        
        if (requirements.length === 0) {
            // No requirements available
            elements.requirementSelect.innerHTML = 
                '<option value="" disabled selected>No requirements available</option>';
            return;
        }
        
        // Add default option
        const defaultOption = document.createElement('option');
        defaultOption.value = '';
        defaultOption.disabled = true;
        defaultOption.textContent = 'Select one or more requirements';
        elements.requirementSelect.appendChild(defaultOption);
        
        // Add requirements
        requirements.forEach(req => {
            const option = document.createElement('option');
            option.value = req.id;
            
            // Format option text based on available properties
            let optionText = req.id;
            if (req.title) {
                optionText += ': ' + req.title;
            } else if (req.summary) {
                optionText += ': ' + req.summary;
            } else if (req.description) {
                const shortDesc = req.description.length > 50 
                    ? req.description.substring(0, 50) + '...' 
                    : req.description;
                optionText += ': ' + shortDesc;
            }
            
            option.textContent = optionText;
            elements.requirementSelect.appendChild(option);
        });
    }
    
    /**
     * Export generated test cases to Excel
     * @private
     */
    function exportToExcel() {
        if (!generatedTestCases) {
            TestGeneration.UIUtils.showNotification(
                'No test cases to export. Please generate test cases first.',
                'warning'
            );
            return;
        }
        
        // Show progress indicator
        TestGeneration.Main.showLoadingSpinner('generation', 'Exporting test cases to Excel...');
        
        // Prepare request data
        const requestData = {
            test_cases: generatedTestCases.test_cases || [{ steps: generatedTestCases.test_case }],
            filename: 'Generated_TestCases_' + TestGeneration.UIUtils.formatDate(new Date())
        };
        
        // Call API to export
        TestGeneration.API.postForBlob('/api/test-cases/export-excel', requestData)
            .then(blob => {
                // Hide progress indicator
                TestGeneration.Main.hideLoadingSpinner('generation');
                
                // Create download link
                TestGeneration.UIUtils.downloadBlob(blob, requestData.filename + '.xlsx');
                
                // Show success notification
                TestGeneration.UIUtils.showNotification(
                    'Test cases exported successfully!',
                    'success'
                );
            })
            .catch(error => {
                console.error('Error exporting test cases:', error);
                
                // Hide progress indicator
                TestGeneration.Main.hideLoadingSpinner('generation');
                
                // Show error notification
                TestGeneration.UIUtils.showNotification(
                    'Error exporting test cases: ' + (error.message || 'Unknown error'),
                    'error'
                );
            });
    }
    
    /**
     * Compare generated test cases with repository
     * @private
     */
    function compareWithRepository() {
        if (!generatedTestCases) {
            TestGeneration.UIUtils.showNotification(
                'No test cases to compare. Please generate test cases first.',
                'warning'
            );
            return;
        }
        
        // Show progress indicator
        TestGeneration.Main.showLoadingSpinner('generation', 'Comparing with repository...');
        
        // Prepare request data
        const requestData = {
            test_cases: generatedTestCases.test_cases || [{ steps: generatedTestCases.test_case }]
        };
        
        // Call API to compare
        TestGeneration.API.post('/api/test-cases/compare-with-repository', requestData)
            .then(response => {
                // Hide progress indicator
                TestGeneration.Main.hideLoadingSpinner('generation');
                
                // Process the response
                if (response.status === 'success' && response.data && response.data.comparison_id) {
                    // Redirect to comparison results page
                    window.location.href = '/test-repository/comparison-results?comparison_id=' + 
                        response.data.comparison_id;
                } else {
                    // Show error notification
                    TestGeneration.UIUtils.showNotification(
                        'Failed to compare test cases: ' + (response.message || 'Unknown error'),
                        'error'
                    );
                }
            })
            .catch(error => {
                console.error('Error comparing test cases:', error);
                
                // Hide progress indicator
                TestGeneration.Main.hideLoadingSpinner('generation');
                
                // Show error notification
                TestGeneration.UIUtils.showNotification(
                    'Error comparing test cases: ' + (error.message || 'Unknown error'),
                    'error'
                );
            });
    }
    
    /**
     * Reset the generate form
     * @public
     */
    function resetForm() {
        // Reset form elements
        if (elements.form) {
            elements.form.reset();
            
            // Reset input source selection (select Requirements by default)
            if (elements.sourceRequirements && elements.requirementsSection && elements.promptSection) {
                elements.sourceRequirements.checked = true;
                elements.requirementsSection.classList.remove('hidden');
                elements.promptSection.classList.add('hidden');
            }
            
            // Reset requirement selection
            if (elements.requirementSelect) {
                // Preserve the options but reset selection
                Array.from(elements.requirementSelect.options).forEach(option => {
                    option.selected = false;
                });
            }
        }
        
        // Hide output area
        if (elements.outputArea) {
            elements.outputArea.classList.add('hidden');
        }
        
        // Clear test case preview
        if (elements.testCasePreview) {
            elements.testCasePreview.innerHTML = '';
        }
        
        // Clear stored test cases
        generatedTestCases = null;
        
        // Reset changes flag
        hasChanges = false;
    }
    
    /**
     * Handle window resize event
     * @public
     */
    function handleResize() {
        // Any resize-specific UI adjustments can be placed here
        
        // Example: Adjust test case table for small screens
        if (elements.testCasePreview) {
            const tables = elements.testCasePreview.querySelectorAll('table');
            const isMobile = window.innerWidth < 768;
            
            tables.forEach(table => {
                if (isMobile) {
                    table.classList.add('table-responsive');
                } else {
                    table.classList.remove('table-responsive');
                }
            });
        }
    }
    
    /**
     * Check if there are unsaved changes
     * @returns {boolean} True if there are unsaved changes
     * @public
     */
    function hasUnsavedChanges() {
        return hasChanges;
    }
    
    /**
     * Check if the module has been initialized
     * @returns {boolean} True if the module has been initialized
     * @public
     */
    function isInitialized() {
        return initialized;
    }
    
    /**
     * Reload requirements from the API
     * @public
     */
    function reloadRequirements() {
        requirementsLoaded = false;
        loadRequirements();
    }
    
    // Return public API
    return {
        initialize: initialize,
        resetForm: resetForm,
        handleResize: handleResize,
        hasUnsavedChanges: hasUnsavedChanges,
        isInitialized: isInitialized,
        reloadRequirements: reloadRequirements
    };
})();
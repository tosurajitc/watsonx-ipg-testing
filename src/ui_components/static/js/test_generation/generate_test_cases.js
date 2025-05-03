/**
 * Test Generation & Refinement - Generate Test Cases Module
 * 
 * This module handles the functionality for generating detailed test cases
 * from requirements or direct user input.
 */

// Create namespace if it doesn't exist
var TestGeneration = TestGeneration || {};

/**
 * Generate module for test case generation functionality
 */
TestGeneration.Generate = (function() {
    // Private variables
    let initialized = false;
    let processedRequirements = [];
    let hasChanges = false;
    
    // Cache DOM elements for better performance
    const elements = {
        form: null,
        inputSourceRadios: null,
        requirementsSection: null,
        promptSection: null,
        requirementsStatus: null,
        promptInput: null,
        detailLevel: null,
        targetFormat: null,
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
        if (initialized) {
            console.log('Generate Test Cases module already initialized');
            return;
        }
    }
    
    /**
     * Display comparison results
     * @param {Object} data - Comparison results
     * @private
     */
    function displayComparisonResults(data) {
        console.log('Comparison results:', data);
        
        try {
            // Create modal element
            let modalHtml = `
                <div class="modal fade" id="comparisonResultsModal" tabindex="-1" aria-labelledby="comparisonResultsModalLabel" aria-hidden="true">
                    <div class="modal-dialog modal-lg">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title" id="comparisonResultsModalLabel">Test Case Comparison Results</h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                            </div>
                            <div class="modal-body">
                                <!-- Modal content here -->
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            
            // Remove any existing modal with the same ID
            const existingModal = document.getElementById('comparisonResultsModal');
            if (existingModal) {
                existingModal.remove();
            }
            
            // Add modal to document
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = modalHtml.trim();
            const modalElement = tempDiv.firstChild;
            document.body.appendChild(modalElement);
            
            // Populate modal content
            const modalBody = modalElement.querySelector('.modal-body');
            if (modalBody) {
                // Add content to modal body
                // ...
            }
            
            // Show modal using Bootstrap
            if (typeof bootstrap !== 'undefined' && bootstrap.Modal) {
                const modal = new bootstrap.Modal(modalElement);
                modal.show();
            } else {
                // Fallback if Bootstrap is not available
                console.error('Bootstrap Modal is not available. Make sure Bootstrap JS is loaded.');
                // Show simple alert instead
                alert('Comparison complete. Found ' + (data.matches ? data.matches.length : 0) + ' matching test cases.');
            }
        } catch (error) {
            console.error('Error displaying comparison results:', error);
            // Show simple alert as fallback
            alert('Comparison complete. Error displaying detailed results.');
        }
    }
    
    /**
     * Reset the generate form
     * @public
     */
    function resetForm() {
        console.log('Resetting form');
        
        // Reset form elements
        if (elements.form) {
            elements.form.reset();
        }
        
        // Hide output area
        if (elements.outputArea) {
            if (!elements.outputArea.classList.contains('d-none')) {
                elements.outputArea.classList.add('d-none');
            }
            elements.outputArea.style.display = 'none';
        }
        
        // Clear test case preview
        if (elements.testCasePreview) {
            elements.testCasePreview.innerHTML = '';
        }
        
        // Reset toggle based on default radio button
        toggleInputSections();
        
        // Reset changes flag
        hasChanges = false;
    }
    
    /**
     * Handle window resize event
     * @public
     */
    function handleResize() {
        // Any resize-specific UI adjustments can be placed here
        console.log('Window resized');
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
    
    // Return public API
    return {
        initialize: initialize,
        resetForm: resetForm,
        handleResize: handleResize,
        hasUnsavedChanges: hasUnsavedChanges,
        isInitialized: isInitialized
    };
})();

// Initialize the module when the DOM is fully loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, initializing TestGeneration.Generate module...');
    TestGeneration.Generate.initialize();
});

console.log('Generate Test Cases module loaded successfully');
        
        console.log('Initializing Generate Test Cases module...');
        
        // Cache DOM elements
        cacheElements();
        
        // Set up event listeners
        setupEventListeners();
        
        // Load processed requirements if available
        loadProcessedRequirements();
        
        // Set initialization flag
        initialized = true;
        
        console.log('Generate Test Cases module initialized successfully');
    }
    
    /**
     * Cache DOM elements for better performance
     * @private
     */
    function cacheElements() {
        elements.form = document.getElementById('generateTestCaseForm');
        elements.inputSourceRadios = document.getElementsByName('inputSource');
        elements.requirementsSection = document.getElementById('requirementsSection');
        elements.promptSection = document.getElementById('promptSection');
        elements.requirementsStatus = document.getElementById('processedRequirementsStatus');
        elements.promptInput = document.getElementById('promptInput');
        elements.detailLevel = document.getElementById('detailLevel');
        elements.targetFormat = document.getElementById('targetFormat');
        elements.generateBtn = document.getElementById('generateTestCaseBtn');
        elements.cancelBtn = document.getElementById('cancelGenerateBtn');
        elements.progressArea = document.getElementById('generationProgress');
        elements.outputArea = document.getElementById('generationOutput');
        elements.testCasePreview = document.getElementById('testCasePreview');
        elements.exportExcelBtn = document.getElementById('exportExcelBtn');
        elements.compareRepoBtn = document.getElementById('compareRepoBtn');
        
        console.log('DOM elements cached:', {
            form: !!elements.form,
            inputSourceRadios: !!elements.inputSourceRadios,
            requirementsSection: !!elements.requirementsSection,
            promptSection: !!elements.promptSection,
            generateBtn: !!elements.generateBtn
        });
    }
    
    /**
     * Set up event listeners for the Generate module
     * @private
     */
    function setupEventListeners() {
        // Input source radio buttons
        if (elements.inputSourceRadios) {
            for (let i = 0; i < elements.inputSourceRadios.length; i++) {
                if (elements.inputSourceRadios[i]) {
                    elements.inputSourceRadios[i].addEventListener('change', toggleInputSections);
                }
            }
            // Set initial state based on current selection
            toggleInputSections();
        }
        
        // Generate button
        if (elements.generateBtn) {
            elements.generateBtn.addEventListener('click', handleGenerateClick);
        }
        
        // Cancel button
        if (elements.cancelBtn) {
            elements.cancelBtn.addEventListener('click', resetForm);
        }
        
        // Export Excel button
        if (elements.exportExcelBtn) {
            elements.exportExcelBtn.addEventListener('click', exportToExcel);
        }
        
        // Compare with Repository button
        if (elements.compareRepoBtn) {
            elements.compareRepoBtn.addEventListener('click', compareWithRepository);
        }
        
        console.log('Event listeners set up successfully');
    }
    
    /**
     * Toggle the display of input sections based on selected radio button
     * @private
     */
    function toggleInputSections() {
        // Find selected input source
        let selectedSource = 'requirements'; // Default
        
        for (let i = 0; i < elements.inputSourceRadios.length; i++) {
            if (elements.inputSourceRadios[i].checked) {
                selectedSource = elements.inputSourceRadios[i].value;
                break;
            }
        }
        
        console.log('Selected input source:', selectedSource);
        
        // Toggle sections based on selection
        if (selectedSource === 'requirements') {
            if (elements.requirementsSection) {
                elements.requirementsSection.style.display = 'block';
            }
            if (elements.promptSection) {
                elements.promptSection.style.display = 'none';
            }
        } else if (selectedSource === 'prompt') {
            if (elements.requirementsSection) {
                elements.requirementsSection.style.display = 'none';
            }
            if (elements.promptSection) {
                elements.promptSection.style.display = 'block';
            }
        }
        
        // Update changes flag
        hasChanges = true;
    }
    
    /**
     * Load processed requirements from the server
     * @private
     */
    function loadProcessedRequirements() {
        console.log('Loading processed requirements...');
        
        // Use the API service if available
        if (TestGeneration.API && TestGeneration.API.get) {
            TestGeneration.API.get('/api/requirements/processed')
                .then(function(response) {
                    if (response.status === 'success' && response.data && response.data.requirements) {
                        processRequirements(response.data.requirements);
                    } else {
                        showNoRequirementsMessage();
                    }
                })
                .catch(function(error) {
                    console.error('Error loading requirements:', error);
                    showNoRequirementsMessage();
                });
        } else {
            // Fallback to direct fetch if API service not available
            fetch('/api/requirements/processed')
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success' && data.data && data.data.requirements) {
                        processRequirements(data.data.requirements);
                    } else {
                        showNoRequirementsMessage();
                    }
                })
                .catch(error => {
                    console.error('Error loading requirements:', error);
                    showNoRequirementsMessage();
                });
        }
    }
    
    /**
     * Process the loaded requirements
     * @param {Array} requirements - Array of requirement objects
     * @private
     */
    function processRequirements(requirements) {
        if (!requirements || requirements.length === 0) {
            showNoRequirementsMessage();
            return;
        }
        
        // Store the requirements
        processedRequirements = requirements;
        
        // Update the UI to show available requirements
        if (elements.requirementsStatus) {
            // Create a requirements selection list
            const requirementsList = document.createElement('div');
            requirementsList.className = 'requirements-list mb-3';
            
            // Add header
            const header = document.createElement('h6');
            header.textContent = 'Select Requirements to Generate Test Cases From:';
            requirementsList.appendChild(header);
            
            // Create a table for requirements
            const table = document.createElement('table');
            table.className = 'table table-hover table-sm';
            
            // Add table header
            const thead = document.createElement('thead');
            const headerRow = document.createElement('tr');
            
            const selectHeader = document.createElement('th');
            selectHeader.style.width = '50px';
            const checkAll = document.createElement('input');
            checkAll.type = 'checkbox';
            checkAll.className = 'form-check-input';
            checkAll.id = 'checkAllRequirements';
            checkAll.addEventListener('change', function() {
                const checkboxes = table.querySelectorAll('tbody input[type="checkbox"]');
                for (let i = 0; i < checkboxes.length; i++) {
                    checkboxes[i].checked = this.checked;
                }
            });
            selectHeader.appendChild(checkAll);
            headerRow.appendChild(selectHeader);
            
            const idHeader = document.createElement('th');
            idHeader.textContent = 'ID';
            idHeader.style.width = '100px';
            headerRow.appendChild(idHeader);
            
            const titleHeader = document.createElement('th');
            titleHeader.textContent = 'Title';
            headerRow.appendChild(titleHeader);
            
            const sourceHeader = document.createElement('th');
            sourceHeader.textContent = 'Source';
            sourceHeader.style.width = '100px';
            headerRow.appendChild(sourceHeader);
            
            thead.appendChild(headerRow);
            table.appendChild(thead);
            
            // Add table body
            const tbody = document.createElement('tbody');
            
            requirements.forEach(function(req) {
                const row = document.createElement('tr');
                
                // Checkbox cell
                const checkCell = document.createElement('td');
                const checkbox = document.createElement('input');
                checkbox.type = 'checkbox';
                checkbox.className = 'form-check-input requirement-checkbox';
                checkbox.value = req.id;
                checkbox.dataset.requirementId = req.id;
                checkCell.appendChild(checkbox);
                row.appendChild(checkCell);
                
                // ID cell
                const idCell = document.createElement('td');
                idCell.textContent = req.id;
                row.appendChild(idCell);
                
                // Title cell
                const titleCell = document.createElement('td');
                titleCell.textContent = req.title;
                row.appendChild(titleCell);
                
                // Source cell
                const sourceCell = document.createElement('td');
                sourceCell.textContent = req.source;
                row.appendChild(sourceCell);
                
                tbody.appendChild(row);
            });
            
            table.appendChild(tbody);
            requirementsList.appendChild(table);
            
            // Replace the status message with the requirements list
            elements.requirementsStatus.innerHTML = '';
            elements.requirementsStatus.className = 'requirements-container';
            elements.requirementsStatus.appendChild(requirementsList);
        }
    }
    
    /**
     * Show a message when no requirements are available
     * @private
     */
    function showNoRequirementsMessage() {
        if (elements.requirementsStatus) {
            elements.requirementsStatus.innerHTML = `
                <div class="alert alert-info">
                    <div class="d-flex align-items-center">
                        <div class="me-3">
                            <i class="fas fa-info-circle fa-lg"></i>
                        </div>
                        <div>
                            <span class="status-text">No processed requirements found. Please go to the Requirements section first or use direct prompt.</span>
                        </div>
                    </div>
                </div>
            `;
            elements.requirementsStatus.className = 'alert alert-info';
        }
    }
    
    /**
     * Handle click on the Generate button
     * @private
     */
    function handleGenerateClick() {
        console.log('Generate button clicked');
        
        // Validate form
        if (!validateForm()) {
            return;
        }
        
        // Show progress indicator
        showProgressIndicator();
        
        // Hide output area if previously shown
        if (elements.outputArea) {
            elements.outputArea.style.display = 'none';
            if (!elements.outputArea.classList.contains('d-none')) {
                elements.outputArea.classList.add('d-none');
            }
        }
        
        // Get form data
        const formData = getFormData();
        
        // Generate test cases
        generateTestCases(formData);
    }
    
    /**
     * Validate the form before submission
     * @returns {boolean} True if valid, false otherwise
     * @private
     */
    function validateForm() {
        // Find selected input source
        let selectedSource = 'requirements'; // Default
        
        for (let i = 0; i < elements.inputSourceRadios.length; i++) {
            if (elements.inputSourceRadios[i].checked) {
                selectedSource = elements.inputSourceRadios[i].value;
                break;
            }
        }
        
        // Validate based on input source
        if (selectedSource === 'requirements') {
            // Check if any requirements are selected
            const checkboxes = document.querySelectorAll('.requirement-checkbox:checked');
            if (checkboxes.length === 0) {
                // If no requirements are available, don't show error
                if (processedRequirements.length === 0) {
                    // Show error using UIUtils if available
                    if (TestGeneration.UIUtils && TestGeneration.UIUtils.showNotification) {
                        TestGeneration.UIUtils.showNotification(
                            'No requirements available. Please process requirements first or use direct prompt.',
                            'warning'
                        );
                    } else {
                        alert('No requirements available. Please process requirements first or use direct prompt.');
                    }
                    return false;
                }
                
                // Show error using UIUtils if available
                if (TestGeneration.UIUtils && TestGeneration.UIUtils.showNotification) {
                    TestGeneration.UIUtils.showNotification(
                        'Please select at least one requirement.',
                        'warning'
                    );
                } else {
                    alert('Please select at least one requirement.');
                }
                return false;
            }
        } else if (selectedSource === 'prompt') {
            // Check if prompt is entered
            if (!elements.promptInput || !elements.promptInput.value.trim()) {
                // Show error using UIUtils if available
                if (TestGeneration.UIUtils && TestGeneration.UIUtils.showNotification) {
                    TestGeneration.UIUtils.showNotification(
                        'Please enter a prompt or keywords.',
                        'warning'
                    );
                } else {
                    alert('Please enter a prompt or keywords.');
                }
                return false;
            }
        }
        
        return true;
    }
    
    /**
     * Get form data for test case generation
     * @returns {Object} Form data
     * @private
     */
    function getFormData() {
        // Find selected input source
        let selectedSource = 'requirements'; // Default
        
        for (let i = 0; i < elements.inputSourceRadios.length; i++) {
            if (elements.inputSourceRadios[i].checked) {
                selectedSource = elements.inputSourceRadios[i].value;
                break;
            }
        }
        
        const formData = {
            sourceType: selectedSource,
            detailLevel: elements.detailLevel ? elements.detailLevel.value : 'medium',
            targetFormat: elements.targetFormat ? elements.targetFormat.value : 'preview'
        };
        
        // Add source-specific data
        if (selectedSource === 'requirements') {
            // Get selected requirement IDs
            const selectedRequirements = [];
            const checkboxes = document.querySelectorAll('.requirement-checkbox:checked');
            
            for (let i = 0; i < checkboxes.length; i++) {
                selectedRequirements.push(checkboxes[i].dataset.requirementId);
            }
            
            formData.requirementIds = selectedRequirements;
        } else if (selectedSource === 'prompt') {
            // Get prompt text
            formData.prompt = elements.promptInput ? elements.promptInput.value.trim() : '';
        }
        
        return formData;
    }
    
    /**
     * Show progress indicator during test case generation
     * @private
     */
    function showProgressIndicator() {
        if (elements.progressArea) {
            if (elements.progressArea.classList.contains('d-none')) {
                elements.progressArea.classList.remove('d-none');
            }
            elements.progressArea.style.display = 'block';
            
            // Update progress status
            const progressStatus = elements.progressArea.querySelector('.progress-status');
            if (progressStatus) {
                progressStatus.textContent = 'Generating test cases... This may take a few moments.';
            }
        }
    }
    
    /**
     * Hide progress indicator
     * @private
     */
    function hideProgressIndicator() {
        if (elements.progressArea) {
            if (!elements.progressArea.classList.contains('d-none')) {
                elements.progressArea.classList.add('d-none');
            }
            elements.progressArea.style.display = 'none';
        }
    }
    
    /**
     * Generate test cases based on form data
     * @param {Object} formData - Form data for test case generation
     * @private
     */
    function generateTestCases(formData) {
        console.log('Generating test cases with data:', formData);
        
        // Use the API service if available
        if (TestGeneration.API && TestGeneration.API.post) {
            TestGeneration.API.post('/api/test-cases/generate', formData)
                .then(function(response) {
                    // Hide progress indicator
                    hideProgressIndicator();
                    
                    if (response.status === 'success') {
                        // Display generated test cases
                        displayTestCases(response.data);
                        
                        // Reset changes flag
                        hasChanges = false;
                        
                        // Show success notification
                        if (TestGeneration.UIUtils && TestGeneration.UIUtils.showNotification) {
                            TestGeneration.UIUtils.showNotification(
                                'Test cases generated successfully!',
                                'success'
                            );
                        }
                    } else {
                        // Show error notification
                        if (TestGeneration.UIUtils && TestGeneration.UIUtils.showNotification) {
                            TestGeneration.UIUtils.showNotification(
                                'Error generating test cases: ' + (response.message || 'Unknown error'),
                                'error'
                            );
                        } else {
                            alert('Error generating test cases: ' + (response.message || 'Unknown error'));
                        }
                    }
                })
                .catch(function(error) {
                    // Hide progress indicator
                    hideProgressIndicator();
                    
                    // Show error notification
                    if (TestGeneration.UIUtils && TestGeneration.UIUtils.showNotification) {
                        TestGeneration.UIUtils.showNotification(
                            'Error generating test cases: ' + (error.message || 'Unknown error'),
                            'error'
                        );
                    } else {
                        alert('Error generating test cases: ' + (error.message || 'Unknown error'));
                    }
                });
        } else {
            // Fallback to direct fetch if API service not available
            const csrfToken = getCSRFToken();
            
            fetch('/api/test-cases/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify(formData),
                credentials: 'same-origin'
            })
            .then(response => response.json())
            .then(data => {
                // Hide progress indicator
                hideProgressIndicator();
                
                if (data.status === 'success') {
                    // Display generated test cases
                    displayTestCases(data.data);
                    
                    // Reset changes flag
                    hasChanges = false;
                    
                    // Show success notification
                    if (TestGeneration.UIUtils && TestGeneration.UIUtils.showNotification) {
                        TestGeneration.UIUtils.showNotification(
                            'Test cases generated successfully!',
                            'success'
                        );
                    } else {
                        alert('Test cases generated successfully!');
                    }
                } else {
                    // Show error notification
                    if (TestGeneration.UIUtils && TestGeneration.UIUtils.showNotification) {
                        TestGeneration.UIUtils.showNotification(
                            'Error generating test cases: ' + (data.message || 'Unknown error'),
                            'error'
                        );
                    } else {
                        alert('Error generating test cases: ' + (data.message || 'Unknown error'));
                    }
                }
            })
            .catch(error => {
                // Hide progress indicator
                hideProgressIndicator();
                
                // Show error notification
                if (TestGeneration.UIUtils && TestGeneration.UIUtils.showNotification) {
                    TestGeneration.UIUtils.showNotification(
                        'Error generating test cases: ' + (error.message || 'Unknown error'),
                        'error'
                    );
                } else {
                    alert('Error generating test cases: ' + (error.message || 'Unknown error'));
                }
            });
        }
    }
    
    /**
     * Get CSRF token from cookie
     * @returns {string|null} CSRF token or null if not found
     * @private
     */
    function getCSRFToken() {
        // Use UIUtils if available
        if (TestGeneration.UIUtils && TestGeneration.UIUtils.getCSRFToken) {
            return TestGeneration.UIUtils.getCSRFToken();
        }
        
        // Internal implementation as fallback
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
    
    /**
     * Display generated test cases in the output area
     * @param {Object} data - Generated test case data
     * @private
     */
    function displayTestCases(data) {
        if (!elements.outputArea || !elements.testCasePreview) {
            console.error('Output area elements not found');
            return;
        }
        
        // Clear previous content
        elements.testCasePreview.innerHTML = '';
        
        // Check target format
        const targetFormat = elements.targetFormat ? elements.targetFormat.value : 'preview';
        
        if (targetFormat === 'preview') {
            // Show output area
            if (elements.outputArea.classList.contains('d-none')) {
                elements.outputArea.classList.remove('d-none');
            }
            elements.outputArea.style.display = 'block';
            
            // Display test cases
            if (data.test_case) {
                // Create table for test case steps
                const table = document.createElement('table');
                table.className = 'table table-bordered';
                
                // Create header
                const thead = document.createElement('thead');
                const headerRow = document.createElement('tr');
                
                const headers = ['Step #', 'Description', 'Test Data', 'Expected Result'];
                headers.forEach(header => {
                    const th = document.createElement('th');
                    th.textContent = header;
                    headerRow.appendChild(th);
                });
                
                thead.appendChild(headerRow);
                table.appendChild(thead);
                
                // Create body
                const tbody = document.createElement('tbody');
                
                data.test_case.forEach((step, index) => {
                    const row = document.createElement('tr');
                    
                    // Step number
                    const stepCell = document.createElement('td');
                    stepCell.textContent = step.STEP_NO || (index + 1);
                    row.appendChild(stepCell);
                    
                    // Description
                    const descCell = document.createElement('td');
                    descCell.textContent = step.TEST_STEP_DESCRIPTION || '';
                    row.appendChild(descCell);
                    
                    // Test data
                    const dataCell = document.createElement('td');
                    dataCell.textContent = step.DATA || '';
                    row.appendChild(dataCell);
                    
                    // Expected result
                    const resultCell = document.createElement('td');
                    resultCell.textContent = step.EXPECTED_RESULT || '';
                    row.appendChild(resultCell);
                    
                    tbody.appendChild(row);
                });
                
                table.appendChild(tbody);
                elements.testCasePreview.appendChild(table);
            } else {
                // No test case data available
                elements.testCasePreview.innerHTML = '<div class="alert alert-warning">No test case data available.</div>';
            }
        } else {
            // For other formats (excel, word, pdf), trigger download
            downloadTestCases(data, targetFormat);
        }
    }
    
    /**
     * Download test cases in the specified format
     * @param {Object} data - Generated test case data
     * @param {string} format - Target format (excel, word, pdf)
     * @private
     */
    function downloadTestCases(data, format) {
        console.log('Downloading test cases in', format, 'format');
        
        // Create download request
        const downloadData = {
            scenarios: [data.scenario || {}],
            format: format
        };
        
        // Use the API service if available
        if (TestGeneration.API && TestGeneration.API.post) {
            TestGeneration.API.post('/api/test-cases/generate-download', downloadData)
                .then(function(response) {
                    // TODO: Handle file download
                    console.log('Download response:', response);
                    
                    // For now, just show success notification
                    if (TestGeneration.UIUtils && TestGeneration.UIUtils.showNotification) {
                        TestGeneration.UIUtils.showNotification(
                            'Test cases downloaded successfully!',
                            'success'
                        );
                    } else {
                        alert('Test cases downloaded successfully!');
                    }
                })
                .catch(function(error) {
                    // Show error notification
                    if (TestGeneration.UIUtils && TestGeneration.UIUtils.showNotification) {
                        TestGeneration.UIUtils.showNotification(
                            'Error downloading test cases: ' + (error.message || 'Unknown error'),
                            'error'
                        );
                    } else {
                        alert('Error downloading test cases: ' + (error.message || 'Unknown error'));
                    }
                });
        } else {
            // Fallback to direct fetch if API service not available
            const csrfToken = getCSRFToken();
            
            fetch('/api/test-cases/generate-download', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify(downloadData),
                credentials: 'same-origin'
            })
            .then(response => {
                // Check if response is OK
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                
                // Get filename from Content-Disposition header if available
                let filename = 'test_cases.' + format;
                const contentDisposition = response.headers.get('Content-Disposition');
                if (contentDisposition) {
                    const filenameMatch = contentDisposition.match(/filename="(.+)"/);
                    if (filenameMatch) {
                        filename = filenameMatch[1];
                    }
                }
                
                // Convert response to blob and trigger download
                return response.blob().then(blob => {
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.style.display = 'none';
                    a.href = url;
                    a.download = filename;
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                    
                    // Show success notification
                    if (TestGeneration.UIUtils && TestGeneration.UIUtils.showNotification) {
                        TestGeneration.UIUtils.showNotification(
                            'Test cases downloaded successfully!',
                            'success'
                        );
                    } else {
                        alert('Test cases downloaded successfully!');
                    }
                });
            })
            .catch(error => {
                // Show error notification
                if (TestGeneration.UIUtils && TestGeneration.UIUtils.showNotification) {
                    TestGeneration.UIUtils.showNotification(
                        'Error downloading test cases: ' + (error.message || 'Unknown error'),
                        'error'
                    );
                } else {
                    alert('Error downloading test cases: ' + (error.message || 'Unknown error'));
                }
            });
        }
    }
    
    /**
     * Export test cases to Excel
     * @private
     */
    function exportToExcel() {
        console.log('Exporting test cases to Excel');
        
        // Trigger download with excel format
        const data = {
            test_case: getTestCaseData()
        };
        
        downloadTestCases(data, 'excel');
    }
    
    /**
     * Get test case data from the preview
     * @returns {Array} Test case data
     * @private
     */
    function getTestCaseData() {
        // This is a simple implementation that extracts data from the table
        // In a real implementation, you would have proper data storage
        
        const testCaseData = [];
        
        // Find the table in the preview
        const table = elements.testCasePreview.querySelector('table');
        if (table) {
            // Get all rows except header
            const rows = table.querySelectorAll('tbody tr');
            
            rows.forEach((row, index) => {
                const cells = row.querySelectorAll('td');
                
                if (cells.length >= 4) {
                    testCaseData.push({
                        STEP_NO: cells[0].textContent.trim(),
                        TEST_STEP_DESCRIPTION: cells[1].textContent.trim(),
                        DATA: cells[2].textContent.trim(),
                        EXPECTED_RESULT: cells[3].textContent.trim()
                    });
                }
            });
        }
        
        return testCaseData;
    }
    
    /**
     * Compare generated test cases with repository
     * @private
     */
    function compareWithRepository() {
        console.log('Comparing test cases with repository');
        
        // Get test case data
        const testCaseData = getTestCaseData();
        
        if (testCaseData.length === 0) {
            // Show error notification
            if (TestGeneration.UIUtils && TestGeneration.UIUtils.showNotification) {
                TestGeneration.UIUtils.showNotification(
                    'No test case data available for comparison.',
                    'warning'
                );
            } else {
                alert('No test case data available for comparison.');
            }
            return;
        }
        
        // Show progress indicator
        showProgressIndicator();
        
        // Prepare request data
        const requestData = {
            testCase: testCaseData
        };
        
        // Call API to compare with repository
        // Use the API service if available
        if (TestGeneration.API && TestGeneration.API.post) {
            TestGeneration.API.post('/api/test-cases/compare-repository', requestData)
                .then(function(response) {
                    // Hide progress indicator
                    hideProgressIndicator();
                    
                    if (response.status === 'success') {
                        // Display comparison results
                        displayComparisonResults(response.data);
                        
                        // Show success notification
                        if (TestGeneration.UIUtils && TestGeneration.UIUtils.showNotification) {
                            TestGeneration.UIUtils.showNotification(
                                'Test cases compared with repository successfully!',
                                'success'
                            );
                        } else {
                            alert('Test cases compared with repository successfully!');
                        }
                    } else {
                        // Show error notification
                        if (TestGeneration.UIUtils && TestGeneration.UIUtils.showNotification) {
                            TestGeneration.UIUtils.showNotification(
                                'Error comparing test cases: ' + (response.message || 'Unknown error'),
                                'error'
                            );
                        } else {
                            alert('Error comparing test cases: ' + (response.message || 'Unknown error'));
                        }
                    }
                })
                .catch(function(error) {
                    // Hide progress indicator
                    hideProgressIndicator();
                    
                    // Show error notification
                    if (TestGeneration.UIUtils && TestGeneration.UIUtils.showNotification) {
                        TestGeneration.UIUtils.showNotification(
                            'Error comparing test cases: ' + (error.message || 'Unknown error'),
                            'error'
                        );
                    } else {
                        alert('Error comparing test cases: ' + (error.message || 'Unknown error'));
                    }
                });
        } else {
            // Fallback to direct fetch if API service not available
            const csrfToken = getCSRFToken();
            
            fetch('/api/test-cases/compare-repository', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify(requestData),
                credentials: 'same-origin'
            })
            .then(response => response.json())
            .then(data => {
                // Hide progress indicator
                hideProgressIndicator();
                
                if (data.status === 'success') {
                    // Display comparison results
                    displayComparisonResults(data.data);
                    
                    // Show success notification
                    if (TestGeneration.UIUtils && TestGeneration.UIUtils.showNotification) {
                        TestGeneration.UIUtils.showNotification(
                            'Test cases compared with repository successfully!',
                            'success'
                        );
                    } else {
                        alert('Test cases compared with repository successfully!');
                    }
                } else {
                    // Show error notification
                    if (TestGeneration.UIUtils && TestGeneration.UIUtils.showNotification) {
                        TestGeneration.UIUtils.showNotification(
                            'Error comparing test cases: ' + (data.message || 'Unknown error'),
                            'error'
                        );
                    } else {
                        alert('Error comparing test cases: ' + (data.message || 'Unknown error'));
                    }
                }
            })
            .catch(error => {
                // Hide progress indicator
                hideProgressIndicator();
                
                // Show error notification
                if (TestGeneration.UIUtils && TestGeneration.UIUtils.showNotification) {
                    TestGeneration.UIUtils.showNotification(
                        'Error comparing test cases: ' + (error.message || 'Unknown error'),
                        'error'
                    );
                } else {
                    alert('Error comparing test cases: ' + (error.message || 'Unknown error'));
                }
            });
        }
    }
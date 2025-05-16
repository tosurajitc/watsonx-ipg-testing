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
    let generatedTestCaseData = null; // Store the generated test case data for export
    
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
            elements.exportExcelBtn.addEventListener('click', function() {
                exportTestCases('excel');
            });
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
        
        // Use the API service
        if (TestGeneration.API) {
            TestGeneration.API.get('/api/requirements/processed')
                .then(function(response) {
                    if (response && response.status === 'success' && response.data && response.data.requirements) {
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
            console.error('API service not available');
            showNoRequirementsMessage();
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
        
        // Clear previous test case data
        generatedTestCaseData = null;
        
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
            
            // Create a scenario object from the prompt
            formData.scenario = {
                name: "Generated from prompt",
                id: "PROMPT-" + Date.now(),
                subject: "Test Generation",
                description: formData.prompt,
                type: "Functional"
            };
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
        
        // Determine which API endpoint to use based on source type
        let apiEndpoint = '/test-cases/api/test-cases/generate/';
        
        
        if (formData.sourceType === 'prompt') {
            apiEndpoint = '/test-cases/api/test-cases/generate-from-prompt/';
        } else if (formData.sourceType === 'requirements' && formData.requirementIds && formData.requirementIds.length > 0) {
            apiEndpoint = '/test-cases/api/test-cases/generate-batch/';
        }

        // Check if we should immediately download instead of previewing
        if (formData.targetFormat !== 'preview') {
            // Call the download endpoint directly
            exportTestCases(formData.targetFormat);
            return;
        }
        
        // Use the API service for backend calls
        if (TestGeneration.API) {
            TestGeneration.API.post(apiEndpoint, formData)
                .then(handleGenerateResponse)
                .catch(handleGenerateError);
        } else {
            console.error('API service not available');
            handleGenerateError(new Error('API service not available'));
        }
    }
    
    /**
     * Handle successful test case generation response
     * @param {Object} response - API response
     * @private
     */
    function handleGenerateResponse(response) {
        // Hide progress indicator
        hideProgressIndicator();
        
        if (response.status === 'success') {
            // Store the generated test case data
            generatedTestCaseData = response.data;
            
            // Add console logs to see the data structure
            console.log("Response from API:", response);
            console.log("Response data type:", typeof response.data);
            console.log("Response data:", response.data);
            
            // Adapt data format if needed
            let displayData = response.data;
            
            // Check if data is missing the expected test_case property
            if (displayData && !displayData.test_case) {
                console.log("Data missing test_case property, adapting format");
                
                // If data is directly an array, wrap it in an object with test_case property
                if (Array.isArray(displayData)) {
                    displayData = { test_case: displayData };
                    console.log("Adapted array data to:", displayData);
                } 
                // If data has a property that contains the test cases
                else if (typeof displayData === 'object') {
                    // Look for likely candidate properties that might contain test cases
                    const candidateProps = ['results', 'test_cases', 'cases', 'data', 'steps'];
                    
                    for (const prop of candidateProps) {
                        if (displayData[prop] && Array.isArray(displayData[prop])) {
                            displayData = { test_case: displayData[prop] };
                            console.log(`Found test case data in '${prop}' property, adapted to:`, displayData);
                            break;
                        }
                    }
                    
                    // If we still don't have test_case, create an empty one to avoid errors
                    if (!displayData.test_case) {
                        console.warn("Could not find test case data in response, creating empty array");
                        displayData = { test_case: [] };
                    }
                }
            }
            
            // Display test cases using the TestCaseDisplay module
            if (TestGeneration.TestCaseDisplay && elements.testCasePreview) {
                // Show output area
                if (elements.outputArea.classList.contains('d-none')) {
                    elements.outputArea.classList.remove('d-none');
                }
                elements.outputArea.style.display = 'block';
                
                console.log("Calling displayTestCase with data:", displayData);
                
                // Display the test case using adapted data
                TestGeneration.TestCaseDisplay.displayTestCase(displayData, elements.testCasePreview);
                
                // Debug check if anything was added to the preview container
                console.log("Content after displayTestCase:", elements.testCasePreview.innerHTML);
                
                // Also check for any CSS issues that might be hiding the content
                const computedStyle = window.getComputedStyle(elements.outputArea);
                console.log("Output area display style:", computedStyle.display);
                console.log("Output area visibility:", computedStyle.visibility);
                console.log("Output area opacity:", computedStyle.opacity);
            } else {
                console.error('Display modules not available:', { 
                    TestCaseDisplay: !!TestGeneration.TestCaseDisplay,
                    testCasePreview: !!elements.testCasePreview
                });
                
                // Try to get the preview element directly
                const previewElement = document.getElementById('testCasePreview');
                console.log("Direct DOM query for testCasePreview:", previewElement);
                
                if (previewElement) {
                    previewElement.innerHTML = '<div class="alert alert-warning">Test case display module not available, but preview element found.</div>';
                } else if (elements.testCasePreview) {
                    elements.testCasePreview.innerHTML = '<div class="alert alert-warning">Test case display module not available.</div>';
                } else {
                    console.error('Cannot find testCasePreview element to display error message');
                }
            }
            
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
    }
    
    /**
     * Handle error in test case generation
     * @param {Error} error - Error object
     * @private
     */
    function handleGenerateError(error) {
        // Hide progress indicator
        hideProgressIndicator();
        
        console.error('Error generating test cases:', error);
        
        // Show error dialog
        let errorTitle = "Error";
        let errorMessage = "An unknown error occurred while generating test cases.";
        let errorDetails = "";
        let userAction = "Please try again later or contact support.";
        
        try {
            // Parse the error response if it's a string
            if (typeof error === 'string' && error.includes('{')) {
                const errorStart = error.indexOf('{');
                const errorJson = error.substring(errorStart);
                const parsedError = JSON.parse(errorJson);
                
                if (parsedError.error) {
                    errorTitle = parsedError.error.title || "Test Case Generation Failed";
                    errorMessage = parsedError.error.message || "There was an error generating the test case.";
                    errorDetails = parsedError.error.details || "";
                    userAction = parsedError.error.user_action || "Please try again later.";
                }
            }
            // Handle if error is already an object with the error info
            else if (error.error) {
                errorTitle = error.error.title || "Test Case Generation Failed";
                errorMessage = error.error.message || "There was an error generating the test case.";
                errorDetails = error.error.details || "";
                userAction = error.error.user_action || "Please try again later.";
            }
        } catch (e) {
            // If parsing failed, use the original error message
            errorMessage = error.message || String(error);
        }
        
        // Show error modal
        showErrorModal(errorTitle, errorMessage, errorDetails, userAction);
    }

    // Add this function to display an error modal
    function showErrorModal(title, message, details, userAction) {
        // Create modal HTML
        const modalHTML = `
        <div class="modal fade" id="errorModal" tabindex="-1" aria-labelledby="errorModalLabel" aria-hidden="true">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header bg-danger text-white">
                        <h5 class="modal-title" id="errorModalLabel">${title}</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <div class="alert alert-danger">
                            <p><strong>${message}</strong></p>
                            ${details ? `<p class="mt-2 small text-muted">${details}</p>` : ''}
                        </div>
                        <div class="mt-3">
                            <h6>Suggested Action:</h6>
                            <p>${userAction}</p>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                    </div>
                </div>
            </div>
        </div>
        `;
        
        // Remove any existing error modal
        const existingModal = document.getElementById('errorModal');
        if (existingModal) {
            existingModal.remove();
        }
        
        // Add the modal to the page
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        
        // Show the modal
        const errorModal = new bootstrap.Modal(document.getElementById('errorModal'));
        errorModal.show();
    }

    // Replace the existing handleGenerateError function with this one
    // In your event handlers, use this instead of the existing error handling

    /**
     * Export test cases to the specified format
     * @param {string} format - Export format (excel, word, pdf)
     * @private
     */
    function exportTestCases(format) {
        console.log('Exporting test cases to', format);
        
        // Show progress indicator
        showProgressIndicator();
        const progressStatus = elements.progressArea.querySelector('.progress-status');
        if (progressStatus) {
            progressStatus.textContent = `Preparing ${format.toUpperCase()} file...`;
        }
        
        // Check if we have test case data to export
        if (!generatedTestCaseData) {
            // Show error notification
            if (TestGeneration.UIUtils && TestGeneration.UIUtils.showNotification) {
                TestGeneration.UIUtils.showNotification(
                    'No test case data available for export.',
                    'warning'
                );
            } else {
                alert('No test case data available for export.');
            }
            
            hideProgressIndicator();
            return;
        }
        
        // Prepare export request data
        const exportData = {
            test_case: generatedTestCaseData.test_case,
            format: format
        };
        
        // Add scenario data if available
        if (generatedTestCaseData.scenario) {
            exportData.scenarios = [generatedTestCaseData.scenario];
        }
        
        // Generate base filename from test case data
        let filename = 'test_case';
        if (generatedTestCaseData.test_case && generatedTestCaseData.test_case.length > 0) {
            const firstRow = generatedTestCaseData.test_case[0];
            if (firstRow['TEST CASE NUMBER']) {
                filename = 'TC_' + firstRow['TEST CASE NUMBER'].replace(/[^a-zA-Z0-9]/g, '_');
            } else if (firstRow['TEST CASE']) {
                filename = firstRow['TEST CASE'].replace(/[^a-zA-Z0-9]/g, '_');
            }
        }
        
        // Add appropriate extension
        switch (format) {
            case 'excel':
                filename += '.xlsx';
                break;
            case 'word':
                filename += '.docx';
                break;
            case 'pdf':
                filename += '.pdf';
                break;
        }
        
        // Use the API service to handle the export
        if (TestGeneration.API && TestGeneration.API.downloadFile) {
            TestGeneration.API.downloadFile('/api/test-cases/generate-download', exportData, filename, 
                // Progress callback
                function(percent) {
                    if (progressStatus) {
                        progressStatus.textContent = `Downloading ${format.toUpperCase()} file... ${Math.round(percent)}%`;
                    }
                }
            )
            .then(function() {
                // Hide progress indicator
                hideProgressIndicator();
                
                // Show success notification
                if (TestGeneration.UIUtils && TestGeneration.UIUtils.showNotification) {
                    TestGeneration.UIUtils.showNotification(
                        `Test case exported to ${format.toUpperCase()} successfully!`,
                        'success'
                    );
                }
            })
            .catch(function(error) {
                // Hide progress indicator
                hideProgressIndicator();
                
                // Show error notification
                console.error('Export error:', error);
                if (TestGeneration.UIUtils && TestGeneration.UIUtils.showNotification) {
                    TestGeneration.UIUtils.showNotification(
                        'Error exporting test case: ' + (error.message || 'Unknown error'),
                        'error'
                    );
                } else {
                    alert('Error exporting test case: ' + (error.message || 'Unknown error'));
                }
            });
        } else if (TestGeneration.API && TestGeneration.API.post) {
            // Fallback to using post with expectBlob=true
            TestGeneration.API.post('/api/test-cases/generate-download', exportData, true)
                .then(function(blob) {
                    // Hide progress indicator
                    hideProgressIndicator();
                    
                    // Create download link
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.style.display = 'none';
                    a.href = url;
                    a.download = filename;
                    document.body.appendChild(a);
                    a.click();
                    
                    // Cleanup
                    setTimeout(function() {
                        document.body.removeChild(a);
                        window.URL.revokeObjectURL(url);
                    }, 100);
                    
                    // Show success notification
                    if (TestGeneration.UIUtils && TestGeneration.UIUtils.showNotification) {
                        TestGeneration.UIUtils.showNotification(
                            `Test case exported to ${format.toUpperCase()} successfully!`,
                            'success'
                        );
                    }
                })
                .catch(function(error) {
                    // Hide progress indicator
                    hideProgressIndicator();
                    
                    // Show error notification
                    console.error('Export error:', error);
                    if (TestGeneration.UIUtils && TestGeneration.UIUtils.showNotification) {
                        TestGeneration.UIUtils.showNotification(
                            'Error exporting test case: ' + (error.message || 'Unknown error'),
                            'error'
                        );
                    } else {
                        alert('Error exporting test case: ' + (error.message || 'Unknown error'));
                    }
                });
        } else {
            // Fallback to direct browser download if API service not available
            handleDirectDownload(format, generatedTestCaseData);
        }
    }
    
    /**
     * Handle direct file download without API service
     * @param {string} format - Export format (excel, word, pdf)
     * @param {Object} data - Test case data
     * @private
     */
    function handleDirectDownload(format, data) {
        // Create a form and post it to trigger a download from the server
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = '/api/test-cases/generate-download';
        form.target = '_blank'; // Open in new tab/window
        
        // Add CSRF token
        const csrfField = document.createElement('input');
        csrfField.type = 'hidden';
        csrfField.name = 'csrfmiddlewaretoken';
        csrfField.value = TestGeneration.UIUtils ? TestGeneration.UIUtils.getCSRFToken() : '';
        form.appendChild(csrfField);
        
        // Add data field
        const dataField = document.createElement('input');
        dataField.type = 'hidden';
        dataField.name = 'data';
        dataField.value = JSON.stringify({
            test_case: data.test_case,
            format: format,
            scenarios: data.scenario ? [data.scenario] : []
        });
        form.appendChild(dataField);
        
        // Add to document and submit
        document.body.appendChild(form);
        form.submit();
        
        // Clean up
        setTimeout(function() {
            document.body.removeChild(form);
            hideProgressIndicator();
            
            // Show success notification
            if (TestGeneration.UIUtils && TestGeneration.UIUtils.showNotification) {
                TestGeneration.UIUtils.showNotification(
                    `Test case export initiated. Check your downloads.`,
                    'success'
                );
            }
        }, 1000);
    }
    
    /**
     * Compare generated test cases with repository
     * @private
     */
    function compareWithRepository() {
        console.log('Comparing test cases with repository');
        
        // Check if we have test case data to compare
        if (!generatedTestCaseData || !generatedTestCaseData.test_case || !generatedTestCaseData.test_case.length) {
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
        const progressStatus = elements.progressArea.querySelector('.progress-status');
        if (progressStatus) {
            progressStatus.textContent = 'Comparing test case with repository...';
        }
        
        // Prepare request data
        const requestData = {
            testCase: generatedTestCaseData.test_case
        };
        
        // Add metadata if available
        if (generatedTestCaseData.test_case && generatedTestCaseData.test_case.length > 0) {
            const firstRow = generatedTestCaseData.test_case[0];
            requestData.metadata = {
                testCaseNumber: firstRow['TEST CASE NUMBER'] || '',
                testCaseName: firstRow['TEST CASE'] || '',
                subject: firstRow['SUBJECT'] || '',
                type: firstRow['TYPE'] || ''
            };
        }
        
        // Use the API service for repository comparison
        if (TestGeneration.API) {
            TestGeneration.API.post('/api/test-cases/compare-repository', requestData)
                .then(handleComparisonResponse)
                .catch(handleComparisonError);
        } else {
            console.error('API service not available');
            handleComparisonError(new Error('API service not available'));
        }
    }
    
    /**
     * Handle successful comparison response
     * @param {Object} response - API response
     * @private
     */
    function handleComparisonResponse(response) {
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
    }
    
    /**
     * Handle error in comparison
     * @param {Error} error - Error object
     * @private
     */
    function handleComparisonError(error) {
        // Hide progress indicator
        hideProgressIndicator();
        
        console.error('Error comparing test cases:', error);
        
        // Show error notification
        if (TestGeneration.UIUtils && TestGeneration.UIUtils.showNotification) {
            TestGeneration.UIUtils.showNotification(
                'Error comparing test cases: ' + (error.message || 'Unknown error'),
                'error'
            );
        } else {
            alert('Error comparing test cases: ' + (error.message || 'Unknown error'));
        }
    }
    
    /**
     * Display comparison results
     * @param {Object} data - Comparison results
     * @private
     */
    function displayComparisonResults(data) {
        console.log('Displaying comparison results:', data);
        
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
                                <!-- Comparison content will go here -->
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
                // Create summary section
                const summaryDiv = document.createElement('div');
                summaryDiv.className = 'comparison-summary mb-4';
                
                // Add match summary
                let matchCount = 0;
                let similarCount = 0;
                let uniqueCount = 0;
                
                if (data.exact_matches) matchCount = data.exact_matches.length;
                if (data.similar_matches) similarCount = data.similar_matches.length;
                if (data.no_match) uniqueCount = data.no_match ? 1 : 0;
                
                const totalMatches = matchCount + similarCount + uniqueCount;
                
                summaryDiv.innerHTML = `
                    <div class="alert ${matchCount > 0 ? 'alert-success' : 'alert-info'}">
                        <h6>Comparison Summary</h6>
                        <p>
                            <strong>${totalMatches}</strong> total results<br>
                            <strong>${matchCount}</strong> exact matches<br>
                            <strong>${similarCount}</strong> similar test cases<br>
                            <strong>${uniqueCount}</strong> unique (no match found)
                        </p>
                    </div>
                `;
                
                modalBody.appendChild(summaryDiv);
                
                // Display matches
                if (matchCount > 0) {
                    const matchesDiv = document.createElement('div');
                    matchesDiv.className = 'exact-matches mb-4';
                    matchesDiv.innerHTML = `<h6 class="text-success">Exact Matches</h6>`;
                    
                    // Create list of matches
                    const matchList = document.createElement('ul');
                    matchList.className = 'list-group';
                    
                    data.exact_matches.forEach(match => {
                        const listItem = document.createElement('li');
                        listItem.className = 'list-group-item';
                        
                        listItem.innerHTML = `
                            <div class="d-flex justify-content-between align-items-center">
                                <div>
                                    <strong>${match.test_case_id || 'Unknown ID'}</strong> - ${match.test_case_name || 'Unnamed Test Case'}
                                </div>
                                <div>
                                    <button class="btn btn-sm btn-outline-primary view-test-case-btn" 
                                            data-test-case-id="${match.test_case_id}">
                                        View
                                    </button>
                                </div>
                            </div>
                            <div class="small text-muted mt-1">
                                ${match.match_details || 'Exact match found in repository'}
                            </div>
                        `;
                        
                        matchList.appendChild(listItem);
                    });
                    
                    matchesDiv.appendChild(matchList);
                    modalBody.appendChild(matchesDiv);
                }
                
                // Display similar matches
                if (similarCount > 0) {
                    const similarDiv = document.createElement('div');
                    similarDiv.className = 'similar-matches mb-4';
                    similarDiv.innerHTML = `<h6 class="text-warning">Similar Test Cases</h6>`;
                    
                    // Create list of similar matches
                    const similarList = document.createElement('ul');
                    similarList.className = 'list-group';
                    
                    data.similar_matches.forEach(match => {
                        const listItem = document.createElement('li');
                        listItem.className = 'list-group-item';
                        
                        // Calculate similarity percentage if available
                        let similarityText = '';
                        if (match.similarity_score) {
                            const percent = Math.round(match.similarity_score * 100);
                            similarityText = ` - ${percent}% similar`;
                        }
                        
                        listItem.innerHTML = `
                            <div class="d-flex justify-content-between align-items-center">
                                <div>
                                    <strong>${match.test_case_id || 'Unknown ID'}</strong> - ${match.test_case_name || 'Unnamed Test Case'}${similarityText}
                                </div>
                                <div>
                                    <button class="btn btn-sm btn-outline-primary view-test-case-btn"
                                            data-test-case-id="${match.test_case_id}">
                                        View
                                    </button>
                                </div>
                            </div>
                            <div class="small text-muted mt-1">
                                ${match.match_details || 'Similar test case found in repository'}
                            </div>
                        `;
                        
                        similarList.appendChild(listItem);
                    });
                    
                    similarDiv.appendChild(similarList);
                    modalBody.appendChild(similarDiv);
                }
                
                // Display no match message
                if (uniqueCount > 0) {
                    const uniqueDiv = document.createElement('div');
                    uniqueDiv.className = 'no-match alert alert-info';
                    uniqueDiv.innerHTML = `
                        <h6>Unique Test Case</h6>
                        <p>No matching test cases found in the repository. This appears to be a new unique test case.</p>
                        <button class="btn btn-success btn-sm add-to-repo-btn">Add to Repository</button>
                    `;
                    
                    modalBody.appendChild(uniqueDiv);
                    
                    // Add event listener for "Add to Repository" button
                    const addToRepoBtn = uniqueDiv.querySelector('.add-to-repo-btn');
                    if (addToRepoBtn) {
                        addToRepoBtn.addEventListener('click', function() {
                            addToRepository();
                        });
                    }
                }
                
                // Add event listeners for view buttons
                const viewButtons = modalBody.querySelectorAll('.view-test-case-btn');
                viewButtons.forEach(button => {
                    button.addEventListener('click', function() {
                        const testCaseId = this.getAttribute('data-test-case-id');
                        viewTestCase(testCaseId);
                    });
                });
            }
            
            // Show modal using Bootstrap
            if (typeof bootstrap !== 'undefined' && bootstrap.Modal) {
                const modal = new bootstrap.Modal(modalElement);
                modal.show();
            } else {
                // Fallback if Bootstrap is not available
                console.error('Bootstrap Modal is not available. Make sure Bootstrap JS is loaded.');
                alert('Comparison complete. Found matches in repository.');
            }
        } catch (error) {
            console.error('Error displaying comparison results:', error);
            // Show simple alert as fallback
            alert('Comparison complete. Error displaying detailed results.');
        }
    }
    
    /**
     * View a test case from the repository
     * @param {string} testCaseId - Test case ID to view
     * @private
     */
    function viewTestCase(testCaseId) {
        console.log('Viewing test case:', testCaseId);
        
        // This would typically open a new page or modal with test case details
        // For now, we'll just simulate with an alert
        alert(`Viewing test case ${testCaseId} - This functionality would open the test case details.`);
        
        // In a real implementation, you might navigate to a test case view page
        // window.location.href = `/test-repository/test-cases/${testCaseId}`;
    }
    
    /**
     * Add the current test case to the repository
     * @private
     */
    function addToRepository() {
        console.log('Adding test case to repository');
        
        // Check if we have test case data
        if (!generatedTestCaseData) {
            if (TestGeneration.UIUtils && TestGeneration.UIUtils.showNotification) {
                TestGeneration.UIUtils.showNotification(
                    'No test case data available to add to repository.',
                    'warning'
                );
            } else {
                alert('No test case data available to add to repository.');
            }
            return;
        }
        
        // Show progress indicator
        showProgressIndicator();
        const progressStatus = elements.progressArea.querySelector('.progress-status');
        if (progressStatus) {
            progressStatus.textContent = 'Adding test case to repository...';
        }
        
        // Use the API service to add to repository
        if (TestGeneration.API) {
            TestGeneration.API.post('/api/test-cases', generatedTestCaseData)
                .then(function(response) {
                    // Hide progress indicator
                    hideProgressIndicator();
                    
                    if (response.status === 'success') {
                        // Show success notification
                        if (TestGeneration.UIUtils && TestGeneration.UIUtils.showNotification) {
                            TestGeneration.UIUtils.showNotification(
                                'Test case added to repository successfully!',
                                'success'
                            );
                        } else {
                            alert('Test case added to repository successfully!');
                        }
                        
                        // Close the modal if it's open
                        const modal = document.getElementById('comparisonResultsModal');
                        if (modal && typeof bootstrap !== 'undefined' && bootstrap.Modal) {
                            const modalInstance = bootstrap.Modal.getInstance(modal);
                            if (modalInstance) {
                                modalInstance.hide();
                            }
                        }
                    } else {
                        // Show error notification
                        if (TestGeneration.UIUtils && TestGeneration.UIUtils.showNotification) {
                            TestGeneration.UIUtils.showNotification(
                                'Error adding test case to repository: ' + (response.message || 'Unknown error'),
                                'error'
                            );
                        } else {
                            alert('Error adding test case to repository: ' + (response.message || 'Unknown error'));
                        }
                    }
                })
                .catch(function(error) {
                    // Hide progress indicator
                    hideProgressIndicator();
                    
                    // Show error notification
                    if (TestGeneration.UIUtils && TestGeneration.UIUtils.showNotification) {
                        TestGeneration.UIUtils.showNotification(
                            'Error adding test case to repository: ' + (error.message || 'Unknown error'),
                            'error'
                        );
                    } else {
                        alert('Error adding test case to repository: ' + (error.message || 'Unknown error'));
                    }
                });
        } else {
            // Handle case where API service is not available
            hideProgressIndicator();
            console.error('API service not available');
            alert('Cannot add to repository - API service not available');
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
        
        // Clear stored test case data
        generatedTestCaseData = null;
        
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
        // Adjust UI based on window size
        const isMobile = window.innerWidth < 768;
        
        // Adjust test case display for mobile if needed
        if (elements.testCasePreview && elements.testCasePreview.querySelector('table')) {
            const table = elements.testCasePreview.querySelector('table');
            
            if (isMobile) {
                table.classList.add('table-responsive');
            } else {
                table.classList.remove('table-responsive');
            }
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
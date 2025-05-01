/**
 * Test Generation & Refinement - Refine Test Cases Module
 * 
 * This module handles the functionality for reviewing and refining existing test cases.
 * It manages file uploads, AI analysis, comparison views, and refinement actions.
 */

// Ensure the TestGeneration namespace exists
const TestGeneration = TestGeneration || {};

/**
 * Refine module for test case refinement functionality
 */
TestGeneration.Refine = (function() {
    // Private variables
    let initialized = false;
    let currentFile = null;
    let analysisResults = null;
    let hasChanges = false;
    
    // Cache DOM elements for better performance
    const elements = {
        form: null,
        dropArea: null,
        fileInput: null,
        filePreview: null,
        fileName: null,
        fileSize: null,
        removeFileBtn: null,
        analyzeBtn: null,
        cancelBtn: null,
        progressArea: null,
        comparisonArea: null,
        originalTestCase: null,
        refinedTestCase: null,
        aiSuggestions: null,
        acceptBtn: null,
        notifyBtn: null,
        markObsoleteBtn: null,
        discardBtn: null
    };
    
    /**
     * Initialize the Refine Test Cases module
     * @public
     */
    function initialize() {
        if (initialized && TestGeneration.Main.getActiveTab() === 'refine') return;
        
        console.log('Initializing Refine Test Cases module...');
        
        // Cache DOM elements
        cacheElements();
        
        // Set up event listeners
        setupEventListeners();
        
        // Set initialization flag
        initialized = true;
        
        console.log('Refine Test Cases module initialized');
    }
    
    /**
     * Cache DOM elements for better performance
     * @private
     */
    function cacheElements() {
        elements.form = document.getElementById('refineTestCaseForm');
        elements.dropArea = document.getElementById('refinement-drop-area');
        elements.fileInput = document.getElementById('test_case_file');
        elements.filePreview = document.getElementById('refinement-file-preview');
        elements.fileName = document.getElementById('refinement-file-name');
        elements.fileSize = document.getElementById('refinement-file-size');
        elements.removeFileBtn = document.getElementById('refinement-remove-file');
        elements.analyzeBtn = document.getElementById('analyzeTestCaseBtn');
        elements.cancelBtn = document.getElementById('cancelRefineBtn');
        elements.progressArea = document.getElementById('refinementProgress');
        elements.comparisonArea = document.getElementById('refinementComparison');
        elements.originalTestCase = document.getElementById('originalTestCase');
        elements.refinedTestCase = document.getElementById('refinedTestCase');
        elements.aiSuggestions = document.getElementById('aiSuggestions');
        elements.acceptBtn = document.getElementById('acceptSuggestionsBtn');
        elements.notifyBtn = document.getElementById('notifyOwnerBtn');
        elements.markObsoleteBtn = document.getElementById('markObsoleteBtn');
        elements.discardBtn = document.getElementById('discardSuggestionsBtn');
    }
    
    /**
     * Set up event listeners for the Refine module
     * @private
     */
    function setupEventListeners() {
        // File drop area
        if (elements.dropArea && elements.fileInput) {
            // Drag over
            elements.dropArea.addEventListener('dragover', function(e) {
                e.preventDefault();
                e.stopPropagation();
                this.classList.add('dragover');
            });
            
            // Drag leave
            elements.dropArea.addEventListener('dragleave', function(e) {
                e.preventDefault();
                e.stopPropagation();
                this.classList.remove('dragover');
            });
            
            // Drop
            elements.dropArea.addEventListener('drop', function(e) {
                e.preventDefault();
                e.stopPropagation();
                this.classList.remove('dragover');
                
                if (e.dataTransfer.files.length > 0) {
                    const file = e.dataTransfer.files[0];
                    if (isValidFileType(file)) {
                        elements.fileInput.files = e.dataTransfer.files;
                        updateFilePreview(file);
                    } else {
                        TestGeneration.UIUtils.showNotification(
                            'Invalid file type. Please upload an Excel or Word file.',
                            'error'
                        );
                    }
                }
            });
            
            // Click to browse
            elements.dropArea.addEventListener('click', function() {
                elements.fileInput.click();
            });
            
            // File input change
            elements.fileInput.addEventListener('change', function() {
                if (this.files.length > 0) {
                    const file = this.files[0];
                    if (isValidFileType(file)) {
                        updateFilePreview(file);
                    } else {
                        TestGeneration.UIUtils.showNotification(
                            'Invalid file type. Please upload an Excel or Word file.',
                            'error'
                        );
                        this.value = '';
                    }
                }
            });
        }
        
        // Remove file button
        if (elements.removeFileBtn) {
            elements.removeFileBtn.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                removeFile();
            });
        }
        
        // Analyze button
        if (elements.analyzeBtn) {
            elements.analyzeBtn.addEventListener('click', handleAnalyzeClick);
        }
        
        // Cancel button
        if (elements.cancelBtn) {
            elements.cancelBtn.addEventListener('click', resetForm);
        }
        
        // Action buttons
        if (elements.acceptBtn) {
            elements.acceptBtn.addEventListener('click', acceptSuggestions);
        }
        
        if (elements.notifyBtn) {
            elements.notifyBtn.addEventListener('click', notifyOwner);
        }
        
        if (elements.markObsoleteBtn) {
            elements.markObsoleteBtn.addEventListener('click', markAsObsolete);
        }
        
        if (elements.discardBtn) {
            elements.discardBtn.addEventListener('click', discardSuggestions);
        }
    }
    
    /**
     * Check if the file type is valid (Excel or Word)
     * @param {File} file - The file to check
     * @returns {boolean} True if the file type is valid
     * @private
     */
    function isValidFileType(file) {
        const validTypes = [
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        ];
        
        return validTypes.includes(file.type) || 
               file.name.endsWith('.xls') || 
               file.name.endsWith('.xlsx') || 
               file.name.endsWith('.doc') || 
               file.name.endsWith('.docx');
    }
    
    /**
     * Update file preview when a file is selected
     * @param {File} file - The selected file
     * @private
     */
    function updateFilePreview(file) {
        if (!file || !elements.filePreview || !elements.fileName || !elements.fileSize) return;
        
        // Store the current file
        currentFile = file;
        
        // Update file information
        elements.fileName.textContent = file.name;
        elements.fileSize.textContent = TestGeneration.UIUtils.formatFileSize(file.size);
        
        // Show preview, hide drop area
        elements.filePreview.classList.remove('hidden');
        elements.dropArea.classList.add('hidden');
        
        // Enable analyze button
        if (elements.analyzeBtn) {
            elements.analyzeBtn.disabled = false;
        }
        
        // Set changes flag
        hasChanges = true;
    }
    
    /**
     * Remove the selected file
     * @private
     */
    function removeFile() {
        if (elements.fileInput) {
            elements.fileInput.value = '';
        }
        
        currentFile = null;
        
        if (elements.filePreview && elements.dropArea) {
            elements.filePreview.classList.add('hidden');
            elements.dropArea.classList.remove('hidden');
        }
        
        // Disable analyze button
        if (elements.analyzeBtn) {
            elements.analyzeBtn.disabled = true;
        }
        
        // Set changes flag
        hasChanges = false;
    }
    
    /**
     * Handle click on the Analyze button
     * @private
     */
    function handleAnalyzeClick() {
        // Validate that a file is selected
        if (!currentFile) {
            TestGeneration.UIUtils.showNotification(
                'Please select a test case file first.',
                'warning'
            );
            return;
        }
        
        // Show progress indicator
        TestGeneration.Main.showLoadingSpinner('refinement', 'Analyzing test case... This may take a few moments.');
        
        // Hide comparison area if previously shown
        if (elements.comparisonArea) {
            elements.comparisonArea.classList.add('hidden');
        }
        
        // Call API to analyze the test case
        analyzeTestCase(currentFile);
    }
    
    /**
     * Analyze the test case file
     * @param {File} file - The test case file to analyze
     * @private
     */
    function analyzeTestCase(file) {
        // Prepare form data
        const formData = new FormData();
        formData.append('test_case_file', file);
        
        // Call API
        TestGeneration.API.postWithFormData('/api/test-cases/refine', formData)
            .then(response => {
                // Hide progress indicator
                TestGeneration.Main.hideLoadingSpinner('refinement');
                
                // Process response
                if (response.status === 'success') {
                    // Store analysis results
                    analysisResults = response.data;
                    
                    // Show comparison area
                    if (elements.comparisonArea) {
                        elements.comparisonArea.classList.remove('hidden');
                    }
                    
                    // Display results
                    displayAnalysisResults(response.data);
                    
                    // Reset changes flag
                    hasChanges = false;
                    
                    // Show success notification
                    TestGeneration.UIUtils.showNotification(
                        'Test case analyzed successfully!',
                        'success'
                    );
                } else {
                    // Show error notification
                    TestGeneration.UIUtils.showNotification(
                        'Failed to analyze test case: ' + (response.message || 'Unknown error'),
                        'error'
                    );
                }
            })
            .catch(error => {
                console.error('Error analyzing test case:', error);
                
                // Hide progress indicator
                TestGeneration.Main.hideLoadingSpinner('refinement');
                
                // Show error notification
                TestGeneration.UIUtils.showNotification(
                    'Error analyzing test case: ' + (error.message || 'Unknown error'),
                    'error'
                );
            });
    }
    
    /**
     * Display analysis results in the comparison view
     * @param {Object} data - Analysis data from API
     * @private
     */
    function displayAnalysisResults(data) {
        // Display original test case
        displayOriginalTestCase(data.test_case_info);
        
        // Display refined test case with suggestions
        displayRefinedTestCase(data);
        
        // Display AI suggestions
        displayAISuggestions(data);
    }
    
    /**
     * Display original test case
     * @param {Object} testCaseInfo - Original test case information
     * @private
     */
    function displayOriginalTestCase(testCaseInfo) {
        if (!elements.originalTestCase) return;
        
        // Clear previous content
        elements.originalTestCase.innerHTML = '';
        
        // Create test case information
        const infoDiv = document.createElement('div');
        infoDiv.className = 'test-case-info mb-3';
        
        // Test case title
        if (testCaseInfo.title) {
            const title = document.createElement('h6');
            title.className = 'fw-bold';
            title.textContent = testCaseInfo.title;
            infoDiv.appendChild(title);
        }
        
        // Test case metadata
        const metadataList = document.createElement('ul');
        metadataList.className = 'list-unstyled small';
        
        // Add ID
        if (testCaseInfo.id) {
            const idItem = document.createElement('li');
            idItem.innerHTML = '<strong>ID:</strong> ' + testCaseInfo.id;
            metadataList.appendChild(idItem);
        }
        
        // Add owner
        if (testCaseInfo.owner) {
            const ownerItem = document.createElement('li');
            ownerItem.innerHTML = '<strong>Owner:</strong> ' + testCaseInfo.owner;
            metadataList.appendChild(ownerItem);
        }
        
        // Add status
        if (testCaseInfo.status) {
            const statusItem = document.createElement('li');
            statusItem.innerHTML = '<strong>Status:</strong> ' + testCaseInfo.status;
            metadataList.appendChild(statusItem);
        }
        
        // Add last updated
        if (testCaseInfo.last_updated) {
            const updatedItem = document.createElement('li');
            updatedItem.innerHTML = '<strong>Last Updated:</strong> ' + 
                TestGeneration.UIUtils.formatDate(new Date(testCaseInfo.last_updated));
            metadataList.appendChild(updatedItem);
        }
        
        infoDiv.appendChild(metadataList);
        elements.originalTestCase.appendChild(infoDiv);
        
        // Create test steps table
        if (testCaseInfo.steps && testCaseInfo.steps.length > 0) {
            const stepsTable = document.createElement('table');
            stepsTable.className = 'table table-sm table-bordered';
            
            // Create header
            const thead = document.createElement('thead');
            const headerRow = document.createElement('tr');
            
            const headers = ['Step #', 'Description', 'Expected Result'];
            headers.forEach(header => {
                const th = document.createElement('th');
                th.textContent = header;
                headerRow.appendChild(th);
            });
            
            thead.appendChild(headerRow);
            stepsTable.appendChild(thead);
            
            // Create body
            const tbody = document.createElement('tbody');
            
            testCaseInfo.steps.forEach((step, index) => {
                const row = document.createElement('tr');
                
                // Step number
                const stepNumCell = document.createElement('td');
                stepNumCell.textContent = (index + 1).toString();
                stepNumCell.style.width = '60px';
                row.appendChild(stepNumCell);
                
                // Description
                const descCell = document.createElement('td');
                descCell.textContent = step.description || '';
                row.appendChild(descCell);
                
                // Expected result
                const resultCell = document.createElement('td');
                resultCell.textContent = step.expected_result || '';
                row.appendChild(resultCell);
                
                tbody.appendChild(row);
            });
            
            stepsTable.appendChild(tbody);
            elements.originalTestCase.appendChild(stepsTable);
        } else {
            // No steps available
            const noStepsAlert = document.createElement('div');
            noStepsAlert.className = 'alert alert-warning';
            noStepsAlert.textContent = 'No test steps found in the original test case.';
            elements.originalTestCase.appendChild(noStepsAlert);
        }
    }
    
    /**
     * Display refined test case with suggestions
     * @param {Object} data - Analysis data from API
     * @private
     */
    function displayRefinedTestCase(data) {
        if (!elements.refinedTestCase) return;
        
        // Clear previous content
        elements.refinedTestCase.innerHTML = '';
        
        // Create test case information (same as original)
        const infoDiv = document.createElement('div');
        infoDiv.className = 'test-case-info mb-3';
        
        // Test case title
        if (data.test_case_info.title) {
            const title = document.createElement('h6');
            title.className = 'fw-bold';
            title.textContent = data.test_case_info.title;
            infoDiv.appendChild(title);
        }
        
        // Test case metadata
        const metadataList = document.createElement('ul');
        metadataList.className = 'list-unstyled small';
        
        // Add ID
        if (data.test_case_info.id) {
            const idItem = document.createElement('li');
            idItem.innerHTML = '<strong>ID:</strong> ' + data.test_case_info.id;
            metadataList.appendChild(idItem);
        }
        
        // Add owner
        if (data.test_case_info.owner) {
            const ownerItem = document.createElement('li');
            ownerItem.innerHTML = '<strong>Owner:</strong> ' + data.test_case_info.owner;
            metadataList.appendChild(ownerItem);
        }
        
        // Add status
        if (data.test_case_info.status) {
            const statusItem = document.createElement('li');
            statusItem.innerHTML = '<strong>Status:</strong> ' + data.test_case_info.status;
            metadataList.appendChild(statusItem);
        }
        
        infoDiv.appendChild(metadataList);
        elements.refinedTestCase.appendChild(infoDiv);
        
        // Check if we have suggestions
        const hasSuggestions = data.step_suggestions && data.step_suggestions.length > 0;
        const hasVariations = data.missing_test_variations && data.missing_test_variations.length > 0;
        
        if (!hasSuggestions && !hasVariations) {
            // No suggestions available
            const noSuggestionsAlert = document.createElement('div');
            noSuggestionsAlert.className = 'alert alert-info';
            noSuggestionsAlert.textContent = 'No refinement suggestions found. The test case appears to be well-defined.';
            elements.refinedTestCase.appendChild(noSuggestionsAlert);
            return;
        }
        
        // Create test steps table with suggestions
        if (data.test_case_info.steps && data.test_case_info.steps.length > 0) {
            const stepsTable = document.createElement('table');
            stepsTable.className = 'table table-sm table-bordered';
            
            // Create header
            const thead = document.createElement('thead');
            const headerRow = document.createElement('tr');
            
            const headers = ['Step #', 'Description', 'Expected Result', 'Suggested Changes'];
            headers.forEach(header => {
                const th = document.createElement('th');
                th.textContent = header;
                headerRow.appendChild(th);
            });
            
            thead.appendChild(headerRow);
            stepsTable.appendChild(thead);
            
            // Create body
            const tbody = document.createElement('tbody');
            
            // Process existing steps with suggestions
            data.test_case_info.steps.forEach((step, index) => {
                const stepNumber = index + 1;
                const row = document.createElement('tr');
                
                // Find suggestions for this step
                const stepSuggestion = data.step_suggestions.find(s => 
                    s.step_number === stepNumber && !s.is_new_step
                );
                
                const hasChanges = !!stepSuggestion;
                
                // Step number
                const stepNumCell = document.createElement('td');
                stepNumCell.textContent = stepNumber.toString();
                stepNumCell.style.width = '60px';
                row.appendChild(stepNumCell);
                
                // Description
                const descCell = document.createElement('td');
                if (stepSuggestion && stepSuggestion.suggested_description) {
                    descCell.innerHTML = `
                        <div class="text-decoration-line-through text-muted mb-2">${step.description || ''}</div>
                        <div class="text-success">${stepSuggestion.suggested_description}</div>
                    `;
                } else {
                    descCell.textContent = step.description || '';
                }
                row.appendChild(descCell);
                
                // Expected result
                const resultCell = document.createElement('td');
                if (stepSuggestion && stepSuggestion.suggested_expected_result) {
                    resultCell.innerHTML = `
                        <div class="text-decoration-line-through text-muted mb-2">${step.expected_result || ''}</div>
                        <div class="text-success">${stepSuggestion.suggested_expected_result}</div>
                    `;
                } else {
                    resultCell.textContent = step.expected_result || '';
                }
                row.appendChild(resultCell);
                
                // Suggested changes
                const suggestionsCell = document.createElement('td');
                if (stepSuggestion && stepSuggestion.explanation) {
                    suggestionsCell.innerHTML = stepSuggestion.explanation;
                } else {
                    suggestionsCell.textContent = 'No changes suggested';
                    suggestionsCell.className = 'text-muted';
                }
                row.appendChild(suggestionsCell);
                
                // Highlight row if it has changes
                if (hasChanges) {
                    row.className = 'table-warning';
                }
                
                tbody.appendChild(row);
            });
            
            // Add suggested new steps
            const newStepSuggestions = data.step_suggestions.filter(s => s.is_new_step);
            if (newStepSuggestions.length > 0) {
                newStepSuggestions.forEach(suggestion => {
                    const row = document.createElement('tr');
                    row.className = 'table-success';
                    
                    // Step number / position
                    const stepNumCell = document.createElement('td');
                    if (suggestion.suggested_position) {
                        stepNumCell.textContent = suggestion.suggested_position;
                        stepNumCell.innerHTML += ' <span class="badge bg-success">New</span>';
                    } else {
                        stepNumCell.innerHTML = '<span class="badge bg-success">New</span>';
                    }
                    row.appendChild(stepNumCell);
                    
                    // Description
                    const descCell = document.createElement('td');
                    descCell.textContent = suggestion.suggested_description || '';
                    descCell.className = 'text-success';
                    row.appendChild(descCell);
                    
                    // Expected result
                    const resultCell = document.createElement('td');
                    resultCell.textContent = suggestion.suggested_expected_result || '';
                    resultCell.className = 'text-success';
                    row.appendChild(resultCell);
                    
                    // Suggested changes
                    const suggestionsCell = document.createElement('td');
                    suggestionsCell.innerHTML = '<strong>Suggested new step:</strong> ' + 
                        (suggestion.explanation || 'Add this step to improve test coverage.');
                    row.appendChild(suggestionsCell);
                    
                    tbody.appendChild(row);
                });
            }
            
            stepsTable.appendChild(tbody);
            elements.refinedTestCase.appendChild(stepsTable);
            
            // Add missing test variations if any
            if (hasVariations) {
                const variationsDiv = document.createElement('div');
                variationsDiv.className = 'missing-variations mt-4';
                
                const variationsTitle = document.createElement('h6');
                variationsTitle.className = 'text-primary mb-3';
                variationsTitle.innerHTML = '<i class="fas fa-code-branch me-2"></i>Suggested Test Variations';
                variationsDiv.appendChild(variationsTitle);
                
                const variationsList = document.createElement('ul');
                variationsList.className = 'list-group';
                
                data.missing_test_variations.forEach(variation => {
                    const variationItem = document.createElement('li');
                    variationItem.className = 'list-group-item';
                    
                    const variationTitle = document.createElement('div');
                    variationTitle.className = 'fw-bold';
                    variationTitle.textContent = variation.title || 'Additional Test Variation';
                    
                    const variationDesc = document.createElement('div');
                    variationDesc.textContent = variation.description || '';
                    
                    variationItem.appendChild(variationTitle);
                    variationItem.appendChild(variationDesc);
                    variationsList.appendChild(variationItem);
                });
                
                variationsDiv.appendChild(variationsList);
                elements.refinedTestCase.appendChild(variationsDiv);
            }
        }
    }
    
    /**
     * Display AI suggestions and analysis
     * @param {Object} data - Analysis data from API
     * @private
     */
    function displayAISuggestions(data) {
        if (!elements.aiSuggestions) return;
        
        // Clear previous content
        elements.aiSuggestions.innerHTML = '';
        
        // Summary section
        if (data.summary) {
            const summaryDiv = document.createElement('div');
            summaryDiv.className = 'suggestion-summary mb-4';
            
            const summaryTitle = document.createElement('h6');
            summaryTitle.className = 'fw-bold';
            summaryTitle.textContent = 'Summary of Analysis';
            summaryDiv.appendChild(summaryTitle);
            
            const summaryContent = document.createElement('p');
            summaryContent.textContent = data.summary;
            summaryDiv.appendChild(summaryContent);
            
            elements.aiSuggestions.appendChild(summaryDiv);
        }
        
        // General suggestions
        if (data.general_suggestions && data.general_suggestions.length > 0) {
            const generalSuggestionsDiv = document.createElement('div');
            generalSuggestionsDiv.className = 'general-suggestions mb-4';
            
            const suggestionsTitle = document.createElement('h6');
            suggestionsTitle.className = 'fw-bold';
            suggestionsTitle.textContent = 'General Improvement Suggestions';
            generalSuggestionsDiv.appendChild(suggestionsTitle);
            
            const suggestionsList = document.createElement('ul');
            suggestionsList.className = 'list-group';
            
            data.general_suggestions.forEach(suggestion => {
                const suggestionItem = document.createElement('li');
                suggestionItem.className = 'list-group-item';
                
                if (typeof suggestion === 'string') {
                    suggestionItem.textContent = suggestion;
                } else if (suggestion.title && suggestion.description) {
                    const suggestionTitle = document.createElement('div');
                    suggestionTitle.className = 'fw-bold';
                    suggestionTitle.textContent = suggestion.title;
                    
                    const suggestionDesc = document.createElement('div');
                    suggestionDesc.textContent = suggestion.description;
                    
                    suggestionItem.appendChild(suggestionTitle);
                    suggestionItem.appendChild(suggestionDesc);
                }
                
                suggestionsList.appendChild(suggestionItem);
            });
            
            generalSuggestionsDiv.appendChild(suggestionsList);
            elements.aiSuggestions.appendChild(generalSuggestionsDiv);
        }
        
        // Recommendation
        const recommendationDiv = document.createElement('div');
        recommendationDiv.className = 'recommendation mt-3';
        
        // Determine recommendation based on suggestions
        let recommendation = '';
        let recommendationClass = '';
        
        const hasStepChanges = data.step_suggestions && 
            data.step_suggestions.some(s => !s.is_new_step);
        const hasNewSteps = data.step_suggestions && 
            data.step_suggestions.some(s => s.is_new_step);
        const hasVariations = data.missing_test_variations && 
            data.missing_test_variations.length > 0;
        
        if (hasStepChanges || hasNewSteps) {
            recommendation = 'Based on the analysis, we recommend accepting the suggested changes to improve this test case.';
            recommendationClass = 'text-success';
        } else if (hasVariations) {
            recommendation = 'The test case is good, but consider creating additional test variations for better coverage.';
            recommendationClass = 'text-info';
        } else {
            recommendation = 'This test case appears to be well-defined. No significant changes are needed.';
            recommendationClass = 'text-primary';
        }
        
        recommendationDiv.innerHTML = `<p class="${recommendationClass}"><strong>AI Recommendation:</strong> ${recommendation}</p>`;
        elements.aiSuggestions.appendChild(recommendationDiv);
    }
    
    /**
     * Accept the suggested refinements
     * @private
     */
    function acceptSuggestions() {
        if (!analysisResults) {
            TestGeneration.UIUtils.showNotification(
                'No analysis results available.',
                'error'
            );
            return;
        }
        
        // Show confirmation dialog
        if (!confirm('Are you sure you want to accept these suggestions and update the repository?')) {
            return;
        }
        
        // Show progress indicator
        TestGeneration.Main.showLoadingSpinner('refinement', 'Applying refinements and updating repository...');
        
        // Prepare request data
        const requestData = {
            test_case_id: analysisResults.test_case_info.id,
            refinements: {
                step_suggestions: analysisResults.step_suggestions,
                general_suggestions: analysisResults.general_suggestions,
                missing_test_variations: analysisResults.missing_test_variations
            },
            comment: 'AI-suggested refinements applied via Test Generation & Refinement module'
        };
        
        // Call API
        TestGeneration.API.post('/api/test-cases/apply-refinements', requestData)
            .then(response => {
                // Hide progress indicator
                TestGeneration.Main.hideLoadingSpinner('refinement');
                
                // Process response
                if (response.status === 'success') {
                    // Show success notification
                    TestGeneration.UIUtils.showNotification(
                        'Refinements applied and repository updated successfully!',
                        'success'
                    );
                    
                    // Redirect to the test case detail view
                    setTimeout(() => {
                        window.location.href = '/test-repository/test-cases/' + analysisResults.test_case_info.id;
                    }, 1500);
                } else {
                    // Show error notification
                    TestGeneration.UIUtils.showNotification(
                        'Failed to apply refinements: ' + (response.message || 'Unknown error'),
                        'error'
                    );
                }
            })
            .catch(error => {
                console.error('Error applying refinements:', error);
                
                // Hide progress indicator
                TestGeneration.Main.hideLoadingSpinner('refinement');
                
                // Show error notification
                TestGeneration.UIUtils.showNotification(
                    'Error applying refinements: ' + (error.message || 'Unknown error'),
                    'error'
                );
            });
    }
    
    /**
     * Notify the test case owner about suggestions
     * @private
     */
    function notifyOwner() {
        if (!analysisResults || !analysisResults.test_case_info) {
            TestGeneration.UIUtils.showNotification(
                'No analysis results available.',
                'error'
            );
            return;
        }
        // Prepare request data
       const requestData = {
        test_case_id: analysisResults.test_case_info.id,
        notification_type: 'suggestion',
        message: 'AI has suggested refinements for your test case.',
        data: {
            summary: analysisResults.summary,
            step_suggestions_count: analysisResults.step_suggestions ? analysisResults.step_suggestions.length : 0,
            variation_suggestions_count: analysisResults.missing_test_variations ? analysisResults.missing_test_variations.length : 0
        }
    };
    
    // Show progress indicator
    TestGeneration.Main.showLoadingSpinner('refinement', 'Notifying test case owner...');
    
    // Call API
    TestGeneration.API.post('/api/test-cases/notify-owner', requestData)
        .then(response => {
            // Hide progress indicator
            TestGeneration.Main.hideLoadingSpinner('refinement');
            
            // Process response
            if (response.status === 'success') {
                // Show success notification
                TestGeneration.UIUtils.showNotification(
                    'Owner notified successfully!',
                    'success'
                );
            } else {
                // Show error notification
                TestGeneration.UIUtils.showNotification(
                    'Failed to notify owner: ' + (response.message || 'Unknown error'),
                    'error'
                );
            }
        })
        .catch(error => {
            console.error('Error notifying owner:', error);
            
            // Hide progress indicator
            TestGeneration.Main.hideLoadingSpinner('refinement');
            
            // Show error notification
            TestGeneration.UIUtils.showNotification(
                'Error notifying owner: ' + (error.message || 'Unknown error'),
                'error'
            );
        });
}

/**
 * Mark the test case as obsolete
 * @private
 */
function markAsObsolete() {
    if (!analysisResults || !analysisResults.test_case_info) {
        TestGeneration.UIUtils.showNotification(
            'No analysis results available.',
            'error'
        );
        return;
    }
    
    // Show confirmation dialog
    if (!confirm('Are you sure you want to mark this test case as obsolete? This will notify the owner and suggest manual review.')) {
        return;
    }
    
    // Show progress indicator
    TestGeneration.Main.showLoadingSpinner('refinement', 'Marking test case as obsolete...');
    
    // Prepare request data
    const requestData = {
        test_case_id: analysisResults.test_case_info.id,
        status: 'Obsolete',
        comment: 'Marked as obsolete via AI analysis in Test Generation & Refinement module'
    };
    
    // Call API
    TestGeneration.API.post('/api/test-cases/' + analysisResults.test_case_info.id + '/status', requestData)
        .then(response => {
            // Hide progress indicator
            TestGeneration.Main.hideLoadingSpinner('refinement');
            
            // Process response
            if (response.status === 'success') {
                // Show success notification
                TestGeneration.UIUtils.showNotification(
                    'Test case marked as obsolete. Owner has been notified.',
                    'success'
                );
                
                // Redirect to the test case repository
                setTimeout(() => {
                    window.location.href = '/test-repository';
                }, 1500);
            } else {
                // Show error notification
                TestGeneration.UIUtils.showNotification(
                    'Failed to mark as obsolete: ' + (response.message || 'Unknown error'),
                    'error'
                );
            }
        })
        .catch(error => {
            console.error('Error marking as obsolete:', error);
            
            // Hide progress indicator
            TestGeneration.Main.hideLoadingSpinner('refinement');
            
            // Show error notification
            TestGeneration.UIUtils.showNotification(
                'Error marking as obsolete: ' + (error.message || 'Unknown error'),
                'error'
            );
        });
}

/**
 * Discard the suggestions and reset the form
 * @private
 */
function discardSuggestions() {
    // Show confirmation dialog if there are changes
    if (analysisResults && !confirm('Are you sure you want to discard these suggestions?')) {
        return;
    }
    
    // Reset the form
    resetForm();
    
    // Show notification
    TestGeneration.UIUtils.showNotification(
        'Suggestions discarded.',
        'info'
    );
}

/**
 * Reset the refine form
 * @public
 */
function resetForm() {
    // Reset form elements
    if (elements.form) {
        elements.form.reset();
    }
    
    // Hide comparison area
    if (elements.comparisonArea) {
        elements.comparisonArea.classList.add('hidden');
    }
    
    // Remove file
    removeFile();
    
    // Clear analysis results
    analysisResults = null;
    
    // Reset changes flag
    hasChanges = false;
}

/**
 * Handle window resize event
 * @public
 */
function handleResize() {
    // Any resize-specific UI adjustments can be placed here
    const isMobile = window.innerWidth < 768;
    
    // Adjust comparison view for mobile
    if (elements.originalTestCase && elements.refinedTestCase) {
        if (isMobile) {
            elements.originalTestCase.parentElement.classList.remove('col-md-6');
            elements.refinedTestCase.parentElement.classList.remove('col-md-6');
        } else {
            elements.originalTestCase.parentElement.classList.add('col-md-6');
            elements.refinedTestCase.parentElement.classList.add('col-md-6');
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
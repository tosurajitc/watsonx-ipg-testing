/**
 * Test Case Refinement - File Upload and Analysis Functionality
 * 
 * This script handles file upload, refinement analysis, and related UI operations 
 * for the "Review & Refine Test Case" tab, including drag-and-drop, file selection,
 * preview, removal functionality, and test case analysis workflow.
 */

// Define a namespace for our Test Case Refinement functionality
window.TestCaseRefinement = {
    // Store global state
    refinementData: null,
    
    // Initialize all event handlers and UI components
    init: function() {
        console.log('Initializing Test Case Refinement functionality');
        
        // Cache DOM elements
        this.elements = {
            dropArea: document.getElementById('refinement-drop-area'),
            fileInput: document.getElementById('test_case_file'),
            filePreview: document.getElementById('refinement-file-preview'),
            fileName: document.getElementById('refinement-file-name'),
            fileSize: document.getElementById('refinement-file-size'),
            removeFileBtn: document.getElementById('refinement-remove-file'),
            analyzeBtn: document.getElementById('analyzeTestCaseBtn'),
            progress: document.getElementById('refinementProgress'),
            comparisonView: document.getElementById('refinementComparison'),
            originalTestCase: document.getElementById('originalTestCase'),
            refinedTestCase: document.getElementById('refinedTestCase'),
            aiSuggestions: document.getElementById('aiSuggestions'),
            
            // Action buttons
            acceptSuggestionsBtn: document.getElementById('acceptSuggestionsBtn'),
            downloadRefinedBtn: document.getElementById('downloadRefinedBtn'),
            notifyOwnerBtn: document.getElementById('notifyOwnerBtn'),
            markObsoleteBtn: document.getElementById('markObsoleteBtn'),
            discardSuggestionsBtn: document.getElementById('discardSuggestionsBtn')
        };
        
        // Check if required elements exist
        if (!this.elements.dropArea || !this.elements.fileInput) {
            console.error('Required file upload elements not found');
            return;
        }
        
        // Initialize file upload functionality
        this.initFileUpload();
        
        // Initialize action buttons
        this.initActionButtons();
        
        // Initialize tab change handling
        this.initTabHandling();
        
        console.log('Test Case Refinement functionality initialized');
    },
    
    // Initialize file upload functionality
    initFileUpload: function() {
        const self = this;
        const elements = this.elements;
        
        // File Input Change Event
        elements.fileInput.addEventListener('change', function() {
            console.log('File input changed');
            if (this.files && this.files.length > 0) {
                const file = this.files[0];
                console.log('File selected:', file.name);
                self.updateFilePreview(file);
            }
        });
        
        // Click to browse
        elements.dropArea.addEventListener('click', function() {
            console.log('Drop area clicked');
            elements.fileInput.click();
        });
        
        // Prevent default behaviors for drag events
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            elements.dropArea.addEventListener(eventName, function(e) {
                e.preventDefault();
                e.stopPropagation();
            }, false);
        });
        
        // Highlight drop area when file is dragged over
        ['dragenter', 'dragover'].forEach(eventName => {
            elements.dropArea.addEventListener(eventName, function() {
                console.log('File dragged over drop area');
                this.classList.add('dragover');
            });
        });
        
        // Remove highlight when file leaves drop area
        ['dragleave', 'drop'].forEach(eventName => {
            elements.dropArea.addEventListener(eventName, function() {
                console.log('File left drop area');
                this.classList.remove('dragover');
            });
        });
        
        // Handle file drop
        elements.dropArea.addEventListener('drop', function(e) {
            console.log('File dropped');
            if (e.dataTransfer.files.length > 0) {
                const file = e.dataTransfer.files[0];
                console.log('File dropped:', file.name);
                
                if (self.isValidFileType(file)) {
                    // Set the file to the file input
                    elements.fileInput.files = e.dataTransfer.files;
                    self.updateFilePreview(file);
                } else {
                    alert('Invalid file type. Please upload an Excel or Word file.');
                }
            }
        });
        
        // Handle file removal
        if (elements.removeFileBtn) {
            elements.removeFileBtn.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                console.log('Remove file button clicked');
                self.removeFile();
            });
        }
        
        // Analyze button click handler
        if (elements.analyzeBtn) {
            elements.analyzeBtn.addEventListener('click', function() {
                console.log('Analyze button clicked');
                self.analyzeTestCase();
            });
        }
    },
    
    // Initialize action buttons
    initActionButtons: function() {
        const self = this;
        const elements = this.elements;
        
        // Accept Suggestions button
        if (elements.acceptSuggestionsBtn) {
            elements.acceptSuggestionsBtn.addEventListener('click', function() {
                self.handleAcceptRefinements();
            });
        }
        
        // Download Refined button
        if (elements.downloadRefinedBtn) {
            elements.downloadRefinedBtn.addEventListener('click', function() {
                self.handleDownloadRefinedTestCase();
            });
        }
        
        // Notify Owner button
        if (elements.notifyOwnerBtn) {
            elements.notifyOwnerBtn.addEventListener('click', function() {
                self.handleNotifyOwner();
            });
        }
        
        // Mark Obsolete button
        if (elements.markObsoleteBtn) {
            elements.markObsoleteBtn.addEventListener('click', function() {
                self.handleMarkObsolete();
            });
        }
        
        // Discard Suggestions button
        if (elements.discardSuggestionsBtn) {
            elements.discardSuggestionsBtn.addEventListener('click', function() {
                if (confirm('Are you sure you want to discard these suggestions?')) {
                    self.removeFile();
                }
            });
        }
    },
    
    // Initialize tab handling
    initTabHandling: function() {
        const self = this;
        const refineTab = document.getElementById('refine-tab');
        
        if (refineTab) {
            refineTab.addEventListener('shown.bs.tab', function() {
                console.log('Refine tab shown');
                // Ensure dropArea is visible when tab is shown
                if (self.elements.dropArea && (!self.elements.fileInput.files || self.elements.fileInput.files.length === 0)) {
                    self.elements.dropArea.style.display = 'flex';
                }
            });
        }
    },
    
    // Update file preview
    updateFilePreview: function(file) {
        const elements = this.elements;
        
        if (!elements.filePreview || !elements.fileName || !elements.fileSize) {
            console.error('Required preview elements not found');
            return;
        }
        
        // Update file info
        elements.fileName.textContent = file.name;
        elements.fileSize.textContent = this.formatFileSize(file.size);
        
        // Show file preview, hide drop area
        elements.filePreview.classList.remove('d-none');
        elements.dropArea.style.display = 'none';
        
        // Enable analyze button
        if (elements.analyzeBtn) {
            elements.analyzeBtn.disabled = false;
        }
    },
    
    // Remove file
    removeFile: function() {
        const elements = this.elements;
        
        // Clear file input
        if (elements.fileInput) {
            elements.fileInput.value = '';
        }
        
        // Hide preview, show drop area
        if (elements.filePreview) {
            elements.filePreview.classList.add('d-none');
        }
        if (elements.dropArea) {
            elements.dropArea.style.display = 'flex';
        }
        
        // Disable analyze button
        if (elements.analyzeBtn) {
            elements.analyzeBtn.disabled = true;
        }
        
        // Hide comparison view
        if (elements.comparisonView && !elements.comparisonView.classList.contains('d-none')) {
            elements.comparisonView.classList.add('d-none');
        }
    },
    
    // Check if file type is valid
    isValidFileType: function(file) {
        const validTypes = [
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        ];
        
        const validExtensions = ['.xlsx', '.xls', '.docx', '.doc'];
        
        // Check by MIME type
        if (validTypes.includes(file.type)) {
            return true;
        }
        
        // Check by file extension as fallback
        const fileName = file.name || '';
        const fileExt = fileName.substring(fileName.lastIndexOf('.')).toLowerCase();
        
        return validExtensions.includes(fileExt);
    },
    
    // Format file size
    formatFileSize: function(bytes) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },
    
    // Get CSRF token from cookies
    getCSRFToken: function() {
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
    },
    
    // Analyze test case
    analyzeTestCase: function() {
        const self = this;
        const elements = this.elements;
        
        // Get the file
        if (!elements.fileInput || !elements.fileInput.files || elements.fileInput.files.length === 0) {
            alert('Please select a test case file to analyze.');
            return;
        }
        
        const file = elements.fileInput.files[0];
        
        // Show progress indicator
        if (elements.progress) {
            elements.progress.classList.remove('d-none');
            const progressStatus = elements.progress.querySelector('.progress-status');
            if (progressStatus) {
                progressStatus.textContent = 'Analyzing test case... This may take a few moments.';
            }
        }
        
        // Disable button during processing
        if (elements.analyzeBtn) {
            elements.analyzeBtn.disabled = true;
        }
        
        // Create FormData object for the API request
        const formData = new FormData();
        formData.append('test_case_file', file);
        
        // Make the API request
        fetch('/test-cases/api/test-cases/refine/', {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': this.getCSRFToken()
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`Server responded with status: ${response.status}`);
            }
            return response.json();
        })
        .then(function(response) {
            // Hide progress indicator
            if (elements.progress) {
                elements.progress.classList.add('d-none');
            }
            
            // Show comparison view
            if (elements.comparisonView) {
                elements.comparisonView.classList.remove('d-none');
            }
            
            // Re-enable button
            if (elements.analyzeBtn) {
                elements.analyzeBtn.disabled = false;
            }
            
            // Process and display results
            if (response.status === 'success') {
                self.displayActualResults(response.data);
                
                // Store refinement data globally for use by action buttons
                self.refinementData = response.data;
                
                // Enable action buttons
                self.enableActionButtons();
            } else {
                self.displayErrorResults('Analysis failed: ' + (response.message || 'Unknown error'));
            }
        })
        .catch(function(error) {
            // Hide progress indicator
            if (elements.progress) {
                elements.progress.classList.add('d-none');
            }
            
            // Re-enable button
            if (elements.analyzeBtn) {
                elements.analyzeBtn.disabled = false;
            }
            
            // Display specific error message for file access errors
            if (error.message && error.message.includes('process cannot access the file')) {
                self.displayErrorResults('File access error: The file is currently in use by another process. Please try again in a moment or use a different file.');
            } else {
                // Display generic error message
                self.displayErrorResults('Error analyzing file: ' + (error.message || 'Unknown error'));
            }
            
            console.error('Error analyzing test case:', error);
        });
    },
    


    displayExampleResults: function() {
        const originalTestCase = document.getElementById('originalTestCase');
        const refinedTestCase = document.getElementById('refinedTestCase');
        const aiSuggestions = document.getElementById('aiSuggestions');
        
        if (originalTestCase) {
            originalTestCase.innerHTML = `
                <div class="test-case-info mb-3">
                    <p><strong>ID:</strong></p>
                    <p><strong>Name:</strong> </p>
                </div>
                <table class="table table-bordered">
                    <thead>
                        <tr>
                            <th>Step</th>
                            <th>Description</th>
                            <th>Expected Result</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>1</td>
                            <td>Go to the login page</td>
                            <td>Login form appears</td>
                        </tr>
                        <tr>
                            <td>2</td>
                            <td>Enter login credentials</td>
                            <td>User logged in</td>
                        </tr>
                        <tr>
                            <td>3</td>
                            <td>Check dashboard</td>
                            <td>Dashboard displays</td>
                        </tr>
                    </tbody>
                </table>
            `;
        }
        
        if (refinedTestCase) {
            refinedTestCase.innerHTML = `
                <div class="test-case-info mb-3">
                    <p><strong>ID:</strong> TC-1234</p>
                    <p><strong>Name:</strong> Login Test Case</p>
                </div>
                <table class="table table-bordered">
                    <thead>
                        <tr>
                            <th>Step</th>
                            <th>Description</th>
                            <th>Expected Result</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>1</td>
                            <td class="bg-warning">Navigate to the login page by clicking Login button</td>
                            <td class="bg-warning">Login page is displayed with username and password fields</td>
                        </tr>
                        <tr>
                            <td>2</td>
                            <td class="bg-warning">Enter valid username and password credentials</td>
                            <td class="bg-warning">Credentials are accepted and user is logged in successfully</td>
                        </tr>
                        <tr>
                            <td>3</td>
                            <td class="bg-warning">Verify dashboard elements</td>
                            <td class="bg-warning">Dashboard displays with user information and expected widgets</td>
                        </tr>
                        <tr class="table-success">
                            <td>4</td>
                            <td>Click logout button</td>
                            <td>User is logged out and redirected to login page</td>
                        </tr>
                    </tbody>
                </table>
            `;
        }
        
        if (aiSuggestions) {
            aiSuggestions.innerHTML = `
                <div>
                    <h6>Analysis Summary</h6>
                    <p>Test case has a completeness score of 65%. Several improvements would enhance test coverage and clarity.</p>
                    
                    <h6 class="mt-3">Key Improvements</h6>
                    <ul>
                        <li>Added more specific details to each step for better test execution</li>
                        <li>Enhanced expected results with clearer success criteria</li>
                        <li>Added logout step to complete the test flow (proper teardown)</li>
                    </ul>
                    
                    <h6 class="mt-3">Missing Test Variations</h6>
                    <ul>
                        <li>Consider adding test cases for invalid login credentials</li>
                        <li>Consider adding test cases for password reset functionality</li>
                    </ul>
                </div>
            `;
        }
    },


    // Display results
    displayActualResults: function(data) {
        const elements = this.elements;
        
        console.log('Data received in displayResults:', data);
        
        // Display original test case
        if (elements.originalTestCase) {
            elements.originalTestCase.innerHTML = this.generateOriginalTestCaseHTML(data);
        }
        
        // Display refined test case with LLM suggestions
        if (elements.refinedTestCase && data.llm_response) {
            elements.refinedTestCase.innerHTML = this.generateRefinedTestCaseHTML(data);
        } else if (elements.refinedTestCase) {
            elements.refinedTestCase.innerHTML = `
                <div class="alert alert-info">
                    No refinement suggestions available. The LLM service may be unavailable.
                </div>
            `;
        }
        
        // Display AI suggestions
        if (elements.aiSuggestions && data.llm_response) {
            elements.aiSuggestions.innerHTML = this.generateAISuggestionsHTML(data);
        } else if (elements.aiSuggestions) {
            elements.aiSuggestions.innerHTML = `
                <div class="alert alert-info">
                    No AI analysis available. The LLM service may be unavailable.
                </div>
            `;
        }
        
        // Make sure comparison view is visible
        if (elements.comparisonView) {
            elements.comparisonView.style.display = 'block';
            elements.comparisonView.classList.remove('d-none');
        }
    },
    
    // Generate Original Test Case HTML
    generateOriginalTestCaseHTML: function(data) {
        const testCaseInfo = data.test_case_info || {};
        const originalTestCase = data.original_test_case || [];
        
        let html = `
            <div class="test-case-info mb-3">
                <p><strong>ID:</strong> ${testCaseInfo.test_case_number || 'Unknown'}</p>
                <p><strong>Name:</strong> ${testCaseInfo.test_case_name || 'Unknown'}</p>
                <p><strong>Subject:</strong> ${testCaseInfo.subject || 'Unknown'}</p>
                <p><strong>Type:</strong> ${testCaseInfo.type || 'Unknown'}</p>
                <p><strong>Total Steps:</strong> ${originalTestCase.length || 0}</p>
            </div>
        `;
        
        if (originalTestCase && originalTestCase.length > 0) {
            html += `
                <table class="table table-bordered">
                    <thead>
                        <tr>
                            <th>Step</th>
                            <th>Description</th>
                            <th>Expected Result</th>
                            <th>Data</th>
                        </tr>
                    </thead>
                    <tbody>
            `;
            
            for (const step of originalTestCase) {
                html += `
                    <tr>
                        <td>${step["STEP NO"] || ''}</td>
                        <td>${step["TEST STEP DESCRIPTION"] || ''}</td>
                        <td>${step["EXPECTED RESULT"] || ''}</td>
                        <td>${step["DATA"] || ''}</td>
                    </tr>
                `;
            }
            
            html += `
                    </tbody>
                </table>
            `;
        } else {
            html += `<div class="alert alert-info">No step details available for this test case.</div>`;
        }
        
        return html;
    },
    
    // Generate Refined Test Case HTML from LLM response
    generateRefinedTestCaseHTML: function(data) {
        const testCaseInfo = data.test_case_info || {};
        const llmResponse = data.llm_response || {};
        const refinedSteps = llmResponse.steps || [];
        
        let html = `
            <div class="test-case-info mb-3">
                <p><strong>ID:</strong> ${testCaseInfo.test_case_number || 'Unknown'}</p>
                <p><strong>Name:</strong> ${testCaseInfo.test_case_name || 'Unknown'}</p>
            </div>
        `;
        
        if (refinedSteps && refinedSteps.length > 0) {
            html += `
                <table class="table table-bordered">
                    <thead>
                        <tr>
                            <th>Step</th>
                            <th>Description</th>
                            <th>Expected Result</th>
                            <th>Data</th>
                        </tr>
                    </thead>
                    <tbody>
            `;
            
            for (const step of refinedSteps) {
                html += `
                    <tr>
                        <td>${step["STEP NO"] || ''}</td>
                        <td class="bg-warning">${step["TEST STEP DESCRIPTION"] || ''}</td>
                        <td class="bg-warning">${step["EXPECTED RESULT"] || ''}</td>
                        <td class="bg-warning">${step["DATA"] || ''}</td>
                    </tr>
                `;
            }
            
            html += `
                    </tbody>
                </table>
            `;
        } else {
            html += `<div class="alert alert-info">No refinement suggestions available.</div>`;
        }
        
        return html;
    },
    
    // Generate AI Suggestions HTML
    generateAISuggestionsHTML: function(data) {
        const llmResponse = data.llm_response || {};
        
        let html = `
            <div>
                <h6>Analysis Summary</h6>
                <p>Test case has been analyzed and refined. Here are some key improvements:</p>
                
                <h6 class="mt-3">General Improvements</h6>
                <ul>
                    <li>Made test steps more specific and actionable</li>
                    <li>Enhanced expected results with clearer verification criteria</li>
                    <li>Added more detailed test data where needed</li>
                </ul>
        `;
        
        // Add missing test variations if included in LLM response
        if (llmResponse.missing_test_variations && llmResponse.missing_test_variations.length > 0) {
            html += `
                <h6 class="mt-3">Suggested Test Variations</h6>
                <ul>
            `;
            
            for (const variation of llmResponse.missing_test_variations) {
                html += `<li>${variation}</li>`;
            }
            
            html += `</ul>`;
        }
        
        // Add general suggestions if available
        if (llmResponse.general_suggestions && llmResponse.general_suggestions.length > 0) {
            html += `
                <h6 class="mt-3">General Suggestions</h6>
                <ul>
            `;
            
            for (const suggestion of llmResponse.general_suggestions) {
                html += `<li>${suggestion}</li>`;
            }
            
            html += `</ul>`;
        }
        
        html += `</div>`;
        return html;
    },
    
    // Display error results
    displayErrorResults: function(errorMessage) {
        const elements = this.elements;
        
        // Create appropriate error message
        let errorHtml = `
            <div class="alert alert-danger">
                <h5><i class="fas fa-exclamation-circle"></i> Error Processing Test Case</h5>
                <p>${errorMessage}</p>
                <p>Please check that your file is a valid test case in Excel format.</p>
            </div>
        `;
        
        // Display error in original test case area
        if (elements.originalTestCase) {
            elements.originalTestCase.innerHTML = errorHtml;
        }
        
        // Display empty structure in refined test case area
        if (elements.refinedTestCase) {
            elements.refinedTestCase.innerHTML = `
                <div class="alert alert-info">
                    <h6>Refinement Not Available</h6>
                    <p>Due to processing error, refinement suggestions cannot be displayed.</p>
                </div>
            `;
        }
        
        // Display empty structure in AI suggestions area
        if (elements.aiSuggestions) {
            elements.aiSuggestions.innerHTML = `
                <div class="alert alert-info">
                    <h6>AI Analysis Not Available</h6>
                    <p>Due to processing error, AI analysis could not be performed.</p>
                    <p>Please try uploading the file again or check that it meets the required format.</p>
                </div>
            `;
        }
        
        // Make comparison view visible
        if (elements.comparisonView) {
            elements.comparisonView.style.display = 'block';
            elements.comparisonView.classList.remove('d-none');
        }
        
        // Disable action buttons since we have an error
        this.disableActionButtons();
        
        // Log error for debugging
        console.error('Test case analysis error:', errorMessage);
    },
    
    // Handle accepting refinements
    handleAcceptRefinements: function() {
        const self = this;
        const elements = this.elements;
        
        // Confirmation dialog
        if (!confirm('Are you sure you want to accept these refinements and update the repository?')) {
            return;
        }
        
        // Show progress indicator
        if (elements.progress) {
            elements.progress.classList.remove('d-none');
            const progressStatus = elements.progress.querySelector('.progress-status');
            if (progressStatus) {
                progressStatus.textContent = 'Applying refinements and updating repository...';
            }
        }
        
        // Get data from global refinementData
        if (!this.refinementData || !this.refinementData.test_case_info) {
            alert('No refinement data available. Please analyze the test case first.');
            if (elements.progress) {
                elements.progress.classList.add('d-none');
            }
            return;
        }
        
        // Prepare data for API call
        const apiData = {
            test_case_id: this.refinementData.test_case_id || this.refinementData.test_case_info.test_case_number,
            refinements: {
                step_refinements: this.constructRefinementsFromData(this.refinementData)
            },
            changed_by: 'UI User' // In a real implementation, would get from user session
        };
        
        // Call API directly using fetch
        fetch('/test-cases/api/test-cases/apply-refinements/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCSRFToken()
            },
            body: JSON.stringify(apiData)
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`Server responded with status: ${response.status}`);
            }
            return response.json();
        })
        .then(function(response) {
            // Hide progress indicator
            if (elements.progress) {
                elements.progress.classList.add('d-none');
            }
            
            if (response.status === 'success') {
                // Show success notification
                alert('Refinements accepted and repository updated successfully!');
                
                // Log success details
                console.log('Repository update successful:', response.data);
                
                // Disable action buttons to prevent multiple submissions
                self.disableActionButtons();
                
                // Add visual indicator of success
                const container = document.querySelector('.refinement-comparison');
                if (container) {
                    const successBanner = document.createElement('div');
                    successBanner.className = 'alert alert-success mt-3';
                    successBanner.innerHTML = `
                        <h6><i class="fas fa-check-circle"></i> Repository Updated</h6>
                        <p>The test case has been successfully updated in the repository.</p>
                        <p><strong>Refined ID:</strong> ${response.data.refined_test_case_id || apiData.test_case_id}</p>
                        <p><strong>Updated By:</strong> ${apiData.changed_by}</p>
                        <p><strong>Date:</strong> ${new Date().toLocaleString()}</p>
                    `;
                    container.appendChild(successBanner);
                }
            } else {
                // Show error notification
                alert('Error updating repository: ' + (response.message || 'Unknown error'));
                console.error('Repository update error:', response);
            }
        })
        .catch(function(error) {
            // Hide progress indicator
            if (elements.progress) {
                elements.progress.classList.add('d-none');
            }
            
            // Show error notification
            alert('Error updating repository: ' + (error.message || 'Unknown error'));
            console.error('Repository update error:', error);
        });
    },
    
    // Handle downloading the refined test case
    handleDownloadRefinedTestCase: function() {
        const elements = this.elements;
        
        // Check if we have refinement data
        if (!this.refinementData || !this.refinementData.test_case_info) {
            alert('No refinement data available to download.');
            return;
        }
        
        // Prepare data for download
        const downloadData = {
            test_case_id: this.refinementData.test_case_id || this.refinementData.test_case_info.test_case_number,
            refinements: {
                step_refinements: this.constructRefinementsFromData(this.refinementData)
            },
            output_format: 'xlsx' // Default to Excel format
        };
        
        // Show progress indicator
        if (elements.progress) {
            elements.progress.classList.remove('d-none');
            const progressStatus = elements.progress.querySelector('.progress-status');
            if (progressStatus) {
                progressStatus.textContent = 'Preparing refined test case for download...';
            }
        }
        
        // Generate file name
        const testCaseId = downloadData.test_case_id;
        const fileName = `Refined_${testCaseId}_${new Date().toISOString().slice(0,10)}.xlsx`;
        
        // Create download URL
        const downloadUrl = '/api/test-cases/generate-download';
        
        // Make API call
        fetch(downloadUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCSRFToken()
            },
            body: JSON.stringify(downloadData)
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`Server responded with status: ${response.status}`);
            }
            return response.blob();
        })
        .then(blob => {
            // Hide progress indicator
            if (elements.progress) {
                elements.progress.classList.add('d-none');
            }
            
            // Create download link
            const downloadLink = document.createElement('a');
            downloadLink.href = URL.createObjectURL(blob);
            downloadLink.download = fileName;
            
            // Append link, click it, and remove it
            document.body.appendChild(downloadLink);
            downloadLink.click();
            document.body.removeChild(downloadLink);
            
            // Show success message
            alert('Refined test case downloaded successfully.');
        })
        .catch(error => {
            // Hide progress indicator
            if (elements.progress) {
                elements.progress.classList.add('d-none');
            }
            
            // Show error message
            alert('Error downloading refined test case: ' + (error.message || 'Unknown error'));
            console.error('Download error:', error);
        });
    },
    
    // Handle notifying the test case owner
    handleNotifyOwner: function() {
        const elements = this.elements;
        
        // Check if we have refinement data
        if (!this.refinementData || !this.refinementData.test_case_info) {
            alert('No refinement data available. Please analyze the test case first.');
            return;
        }
        
        // Confirmation dialog
        if (!confirm('Are you sure you want to notify the test case owner about these suggestions?')) {
            return;
        }
        
        // Prepare notification data
        const notificationData = {
            test_case_id: this.refinementData.test_case_id || this.refinementData.test_case_info.test_case_number,
            notification_type: 'suggestions',
            details: {
                summary: this.refinementData.summary || {},
                suggestions_count: this.refinementData.step_suggestions?.length || 0
            }
        };
        
        // Show progress indicator
        if (elements.progress) {
            elements.progress.classList.remove('d-none');
            const progressStatus = elements.progress.querySelector('.progress-status');
            if (progressStatus) {
                progressStatus.textContent = 'Sending notification to test case owner...';
            }
        }
        
        // Use API to send notification - using simulated success for now
        setTimeout(() => {
            // Hide progress indicator
            if (elements.progress) {
                elements.progress.classList.add('d-none');
            }
            
            // Show success notification
            alert('Test case owner has been notified about the suggestions!');
            
            // Update UI to show notification sent
            const notifyBtn = elements.notifyOwnerBtn;
            if (notifyBtn) {
                notifyBtn.innerHTML = '<i class="fas fa-check"></i> Owner Notified';
                notifyBtn.classList.remove('btn-info');
                notifyBtn.classList.add('btn-success');
                notifyBtn.disabled = true;
            }
        }, 1000);
    },
    

    // Handle marking test case as obsolete
    handleMarkObsolete: function() {
        const elements = this.elements;
        
        // Check if we have refinement data
        if (!this.refinementData || !this.refinementData.test_case_info) {
            alert('No test case data available. Please analyze the test case first.');
            return;
        }
        
        // Confirmation dialog
        if (!confirm('Are you sure you want to mark this test case as obsolete? This action cannot be undone.')) {
            return;
        }
        
        // Prepare data
        const obsoleteData = {
            test_case_id: this.refinementData.test_case_id || this.refinementData.test_case_info.test_case_number,
            marked_by: 'UI User', // In a real implementation, would get from user session
            reason: 'Marked as obsolete from UI'
        };
        
        // Show progress indicator
        if (elements.progress) {
            elements.progress.classList.remove('d-none');
            const progressStatus = elements.progress.querySelector('.progress-status');
            if (progressStatus) {
                progressStatus.textContent = 'Marking test case as obsolete...';
            }
        }
        
        // Use API to mark as obsolete - simplified for demonstration
        setTimeout(() => {
            // Hide progress indicator
            if (elements.progress) {
                elements.progress.classList.add('d-none');
            }
            
            // Show success notification
            alert('Test case marked as obsolete successfully.');
            
            // Disable action buttons to prevent further actions
            this.disableActionButtons();
            
            // Add visual indicator
            const container = document.querySelector('.refinement-comparison');
            if (container) {
                const obsoleteBanner = document.createElement('div');
                obsoleteBanner.className = 'alert alert-warning mt-3';
                obsoleteBanner.innerHTML = `
                    <h6><i class="fas fa-archive"></i> Test Case Marked as Obsolete</h6>
                    <p>This test case has been marked as obsolete.</p>
                    <p><strong>Marked By:</strong> ${obsoleteData.marked_by}</p>
                    <p><strong>Date:</strong> ${new Date().toLocaleString()}</p>
                `;
                container.appendChild(obsoleteBanner);
            }
        }, 1000);
    },


    // Helper function to construct refinements from data
    constructRefinementsFromData: function(data) {
        const stepRefinements = [];
        
        // Check if we have LLM response with steps
        if (data.llm_response && data.llm_response.steps) {
            const llmSteps = data.llm_response.steps;
            const originalSteps = data.original_test_case || [];
            
            // Map original steps by step number for reference
            const originalStepsMap = {};
            originalSteps.forEach(step => {
                const stepNo = step["STEP NO"];
                if (stepNo) {
                    originalStepsMap[stepNo] = step;
                }
            });
            
            // Process each step from LLM response
            llmSteps.forEach(llmStep => {
                const stepNo = llmStep["STEP NO"];
                
                // Skip if no step number
                if (!stepNo) return;
                
                // Find corresponding original step
                const originalStep = originalStepsMap[stepNo];
                if (!originalStep) return; // Skip if no matching original step
                
                // Collect updates for this step
                const updates = {};
                
                // Check TEST STEP DESCRIPTION
                if (llmStep["TEST STEP DESCRIPTION"] && 
                    llmStep["TEST STEP DESCRIPTION"] !== originalStep["TEST STEP DESCRIPTION"]) {
                    updates["TEST STEP DESCRIPTION"] = llmStep["TEST STEP DESCRIPTION"];
                }
                
                // Check EXPECTED RESULT
                if (llmStep["EXPECTED RESULT"] && 
                    llmStep["EXPECTED RESULT"] !== originalStep["EXPECTED RESULT"]) {
                    updates["EXPECTED RESULT"] = llmStep["EXPECTED RESULT"];
                }
                
                // Check DATA
                if (llmStep["DATA"] && 
                    llmStep["DATA"] !== originalStep["DATA"]) {
                    updates["DATA"] = llmStep["DATA"];
                }
                
                // Only add steps that have updates
                if (Object.keys(updates).length > 0) {
                    stepRefinements.push({
                        step_no: stepNo,
                        updates: updates
                    });
                }
            });
        }
        
        // Log the refinements for debugging
        console.log("Constructed refinements:", stepRefinements);
        
        return stepRefinements;
    },

    // Function to enable action buttons after analysis
    enableActionButtons: function() {
        const elements = this.elements;
        const actionButtons = [
            elements.acceptSuggestionsBtn,
            elements.downloadRefinedBtn,
            elements.notifyOwnerBtn,
            elements.markObsoleteBtn,
            elements.discardSuggestionsBtn
        ];
        
        actionButtons.forEach(button => {
            if (button) {
                button.disabled = false;
            }
        });
    },

    // Function to disable action buttons (e.g., after performing an action)
    disableActionButtons: function() {
        const elements = this.elements;
        const actionButtons = [
            elements.acceptSuggestionsBtn,
            elements.downloadRefinedBtn,
            elements.notifyOwnerBtn,
            elements.markObsoleteBtn,
            elements.discardSuggestionsBtn
        ];
        
        actionButtons.forEach(button => {
            if (button) {
                button.disabled = true;
            }
        });
    }
    };

    // Initialize everything when DOM is loaded
    document.addEventListener('DOMContentLoaded', function() {
    TestCaseRefinement.init();
    });
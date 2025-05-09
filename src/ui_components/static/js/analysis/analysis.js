// analysis.js - JavaScript for the Analysis & Defects page

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize toast
    var toastElements = document.querySelectorAll('.toast');
    toastElements.forEach(function(toastElement) {
        return new bootstrap.Toast(toastElement, {
            autohide: true,
            delay: 5000
        });
    });

    // Failed Tests Table Search Functionality
    const searchFailedTests = document.getElementById('searchFailedTests');
    if (searchFailedTests) {
        searchFailedTests.addEventListener('keyup', function() {
            const searchValue = this.value.toLowerCase();
            const tableRows = document.querySelectorAll('#failedTestsTable tbody tr');
            
            tableRows.forEach(row => {
                const rowText = row.textContent.toLowerCase();
                if (rowText.includes(searchValue)) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });
        });
    }

    // Defects Table Search Functionality
    const searchDefects = document.getElementById('searchDefects');
    if (searchDefects) {
        searchDefects.addEventListener('keyup', function() {
            const searchValue = this.value.toLowerCase();
            const tableRows = document.querySelectorAll('#defectsTable tbody tr');
            
            tableRows.forEach(row => {
                const rowText = row.textContent.toLowerCase();
                if (rowText.includes(searchValue)) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });
        });
    }

    // Failed Test Filters
    const filterLinks = document.querySelectorAll('[data-filter]');
    filterLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const filterType = this.getAttribute('data-filter');
            applyTestFilter(filterType);
        });
    });

    // Defect Filters
    const defectFilterLinks = document.querySelectorAll('[data-defect-filter]');
    defectFilterLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const filterType = this.getAttribute('data-defect-filter');
            applyDefectFilter(filterType);
        });
    });

    // Analyze Button Click
    const analyzeButtons = document.querySelectorAll('.analyze-btn');
    analyzeButtons.forEach(button => {
        button.addEventListener('click', function() {
            const testId = this.getAttribute('data-test-id');
            const stepNum = this.getAttribute('data-step');
            showAnalysisPanel(testId, stepNum);
        });
    });

    // Close Analysis Panel Button
    const closeAnalysisPanel = document.getElementById('closeAnalysisPanel');
    if (closeAnalysisPanel) {
        closeAnalysisPanel.addEventListener('click', function() {
            hideAnalysisPanel();
        });
    }

    // Screenshot Modal Event Handlers
    const screenshotModal = document.getElementById('screenshotModal');
    if (screenshotModal) {
        screenshotModal.addEventListener('show.bs.modal', function(event) {
            const button = event.relatedTarget;
            const testId = button.getAttribute('data-test-id');
            const stepNum = button.getAttribute('data-step');
            
            // Update modal content
            document.getElementById('screenshotTcId').textContent = testId;
            document.getElementById('screenshotStepNum').textContent = stepNum;
            
            // In a real app, we would fetch the actual screenshot here
            // For now, we'll just update the alt text
            const screenshotImg = document.getElementById('errorScreenshot');
            screenshotImg.alt = `Error Screenshot for ${testId} Step ${stepNum}`;
        });
    }

    // Create Defect Modal Event Handlers
    const createDefectModal = document.getElementById('createDefectModal');
    if (createDefectModal) {
        createDefectModal.addEventListener('show.bs.modal', function() {
            // In a real app, we would pre-fill form based on current analysis
            // For now, we'll use the static mock data already in the HTML
        });
    }

    // Defect System Selection Change
    const defectSystem = document.getElementById('defectSystem');
    if (defectSystem) {
        defectSystem.addEventListener('change', function() {
            const targetSystem = document.getElementById('targetSystem');
            if (targetSystem) {
                targetSystem.textContent = this.value.charAt(0).toUpperCase() + this.value.slice(1);
            }
        });
    }

    // Submit Defect Button
    const submitDefectBtn = document.getElementById('submitDefectBtn');
    if (submitDefectBtn) {
        submitDefectBtn.addEventListener('click', function() {
            // In a real app, we would submit the form to the backend
            // For now, we'll just show a success toast and close the modal
            const toast = document.getElementById('successToast');
            const toastMessage = document.getElementById('toastMessage');
            
            if (toast && toastMessage) {
                toastMessage.textContent = 'Defect created successfully!';
                const bsToast = new bootstrap.Toast(toast);
                bsToast.show();
            }
            
            const modal = bootstrap.Modal.getInstance(document.getElementById('createDefectModal'));
            if (modal) {
                modal.hide();
            }
        });
    }

    // View Defect Details Button
    const viewDefectButtons = document.querySelectorAll('.view-defect-btn');
    viewDefectButtons.forEach(button => {
        button.addEventListener('click', function() {
            const defectId = this.getAttribute('data-defect-id');
            showDefectDetails(defectId);
        });
    });

    // Helper Functions
    
    /**
     * Apply filter to the failed tests table
     * @param {string} filterType - Type of filter to apply
     */
    function applyTestFilter(filterType) {
        const tableRows = document.querySelectorAll('#failedTestsTable tbody tr');
        const today = new Date().toDateString();
        
        tableRows.forEach(row => {
            const dateCell = row.querySelector('td:nth-child(4)').textContent;
            const statusCell = row.querySelector('td:nth-child(5)').textContent;
            
            switch(filterType) {
                case 'all':
                    row.style.display = '';
                    break;
                case 'today':
                    if (new Date(dateCell).toDateString() === today) {
                        row.style.display = '';
                    } else {
                        row.style.display = 'none';
                    }
                    break;
                case 'week':
                    const oneWeekAgo = new Date();
                    oneWeekAgo.setDate(oneWeekAgo.getDate() - 7);
                    if (new Date(dateCell) >= oneWeekAgo) {
                        row.style.display = '';
                    } else {
                        row.style.display = 'none';
                    }
                    break;
                case 'unanalyzed':
                    if (statusCell.includes('Unanalyzed')) {
                        row.style.display = '';
                    } else {
                        row.style.display = 'none';
                    }
                    break;
            }
        });
    }
    
    /**
     * Apply filter to the defects table
     * @param {string} filterType - Type of filter to apply
     */
    function applyDefectFilter(filterType) {
        const tableRows = document.querySelectorAll('#defectsTable tbody tr');
        
        tableRows.forEach(row => {
            const statusCell = row.querySelector('td:nth-child(6)').textContent;
            
            if (filterType === 'all') {
                row.style.display = '';
            } else if (statusCell.toLowerCase().includes(filterType.toLowerCase())) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        });
    }
    
    /**
     * Show the analysis panel with details for the selected test
     * @param {string} testId - Test case ID
     * @param {string} stepNum - Step number
     */
    function showAnalysisPanel(testId, stepNum) {
        // Update panel title and details
        document.getElementById('analysisTcId').textContent = testId;
        document.getElementById('analysisStepNum').textContent = stepNum;
        document.getElementById('tcDetailsId').textContent = testId;
        document.getElementById('tcDetailsStep').textContent = stepNum;
        
        // In a real app, we would fetch and display actual data here
        // For this demo, we're using the static mock data
        
        // Show the panel
        const analysisPanel = document.getElementById('analysisPanel');
        if (analysisPanel) {
            analysisPanel.style.display = 'block';
            
            // Scroll to panel
            analysisPanel.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }
    
    /**
     * Hide the analysis panel
     */
    function hideAnalysisPanel() {
        const analysisPanel = document.getElementById('analysisPanel');
        if (analysisPanel) {
            analysisPanel.style.display = 'none';
        }
    }
    
    /**
     * Show defect details in modal
     * @param {string} defectId - Defect ID
     */
    function showDefectDetails(defectId) {
        // Update modal with defect details
        document.getElementById('detailsDefectId').textContent = defectId;
        
        // In a real app, we would fetch actual defect data here
        // For this demo, we're using the static mock data
        
        // Show the modal
        const modal = new bootstrap.Modal(document.getElementById('defectDetailsModal'));
        modal.show();
    }
    
    /**
     * AI Analysis Simulation (for demo purposes)
     * In a real app, this would make an API call to the backend AI service
     */
    function simulateAIAnalysis() {
        // Mock for demonstration - would be replaced with actual API call
        return new Promise((resolve) => {
            // Simulate API delay
            setTimeout(() => {
                resolve({
                    potentialCauses: [
                        { label: 'ID Changed', description: 'The login button\'s ID may have been updated in the latest build' },
                        { label: 'Loading Issue', description: 'The login form might not have fully loaded before the test attempted to click the button' },
                        { label: 'Visibility Problem', description: 'The button might be present in DOM but not visible/clickable (CSS issue)' }
                    ],
                    mostLikelyCause: 'Based on log analysis and recent code changes, the login button ID was changed from "login_button" to "btn-login" in the latest sprint (JIRA-123).',
                    logSnippets: `2025-05-07 14:23:01 INFO: Navigating to login page
2025-05-07 14:23:02 INFO: Entering username 'testuser'
2025-05-07 14:23:03 INFO: Entering password '********'
2025-05-07 14:23:03 DEBUG: Attempting to find element: login_button
2025-05-07 14:23:06 ERROR: NoSuchElementException: Unable to locate element: {"method":"id","selector":"login_button"}
2025-05-07 14:23:06 DEBUG: Page source: <div class="login-form">...<button id="btn-login">Login</button>...</div>`,
                    debuggingSteps: [
                        'Verify the current ID of the login button in the application',
                        'Check recent code changes affecting the login form',
                        'Update the test script to use the new button ID',
                        'Consider adding wait conditions to ensure elements are fully loaded'
                    ],
                    fixRecommendation: 'Update test script to use the new ID: <code>btn-login</code> instead of <code>login_button</code>. Alternatively, consider using more robust selectors like XPath that include multiple attributes.'
                });
            }, 1500);
        });
    }
});
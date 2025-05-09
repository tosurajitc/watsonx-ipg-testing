// code_automation.js - Part 1: Initialization and Event Handlers
// This part contains the document ready function, event listeners, and basic interaction handlers

document.addEventListener('DOMContentLoaded', function() {
    // Initialize syntax highlighting
    document.querySelectorAll('pre code').forEach((block) => {
        hljs.highlightBlock(block);
    });

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

    // Code Generation Form Submission
    const codeGenerationForm = document.getElementById('codeGenerationForm');
    if (codeGenerationForm) {
        codeGenerationForm.addEventListener('submit', function(e) {
            e.preventDefault();
            generateCode();
        });
    }

    // UFT Automation Analysis Form Submission
    const uftCheckForm = document.getElementById('uftCheckForm');
    if (uftCheckForm) {
        uftCheckForm.addEventListener('submit', function(e) {
            e.preventDefault();
            analyzeAutomationPotential();
        });
    }

    // Test Case Source Change
    const testCaseSource = document.getElementById('testCaseSource');
    if (testCaseSource) {
        testCaseSource.addEventListener('change', function() {
            toggleTestCaseSelectionMethod(this.value);
        });
    }

    // Automation Scope Change
    const automationScope = document.getElementById('automationScope');
    if (automationScope) {
        automationScope.addEventListener('change', function() {
            toggleStepSelection(this.value);
        });
    }

    // Example Request Buttons
    const exampleButtons = document.querySelectorAll('.use-example-btn');
    exampleButtons.forEach(button => {
        button.addEventListener('click', function() {
            const exampleText = this.previousElementSibling.textContent;
            useExampleRequest(exampleText);
        });
    });

    // Refine Request Button
    const refineRequestBtn = document.getElementById('refineRequestBtn');
    if (refineRequestBtn) {
        refineRequestBtn.addEventListener('click', function() {
            showRefinementModal();
        });
    }

    // Apply Refinement Button
    const applyRefinementBtn = document.getElementById('applyRefinementBtn');
    if (applyRefinementBtn) {
        applyRefinementBtn.addEventListener('click', function() {
            refineCode();
        });
    }

    // Submit Refinement Options Button
    const submitRefinementOptions = document.getElementById('submitRefinementOptions');
    if (submitRefinementOptions) {
        submitRefinementOptions.addEventListener('click', function() {
            applyRefinementOptions();
        });
    }

    // Copy Code Buttons
    const copyCodeBtn = document.getElementById('copyCodeBtn');
    if (copyCodeBtn) {
        copyCodeBtn.addEventListener('click', function() {
            copyToClipboard('generatedCode');
        });
    }

    const copyUftCodeBtn = document.getElementById('copyUftCodeBtn');
    if (copyUftCodeBtn) {
        copyUftCodeBtn.addEventListener('click', function() {
            copyToClipboard('uftStarterCode');
        });
    }

    // Download Code Buttons
    const downloadCodeBtn = document.getElementById('downloadCodeBtn');
    if (downloadCodeBtn) {
        downloadCodeBtn.addEventListener('click', function() {
            downloadCode('generatedCode', getFileNameForCode());
        });
    }

    const downloadUftCodeBtn = document.getElementById('downloadUftCodeBtn');
    if (downloadUftCodeBtn) {
        downloadUftCodeBtn.addEventListener('click', function() {
            downloadCode('uftStarterCode', 'TC1001_Login_Automation.vbs');
        });
    }

    // Generate Full Script Button
    const generateFullScriptBtn = document.getElementById('generateFullScriptBtn');
    if (generateFullScriptBtn) {
        generateFullScriptBtn.addEventListener('click', function() {
            showFullScriptModal();
        });
    }

    // Generate Full Script Submit Button
    const generateFullScriptSubmit = document.getElementById('generateFullScriptSubmit');
    if (generateFullScriptSubmit) {
        generateFullScriptSubmit.addEventListener('click', function() {
            generateFullUftScript();
        });
    }

    // Export Analysis Report Button
    const exportAnalysisBtn = document.getElementById('exportAnalysisBtn');
    if (exportAnalysisBtn) {
        exportAnalysisBtn.addEventListener('click', function() {
            exportAnalysisReport();
        });
    }

    // Test Case List Change
    const testCaseList = document.getElementById('testCaseList');
    if (testCaseList) {
        testCaseList.addEventListener('change', function() {
            updateTestCasePreview(this.value);
        });
    }

    // Core application functions
    
    /**
     * Generate code based on form inputs
     */
    function generateCode() {
        const targetLanguage = document.getElementById('targetLanguage').value;
        const codeDescription = document.getElementById('codeDescription').value;
        const includeComments = document.getElementById('includeComments').checked;
        const includeErrorHandling = document.getElementById('includeErrorHandling').checked;
        const includeImports = document.getElementById('includeImports').checked;
        
        if (!targetLanguage || !codeDescription) {
            showToast('Please select a language and describe what you need', 'danger');
            return;
        }
        
        // Update language badge
        updateLanguageBadge(targetLanguage);
        
        // Show loading state
        document.getElementById('generatedCode').textContent = 'Generating code...';
        hljs.highlightBlock(document.getElementById('generatedCode'));
        
        // Enable code footer
        document.getElementById('codeFooter').style.display = 'block';
        
        // Disable copy/download buttons while generating
        document.getElementById('copyCodeBtn').disabled = true;
        document.getElementById('downloadCodeBtn').disabled = true;
        
        // Simulate API call to generate code (in real app, this would be an actual API call)
        setTimeout(() => {
            const generatedCode = simulateCodeGeneration(targetLanguage, codeDescription, includeComments, includeErrorHandling, includeImports);
            
            // Update code display
            document.getElementById('generatedCode').textContent = generatedCode;
            document.getElementById('generatedCode').className = `language-${getLanguageClass(targetLanguage)}`;
            hljs.highlightBlock(document.getElementById('generatedCode'));
            
            // Enable copy/download buttons
            document.getElementById('copyCodeBtn').disabled = false;
            document.getElementById('downloadCodeBtn').disabled = false;
            
            // Update generation time
            document.getElementById('codeGenerationTime').textContent = `Generated ${new Date().toLocaleTimeString()}`;
            
            showToast('Code generated successfully!', 'success');
        }, 1500);
    }
    
    /**
     * Analyze automation potential for the selected test case
     */
    function analyzeAutomationPotential() {
        const testCaseSource = document.getElementById('testCaseSource').value;
        let testCaseIdentifier;
        
        if (testCaseSource === 'repository') {
            testCaseIdentifier = document.getElementById('testCaseList').value;
            if (!testCaseIdentifier) {
                showToast('Please select a test case from the list', 'danger');
                return;
            }
        } else {
            const fileInput = document.getElementById('testCaseFile');
            if (!fileInput.files.length) {
                showToast('Please upload a test case file', 'danger');
                return;
            }
            testCaseIdentifier = fileInput.files[0].name;
        }
        
        // Hide placeholder and show loading
        document.getElementById('analysisPlaceholder').style.display = 'none';
        document.getElementById('analysisLoading').style.display = 'block';
        document.getElementById('analysisResults').style.display = 'none';
        
        // Simulate API call for analysis (in real app, this would be an actual API call)
        setTimeout(() => {
            // Hide loading and show results
            document.getElementById('analysisLoading').style.display = 'none';
            document.getElementById('analysisResults').style.display = 'block';
            
            // In a real app, we would update the results with actual data from the API
            // For now, we'll use the static mock data
            
            showToast('Analysis completed successfully!', 'success');
        }, 2000);
    }
    
    /**
     * Toggle between repository selection and file upload
     */
    function toggleTestCaseSelectionMethod(method) {
        const repositorySelection = document.getElementById('repositorySelection');
        const fileUploadSelection = document.getElementById('fileUploadSelection');
        
        if (method === 'repository') {
            repositorySelection.style.display = 'block';
            fileUploadSelection.style.display = 'none';
        } else {
            repositorySelection.style.display = 'none';
            fileUploadSelection.style.display = 'block';
        }
    }
    
    /**
     * Toggle step selection based on automation scope
     */
    function toggleStepSelection(scope) {
        const stepSelectionContainer = document.getElementById('stepSelectionContainer');
        
        if (scope === 'partial') {
            stepSelectionContainer.style.display = 'block';
        } else {
            stepSelectionContainer.style.display = 'none';
        }
    }
    
    /**
     * Use example code request
     */
    function useExampleRequest(exampleText) {
        const codeDescription = document.getElementById('codeDescription');
        codeDescription.value = exampleText;
        codeDescription.focus();
        
        // Auto-select appropriate language based on example
        const targetLanguage = document.getElementById('targetLanguage');
        if (exampleText.toLowerCase().includes('python')) {
            if (exampleText.toLowerCase().includes('selenium')) {
                targetLanguage.value = 'python-selenium';
            } else if (exampleText.toLowerCase().includes('requests')) {
                targetLanguage.value = 'python-requests';
            } else if (exampleText.toLowerCase().includes('playwright')) {
                targetLanguage.value = 'python-playwright';
            } else {
                targetLanguage.value = 'python-selenium';
            }
        } else if (exampleText.toLowerCase().includes('java')) {
            targetLanguage.value = 'java-selenium';
        } else if (exampleText.toLowerCase().includes('javascript') || exampleText.toLowerCase().includes('cypress')) {
            targetLanguage.value = 'javascript-cypress';
        } else if (exampleText.toLowerCase().includes('c#')) {
            targetLanguage.value = 'csharp-selenium';
        }
        
        // Collapse examples
        const examplesCollapse = document.getElementById('examplesCollapse');
        const bsCollapse = bootstrap.Collapse.getInstance(examplesCollapse);
        if (bsCollapse) {
            bsCollapse.hide();
        }
    }
    
    // Helper functions (modals, UI controls, etc.)
    
    /**
     * Show refinement modal
     */
    function showRefinementModal() {
        const refinementModal = new bootstrap.Modal(document.getElementById('refinementModal'));
        refinementModal.show();
    }
    
    /**
     * Show full script generation modal
     */
    function showFullScriptModal() {
        const fullScriptModal = new bootstrap.Modal(document.getElementById('fullScriptModal'));
        fullScriptModal.show();
    }
    
    /**
     * Refine existing code
     */
    function refineCode() {
        const refinementPanel = document.getElementById('refinementPanel');
        refinementPanel.style.display = 'block';
        
        // Scroll to refinement panel
        refinementPanel.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
    
    /**
     * Apply refinement options
     */
    function applyRefinementOptions() {
        const optionAddComments = document.getElementById('optionAddComments').checked;
        const optionEnhanceErrorHandling = document.getElementById('optionEnhanceErrorHandling').checked;
        const optionOptimizeCode = document.getElementById('optionOptimizeCode').checked;
        const optionChangeSelectors = document.getElementById('optionChangeSelectors').checked;
        const optionIncludeWaits = document.getElementById('optionIncludeWaits').checked;
        const customRefinementRequest = document.getElementById('customRefinementRequest').value;
        
        // In a real app, we would send these options to an API
        // For now, we'll just close the modal and simulate refinement
        
        const modal = bootstrap.Modal.getInstance(document.getElementById('refinementModal'));
        if (modal) {
            modal.hide();
        }
        
        // Show loading state in code area
        document.getElementById('generatedCode').textContent = 'Refining code...';
        hljs.highlightBlock(document.getElementById('generatedCode'));
        
        // Disable buttons during refinement
        document.getElementById('copyCodeBtn').disabled = true;
        document.getElementById('downloadCodeBtn').disabled = true;
        
        // Simulate API call for refinement
        setTimeout(() => {
            const currentCode = document.getElementById('generatedCode').textContent;
            const targetLanguage = document.getElementById('targetLanguage').value;
            const refinedCode = simulateCodeRefinement(currentCode, targetLanguage, {
                addComments: optionAddComments,
                enhanceErrorHandling: optionEnhanceErrorHandling,
                optimizeCode: optionOptimizeCode,
                changeSelectors: optionChangeSelectors,
                includeWaits: optionIncludeWaits,
                customRequest: customRefinementRequest
            });
            
            // Update code display
            document.getElementById('generatedCode').textContent = refinedCode;
            hljs.highlightBlock(document.getElementById('generatedCode'));
            
            // Enable copy/download buttons
            document.getElementById('copyCodeBtn').disabled = false;
            document.getElementById('downloadCodeBtn').disabled = false;
            
            // Update generation time
            document.getElementById('codeGenerationTime').textContent = `Refined ${new Date().toLocaleTimeString()}`;
            
            // Hide refinement panel
            document.getElementById('refinementPanel').style.display = 'none';
            
            showToast('Code refined successfully!', 'success');
        }, 1500);
    }
});


// code_automation.js - Part 2: Utility Functions
// This part contains utility functions for file operations, code generation/manipulation, and UI updates

/**
 * Generate full UFT script
 */
function generateFullUftScript() {
    const scriptName = document.getElementById('scriptName').value;
    const scriptAuthor = document.getElementById('scriptAuthor').value;
    const scriptVersion = document.getElementById('scriptVersion').value;
    const includeHeader = document.getElementById('includeHeader').checked;
    const includeEnvironmentSetup = document.getElementById('includeEnvironmentSetup').checked;
    const includeErrorRecovery = document.getElementById('includeErrorRecovery').checked;
    const includeCleanup = document.getElementById('includeCleanup').checked;
    const includeReporting = document.getElementById('includeReporting').checked;
    const additionalNotes = document.getElementById('additionalNotes').value;
    
    // In a real app, we would send these options to an API
    // For now, we'll just close the modal and show a toast
    
    const modal = bootstrap.Modal.getInstance(document.getElementById('fullScriptModal'));
    if (modal) {
        modal.hide();
    }
    
    showToast('Full UFT script generation started. This may take a few minutes.', 'info');
    
    // Simulate API call completion after delay
    setTimeout(() => {
        showToast('Full UFT script generated and saved to repository.', 'success');
    }, 3000);
}

/**
 * Export analysis report
 */
function exportAnalysisReport() {
    showToast('Analysis report exported to PDF.', 'success');
}

/**
 * Update test case preview based on selected test case
 */
function updateTestCasePreview(testCaseId) {
    // In a real app, we would fetch the actual test case details from an API
    // For now, we'll just update the title in the preview panel
    
    const previewTitle = document.querySelector('#testCasePreview h6');
    if (previewTitle) {
        previewTitle.textContent = testCaseId + ': ' + getTestCaseName(testCaseId);
    }
    
    // We would also update the table rows with actual test steps
    // For this demo, we'll keep the existing mock data
}

/**
 * Copy code to clipboard
 */
function copyToClipboard(elementId) {
    const codeElement = document.getElementById(elementId);
    const textToCopy = codeElement.textContent;
    
    navigator.clipboard.writeText(textToCopy).then(() => {
        // Visual feedback for copy success
        const copyBtn = document.getElementById(elementId === 'generatedCode' ? 'copyCodeBtn' : 'copyUftCodeBtn');
        
        // Change button appearance temporarily
        const originalText = copyBtn.innerHTML;
        copyBtn.innerHTML = '<i class="fas fa-check me-1"></i>Copied!';
        copyBtn.classList.add('copy-success');
        
        setTimeout(() => {
            copyBtn.innerHTML = originalText;
            copyBtn.classList.remove('copy-success');
        }, 2000);
        
        showToast('Code copied to clipboard!', 'success');
    }, (err) => {
        console.error('Failed to copy text: ', err);
        showToast('Failed to copy code. Please try again.', 'danger');
    });
}

/**
 * Download code as a file
 */
function downloadCode(elementId, filename) {
    const codeElement = document.getElementById(elementId);
    const textToDownload = codeElement.textContent;
    
    const element = document.createElement('a');
    element.setAttribute('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(textToDownload));
    element.setAttribute('download', filename);
    
    element.style.display = 'none';
    document.body.appendChild(element);
    
    element.click();
    
    document.body.removeChild(element);
    
    showToast(`Code downloaded as ${filename}`, 'success');
}

/**
 * Update language badge in code panel
 */
function updateLanguageBadge(targetLanguage) {
    const languageBadge = document.getElementById('codeLanguageBadge');
    let displayLanguage = '';
    
    // Extract display language from the value
    if (targetLanguage.includes('-')) {
        const parts = targetLanguage.split('-');
        displayLanguage = parts[0].charAt(0).toUpperCase() + parts[0].slice(1) + ' (' + parts[1].charAt(0).toUpperCase() + parts[1].slice(1) + ')';
    } else {
        displayLanguage = targetLanguage.charAt(0).toUpperCase() + targetLanguage.slice(1);
    }
    
    languageBadge.textContent = displayLanguage;
}

/**
 * Get appropriate file extension based on language
 */
function getFileNameForCode() {
    const targetLanguage = document.getElementById('targetLanguage').value;
    const baseName = 'generated_code';
    
    if (targetLanguage.startsWith('python')) {
        return baseName + '.py';
    } else if (targetLanguage.startsWith('java')) {
        return baseName + '.java';
    } else if (targetLanguage.startsWith('csharp')) {
        return baseName + '.cs';
    } else if (targetLanguage.startsWith('javascript')) {
        return baseName + '.js';
    } else if (targetLanguage.startsWith('ruby')) {
        return baseName + '.rb';
    } else if (targetLanguage.startsWith('vbscript')) {
        return baseName + '.vbs';
    } else {
        return baseName + '.txt';
    }
}

/**
 * Get highlighting language class from target language
 */
function getLanguageClass(targetLanguage) {
    if (targetLanguage.startsWith('python')) {
        return 'python';
    } else if (targetLanguage.startsWith('java')) {
        return 'java';
    } else if (targetLanguage.startsWith('csharp')) {
        return 'csharp';
    } else if (targetLanguage.startsWith('javascript')) {
        return 'javascript';
    } else if (targetLanguage.startsWith('ruby')) {
        return 'ruby';
    } else if (targetLanguage.startsWith('vbscript')) {
        return 'vbscript';
    } else {
        return 'plaintext';
    }
}

/**
 * Get test case name from ID
 */
function getTestCaseName(testCaseId) {
    // Mock data - in a real app, this would come from an API
    const testCaseMap = {
        'TC-1001': 'Login Functionality',
        'TC-1002': 'User Registration',
        'TC-1003': 'Password Reset',
        'TC-2001': 'Product Search',
        'TC-2002': 'Shopping Cart',
        'TC-3001': 'Payment Processing'
    };
    
    return testCaseMap[testCaseId] || 'Unknown Test Case';
}

/**
 * Show toast message
 */
function showToast(message, type = 'success') {
    const toast = document.getElementById('successToast');
    const toastMessage = document.getElementById('toastMessage');
    
    if (toast && toastMessage) {
        // Update toast styles based on type
        toast.classList.remove('bg-success', 'bg-danger', 'bg-info', 'bg-warning');
        
        switch (type) {
            case 'success':
                toast.classList.add('bg-success');
                break;
            case 'danger':
                toast.classList.add('bg-danger');
                break;
            case 'warning':
                toast.classList.add('bg-warning');
                break;
            case 'info':
                toast.classList.add('bg-info');
                break;
            default:
                toast.classList.add('bg-success');
        }
        
        toastMessage.textContent = message;
        
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
    }
}

/**
 * Simulate code refinement
 */
function simulateCodeRefinement(currentCode, targetLanguage, options) {
    // In a real app, this would make an API call to refine the code
    // For this demo, we'll just add some comments about what changes would be made
    
    let refinedCode = currentCode;
    
    // Add an explanatory comment at the top
    refinedCode = `${currentCode}\n\n# CODE REFINEMENT APPLIED:`;
    
    if (options.addComments) {
        refinedCode += `\n# - Enhanced code comments`;
    }
    
    if (options.enhanceErrorHandling) {
        refinedCode += `\n# - Added more robust error handling`;
    }
    
    if (options.optimizeCode) {
        refinedCode += `\n# - Optimized code for better performance`;
    }
    
    if (options.changeSelectors) {
        refinedCode += `\n# - Changed element selectors to more robust ones`;
    }
    
    if (options.includeWaits) {
        refinedCode += `\n# - Added explicit waits for better synchronization`;
    }
    
    if (options.customRequest && options.customRequest.trim() !== '') {
        refinedCode += `\n# - Applied custom changes: ${options.customRequest}`;
    }
    
    return refinedCode;
}

/**
 * Generate a generic click function for Python Selenium
 */
function generateGenericClickFunction(includeErrorHandling) {
    if (includeErrorHandling) {
        return `\ndef click_element(driver, locator_type, locator_value, timeout=10):
    """
    Click on an element safely with explicit wait
    
    Args:
        driver: WebDriver instance
        locator_type: By.ID, By.CSS_SELECTOR, etc.
        locator_value: The ID, CSS selector, etc.
        timeout: Maximum wait time in seconds
    
    Returns:
        bool: True if click successful, False otherwise
    """
    try:
        # Wait for the element to be clickable
        element = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((locator_type, locator_value))
        )
        
        # Scroll element into view
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
        
        # Click the element
        element.click()
        
        return True
    except Exception as e:
        print(f"Error clicking element: {str(e)}")
        return False

# Example usage
if __name__ == "__main__":
    driver = webdriver.Chrome()
    driver.get("https://example.com")
    
    # Click on a button with ID 'submit'
    success = click_element(driver, By.ID, "submit")
    
    if success:
        print("Button clicked successfully!")
    else:
        print("Failed to click button.")
    
    driver.quit()`;
    } else {
        return `\ndef click_element(driver, locator_type, locator_value):
    """
    Click on an element
    
    Args:
        driver: WebDriver instance
        locator_type: By.ID, By.CSS_SELECTOR, etc.
        locator_value: The ID, CSS selector, etc.
    """
    element = driver.find_element(locator_type, locator_value)
    element.click()

# Example usage
if __name__ == "__main__":
    driver = webdriver.Chrome()
    driver.get("https://example.com")
    
    # Click on a button with ID 'submit'
    click_element(driver, By.ID, "submit")
    
    driver.quit()`;
    }
}
/**
 * Watsonx for IPG Testing - Test Execution Module
 * JavaScript for handling test execution interfaces and interactions
 */

$(document).ready(function () {
    // Tab management
    $('#executionTabs button').on('click', function (e) {
        e.preventDefault();
        $(this).tab('show');
    });

    // Initialize counters for selected tests
    updateSelectedCounters();

    // Toggle between automated and manual execution options
    $('input[name="executionType"]').on('change', function() {
        const executionType = $('input[name="executionType"]:checked').val();
        if (executionType === 'automated') {
            $('#automatedOptions').show();
            $('#manualOptions').hide();
            $('#automatedExecuteBtn').show();
            $('#manualExecuteBtn').hide();
        } else {
            $('#automatedOptions').hide();
            $('#manualOptions').show();
            $('#automatedExecuteBtn').hide();
            $('#manualExecuteBtn').show();
        }
    });

    // Test Case Selection in "Initiate Execution" tab
    $('#selectAllCheckbox').on('change', function() {
        const isChecked = $(this).prop('checked');
        $('.test-case-checkbox:not(:disabled)').prop('checked', isChecked);
        updateSelectedCounters();
    });

    $('.test-case-checkbox').on('change', function() {
        updateSelectedCounters();
        // Uncheck "select all" if any individual checkbox is unchecked
        if (!$(this).prop('checked')) {
            $('#selectAllCheckbox').prop('checked', false);
        }
        // Check "select all" if all individual checkboxes are checked
        else if ($('.test-case-checkbox:checked').length === $('.test-case-checkbox:not(:disabled)').length) {
            $('#selectAllCheckbox').prop('checked', true);
        }
    });

    // Select/Deselect All buttons
    $('#selectAllBtn').on('click', function() {
        $('.test-case-checkbox:not(:disabled)').prop('checked', true);
        $('#selectAllCheckbox').prop('checked', true);
        updateSelectedCounters();
    });

    $('#deselectAllBtn').on('click', function() {
        $('.test-case-checkbox').prop('checked', false);
        $('#selectAllCheckbox').prop('checked', false);
        updateSelectedCounters();
    });

    // Controller file and driver script selection
    $('#changeControllerBtn').on('click', function() {
        $('#controllerFileModal').modal('show');
    });

    $('#changeDriverBtn').on('click', function() {
        $('#driverScriptModal').modal('show');
    });

    // Select controller file from modal
    $('#selectControllerBtn').on('click', function() {
        const selectedFile = $('#controllerFileSelect').val();
        $('#controllerFile').val(selectedFile);
        $('#controllerFileModal').modal('hide');
    });

    // Select driver script from modal
    $('#selectDriverBtn').on('click', function() {
        const selectedScript = $('#driverScriptSelect').val();
        $('#driverScript').val(selectedScript);
        $('#driverScriptModal').modal('hide');
    });

    // Filter test cases in the initiate execution tab
    $('#search-test-cases').on('keyup', function() {
        const searchText = $(this).val().toLowerCase();
        $('#execution-test-cases-table tbody tr').each(function() {
            const rowText = $(this).text().toLowerCase();
            if (rowText.includes(searchText)) {
                $(this).show();
            } else {
                $(this).hide();
            }
        });
    });

    // Filter by status and type
    $('#filter-status, #filter-type').on('change', function() {
        filterTestCases();
    });

    // Execution button handlers
    $('#prepareRunTestsBtn').on('click', function() {
        if (validateExecutionForm()) {
            simulateAutomatedExecution();
        }
    });

    $('#notifyTesterBtn').on('click', function() {
        if (validateExecutionForm()) {
            simulateManualExecution();
        }
    });

    // Dashboard tab functionality
    $('#refreshDashboardBtn').on('click', function() {
        // Simulate refresh with loading animation
        const $icon = $(this).find('i');
        $icon.addClass('fa-spin');
        setTimeout(function() {
            $icon.removeClass('fa-spin');
            showToast('Dashboard refreshed successfully', 'success');
        }, 1000);
    });

    // Dashboard filter
    $('#dashboard-filter').on('change', function() {
        filterExecutionRuns($(this).val());
    });

    // Collapse/Expand monitor
    $('#collapseMonitorBtn').on('click', function() {
        const $icon = $(this).find('i');
        if ($('#activeMonitorContent').hasClass('show')) {
            $icon.removeClass('fa-chevron-up').addClass('fa-chevron-down');
        } else {
            $icon.removeClass('fa-chevron-down').addClass('fa-chevron-up');
        }
    });

    // View Run Details button
    $('.view-run-details').on('click', function() {
        const runId = $(this).data('id');
        populateRunDetailsModal(runId);
        $('#viewRunDetailsModal').modal('show');
    });

    // Analyze Failures button
    $('.analyze-failures').on('click', function() {
        const runId = $(this).data('id');
        $('#analyzeFailuresRunId').text(runId);
        $('#analyzeFailuresModal').modal('show');
    });

    // View Report button
    $('.view-report').on('click', function() {
        const runId = $(this).data('id');
        $('#reportRunId').text(runId);
        $('#viewReportModal').modal('show');
    });

    // Abort Run button
    $('.abort-run').on('click', function() {
        const runId = $(this).data('id');
        if (confirm(`Are you sure you want to abort run ${runId}?`)) {
            simulateAbortRun(runId);
        }
    });

    // Upload Manual Results functionality
    $('#testRunID').on('change', function() {
        const selectedRunId = $(this).val();
        if (selectedRunId) {
            showRunDetailsPreview(selectedRunId);
        } else {
            $('.run-details-preview').hide();
        }
    });

    // Handle file uploads
    $('#resultFiles').on('change', function() {
        if (this.files.length > 0) {
            $('.upload-summary').show();
            updateFileList(this.files);
        } else {
            $('.upload-summary').hide();
        }
    });

    // Remove file button
    $(document).on('click', '.remove-file', function() {
        $(this).closest('tr').remove();
        if ($('#fileList tr').length === 0) {
            $('.upload-summary').hide();
        }
    });

    // Test result radio buttons
    $('input[name="testResult"]').on('change', function() {
        const result = $(this).val();
        if (result === 'passed_with_issues' || result === 'failed') {
            $('.issues-section').show();
        } else {
            $('.issues-section').hide();
        }
    });

    // Add issue button
    $('.add-issue-btn').on('click', function() {
        const newIssueItem = `
            <div class="issue-item mb-2">
                <div class="input-group">
                    <input type="text" class="form-control" placeholder="Describe the issue...">
                    <select class="form-select" style="max-width: 140px;">
                        <option value="minor">Minor</option>
                        <option value="major">Major</option>
                        <option value="critical">Critical</option>
                    </select>
                    <button class="btn btn-outline-danger" type="button"><i class="fas fa-trash"></i></button>
                </div>
            </div>
        `;
        $('.issues-list').append(newIssueItem);
    });

    // Remove issue button
    $(document).on('click', '.issues-list .btn-outline-danger', function() {
        $(this).closest('.issue-item').remove();
    });

    // Upload to SharePoint button
    $('#uploadToSharePointBtn').on('click', function() {
        if (validateUploadForm()) {
            simulateSharePointUpload();
        }
    });

    // Cancel Upload button
    $('#cancelUploadBtn').on('click', function() {
        if (confirm('Are you sure you want to cancel? All entered data will be lost.')) {
            resetUploadForm();
        }
    });

    // View in SharePoint button
    $('#viewSharePointBtn').on('click', function() {
        // Simulate opening SharePoint in a new tab
        window.open('#', '_blank');
    });

    // View in Dashboard button from success modal
    $('#viewExecutionDashboardBtn').on('click', function() {
        $('#executionSuccessModal').modal('hide');
        // Switch to dashboard tab
        $('#executionTabs button[data-bs-target="#dashboard"]').tab('show');
    });

    // Handle drag and drop file uploads
    setupDragAndDrop();
});

/**
 * Update selected test case counter displays
 */
function updateSelectedCounters() {
    const totalSelected = $('.test-case-checkbox:checked').length;
    $('#selectedCount').text(totalSelected);
    
    // Count automated vs manual tests
    let automatedCount = 0;
    let manualCount = 0;
    
    $('.test-case-checkbox:checked').each(function() {
        const rowType = $(this).closest('tr').find('td:eq(4)').text().trim();
        if (rowType.includes('Automated')) {
            automatedCount++;
        } else if (rowType.includes('Manual')) {
            manualCount++;
        }
    });
    
    $('#automatedCount').text(automatedCount);
    $('#manualCount').text(manualCount);
}

/**
 * Filter test cases based on selected criteria
 */
function filterTestCases() {
    const statusFilter = $('#filter-status').val().toLowerCase();
    const typeFilter = $('#filter-type').val().toLowerCase();
    const searchText = $('#search-test-cases').val().toLowerCase();
    
    $('#execution-test-cases-table tbody tr').each(function() {
        const rowText = $(this).text().toLowerCase();
        const status = $(this).find('td:eq(3)').text().toLowerCase();
        const type = $(this).find('td:eq(4)').text().toLowerCase();
        
        const matchesSearch = searchText === '' || rowText.includes(searchText);
        const matchesStatus = statusFilter === '' || status.includes(statusFilter);
        const matchesType = typeFilter === '' || type.includes(typeFilter);
        
        if (matchesSearch && matchesStatus && matchesType) {
            $(this).show();
        } else {
            $(this).hide();
        }
    });
}

/**
 * Filter execution runs based on time period
 */
function filterExecutionRuns(filter) {
    // This would typically involve a server call
    // For demo, we just show a loading indicator
    $('#execution-runs-table tbody').addClass('opacity-50');
    setTimeout(() => {
        $('#execution-runs-table tbody').removeClass('opacity-50');
        showToast(`Filtered to show ${filter} execution runs`, 'info');
    }, 500);
}

/**
 * Validate execution form before submitting
 */
function validateExecutionForm() {
    // Check if any test cases are selected
    if ($('.test-case-checkbox:checked').length === 0) {
        showToast('Please select at least one test case to execute', 'warning');
        return false;
    }
    
    // Check execution name
    if (!$('#executionName').val().trim()) {
        showToast('Please enter an execution name', 'warning');
        $('#executionName').focus();
        return false;
    }
    
    // If manual execution, check if tester is assigned
    const executionType = $('input[name="executionType"]:checked').val();
    if (executionType === 'manual' && !$('#assignTester').val()) {
        showToast('Please assign a tester for manual execution', 'warning');
        $('#assignTester').focus();
        return false;
    }
    
    return true;
}

/**
 * Validate upload form before submitting
 */
function validateUploadForm() {
    // Check if test run is selected
    if (!$('#testRunID').val()) {
        showToast('Please select a test run', 'warning');
        $('#testRunID').focus();
        return false;
    }
    
    // Check if files are selected
    if ($('#fileList tr').length === 0) {
        showToast('Please upload at least one result file', 'warning');
        return false;
    }
    
    // Check if test result is selected
    if (!$('input[name="testResult"]:checked').val()) {
        showToast('Please select an overall test result', 'warning');
        return false;
    }
    
    return true;
}

/**
 * Reset upload form to initial state
 */
function resetUploadForm() {
    $('#uploadResultsForm')[0].reset();
    $('.run-details-preview').hide();
    $('.upload-summary').hide();
    $('.issues-section').hide();
    $('#fileList').empty();
}

/**
 * Display run details in the preview section
 */
function showRunDetailsPreview(runId) {
    // In a real app, this would fetch data from the server
    // For demo, we're using hardcoded values
    
    let runName, runStatus, runAssigned, runStart, runDue, runCases;
    
    if (runId === 'RUN-1004') {
        runName = 'User Profile Tests';
        runStatus = '<span class="badge bg-secondary">Scheduled</span>';
        runAssigned = 'John Doe';
        runStart = '2025-05-10 10:00:00';
        runDue = '2025-05-11 17:00:00';
        runCases = '5 test cases';
    } else if (runId === 'RUN-1005') {
        runName = 'Registration Flow Tests';
        runStatus = '<span class="badge bg-warning">In Progress</span>';
        runAssigned = 'Jane Smith';
        runStart = '2025-05-09 09:00:00';
        runDue = '2025-05-09 17:00:00';
        runCases = '5 test cases (2 completed, 3 pending)';
    }
    
    $('#preview-run-name').html(runName);
    $('#preview-run-status').html(runStatus);
    $('#preview-run-assigned').text(runAssigned);
    $('#preview-run-start').text(runStart);
    $('#preview-run-due').text(runDue);
    $('#preview-run-cases').text(runCases);
    
    $('.run-details-preview').show();
}

/**
 * Update file list in the upload summary section
 */
function updateFileList(files) {
    $('#fileList').empty();
    
    for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const fileSize = formatFileSize(file.size);
        const fileType = getFileTypeLabel(file.name);
        
        const row = `
            <tr>
                <td>${file.name}</td>
                <td>${fileType}</td>
                <td>${fileSize}</td>
                <td>
                    <button type="button" class="btn btn-sm btn-outline-danger remove-file">
                        <i class="fas fa-times"></i>
                    </button>
                </td>
            </tr>
        `;
        
        $('#fileList').append(row);
    }
}

/**
 * Format file size in human-readable format
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * Get file type label based on file extension
 */
function getFileTypeLabel(filename) {
    const extension = filename.split('.').pop().toLowerCase();
    
    switch (extension) {
        case 'xlsx':
        case 'xls':
            return 'Excel';
        case 'pdf':
            return 'PDF';
        case 'csv':
            return 'CSV';
        case 'png':
        case 'jpg':
        case 'jpeg':
        case 'gif':
            return 'Image';
        default:
            return 'Document';
    }
}

/**
 * Setup drag and drop functionality for file uploads
 */
function setupDragAndDrop() {
    const dropArea = document.querySelector('.upload-area');
    
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, preventDefaults, false);
    });
    
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    ['dragenter', 'dragover'].forEach(eventName => {
        dropArea.addEventListener(eventName, highlight, false);
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, unhighlight, false);
    });
    
    function highlight() {
        dropArea.classList.add('bg-light-hover');
    }
    
    function unhighlight() {
        dropArea.classList.remove('bg-light-hover');
    }
    
    dropArea.addEventListener('drop', handleDrop, false);
    
    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        
        $('#resultFiles')[0].files = files;
        $('#resultFiles').trigger('change');
    }
}

/**
 * Populate run details modal with data for the selected run
 */
function populateRunDetailsModal(runId) {
    // In a real app, this would fetch data from the server
    // For demo, we're using hardcoded values
    
    $('#modalRunId').text(runId);
    
    if (runId === 'RUN-1001') {
        $('#modalRunName').text('Login Test Suite');
        $('#modalRunStatus').html('<span class="badge bg-success">Completed</span>');
        $('#modalRunType').html('<span class="badge bg-info">Automated</span>');
        $('#modalRunUser').text('John Doe');
        $('#modalRunStartTime').text('2025-05-09 09:30:00');
        $('#modalRunEndTime').text('2025-05-09 09:35:12');
        $('#modalRunDuration').text('5m 12s');
        $('#modalRunEnvironment').text('Test');
        $('#modalRunController').text('/path/to/controller.xlsx');
        $('#modalTotalTests').text('12');
        $('#modalPassedTests').text('12');
        $('#modalFailedTests').text('0');
        $('#modalSkippedTests').text('0');
        
        // Clear test case results table and add rows for this run
        $('#modalTestCaseResults').html(`
            <tr>
                <td>TC-1001</td>
                <td>Verify login with valid credentials</td>
                <td><span class="badge bg-success">Passed</span></td>
                <td>1.2s</td>
                <td>
                    <button class="btn btn-sm btn-outline-primary view-test-details" data-id="TC-1001">View Details</button>
                </td>
            </tr>
            <tr>
                <td>TC-1002</td>
                <td>Verify login with invalid credentials</td>
                <td><span class="badge bg-success">Passed</span></td>
                <td>0.8s</td>
                <td>
                    <button class="btn btn-sm btn-outline-primary view-test-details" data-id="TC-1002">View Details</button>
                </td>
            </tr>
        `);
    } else if (runId === 'RUN-1002') {
        $('#modalRunName').text('Checkout Process Tests');
        $('#modalRunStatus').html('<span class="badge bg-warning">In Progress</span>');
        $('#modalRunType').html('<span class="badge bg-info">Automated</span>');
        $('#modalRunUser').text('Jane Smith');
        $('#modalRunStartTime').text('2025-05-09 09:45:00');
        $('#modalRunEndTime').text('--');
        $('#modalRunDuration').text('15m 12s (ongoing)');
        $('#modalRunEnvironment').text('Test');
        $('#modalRunController').text('/path/to/controller.xlsx');
        $('#modalTotalTests').text('10');
        $('#modalPassedTests').text('3');
        $('#modalFailedTests').text('1');
        $('#modalSkippedTests').text('0');
        
        // Populate test case results for this run
        $('#modalTestCaseResults').html(`
            <tr>
                <td>TC-1003</td>
                <td>Verify product added to cart</td>
                <td><span class="badge bg-success">Passed</span></td>
                <td>27s</td>
                <td>
                    <button class="btn btn-sm btn-outline-primary view-test-details" data-id="TC-1003">View Details</button>
                </td>
            </tr>
            <tr>
                <td>TC-1004</td>
                <td>Verify cart update quantity</td>
                <td><span class="badge bg-success">Passed</span></td>
                <td>28s</td>
                <td>
                    <button class="btn btn-sm btn-outline-primary view-test-details" data-id="TC-1004">View Details</button>
                </td>
            </tr>
            <tr>
                <td>TC-1005</td>
                <td>Verify remove item from cart</td>
                <td><span class="badge bg-success">Passed</span></td>
                <td>26s</td>
                <td>
                    <button class="btn btn-sm btn-outline-primary view-test-details" data-id="TC-1005">View Details</button>
                </td>
            </tr>
            <tr>
                <td>TC-1006</td>
                <td>Verify checkout process</td>
                <td><span class="badge bg-danger">Failed</span></td>
                <td>4m 16s</td>
                <td>
                    <button class="btn btn-sm btn-outline-primary view-test-details" data-id="TC-1006">View Details</button>
                </td>
            </tr>
            <tr>
                <td>TC-1007</td>
                <td>Verify payment processing</td>
                <td><span class="badge bg-secondary">Running</span></td>
                <td>--</td>
                <td>
                    <button class="btn btn-sm btn-outline-primary view-test-details" data-id="TC-1007" disabled>View Details</button>
                </td>
            </tr>
        `);
    } else if (runId === 'RUN-1003') {
        $('#modalRunName').text('Payment Processing Tests');
        $('#modalRunStatus').html('<span class="badge bg-danger">Failed</span>');
        $('#modalRunType').html('<span class="badge bg-info">Automated</span>');
        $('#modalRunUser').text('Alex Wilson');
        $('#modalRunStartTime').text('2025-05-09 08:30:00');
        $('#modalRunEndTime').text('2025-05-09 08:45:23');
        $('#modalRunDuration').text('15m 23s');
        $('#modalRunEnvironment').text('Test');
        $('#modalRunController').text('/path/to/controller.xlsx');
        $('#modalTotalTests').text('7');
        $('#modalPassedTests').text('4');
        $('#modalFailedTests').text('3');
        $('#modalSkippedTests').text('0');
    }
}

/**
 * Simulate starting an automated test execution
 */
function simulateAutomatedExecution() {
    // Show loading state on button
    const $button = $('#prepareRunTestsBtn');
    const originalText = $button.html();
    $button.html('<i class="fas fa-spinner fa-spin me-2"></i>Processing...');
    $button.prop('disabled', true);
    
    // In a real app, this would submit data to the server
    // For demo, we're just showing a success message after a delay
    setTimeout(() => {
        // Restore button state
        $button.html(originalText);
        $button.prop('disabled', false);
        
        // Show success modal
        $('#successRunId').text('RUN-1006');
        $('#successRunName').text($('#executionName').val());
        $('#successRunCases').text($('.test-case-checkbox:checked').length + ' test cases selected');
        $('#successRunStartTime').text(new Date().toLocaleString());
        $('#executionSuccessModal').modal('show');
    }, 2000);
}

/**
 * Simulate starting a manual test execution
 */
function simulateManualExecution() {
    // Show loading state on button
    const $button = $('#notifyTesterBtn');
    const originalText = $button.html();
    $button.html('<i class="fas fa-spinner fa-spin me-2"></i>Sending Notification...');
    $button.prop('disabled', true);
    
    // In a real app, this would submit data to the server
    // For demo, we're just showing a success message after a delay
    setTimeout(() => {
        // Restore button state
        $button.html(originalText);
        $button.prop('disabled', false);
        
        // Show toast notification
        showToast(`Notification sent to ${$('#assignTester').val()} for manual execution`, 'success');
        
        // Show success modal
        $('#successRunId').text('RUN-1007');
        $('#successRunName').text($('#executionName').val());
        $('#successRunCases').text($('.test-case-checkbox:checked').length + ' test cases selected');
        $('#successRunStartTime').text('Manual execution scheduled for ' + ($('#dueDate').val() || 'today'));
        $('#executionSuccessModal').modal('show');
    }, 1500);
}

/**
 * Simulate aborting a test run
 */
function simulateAbortRun(runId) {
    // Show a loading indicator
    showToast(`Aborting run ${runId}...`, 'info');
    
    // In a real app, this would call the server to abort the run
    // For demo, we're just showing a success message after a delay
    setTimeout(() => {
        // Show success notification
        showToast(`Run ${runId} aborted successfully`, 'success');
        
        // Update UI to reflect aborted status
        $(`button.abort-run[data-id="${runId}"]`).closest('tr').find('td:eq(2)').html('<span class="badge bg-danger">Aborted</span>');
        $(`button.abort-run[data-id="${runId}"]`).prop('disabled', true);
    }, 1500);
}

/**
 * Simulate uploading test results to SharePoint
 */
function simulateSharePointUpload() {
    // Show loading state on button
    const $button = $('#uploadToSharePointBtn');
    const originalText = $button.html();
    $button.html('<i class="fas fa-spinner fa-spin me-2"></i>Uploading...');
    $button.prop('disabled', true);
    
    // In a real app, this would submit data to the server
    // For demo, we're just showing a success message after a delay
    setTimeout(() => {
        // Restore button state
        $button.html(originalText);
        $button.prop('disabled', false);
        
        // Show success modal
        $('#uploadRunId').text($('#testRunID').val());
        $('#uploadLocation').text(`/Test Results/Manual Tests/2025/May/${$('#testRunID').val()}`);
        $('#uploadFileCount').text($('#fileList tr').length + ' files');
        $('#uploadTime').text(new Date().toLocaleString());
        $('#uploadSuccessModal').modal('show');
        
        // Reset form
        resetUploadForm();
    }, 2000);
}

/**
 * Display a toast notification
 */
function showToast(message, type = 'info') {
    // Check if toast container exists, create if not
    if ($('#toast-container').length === 0) {
        $('body').append('<div id="toast-container" class="position-fixed bottom-0 end-0 p-3" style="z-index: 5"></div>');
    }
    
    // Create a unique ID for this toast
    const toastId = 'toast-' + new Date().getTime();
    
    // Set color based on type
    let bgClass = 'bg-info';
    switch (type) {
        case 'success':
            bgClass = 'bg-success';
            break;
        case 'warning':
            bgClass = 'bg-warning';
            break;
        case 'danger':
        case 'error':
            bgClass = 'bg-danger';
            break;
    }
    
    // Create toast HTML
    const toastHtml = `
        <div id="${toastId}" class="toast text-white ${bgClass}" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="toast-header">
                <strong class="me-auto">Watsonx for IPG Testing</strong>
                <small>Just now</small>
                <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
        </div>
    `;
    
    // Add toast to container
    $('#toast-container').append(toastHtml);
    
    // Initialize and show toast
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement, { delay: 5000 });
    toast.show();
    
    // Remove toast from DOM after it's hidden
    toastElement.addEventListener('hidden.bs.toast', function () {
        $(this).remove();
    });
}
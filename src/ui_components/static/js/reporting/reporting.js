/**
 * Reporting Module JavaScript
 * Handles the functionality for the ALM Report Utility and View Reports sections
 */

document.addEventListener('DOMContentLoaded', function() {
    // Elements from ALM Report Utility section
    const connectionStatus = document.getElementById('connectionStatus');
    const refreshConnection = document.getElementById('refreshConnection');
    const fetchReportBtn = document.getElementById('fetchReportBtn');
    const progressContainer = document.getElementById('progressContainer');
    const reportProgress = document.getElementById('reportProgress');
    const progressStatus = document.getElementById('progressStatus');
    const statusLogContainer = document.getElementById('statusLogContainer');
    const statusLog = document.getElementById('statusLog');
    const completionActions = document.getElementById('completionActions');
    const shareReportBtn = document.getElementById('shareReportBtn');
    const viewReportBtn = document.getElementById('viewReportBtn');
    
    // Elements from View Reports section
    const dateRangeFilter = document.getElementById('dateRangeFilter');
    const customDateRange = document.getElementById('customDateRange');
    const applyFilters = document.getElementById('applyFilters');
    const refreshReportsList = document.getElementById('refreshReportsList');
    const reportsTableBody = document.getElementById('reportsTableBody');
    const sortLinks = document.querySelectorAll('.sort-link');
    
    // Modal elements
    const shareReportModal = new bootstrap.Modal(document.getElementById('shareReportModal'));
    const viewReportModal = new bootstrap.Modal(document.getElementById('viewReportModal'));
    const sendReportBtn = document.getElementById('sendReportBtn');
    
    // Variables to track state
    let currentSort = { field: 'date', direction: 'desc' };
    let isReportGenerating = false;
    let reportGenerationTimer = null;
    
    // Initialize charts when metrics tab is shown
    const metricsTab = document.getElementById('metrics-tab');
    if (metricsTab) {
        metricsTab.addEventListener('shown.bs.tab', initializeCharts);
    }
    
    // ---------------------------------------------------
    // ALM Report Utility Functions
    // ---------------------------------------------------
    
    /**
     * Check connection status with the Excel macro utility
     */
    function checkConnectionStatus() {
        // Simulate checking connection - in a real implementation, this would make an API call
        refreshConnection.disabled = true;
        refreshConnection.innerHTML = '<i class="fas fa-sync-alt fa-spin"></i>';
        
        setTimeout(() => {
            // Simulate random connection status for demo purposes
            const statusOptions = [
                { status: 'Connected', class: 'bg-success' },
                { status: 'Connecting...', class: 'bg-warning' },
                { status: 'Disconnected', class: 'bg-danger' }
            ];
            
            const randomStatus = Math.random() > 0.3 ? statusOptions[0] : 
                               (Math.random() > 0.5 ? statusOptions[1] : statusOptions[2]);
            
            connectionStatus.textContent = randomStatus.status;
            connectionStatus.className = `badge ${randomStatus.class}`;
            
            refreshConnection.disabled = false;
            refreshConnection.innerHTML = '<i class="fas fa-sync-alt"></i>';
            
            // Update fetch report button state based on connection status
            fetchReportBtn.disabled = randomStatus.class === 'bg-danger';
            
            addLogEntry(`Connection status checked: ${randomStatus.status}`);
        }, 1500);
    }
    
    /**
     * Add entry to the status log
     */
    function addLogEntry(message, type = '') {
        const now = new Date();
        const timestamp = now.toLocaleTimeString();
        
        const logEntry = document.createElement('div');
        logEntry.className = 'log-entry';
        
        const timestampSpan = document.createElement('span');
        timestampSpan.className = 'timestamp';
        timestampSpan.textContent = timestamp;
        
        const messageSpan = document.createElement('span');
        messageSpan.className = type ? `log-message ${type}` : 'log-message';
        messageSpan.textContent = message;
        
        logEntry.appendChild(timestampSpan);
        logEntry.appendChild(messageSpan);
        
        statusLog.appendChild(logEntry);
        
        // Auto-scroll to bottom
        statusLog.scrollTop = statusLog.scrollHeight;
    }
    
    /**
     * Start report generation process
     */
    function generateReport() {
        if (isReportGenerating) return;
        
        isReportGenerating = true;
        fetchReportBtn.disabled = true;
        
        // Show progress container and status log
        progressContainer.classList.remove('d-none');
        statusLogContainer.classList.remove('d-none');
        completionActions.classList.add('d-none');
        
        // Clear previous log
        statusLog.innerHTML = '';
        
        // Add initial log entry
        addLogEntry('Starting report generation...');
        
        // Set initial progress
        reportProgress.style.width = '0%';
        progressStatus.textContent = 'Initializing report generation...';
        
        // Simulate report generation process
        const steps = [
            { progress: 10, message: 'Connecting to ALM...', delay: 1500 },
            { progress: 20, message: 'Authentication successful.', delay: 1000 },
            { progress: 30, message: 'Fetching test execution data...', delay: 2000 },
            { progress: 50, message: 'Fetching defect data...', delay: 2500 },
            { progress: 70, message: 'Processing data...', delay: 1800 },
            { progress: 85, message: 'Generating report...', delay: 2200 },
            { progress: 95, message: 'Finalizing...', delay: 1000 },
            { progress: 100, message: 'Report generation completed!', delay: 800 }
        ];
        
        let stepIndex = 0;
        
        function processStep() {
            if (stepIndex < steps.length) {
                const step = steps[stepIndex];
                
                // Update progress
                reportProgress.style.width = `${step.progress}%`;
                reportProgress.setAttribute('aria-valuenow', step.progress);
                progressStatus.textContent = step.message;
                
                // Add log entry
                addLogEntry(step.message, step.progress === 100 ? 'success' : '');
                
                // Process next step after delay
                stepIndex++;
                setTimeout(processStep, step.delay);
            } else {
                // Report generation completed
                completeReportGeneration();
            }
        }
        
        // Start processing steps
        processStep();
    }
    
    /**
     * Complete report generation and show actions
     */
    function completeReportGeneration() {
        isReportGenerating = false;
        fetchReportBtn.disabled = false;
        
        // Show completion actions
        completionActions.classList.remove('d-none');
        
        // Add final log entries
        addLogEntry('Report saved to SharePoint.', 'success');
        addLogEntry('Ready to share or view the report.', 'success');
    }
    
    // ---------------------------------------------------
    // View Reports Functions
    // ---------------------------------------------------
    
    /**
     * Filter reports based on selected criteria
     */
    function filterReports() {
        const reportType = document.getElementById('reportTypeFilter').value;
        const dateRange = document.getElementById('dateRangeFilter').value;
        const searchTerm = document.getElementById('searchFilter').value.toLowerCase();
        
        // In a real implementation, this would make an API call with filter parameters
        // For demo purposes, we'll simulate filtering with a timeout
        
        // Show loading state
        reportsTableBody.innerHTML = '<tr><td colspan="5" class="text-center"><i class="fas fa-spinner fa-spin me-2"></i> Filtering reports...</td></tr>';
        
        setTimeout(() => {
            // Fetch sample data (in a real implementation, this would come from the server)
            let reports = getSampleReports();
            
            // Apply filters (simplified for demo)
            if (reportType) {
                reports = reports.filter(report => report.type.toLowerCase() === reportType.toLowerCase());
            }
            
            if (searchTerm) {
                reports = reports.filter(report => 
                    report.name.toLowerCase().includes(searchTerm) || 
                    report.generatedBy.toLowerCase().includes(searchTerm)
                );
            }
            
            // Sort the filtered results
            sortReports(reports);
            
            // Render the filtered results
            renderReportsTable(reports);
        }, 800);
    }
    
    /**
     * Sort reports based on the current sort field and direction
     */
    function sortReports(reports) {
        reports.sort((a, b) => {
            let comparison = 0;
            
            switch (currentSort.field) {
                case 'name':
                    comparison = a.name.localeCompare(b.name);
                    break;
                case 'type':
                    comparison = a.type.localeCompare(b.type);
                    break;
                case 'date':
                    // For demo purposes, using string comparison
                    // In a real implementation, you would parse and compare actual dates
                    comparison = new Date(b.date) - new Date(a.date);
                    break;
                default:
                    comparison = 0;
            }
            
            return currentSort.direction === 'asc' ? comparison : -comparison;
        });
        
        return reports;
    }
    
    /**
     * Render the reports table with the provided data
     */
    function renderReportsTable(reports) {
        if (reports.length === 0) {
            reportsTableBody.innerHTML = '<tr><td colspan="5" class="text-center">No reports found matching the criteria.</td></tr>';
            return;
        }
        
        reportsTableBody.innerHTML = '';
        
        reports.forEach(report => {
            const row = document.createElement('tr');
            
            // Create badge based on report type
            let badgeClass = 'bg-primary';
            if (report.type.toLowerCase() === 'defect') badgeClass = 'bg-danger';
            if (report.type.toLowerCase() === 'analysis') badgeClass = 'bg-info';
            
            row.innerHTML = `
                <td>${report.name}</td>
                <td><span class="badge ${badgeClass}">${report.type}</span></td>
                <td>${report.date}</td>
                <td>${report.generatedBy}</td>
                <td>
                    <div class="btn-group btn-group-sm">
                        <a href="#" class="btn btn-outline-primary view-report-btn" title="View" data-report-id="${report.id}">
                            <i class="fas fa-eye"></i>
                        </a>
                        <a href="#" class="btn btn-outline-secondary" title="Download">
                            <i class="fas fa-download"></i>
                        </a>
                        <a href="#" class="btn btn-outline-success share-report-btn" title="Share" data-report-id="${report.id}">
                            <i class="fas fa-share-alt"></i>
                        </a>
                    </div>
                </td>
            `;
            
            reportsTableBody.appendChild(row);
        });
        
        // Add event listeners to the view and share buttons
        document.querySelectorAll('.view-report-btn').forEach(btn => {
            btn.addEventListener('click', function(e) {
                e.preventDefault();
                viewReportModal.show();
            });
        });
        
        document.querySelectorAll('.share-report-btn').forEach(btn => {
            btn.addEventListener('click', function(e) {
                e.preventDefault();
                shareReportModal.show();
            });
        });
    }
    
    /**
     * Get sample reports data for demo purposes
     */
    function getSampleReports() {
        return [
            {
                id: 1,
                name: 'April Sprint 1 - Execution Summary',
                type: 'Execution',
                date: 'May 5, 2025',
                generatedBy: 'John Doe'
            },
            {
                id: 2,
                name: 'Regression Test - Defect Report',
                type: 'Defect',
                date: 'May 3, 2025',
                generatedBy: 'Jane Smith'
            },
            {
                id: 3,
                name: 'Q2 Test Metrics - Analysis Report',
                type: 'Analysis',
                date: 'May 1, 2025',
                generatedBy: 'Robert Johnson'
            },
            {
                id: 4,
                name: 'Login Feature - Execution Summary',
                type: 'Execution',
                date: 'April 28, 2025',
                generatedBy: 'John Doe'
            },
            {
                id: 5,
                name: 'Payment Processing - Defect Report',
                type: 'Defect',
                date: 'April 25, 2025',
                generatedBy: 'Jane Smith'
            },
            {
                id: 6,
                name: 'Performance Test - Analysis Report',
                type: 'Analysis',
                date: 'April 23, 2025',
                generatedBy: 'Robert Johnson'
            },
            {
                id: 7,
                name: 'User Profile - Execution Summary',
                type: 'Execution',
                date: 'April 20, 2025',
                generatedBy: 'John Doe'
            }
        ];
    }
    
    /**
     * Initialize charts in the metrics tab
     */
    function initializeCharts() {
        if (!window.Chart) {
            console.error('Chart.js not loaded');
            return;
        }
        
        const chartContainers = document.querySelectorAll('.chart-container');
        
        // Clear any placeholder content
        chartContainers.forEach(container => {
            container.innerHTML = '';
        });
        
        // Only proceed if we have chart containers and Chart.js is loaded
        if (chartContainers.length === 0) return;
        
        // Create charts
        createExecutionStatusChart(chartContainers[0]);
        createDefectSeverityChart(chartContainers[1]);
        createExecutionTrendChart(chartContainers[2]);
        createDefectStatusChart(chartContainers[3]);
    }
    
    /**
     * Create Test Execution Status chart
     */
    function createExecutionStatusChart(container) {
        const canvas = document.createElement('canvas');
        container.appendChild(canvas);
        
        new Chart(canvas, {
            type: 'pie',
            data: {
                labels: ['Passed', 'Failed', 'Blocked'],
                datasets: [{
                    data: [98, 18, 10],
                    backgroundColor: ['#198754', '#dc3545', '#ffc107'],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right'
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.label || '';
                                const value = context.raw || 0;
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = Math.round((value / total) * 100);
                                return `${label}: ${value} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
    }
    
    /**
     * Create Defect Severity Distribution chart
     */
    function createDefectSeverityChart(container) {
        const canvas = document.createElement('canvas');
        container.appendChild(canvas);
        
        new Chart(canvas, {
            type: 'doughnut',
            data: {
                labels: ['Critical', 'Major', 'Minor'],
                datasets: [{
                    data: [3, 8, 7],
                    backgroundColor: ['#dc3545', '#ffc107', '#0dcaf0'],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right'
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.label || '';
                                const value = context.raw || 0;
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = Math.round((value / total) * 100);
                                return `${label}: ${value} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
    }
    
    /**
     * Create Test Execution Trend chart
     */
    function createExecutionTrendChart(container) {
        const canvas = document.createElement('canvas');
        container.appendChild(canvas);
        
        new Chart(canvas, {
            type: 'line',
            data: {
                labels: ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
                datasets: [
                    {
                        label: 'Passed',
                        data: [42, 56, 75, 98],
                        borderColor: '#198754',
                        backgroundColor: 'rgba(25, 135, 84, 0.1)',
                        tension: 0.1,
                        fill: true
                    },
                    {
                        label: 'Failed',
                        data: [15, 12, 22, 18],
                        borderColor: '#dc3545',
                        backgroundColor: 'rgba(220, 53, 69, 0.1)',
                        tension: 0.1,
                        fill: true
                    },
                    {
                        label: 'Blocked',
                        data: [8, 12, 6, 10],
                        borderColor: '#ffc107',
                        backgroundColor: 'rgba(255, 193, 7, 0.1)',
                        tension: 0.1,
                        fill: true
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top'
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        stacked: false,
                        title: {
                            display: true,
                            text: 'Number of Test Cases'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Time Period'
                        }
                    }
                }
            }
        });
    }
    
    /**
     * Create Defect Status Distribution chart
     */
    function createDefectStatusChart(container) {
        const canvas = document.createElement('canvas');
        container.appendChild(canvas);
        
        new Chart(canvas, {
            type: 'bar',
            data: {
                labels: ['Open', 'In Progress', 'Resolved', 'Closed', 'Reopened'],
                datasets: [{
                    label: 'Number of Defects',
                    data: [7, 5, 3, 2, 1],
                    backgroundColor: [
                        '#0d6efd',
                        '#ffc107',
                        '#198754',
                        '#6c757d',
                        '#dc3545'
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Number of Defects'
                        }
                    }
                }
            }
        });
    }
    
    // ---------------------------------------------------
    // Event Listeners
    // ---------------------------------------------------
    
    // Check connection status on page load
    checkConnectionStatus();
    
    // Refresh connection button
    if (refreshConnection) {
        refreshConnection.addEventListener('click', checkConnectionStatus);
    }
    
    // Fetch report button
    if (fetchReportBtn) {
        fetchReportBtn.addEventListener('click', generateReport);
    }
    
    // Share report button
    if (shareReportBtn) {
        shareReportBtn.addEventListener('click', function() {
            shareReportModal.show();
        });
    }
    
    // View report button
    if (viewReportBtn) {
        viewReportBtn.addEventListener('click', function() {
            viewReportModal.show();
        });
    }
    
    // Date range filter change
    if (dateRangeFilter) {
        dateRangeFilter.addEventListener('change', function() {
            if (this.value === 'custom') {
                customDateRange.classList.remove('d-none');
            } else {
                customDateRange.classList.add('d-none');
            }
        });
    }
    
    // Apply filters button
    if (applyFilters) {
        applyFilters.addEventListener('click', filterReports);
    }
    
    // Refresh reports list button
    if (refreshReportsList) {
        refreshReportsList.addEventListener('click', function() {
            // Reset filters
            document.getElementById('reportTypeFilter').value = '';
            document.getElementById('dateRangeFilter').value = '';
            document.getElementById('searchFilter').value = '';
            customDateRange.classList.add('d-none');
            
            // Reload reports
            filterReports();
        });
    }
    
    // Send report button in modal
    if (sendReportBtn) {
        sendReportBtn.addEventListener('click', function() {
            // Show sending state
            this.disabled = true;
            this.innerHTML = '<i class="fas fa-circle-notch fa-spin me-2"></i>Sending...';
            
            // Simulate sending email
            setTimeout(() => {
                // Hide modal
                shareReportModal.hide();
                
                // Show success message
                const alertDiv = document.createElement('div');
                alertDiv.className = 'alert alert-success alert-dismissible fade show';
                alertDiv.innerHTML = `
                    <i class="fas fa-check-circle me-2"></i>Report successfully shared with test lead.
                    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                `;
                
                document.querySelector('.messages').appendChild(alertDiv);
                
                // Reset button state
                this.disabled = false;
                this.innerHTML = 'Send Report';
                
                // Auto dismiss alert after 5 seconds
                setTimeout(() => {
                    alertDiv.classList.remove('show');
                }, 5000);
            }, 2000);
        });
    }
    
    // Sort links
    sortLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            
            const sortField = this.getAttribute('data-sort');
            
            // Toggle sort direction if same field, otherwise default to ascending
            if (currentSort.field === sortField) {
                currentSort.direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
            } else {
                currentSort.field = sortField;
                currentSort.direction = 'asc';
            }
            
            // Update sort icons
            sortLinks.forEach(sl => {
                sl.classList.remove('asc', 'desc');
            });
            
            this.classList.add(currentSort.direction);
            
            // Apply filtering with new sort
            filterReports();
        });
    });
    
    // Initialize reports table
    filterReports();
});
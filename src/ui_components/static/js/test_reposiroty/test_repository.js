document.addEventListener('DOMContentLoaded', function() {
    // Initialize all tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Import Source Change Handler
    const importSource = document.getElementById('importSource');
    const fileUploadSection = document.getElementById('fileUploadSection');
    const jiraSection = document.getElementById('jiraSection');
    const almSection = document.getElementById('almSection');

    if (importSource) {
        importSource.addEventListener('change', function() {
            // Hide all sections first
            fileUploadSection.style.display = 'none';
            jiraSection.style.display = 'none';
            almSection.style.display = 'none';
            
            // Show the selected section
            if (this.value === 'file') {
                fileUploadSection.style.display = 'block';
            } else if (this.value === 'jira') {
                jiraSection.style.display = 'block';
            } else if (this.value === 'alm') {
                almSection.style.display = 'block';
            }
        });
    }

    // Compare Source Change Handler
    const compareSource = document.getElementById('compareSource');
    const uploadTestCaseSection = document.getElementById('uploadTestCaseSection');
    const generatedTestCaseSection = document.getElementById('generatedTestCaseSection');

    if (compareSource) {
        compareSource.addEventListener('change', function() {
            // Hide all sections first
            uploadTestCaseSection.style.display = 'none';
            generatedTestCaseSection.style.display = 'none';
            
            // Show the selected section
            if (this.value === 'upload') {
                uploadTestCaseSection.style.display = 'block';
            } else if (this.value === 'generate') {
                generatedTestCaseSection.style.display = 'block';
            }
        });
    }

    // Start Comparison Button Handler
    const startComparisonBtn = document.getElementById('startComparisonBtn');
    const comparisonResultsSection = document.getElementById('comparisonResultsSection');

    if (startComparisonBtn) {
        startComparisonBtn.addEventListener('click', function() {
            // Show loading state
            startComparisonBtn.disabled = true;
            startComparisonBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Comparing...';
            
            // Simulate API call with timeout
            setTimeout(function() {
                // Show comparison results
                comparisonResultsSection.style.display = 'block';
                
                // Reset button state
                startComparisonBtn.disabled = false;
                startComparisonBtn.innerHTML = 'Start Comparison';
                
                // Scroll to results
                comparisonResultsSection.scrollIntoView({ behavior: 'smooth' });
            }, 1500);
        });
    }

    // Filter functionality
    const applyFilters = document.getElementById('apply-filters');
    const resetFilters = document.getElementById('reset-filters');
    const searchInput = document.getElementById('search-test-cases');
    const filterStatus = document.getElementById('filter-status');
    const filterOwner = document.getElementById('filter-owner');
    const filterType = document.getElementById('filter-type');
    
    if (applyFilters) {
        applyFilters.addEventListener('click', function() {
            // Get filter values
            const searchValue = searchInput.value.toLowerCase();
            const statusValue = filterStatus.value;
            const ownerValue = filterOwner.value;
            const typeValue = filterType.value;
            
            // Get all rows in the table
            const rows = document.querySelectorAll('#all-test-cases-table tbody tr');
            
            // Filter rows
            rows.forEach(row => {
                const id = row.cells[0].textContent.toLowerCase();
                const title = row.cells[1].textContent.toLowerCase();
                const status = row.cells[2].querySelector('.badge').textContent.toLowerCase();
                const owner = row.cells[3].textContent.toLowerCase();
                const type = row.cells[4].querySelector('.badge').textContent.toLowerCase();
                
                // Check if row matches all filters
                const matchesSearch = searchValue === '' || id.includes(searchValue) || title.includes(searchValue);
                const matchesStatus = statusValue === '' || status.includes(statusValue.toLowerCase());
                const matchesOwner = ownerValue === '' || owner.includes(ownerValue.toLowerCase());
                const matchesType = typeValue === '' || type.includes(typeValue.toLowerCase());
                
                // Show or hide row based on filter match
                if (matchesSearch && matchesStatus && matchesOwner && matchesType) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });
            
            // Show message if no results found
            const visibleRows = document.querySelectorAll('#all-test-cases-table tbody tr:not([style*="display: none"])');
            const tableBody = document.querySelector('#all-test-cases-table tbody');
            
            if (visibleRows.length === 0 && tableBody.querySelector('.no-results') === null) {
                const noResultsRow = document.createElement('tr');
                noResultsRow.className = 'no-results';
                noResultsRow.innerHTML = '<td colspan="7" class="text-center py-3">No test cases match the selected filters.</td>';
                tableBody.appendChild(noResultsRow);
            } else if (visibleRows.length > 0) {
                const noResultsRow = tableBody.querySelector('.no-results');
                if (noResultsRow) {
                    noResultsRow.remove();
                }
            }
        });
    }
    
    if (resetFilters) {
        resetFilters.addEventListener('click', function() {
            // Reset form inputs
            searchInput.value = '';
            filterStatus.value = '';
            filterOwner.value = '';
            filterType.value = '';
            
            // Show all rows
            const rows = document.querySelectorAll('#all-test-cases-table tbody tr');
            rows.forEach(row => {
                row.style.display = '';
            });
            
            // Remove no results message if exists
            const noResultsRow = document.querySelector('#all-test-cases-table tbody .no-results');
            if (noResultsRow) {
                noResultsRow.remove();
            }
        });
    }

    // View Test Case Modal Handler
    const viewTestCaseBtns = document.querySelectorAll('.view-test-case');
    const viewTestCaseModal = document.getElementById('viewTestCaseModal');
    let viewTestCaseModalInstance;
    
    if (viewTestCaseModal) {
        viewTestCaseModalInstance = new bootstrap.Modal(viewTestCaseModal);
    }
    
    if (viewTestCaseBtns.length > 0) {
        viewTestCaseBtns.forEach(btn => {
            btn.addEventListener('click', function() {
                const testCaseId = this.getAttribute('data-id');
                
                // Here you would normally fetch test case details from API
                // For demo purposes, we're just showing the modal
                
                // Update modal with test case details (would come from API)
                document.getElementById('viewTestCaseId').textContent = testCaseId;
                
                // Set different details based on test case ID for demo
                if (testCaseId === 'TC-1001') {
                    document.getElementById('viewTestCaseTitle').textContent = 'Verify login with valid credentials';
                    document.getElementById('viewTestCaseStatus').textContent = 'Active';
                    document.getElementById('viewTestCaseStatus').className = 'badge bg-success mb-1';
                    document.getElementById('viewTestCaseType').textContent = 'Automated';
                    document.getElementById('viewTestCaseType').className = 'badge bg-info mb-1';
                    document.getElementById('viewTestCaseOwner').textContent = 'John Doe';
                } else if (testCaseId === 'TC-1003') {
                    document.getElementById('viewTestCaseTitle').textContent = 'Verify password recovery functionality';
                    document.getElementById('viewTestCaseStatus').textContent = 'Under Maintenance';
                    document.getElementById('viewTestCaseStatus').className = 'badge bg-warning mb-1';
                    document.getElementById('viewTestCaseType').textContent = 'Automated';
                    document.getElementById('viewTestCaseType').className = 'badge bg-info mb-1';
                    document.getElementById('viewTestCaseOwner').textContent = 'Jane Smith';
                }
                
                // Show the modal
                viewTestCaseModalInstance.show();
            });
        });
    }

    // Execute Test Case Button Handler
    const executeTestCaseBtns = document.querySelectorAll('.execute-test-case');
    
    if (executeTestCaseBtns.length > 0) {
        executeTestCaseBtns.forEach(btn => {
            btn.addEventListener('click', function() {
                const testCaseId = this.getAttribute('data-id');
                
                // Disable button and show loading state
                this.disabled = true;
                const originalHTML = this.innerHTML;
                this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>';
                
                // Simulate API call with timeout
                setTimeout(() => {
                    // Show a success toast or notification
                    alert(`Test case ${testCaseId} execution triggered successfully!`);
                    
                    // Reset button state
                    this.disabled = false;
                    this.innerHTML = originalHTML;
                }, 1500);
            });
        });
    }

    // Notify Owner Button Handler
    const notifyOwnerBtns = document.querySelectorAll('.notify-owner');
    
    if (notifyOwnerBtns.length > 0) {
        notifyOwnerBtns.forEach(btn => {
            btn.addEventListener('click', function() {
                const testCaseId = this.getAttribute('data-id');
                
                // Disable button and show loading state
                this.disabled = true;
                const originalHTML = this.innerHTML;
                this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>';
                
                // Simulate API call with timeout
                setTimeout(() => {
                    // Show a success toast or notification
                    alert(`Owner has been notified about test case ${testCaseId}`);
                    
                    // Reset button state
                    this.disabled = false;
                    this.innerHTML = originalHTML;
                }, 1500);
            });
        });
    }

    // Action buttons inside comparison results
    const triggerExecutionBtn = document.getElementById('triggerExecutionBtn');
    const updateMatchedListBtn = document.getElementById('updateMatchedListBtn');
    const notifyOwnerBtn = document.getElementById('notifyOwnerBtn');
    const uploadNewVersionBtn = document.getElementById('uploadNewVersionBtn');
    const updateModificationListBtn = document.getElementById('updateModificationListBtn');
    const uploadRepositoryBtn = document.getElementById('uploadRepositoryBtn');
    const updateNewListBtn = document.getElementById('updateNewListBtn');
    
    // Helper function for button click handler
    function attachButtonHandler(btn, successMessage) {
        if (btn) {
            btn.addEventListener('click', function() {
                // Disable button and show loading state
                this.disabled = true;
                const originalHTML = this.innerHTML;
                this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processing...';
                
                // Simulate API call with timeout
                setTimeout(() => {
                    // Show a success toast or notification
                    alert(successMessage);
                    
                    // Reset button state
                    this.disabled = false;
                    this.innerHTML = originalHTML;
                }, 1500);
            });
        }
    }
    
    // Attach handlers to all comparison action buttons
    attachButtonHandler(triggerExecutionBtn, 'Test execution triggered successfully!');
    attachButtonHandler(updateMatchedListBtn, 'Matched list updated successfully!');
    attachButtonHandler(notifyOwnerBtn, 'Owner has been notified of suggested changes!');
    attachButtonHandler(uploadNewVersionBtn, 'New version uploaded successfully!');
    attachButtonHandler(updateModificationListBtn, 'Modification list updated successfully!');
    attachButtonHandler(uploadRepositoryBtn, 'Test case uploaded to repository and assigned to owner!');
    attachButtonHandler(updateNewListBtn, 'New list updated successfully!');

    // Import Test Case Button Handler
    const importTestCaseBtn = document.getElementById('importTestCaseBtn');
    
    if (importTestCaseBtn) {
        importTestCaseBtn.addEventListener('click', function() {
            // Disable button and show loading state
            this.disabled = true;
            const originalHTML = this.innerHTML;
            this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Importing...';
            
            // Get the selected import source
            const importSource = document.getElementById('importSource').value;
            let successMessage = 'Test case imported successfully!';
            
            if (importSource === 'jira') {
                successMessage = 'Test cases imported from JIRA successfully!';
            } else if (importSource === 'alm') {
                successMessage = 'Test cases imported from ALM successfully!';
            }
            
            // Simulate API call with timeout
            setTimeout(() => {
                // Show a success toast or notification
                alert(successMessage);
                
                // Reset button state
                this.disabled = false;
                this.innerHTML = originalHTML;
                
                // Close the modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('importTestCaseModal'));
                if (modal) {
                    modal.hide();
                }
            }, 2000);
        });
    }

    function updateConnectionStatus(serviceId, isConnected) {
        const statusElement = document.getElementById(serviceId);
        if (!statusElement) {
            console.error(`Element with id ${serviceId} not found`);
            return;
        }

        const badgeElement = statusElement.querySelector('.badge');
        if (!badgeElement) {
            console.error(`Badge element not found in ${serviceId}`);
            return;
        }

        // Add console logs for debugging
        console.log(`Updating ${serviceId} connection status to: ${isConnected}`);

        if (isConnected) {
            badgeElement.classList.remove('bg-danger');
            badgeElement.classList.add('bg-success');
            badgeElement.setAttribute('data-connection-status', 'connected');
            badgeElement.innerHTML = '<i class="fas fa-check-circle me-1"></i>Connected';
        } else {
            badgeElement.classList.remove('bg-success');
            badgeElement.classList.add('bg-danger');
            badgeElement.setAttribute('data-connection-status', 'disconnected');
            badgeElement.innerHTML = '<i class="fas fa-times-circle me-1"></i>Disconnected';
        }
    }
    // Example connection status (replace with actual connection checks)
    updateConnectionStatus('sharepoint-connection-status', true);  // Connected
    updateConnectionStatus('jira-connection-status', false);      // Disconnected
    updateConnectionStatus('alm-connection-status', true);        // Connected
});


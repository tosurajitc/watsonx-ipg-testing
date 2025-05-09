/**
 * Test Case Display Module for the Watsonx IPG Testing platform.
 * 
 * This module handles the display and formatting of test cases in the UI.
 */

// Create namespace if it doesn't exist
var TestGeneration = TestGeneration || {};

/**
 * Test Case Display module
 */
TestGeneration.TestCaseDisplay = (function() {
    /**
     * Display test cases in the specified container
     * 
     * @param {Object} data - The test case data from the API
     * @param {HTMLElement} container - The container element to display the test case in
     * @returns {boolean} - True if display was successful, false otherwise
     */
    function displayTestCase(data, container) {
        if (!container) {
            console.error('Display container not provided');
            return false;
        }
        
        // Clear previous content
        container.innerHTML = '';
        
        // Check if we have valid test case data
        if (!data || !data.test_case || !Array.isArray(data.test_case) || data.test_case.length === 0) {
            container.innerHTML = '<div class="alert alert-warning">No test case data available.</div>';
            return false;
        }
        
        try {
            // Create test case information section
            const infoDiv = document.createElement('div');
            infoDiv.className = 'test-case-info mb-3';
            
            // Extract test case metadata from the first row
            const firstRow = data.test_case[0];
            const testCaseNumber = firstRow['TEST CASE NUMBER'] || '';
            const testCaseName = firstRow['TEST CASE'] || '';
            const testCaseSubject = firstRow['SUBJECT'] || '';
            const testCaseType = firstRow['TYPE'] || '';
            
            if (testCaseNumber || testCaseName || testCaseSubject) {
                // Test case header
                const header = document.createElement('div');
                header.className = 'card bg-light mb-3';
                
                const headerBody = document.createElement('div');
                headerBody.className = 'card-body';
                
                if (testCaseName) {
                    const title = document.createElement('h5');
                    title.className = 'card-title';
                    title.textContent = testCaseName;
                    headerBody.appendChild(title);
                }
                
                const headerDetails = document.createElement('div');
                headerDetails.className = 'row';
                
                // Add test case ID
                if (testCaseNumber) {
                    const idCol = document.createElement('div');
                    idCol.className = 'col-md-4';
                    idCol.innerHTML = `<strong>Test Case ID:</strong> ${testCaseNumber}`;
                    headerDetails.appendChild(idCol);
                }
                
                // Add subject
                if (testCaseSubject) {
                    const subjectCol = document.createElement('div');
                    subjectCol.className = 'col-md-4';
                    subjectCol.innerHTML = `<strong>Subject:</strong> ${testCaseSubject}`;
                    headerDetails.appendChild(subjectCol);
                }
                
                // Add type
                if (testCaseType) {
                    const typeCol = document.createElement('div');
                    typeCol.className = 'col-md-4';
                    typeCol.innerHTML = `<strong>Type:</strong> ${testCaseType}`;
                    headerDetails.appendChild(typeCol);
                }
                
                headerBody.appendChild(headerDetails);
                header.appendChild(headerBody);
                infoDiv.appendChild(header);
            }
            
            container.appendChild(infoDiv);
            
            // Create table for test case steps
            const table = document.createElement('table');
            table.className = 'table table-bordered table-hover';
            
            // Create header
            const thead = document.createElement('thead');
            const headerRow = document.createElement('tr');
            
            // Define which columns to display
            const displayColumns = [
                'STEP NO', 
                'TEST STEP DESCRIPTION', 
                'DATA', 
                'EXPECTED RESULT'
            ];
            
            // Add header cells
            const headerLabels = {
                'STEP NO': 'Step #',
                'TEST STEP DESCRIPTION': 'Description',
                'DATA': 'Test Data',
                'EXPECTED RESULT': 'Expected Result'
            };
            
            displayColumns.forEach(column => {
                const th = document.createElement('th');
                th.textContent = headerLabels[column] || column;
                headerRow.appendChild(th);
            });
            
            thead.appendChild(headerRow);
            table.appendChild(thead);
            
            // Create body
            const tbody = document.createElement('tbody');
            
            data.test_case.forEach((step, index) => {
                const row = document.createElement('tr');
                
                // Add cells for each displayed column
                displayColumns.forEach(column => {
                    const cell = document.createElement('td');
                    
                    // Handle special formatting for different column types
                    if (column === 'STEP NO') {
                        cell.textContent = step[column] || (index + 1);
                        cell.style.width = '80px'; // Set fixed width for step numbers
                    } else if (column === 'DATA') {
                        // Combine DATA, VALUES, and REFERENCE VALUES if available
                        let dataText = step[column] || '';
                        
                        if (step['VALUES']) {
                            if (dataText) dataText += '\n';
                            dataText += 'Values: ' + step['VALUES'];
                        }
                        
                        if (step['REFERENCE VALUES']) {
                            if (dataText) dataText += '\n';
                            dataText += 'Reference: ' + step['REFERENCE VALUES'];
                        }
                        
                        cell.textContent = dataText;
                        
                        // Add formatting for multi-line content
                        cell.style.whiteSpace = 'pre-line';
                    } else {
                        cell.textContent = step[column] || '';
                    }
                    
                    row.appendChild(cell);
                });
                
                tbody.appendChild(row);
            });
            
            table.appendChild(tbody);
            container.appendChild(table);
            
            return true;
        } catch (error) {
            console.error('Error displaying test case:', error);
            container.innerHTML = '<div class="alert alert-danger">Error displaying test case: ' + error.message + '</div>';
            return false;
        }
    }
    
    /**
     * Create a download URL for exporting test cases
     * 
     * @param {Object} data - The test case data
     * @param {string} format - The export format (excel, word, pdf)
     * @returns {string} - The download URL
     */
    function getExportUrl(data, format) {
        // Basic validation
        if (!data || !format) {
            console.error('Invalid data or format for export');
            return null;
        }
        
        // Create a base filename from test case data
        let filename = 'test_case_' + new Date().toISOString().split('T')[0];
        
        if (data.test_case && data.test_case.length > 0) {
            const firstRow = data.test_case[0];
            if (firstRow['TEST CASE NUMBER']) {
                filename = 'TC_' + firstRow['TEST CASE NUMBER'].replace(/[^a-zA-Z0-9]/g, '_');
            } else if (firstRow['TEST CASE']) {
                filename = firstRow['TEST CASE'].replace(/[^a-zA-Z0-9]/g, '_');
            }
        }
        
        // Construct data for export request
        const exportData = {
            test_case: data.test_case,
            format: format,
            filename: filename
        };
        
        // Add scenario data if available
        if (data.scenario) {
            exportData.scenarios = [data.scenario];
        }
        
        // Convert to JSON and encode for URL
        const jsonData = encodeURIComponent(JSON.stringify(exportData));
        
        // Return URL
        return '/api/test-cases/export-' + format + '?data=' + jsonData;
    }
    
    /**
     * Extract formatted metadata from test case data
     * 
     * @param {Object} data - The test case data
     * @returns {Object} - Formatted metadata object
     */
    function extractMetadata(data) {
        const metadata = {
            testCaseId: '',
            testCaseName: '',
            subject: '',
            type: '',
            stepCount: 0
        };
        
        if (data && data.test_case && data.test_case.length > 0) {
            const firstRow = data.test_case[0];
            metadata.testCaseId = firstRow['TEST CASE NUMBER'] || '';
            metadata.testCaseName = firstRow['TEST CASE'] || '';
            metadata.subject = firstRow['SUBJECT'] || '';
            metadata.type = firstRow['TYPE'] || '';
            metadata.stepCount = data.test_case.length;
        }
        
        return metadata;
    }
    
    // Return public API
    return {
        displayTestCase: displayTestCase,
        getExportUrl: getExportUrl,
        extractMetadata: extractMetadata
    };
})();

// Log that this module has loaded successfully
console.log('Test Case Display module loaded successfully');
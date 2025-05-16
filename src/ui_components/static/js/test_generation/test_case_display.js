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
        
        // Log the received data for debugging
        console.log('displayTestCase received data:', data);
        
        // Clear previous content
        container.innerHTML = '';
        
        // Normalize the test case data structure - handle various possible formats
        let testCaseData = null;
        
        // Extract test case array from different possible structures
        if (data === null || data === undefined) {
            console.error('Display function received null or undefined data');
            container.innerHTML = '<div class="alert alert-danger">No data received for display.</div>';
            return false;
        } else if (Array.isArray(data)) {
            // Data itself is an array of test cases
            console.log('Data is directly an array');
            testCaseData = data;
        } else if (data.test_case && Array.isArray(data.test_case)) {
            // Standard structure with test_case property
            console.log('Found test_case array property');
            testCaseData = data.test_case;
        } else if (data.data && data.data.test_case && Array.isArray(data.data.test_case)) {
            // Nested structure with data.test_case property
            console.log('Found nested data.test_case array property');
            testCaseData = data.data.test_case;
        } else {
            // Attempt to find any array in the data that might be test cases
            console.log('Searching for any array property in data');
            for (const key in data) {
                if (Array.isArray(data[key]) && data[key].length > 0) {
                    console.log(`Found array in property "${key}"`);
                    testCaseData = data[key];
                    break;
                } else if (typeof data[key] === 'object' && data[key] !== null) {
                    // Check one level deeper
                    for (const subKey in data[key]) {
                        if (Array.isArray(data[key][subKey]) && data[key][subKey].length > 0) {
                            console.log(`Found array in nested property "${key}.${subKey}"`);
                            testCaseData = data[key][subKey];
                            break;
                        }
                    }
                    if (testCaseData) break;
                }
            }
        }
        
        // Check if we found valid test case data
        if (!testCaseData || !Array.isArray(testCaseData) || testCaseData.length === 0) {
            console.error('No valid test case data found in:', data);
            container.innerHTML = `
                <div class="alert alert-warning">
                    <h5>No test case data available</h5>
                    <p>The system received a response but couldn't find test case data in the expected format.</p>
                    <p>Please check the browser console for details.</p>
                </div>
            `;
            return false;
        }
        
        console.log(`Found test case data with ${testCaseData.length} items`);
        
        try {
            // Create test case information section
            const infoDiv = document.createElement('div');
            infoDiv.className = 'test-case-info mb-3';
            
            // Extract test case metadata from the first row
            const firstRow = testCaseData[0];
            
            // Look for various column name formats - handle case sensitivity
            const getMetadataValue = (possibleNames) => {
                for (const name of possibleNames) {
                    // Check for exact match
                    if (firstRow[name] !== undefined) {
                        return firstRow[name];
                    }
                    
                    // Check for case-insensitive match
                    const lowerName = name.toLowerCase();
                    for (const key in firstRow) {
                        if (key.toLowerCase() === lowerName && firstRow[key] !== undefined) {
                            return firstRow[key];
                        }
                    }
                }
                return '';
            };
            
            const testCaseNumber = getMetadataValue(['TEST CASE NUMBER', 'Test Case Number', 'ID', 'test_case_number']);
            const testCaseName = getMetadataValue(['TEST CASE', 'Test Case', 'Name', 'test_case_name']);
            const testCaseSubject = getMetadataValue(['SUBJECT', 'Subject', 'Module', 'Area']);
            const testCaseType = getMetadataValue(['TYPE', 'Type', 'Category']);
            
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
            
            // Determine available columns from the data
            const availableColumns = new Set();
            testCaseData.forEach(step => {
                Object.keys(step).forEach(key => {
                    availableColumns.add(key);
                });
            });
            
            // Define preferred columns to display if available
            const preferredColumns = [
                ['STEP NO', 'Step No', 'Step Number', 'step_no'],
                ['TEST STEP DESCRIPTION', 'Test Step Description', 'Description', 'description'], 
                ['DATA', 'Test Data', 'Data', 'data'], 
                ['EXPECTED RESULT', 'Expected Result', 'Expected', 'expected_result']
            ];
            
            // Find the actual column names from preferred columns that exist in the data
            const displayColumns = [];
            const columnMapping = {}; // Maps preferred column name to actual column name in data
            
            preferredColumns.forEach(possibleNames => {
                for (const name of possibleNames) {
                    if (availableColumns.has(name)) {
                        displayColumns.push(name);
                        columnMapping[possibleNames[0]] = name; // Map canonical name to actual name
                        break;
                    }
                }
            });
            
            // Add any other columns not in preferred list
            if (displayColumns.length === 0) {
                // If we couldn't find any preferred columns, just use all available columns
                availableColumns.forEach(column => {
                    displayColumns.push(column);
                });
            }
            
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
            
            testCaseData.forEach((step, index) => {
                const row = document.createElement('tr');
                
                // Add cells for each displayed column
                displayColumns.forEach(column => {
                    const cell = document.createElement('td');
                    
                    // Handle special formatting for different column types
                    if (column === 'STEP NO' || column === 'Step No' || column === 'step_no') {
                        cell.textContent = step[column] || (index + 1);
                        cell.style.width = '80px'; // Set fixed width for step numbers
                    } else if (column === 'DATA' || column === 'Test Data' || column === 'data') {
                        // Combine DATA, VALUES, and REFERENCE VALUES if available
                        let dataText = step[column] || '';
                        
                        // Look for values in any of these columns
                        const valueColumns = ['VALUES', 'Values', 'values'];
                        const refValueColumns = ['REFERENCE VALUES', 'Reference Values', 'reference_values'];
                        
                        for (const valCol of valueColumns) {
                            if (step[valCol]) {
                                if (dataText) dataText += '\n';
                                dataText += 'Values: ' + step[valCol];
                                break;
                            }
                        }
                        
                        for (const refCol of refValueColumns) {
                            if (step[refCol]) {
                                if (dataText) dataText += '\n';
                                dataText += 'Reference: ' + step[refCol];
                                break;
                            }
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
            
            console.log('Test case displayed successfully');
            return true;
        } catch (error) {
            console.error('Error displaying test case:', error);
            container.innerHTML = `
                <div class="alert alert-danger">
                    <h5>Error displaying test case</h5>
                    <p>${error.message}</p>
                    <p>Please check the browser console for more details.</p>
                </div>
            `;
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
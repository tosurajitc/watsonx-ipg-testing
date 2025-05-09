document.addEventListener('DOMContentLoaded', function() {
    // Password visibility toggle
    setupPasswordVisibility();

    // Connection testing
    setupConnectionTests();

    // Rule Engine Dynamic Rule Addition
    setupRuleEngineInteractions();

    // Template Management
    setupTemplateManagement();

    // User Management
    setupUserManagement();

    // Form Submissions
    setupFormSubmissions();
});

function setupPasswordVisibility() {
    // Password visibility toggles
    const passwordFields = [
        { inputId: 'jira-api-key', toggleId: 'jira-show-password' },
        { inputId: 'alm-password', toggleId: 'alm-show-password' },
        { inputId: 'new-user-password', toggleId: 'generate-password' }
    ];

    passwordFields.forEach(field => {
        const passwordInput = document.getElementById(field.inputId);
        const toggleButton = document.getElementById(field.toggleId);

        if (passwordInput && toggleButton) {
            toggleButton.addEventListener('click', function() {
                if (field.inputId === 'new-user-password') {
                    // Generate password for new user
                    if (passwordInput.value === '') {
                        passwordInput.value = generatePassword();
                    }
                }

                // Toggle password visibility
                const type = passwordInput.getAttribute('type') === 'password' ? 'text' : 'password';
                passwordInput.setAttribute('type', type);
                
                // Toggle icon
                this.querySelector('i').classList.toggle('fa-eye');
                this.querySelector('i').classList.toggle('fa-eye-slash');
            });
        }
    });
}

function generatePassword(length = 12) {
    const charset = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()_+';
    let password = '';
    for (let i = 0; i < length; i++) {
        const randomIndex = Math.floor(Math.random() * charset.length);
        password += charset[randomIndex];
    }
    return password;
}

function setupConnectionTests() {
    // JIRA Connection Test
    const jiraTestBtn = document.getElementById('test-jira-connection');
    if (jiraTestBtn) {
        jiraTestBtn.addEventListener('click', function() {
            const jiraUrl = document.getElementById('jira-url').value;
            const jiraApiKey = document.getElementById('jira-api-key').value;

            // Simulate connection test (replace with actual AJAX call)
            testConnection('jira', { url: jiraUrl, apiKey: jiraApiKey });
        });
    }

    // SharePoint Connection Test
    const sharepointTestBtn = document.getElementById('test-sharepoint-connection');
    if (sharepointTestBtn) {
        sharepointTestBtn.addEventListener('click', function() {
            const sharepointUrl = document.getElementById('sharepoint-url').value;
            const sharepointClientId = document.getElementById('sharepoint-client-id').value;

            // Simulate connection test (replace with actual AJAX call)
            testConnection('sharepoint', { url: sharepointUrl, clientId: sharepointClientId });
        });
    }
}

function testConnection(service, credentials) {
    // Simulated connection test - replace with actual AJAX call
    try {
        // Placeholder for actual connection testing logic
        console.log(`Testing ${service} connection`, credentials);
        
        // Simulated success
        showConnectionResult(service, true, 'Connection successful!');
    } catch (error) {
        // Simulated failure
        showConnectionResult(service, false, 'Connection failed. Please check your credentials.');
    }
}

function showConnectionResult(service, success, message) {
    // Create or get the existing toast element
    let toastContainer = document.getElementById('connection-toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'connection-toast-container';
        toastContainer.classList.add('position-fixed', 'top-0', 'end-0', 'p-3');
        toastContainer.style.zIndex = '1100';
        document.body.appendChild(toastContainer);
    }

    // Create toast element
    const toastEl = document.createElement('div');
    toastEl.classList.add('toast', 'align-items-center', 'text-white', 'border-0');
    toastEl.classList.add(success ? 'bg-success' : 'bg-danger');
    
    toastEl.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                <i class="fas ${success ? 'fa-check-circle' : 'fa-times-circle'} me-2"></i>
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;

    // Add to container and show
    toastContainer.appendChild(toastEl);
    const toast = new bootstrap.Toast(toastEl);
    toast.show();
}

function setupRuleEngineInteractions() {
    // Dynamic Rule Addition for Test Case Owner
    const addTestCaseRuleBtn = document.getElementById('add-test-case-rule');
    const testCaseRuleContainer = document.getElementById('test-case-rule-details');

    if (addTestCaseRuleBtn && testCaseRuleContainer) {
        addTestCaseRuleBtn.addEventListener('click', function() {
            const ruleGroup = createRuleGroup([
                {
                    type: 'select',
                    options: ['Web Application', 'Mobile Application', 'API']
                },
                {
                    type: 'select',
                    options: ['John Doe', 'Jane Smith', 'Alex Johnson']
                }
            ]);
            testCaseRuleContainer.insertBefore(ruleGroup, addTestCaseRuleBtn);
        });
    }

    // Dynamic Rule Addition for Defect Assignment
    const addDefectRuleBtn = document.getElementById('add-defect-rule');
    const defectRuleContainer = document.getElementById('defect-rule-details');

    if (addDefectRuleBtn && defectRuleContainer) {
        addDefectRuleBtn.addEventListener('click', function() {
            const ruleGroup = createRuleGroup([
                {
                    type: 'select',
                    options: ['Frontend', 'Backend', 'Database']
                },
                {
                    type: 'select',
                    options: ['High Severity', 'Medium Severity', 'Low Severity']
                },
                {
                    type: 'select',
                    options: ['Dev Team Lead', 'QA Manager', 'Project Manager']
                }
            ]);
            defectRuleContainer.insertBefore(ruleGroup, addDefectRuleBtn);
        });
    }
}

function createRuleGroup(selectOptions) {
    const ruleGroup = document.createElement('div');
    ruleGroup.classList.add('rule-group', 'input-group', 'mb-3');

    // Create select elements
    selectOptions.forEach(option => {
        const select = document.createElement('select');
        select.classList.add('form-select');
        
        option.options.forEach(optionText => {
            const optionEl = document.createElement('option');
            optionEl.textContent = optionText;
            optionEl.value = optionText;
            select.appendChild(optionEl);
        });

        ruleGroup.appendChild(select);
    });

    // Add delete button
    const deleteBtn = document.createElement('button');
    deleteBtn.classList.add('btn', 'btn-danger');
    deleteBtn.innerHTML = '<i class="fas fa-trash"></i>';
    deleteBtn.addEventListener('click', function() {
        ruleGroup.remove();
    });
    ruleGroup.appendChild(deleteBtn);

    return ruleGroup;
}

function setupTemplateManagement() {
    // View Template functionality
    const viewTemplateBtn = document.getElementById('view-template');
    if (viewTemplateBtn) {
        viewTemplateBtn.addEventListener('click', function() {
            const templateInput = document.getElementById('test-case-template');
            if (templateInput.files.length > 0) {
                // In a real app, this would open the file or show a preview
                alert(`Selected template: ${templateInput.files[0].name}`);
            } else {
                alert('Please select a template file first.');
            }
        });
    }
}

function setupUserManagement() {
    // Generate Password for New User
    const generatePasswordBtn = document.getElementById('generate-password');
    const newUserPasswordInput = document.getElementById('new-user-password');

    if (generatePasswordBtn && newUserPasswordInput) {
        generatePasswordBtn.addEventListener('click', function() {
            newUserPasswordInput.value = generatePassword();
            // Optionally, switch to text type to show the generated password
            newUserPasswordInput.setAttribute('type', 'text');
        });
    }

    // Add User Form Submission
    const addUserForm = document.getElementById('add-user-form');
    if (addUserForm) {
        addUserForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const formData = new FormData(addUserForm);
            
            // Basic validation
            const userName = formData.get('new_user_name');
            const userEmail = formData.get('new_user_email');
            const userRole = formData.get('new_user_role');
            const userPassword = formData.get('new_user_password');

            if (validateUserInput(userName, userEmail, userRole, userPassword)) {
                // Simulate user creation (replace with actual AJAX call)
                createUser(userName, userEmail, userRole);
                addUserForm.reset();
            }
        });
    }
}

function validateUserInput(name, email, role, password) {
    let isValid = true;
    
    // Name validation
    if (!name || name.trim().length < 2) {
        alert('Please enter a valid name');
        isValid = false;
    }

    // Email validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!email || !emailRegex.test(email)) {
        alert('Please enter a valid email address');
        isValid = false;
    }

    // Role validation
    if (!role) {
        alert('Please select a user role');
        isValid = false;
    }

    // Password validation
    if (!password || password.length < 8) {
        alert('Password must be at least 8 characters long');
        isValid = false;
    }

    return isValid;
}

function createUser(name, email, role) {
    // Simulate user creation
    console.log('Creating user:', { name, email, role });
    
    // Update user list (would typically be done via backend in a real app)
    const userList = document.querySelector('.user-list');
    if (userList) {
        const newUserCard = document.createElement('div');
        newUserCard.classList.add('card', 'mb-2');
        newUserCard.innerHTML = `
            <div class="card-body d-flex justify-content-between align-items-center">
                <div>
                    <strong>${name}</strong>
                    <p class="text-muted mb-0">${email}</p>
                    <span class="badge bg-secondary">${role}</span>
                </div>
                <div>
                    <button class="btn btn-sm btn-outline-primary me-2" data-bs-toggle="modal" data-bs-target="#edit-user-modal">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-danger">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        `;
        userList.appendChild(newUserCard);
    }

    // Show success message
    showConnectionResult('user', true, `User ${name} created successfully!`);
}

function setupFormSubmissions() {
    // Connections Form
    const connectionsForm = document.getElementById('connections-form');
    if (connectionsForm) {
        connectionsForm.addEventListener('submit', function(e) {
            e.preventDefault();
            saveConnections();
        });
    }

    // Rule Engine Forms
    const testCaseRuleForm = document.getElementById('test-case-owner-rules');
    const defectRuleForm = document.getElementById('defect-assignment-rules');
    
    if (testCaseRuleForm) {
        testCaseRuleForm.addEventListener('submit', function(e) {
            e.preventDefault();
            saveRules('test-case');
        });
    }

    if (defectRuleForm) {
        defectRuleForm.addEventListener('submit', function(e) {
            e.preventDefault();
            saveRules('defect');
        });
    }

    // Templates Form
    const templatesForm = document.getElementById('templates-form');
    if (templatesForm) {
        templatesForm.addEventListener('submit', function(e) {
            e.preventDefault();
            saveTemplates();
        });
    }

    // Automation Form
    const automationForm = document.getElementById('automation-form');
    if (automationForm) {
        automationForm.addEventListener('submit', function(e) {
            e.preventDefault();
            saveAutomationPaths();
        });
    }

    // Notifications Form
    const notificationsForm = document.getElementById('notifications-form');
    if (notificationsForm) {
        notificationsForm.addEventListener('submit', function(e) {
            e.preventDefault();
            saveNotificationSettings();
        });
    }
}

// Placeholder functions for form submissions (to be replaced with actual AJAX calls)
function saveConnections() {
    const formData = new FormData(document.getElementById('connections-form'));
    console.log('Saving Connections:', Object.fromEntries(formData));
    showConnectionResult('connections', true, 'Connection settings saved successfully!');
}

function saveRules(ruleType) {
    const formData = new FormData(document.getElementById(`${ruleType}-assignment-rules`));
    console.log(`Saving ${ruleType} Rules:`, Object.fromEntries(formData));
    showConnectionResult('rules', true, `${ruleType.replace('-', ' ').toUpperCase()} rules saved successfully!`);
}

function saveTemplates() {
    const formData = new FormData(document.getElementById('templates-form'));
    console.log('Saving Templates:', Object.fromEntries(formData));
    showConnectionResult('templates', true, 'Templates saved successfully!');
}

function saveAutomationPaths() {
    const formData = new FormData(document.getElementById('automation-form'));
    console.log('Saving Automation Paths:', Object.fromEntries(formData));
    showConnectionResult('automation', true, 'Automation paths saved successfully!');
}

function saveNotificationSettings() {
    const formData = new FormData(document.getElementById('notifications-form'));
    console.log('Saving Notification Settings:', Object.fromEntries(formData));
    showConnectionResult('notifications', true, 'Notification settings saved successfully!');
}
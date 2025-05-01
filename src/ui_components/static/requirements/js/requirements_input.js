// src/phase1/llm_test_scenario_generator/static/llm_test_scenario_generator/js/requirements_input.js

document.addEventListener('DOMContentLoaded', function() {
    // Tab switching
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabButtons.forEach(button => {
      button.addEventListener('click', function() {
        const targetId = this.getAttribute('data-target');
        
        // Update active tab button
        tabButtons.forEach(btn => btn.classList.remove('active'));
        this.classList.add('active');
        
        // Show target tab content, hide others
        tabContents.forEach(content => {
          content.classList.add('hidden');
        });
        document.getElementById(targetId).classList.remove('hidden');
      });
    });
    
    // JIRA connection form
    const authMethodRadios = document.querySelectorAll('input[name="auth_method"]');
    const authDetailsSections = document.querySelectorAll('.auth-details');
    
    authMethodRadios.forEach(radio => {
      radio.addEventListener('change', function() {
        const selectedValue = this.value;
        
        // Hide all auth details sections
        authDetailsSections.forEach(section => {
          section.classList.add('hidden');
        });
        
        // Show selected section
        document.getElementById(selectedValue + '-details').classList.remove('hidden');
      });
    });
    
    // Toggle JQL query section
    const useCustomJql = document.getElementById('id_use_custom_jql');
    const customJqlSection = document.getElementById('custom-jql-section');
    const standardFilters = document.getElementById('standard-filters');
    const useFilters = document.getElementById('id_use_filters');
    
    if (useCustomJql) {
      useCustomJql.addEventListener('change', function() {
        if (this.checked) {
          customJqlSection.classList.remove('hidden');
          standardFilters.classList.add('hidden');
          if (useFilters) useFilters.checked = false;
        } else {
          customJqlSection.classList.add('hidden');
          standardFilters.classList.remove('hidden');
          if (useFilters) useFilters.checked = true;
        }
      });
    }
    
    if (useFilters) {
      useFilters.addEventListener('change', function() {
        if (this.checked) {
          standardFilters.classList.remove('hidden');
          customJqlSection.classList.add('hidden');
          if (useCustomJql) useCustomJql.checked = false;
        } else {
          standardFilters.classList.add('hidden');
          customJqlSection.classList.remove('hidden');
          if (useCustomJql) useCustomJql.checked = true;
        }
      });
    }
    
    // File upload functionality
    const dropArea = document.getElementById('drop-area');
    const fileInput = document.getElementById('id_requirement_file');
    const filePreview = document.getElementById('file-preview');
    const fileName = document.getElementById('file-name');
    const fileSize = document.getElementById('file-size');
    const removeFileBtn = document.getElementById('remove-file');
    
    if (dropArea && fileInput) {
      // Click to browse
      dropArea.addEventListener('click', function() {
        fileInput.click();
      });
      
      // Handle file selection
      fileInput.addEventListener('change', function() {
        if (this.files.length > 0) {
          updateFilePreview(this.files[0]);
        }
      });
      
      // Handle drag and drop
      ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, preventDefaults, false);
      });
      
      function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
      }
      

      ['dragenter', 'dragover'].forEach(eventName => {
        dropArea.addEventListener(eventName, function() {
          dropArea.classList.add('drag-active');
        });
      });
      
      ['dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, function() {
          dropArea.classList.remove('drag-active');
        });
      });
      
      dropArea.addEventListener('drop', function(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        
        if (files.length > 0) {
          fileInput.files = files;
          updateFilePreview(files[0]);
        }
      });
      
      // Handle file removal
      if (removeFileBtn) {
        removeFileBtn.addEventListener('click', function(e) {
          e.preventDefault();
          e.stopPropagation();
          
          fileInput.value = '';
          dropArea.classList.remove('hidden');
          filePreview.classList.add('hidden');
        });
      }
      
      function updateFilePreview(file) {
        // Update file info
        fileName.textContent = file.name;
        fileSize.textContent = formatFileSize(file.size);
        
        // Show preview, hide drop area
        dropArea.classList.add('hidden');
        filePreview.classList.remove('hidden');
      }
      
      function formatFileSize(bytes) {
        if (bytes < 1024) {
          return bytes + ' bytes';
        } else if (bytes < 1024 * 1024) {
          return (bytes / 1024).toFixed(2) + ' KB';
        } else {
          return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
        }
      }
    }
    
    // Form submission handling
    const forms = document.querySelectorAll('form');
    const processingStatus = document.getElementById('processing-status');
    const statusText = document.getElementById('status-text');
    
    forms.forEach(form => {
      form.addEventListener('submit', function(e) {
        const isValid = form.checkValidity();
        
        if (isValid) {
          // Show processing status
          processingStatus.classList.remove('hidden');
          
          // Disable submit button
          const submitBtn = form.querySelector('button[type="submit"]');
          if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="icon spinner-icon rotating"></i> Processing...';
          }
          
          // Get the form type
          if (form.classList.contains('jira-form')) {
            statusText.textContent = 'Connecting to JIRA and fetching requirements...';
          } else if (form.classList.contains('file-upload-form')) {
            statusText.textContent = 'Uploading and processing file...';
          } else if (form.classList.contains('manual-input-form')) {
            statusText.textContent = 'Processing manual input...';
          }
        }
      });
    });
    
    // Manual input format examples
    const inputFormatRadios = document.querySelectorAll('input[name="input_format"]');
    const requirementTextarea = document.getElementById('id_requirement_text');
    
    if (inputFormatRadios.length > 0 && requirementTextarea) {
      inputFormatRadios.forEach(radio => {
        radio.addEventListener('change', function() {
          const format = this.value;
          let placeholder = '';
          
          if (format === 'user_story') {
            placeholder = 'As a user, I want to log in to the system, so that I can access my account.\n\nAs an admin, I want to view all user accounts, so that I can manage them effectively.';
          } else if (format === 'requirement') {
            placeholder = '1. The system shall allow users to log in using email and password.\n2. The system shall provide admin users with the ability to view all user accounts.\n3. The system shall log all login attempts.';
          } else if (format === 'free_text') {
            placeholder = 'Enter your requirements in any format. The system will try to extract meaningful requirements from your text.';
          }
          
          requirementTextarea.placeholder = placeholder;
        });
      });
      
      // Trigger the change event on the selected radio
      const selectedInputFormat = document.querySelector('input[name="input_format"]:checked');
      if (selectedInputFormat) {
        selectedInputFormat.dispatchEvent(new Event('change'));
      }
    }
  });
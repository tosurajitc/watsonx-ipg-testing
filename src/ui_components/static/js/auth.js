// Auth JavaScript for Watsonx IPG Testing

document.addEventListener('DOMContentLoaded', function() {
    // Password visibility toggle
    const passwordField = document.getElementById('password');
    if (passwordField) {
        // Add password visibility toggle button
        const passwordContainer = passwordField.parentElement;
        const toggleButton = document.createElement('button');
        toggleButton.type = 'button';
        toggleButton.className = 'btn btn-outline-secondary password-toggle';
        toggleButton.innerHTML = '<i class="fas fa-eye"></i>';
        toggleButton.style.borderLeft = 'none';
        
        passwordContainer.appendChild(toggleButton);
        
        // Toggle password visibility when clicked
        toggleButton.addEventListener('click', function() {
            const type = passwordField.getAttribute('type') === 'password' ? 'text' : 'password';
            passwordField.setAttribute('type', type);
            
            // Toggle icon
            this.innerHTML = type === 'password' ? 
                '<i class="fas fa-eye"></i>' : 
                '<i class="fas fa-eye-slash"></i>';
        });
    }
    
    // Form validation
    const loginForm = document.querySelector('form');
    if (loginForm) {
        loginForm.addEventListener('submit', function(event) {
            let isValid = true;
            
            // Basic email validation for IBM emails
            const emailField = document.getElementById('username');
            if (emailField && emailField.value.trim()) {
                const email = emailField.value.trim();
                if (!email.endsWith('@ibm.com') && !email.endsWith('@in.ibm.com')) {
                    // Mark as invalid if not an IBM email
                    emailField.classList.add('is-invalid');
                    
                    // Add feedback if not already present
                    let feedback = emailField.parentElement.querySelector('.invalid-feedback');
                    if (!feedback) {
                        feedback = document.createElement('div');
                        feedback.className = 'invalid-feedback';
                        feedback.textContent = 'Please enter a valid IBM email address';
                        emailField.parentElement.appendChild(feedback);
                    }
                    
                    isValid = false;
                } else {
                    emailField.classList.remove('is-invalid');
                    emailField.classList.add('is-valid');
                }
            }
            
            // Could add more validation here
            
            if (!isValid) {
                event.preventDefault();
            }
        });
    }
    
    // Theme switcher in preferences
    const themeSelect = document.getElementById('theme');
    if (themeSelect) {
        themeSelect.addEventListener('change', function() {
            // This is just a placeholder functionality
            // In a real implementation, this would apply the theme
            console.log('Theme changed to:', this.value);
            
            // Example of how you might set a class on the body
            // document.body.className = 'theme-' + this.value;
        });
    }
});
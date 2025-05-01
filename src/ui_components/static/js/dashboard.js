// Dashboard interactions
document.addEventListener('DOMContentLoaded', function() {
    // Initialize any dashboard-specific functionality
    console.log('Dashboard initialized');
    
    // Example: Add click handler for quick action buttons
    const quickActionButtons = document.querySelectorAll('.quick-action');
    quickActionButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            console.log('Quick action clicked:', this.getAttribute('data-action'));
        });
    });
    
    // Example: Add hover effects for cards
    const dashboardCards = document.querySelectorAll('.dashboard-card');
    dashboardCards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.classList.add('shadow-lg');
        });
        card.addEventListener('mouseleave', function() {
            this.classList.remove('shadow-lg');
        });
    });
});
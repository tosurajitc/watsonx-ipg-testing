// src/ui_components/static/js/base.js

$(document).ready(function() {
    // Sidebar toggle functionality
    $('.sidebar-toggler').on('click', function() {
        $('body').toggleClass('sidebar-open');
    });
    
    // Sidebar collapse toggle (optional - for desktop view)
    $('#sidebar-collapse-toggle').on('click', function() {
        $('body').toggleClass('sidebar-collapsed');
        $(this).find('i').toggleClass('rotate-180');
    });
    
    // Close sidebar when clicking outside on mobile
    $(document).on('click', function(e) {
        if ($(window).width() < 992) {
            if (!$(e.target).closest('.sidebar').length && 
                !$(e.target).closest('.sidebar-toggler').length && 
                $('body').hasClass('sidebar-open')) {
                $('body').removeClass('sidebar-open');
            }
        }
    });
    
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // Active menu item handling based on current path
    const currentPath = window.location.pathname;
    $('.sidebar-menu .nav-link').each(function() {
        const linkPath = $(this).attr('href');
        if (currentPath.startsWith(linkPath) && linkPath !== '/') {
            $(this).addClass('active');
        }
    });
});

// Add a method to show notifications
function showNotification(title, message, type = 'primary') {
    const notificationHtml = `
        <div class="alert alert-${type} alert-dismissible fade show notification-toast" role="alert">
            <strong>${title}</strong>
            <p class="mb-0">${message}</p>
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
    `;
    
    const notificationContainer = document.createElement('div');
    notificationContainer.className = 'notification-container';
    notificationContainer.innerHTML = notificationHtml;
    
    document.body.appendChild(notificationContainer);
    
    // Remove notification after 5 seconds
    setTimeout(() => {
        if (notificationContainer.querySelector('.alert')) {
            const alertInstance = bootstrap.Alert.getInstance(notificationContainer.querySelector('.alert'));
            if (alertInstance) {
                alertInstance.close();
            } else {
                notificationContainer.remove();
            }
        }
    }, 5000);
}
// Replace the sidebar-related JavaScript in static/js/main.js with this simplified version

// User card toggle functionality
let userCardExpanded = false;

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    // Initialize user card functionality
    initializeUserCard();
    
    // Initialize other components
    initializeTimeDisplay();
    initializeAlertDismiss();
    initializeMobileNavigation();
});

// Initialize user card functionality 
function initializeUserCard() {
    const userCard = document.querySelector('.user-card');
    if (!userCard) return;
    
    userCard.addEventListener('click', function(e) {
        // Don't toggle if clicking on action buttons
        if (e.target.closest('.user-action-btn')) {
            return;
        }
        
        toggleUserActions();
    });
    
    // Close user actions when clicking outside
    document.addEventListener('click', function(e) {
        if (!e.target.closest('.user-card') && userCardExpanded) {
            hideUserActions();
        }
    });
}

// Toggle user actions visibility
function toggleUserActions() {
    const userActions = document.querySelector('.user-actions');
    const userCard = document.querySelector('.user-card');
    
    if (!userActions || !userCard) return;
    
    userCardExpanded = !userCardExpanded;
    
    if (userCardExpanded) {
        userActions.classList.add('show');
        userCard.classList.add('expanded');
    } else {
        userActions.classList.remove('show');
        userCard.classList.remove('expanded');
    }
}

// Hide user actions
function hideUserActions() {
    const userActions = document.querySelector('.user-actions');
    const userCard = document.querySelector('.user-card');
    
    if (userActions && userCard) {
        userActions.classList.remove('show');
        userCard.classList.remove('expanded');
        userCardExpanded = false;
    }
}

// Mobile sidebar functionality (simplified)
function toggleMobileSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.querySelector('.mobile-sidebar-overlay');
    
    if (sidebar && overlay) {
        sidebar.classList.add('mobile-open');
        overlay.classList.add('show');
        hideUserActions(); // Hide user actions on mobile
    }
}

function closeMobileSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.querySelector('.mobile-sidebar-overlay');
    
    if (sidebar && overlay) {
        sidebar.classList.remove('mobile-open');
        overlay.classList.remove('show');
        hideUserActions(); // Hide user actions when closing
    }
}

// Initialize time display
function initializeTimeDisplay() {
    function updateTime() {
        const now = new Date();
        const timeElement = document.getElementById('current-time');
        if (timeElement) {
            timeElement.textContent = now.toLocaleTimeString();
        }
    }
    
    if (document.getElementById('current-time')) {
        updateTime();
        setInterval(updateTime, 1000);
    }
}

// Initialize alert auto-dismiss
function initializeAlertDismiss() {
    setTimeout(function() {
        const alerts = document.querySelectorAll('.alert');
        alerts.forEach(function(alert) {
            if (alert.classList.contains('alert-success') || alert.classList.contains('alert-info')) {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            }
        });
    }, 5000);
}

// Initialize mobile navigation
function initializeMobileNavigation() {
    // Close mobile sidebar when clicking on nav links
    const navLinks = document.querySelectorAll('.nav-link');
    navLinks.forEach(link => {
        link.addEventListener('click', function() {
            if (window.innerWidth <= 768) {
                closeMobileSidebar();
            }
        });
    });
    
    // Handle window resize
    window.addEventListener('resize', function() {
        if (window.innerWidth > 768) {
            closeMobileSidebar();
        }
    });
}

// Utility functions for forms
function showLoading(buttonElement, loadingText = 'Loading...') {
    if (buttonElement) {
        buttonElement.disabled = true;
        buttonElement.innerHTML = `<i class="fas fa-spinner fa-spin me-2"></i>${loadingText}`;
    }
}

function hideLoading(buttonElement, originalText) {
    if (buttonElement) {
        buttonElement.disabled = false;
        buttonElement.innerHTML = originalText;
    }
}

// Form validation helpers
function validateRequired(input) {
    const value = input.value.trim();
    if (!value) {
        showFieldError(input, 'This field is required');
        return false;
    }
    clearFieldError(input);
    return true;
}

function validateEmail(input) {
    const email = input.value.trim();
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    
    if (email && !emailRegex.test(email)) {
        showFieldError(input, 'Please enter a valid email address');
        return false;
    }
    clearFieldError(input);
    return true;
}

function showFieldError(input, message) {
    input.classList.add('is-invalid');
    
    let errorDiv = input.parentNode.querySelector('.invalid-feedback');
    if (!errorDiv) {
        errorDiv = document.createElement('div');
        errorDiv.className = 'invalid-feedback';
        input.parentNode.appendChild(errorDiv);
    }
    errorDiv.textContent = message;
}

function clearFieldError(input) {
    input.classList.remove('is-invalid');
    const errorDiv = input.parentNode.querySelector('.invalid-feedback');
    if (errorDiv) {
        errorDiv.textContent = '';
    }
}

// AJAX helper functions
function makeRequest(url, options = {}) {
    const defaultOptions = {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
        },
    };
    
    return fetch(url, { ...defaultOptions, ...options })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .catch(error => {
            console.error('Request failed:', error);
            throw error;
        });
}

// Toast notifications
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0`;
    toast.role = 'alert';
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    
    let toastContainer = document.querySelector('.toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
        document.body.appendChild(toastContainer);
    }
    
    toastContainer.appendChild(toast);
    
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
    
    toast.addEventListener('hidden.bs.toast', () => {
        toast.remove();
    });
}

// Export functions for use in other scripts
window.FinancialSystem = {
    toggleUserActions,
    hideUserActions,
    toggleMobileSidebar,
    closeMobileSidebar,
    showLoading,
    hideLoading,
    validateRequired,
    validateEmail,
    showFieldError,
    clearFieldError,
    makeRequest,
    showToast
};
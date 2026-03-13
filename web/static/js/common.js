/**
 * Common utilities for News Digest Web UI
 */

// API base URL
const API_BASE = '';

// Format time remaining
function formatTimeRemaining(targetTime) {
    const now = new Date();
    const diff = targetTime - now;
    
    if (diff <= 0) return '00:00';
    
    const hours = Math.floor(diff / (1000 * 60 * 60));
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
    
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}`;
}

// Format relative time
function timeAgo(date) {
    const seconds = Math.floor((new Date() - new Date(date)) / 1000);
    
    if (seconds < 60) return 'just now';
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    return `${Math.floor(seconds / 86400)}d ago`;
}

// API fetch wrapper
async function api(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    const response = await fetch(url, {
        headers: {
            'Content-Type': 'application/json',
        },
        ...options,
    });
    
    if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
    }
    
    return response.json();
}

// Show notification
function showNotification(message, type = 'info') {
    // Simple alert for now - could be enhanced with toast notifications
    console.log(`[${type}] ${message}`);
}

// Modal helpers
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('active');
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('active');
    }
}

// Format number with commas
function formatNumber(num) {
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

// Truncate text
function truncate(str, maxLength) {
    if (str.length <= maxLength) return str;
    return str.substring(0, maxLength) + '...';
}

// Update countdown timer for 8am Asia/Shanghai
function updatePostTimer(elementId = 'timeUntilPost') {
    const el = document.getElementById(elementId);
    if (!el) return;
    
    const update = () => {
        const now = new Date();
        const target = new Date();
        target.setHours(8, 0, 0, 0);
        
        // If past 8am, target is tomorrow
        if (now > target) {
            target.setDate(target.getDate() + 1);
        }
        
        el.textContent = formatTimeRemaining(target);
    };
    
    update();
    setInterval(update, 60000); // Update every minute
}

// Initialize common functionality
document.addEventListener('DOMContentLoaded', () => {
    // Start post timer
    updatePostTimer();
    
    // Close modals on escape
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            document.querySelectorAll('.modal.active').forEach(modal => {
                modal.classList.remove('active');
            });
        }
    });
    
    // Close modals on backdrop click
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.classList.remove('active');
            }
        });
    });
});

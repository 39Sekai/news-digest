/**
 * Feeds management page JavaScript
 */

let feedsData = [];

document.addEventListener('DOMContentLoaded', () => {
    loadFeeds();
    
    // Add feed button
    const addBtn = document.getElementById('addFeedBtn');
    if (addBtn) {
        addBtn.addEventListener('click', () => openModal('addFeedModal'));
    }
    
    // Close modal
    const closeAddModal = document.getElementById('closeAddModal');
    if (closeAddModal) {
        closeAddModal.addEventListener('click', () => closeModal('addFeedModal'));
    }
    
    // Cancel button
    const cancelAdd = document.getElementById('cancelAdd');
    if (cancelAdd) {
        cancelAdd.addEventListener('click', () => closeModal('addFeedModal'));
    }
    
    // Add feed form
    const addForm = document.getElementById('addFeedForm');
    if (addForm) {
        addForm.addEventListener('submit', handleAddFeed);
    }
    
    // Filters
    const statusFilter = document.getElementById('statusFilter');
    const categoryFilter = document.getElementById('categoryFilter');
    const searchInput = document.getElementById('searchFeeds');
    
    if (statusFilter) statusFilter.addEventListener('change', filterFeeds);
    if (categoryFilter) categoryFilter.addEventListener('change', filterFeeds);
    if (searchInput) searchInput.addEventListener('input', debounce(filterFeeds, 300));
});

async function loadFeeds() {
    try {
        const data = await api('/api/feeds');
        feedsData = data.feeds;
        renderFeeds(feedsData);
        updateStats(data.feeds);
    } catch (error) {
        console.error('Failed to load feeds:', error);
        const list = document.getElementById('feedList');
        list.innerHTML = '<div class="error">Failed to load feeds. <button onclick="loadFeeds()">Retry</button></div>';
    }
}

function renderFeeds(feeds) {
    const list = document.getElementById('feedList');
    
    if (feeds.length === 0) {
        list.innerHTML = '<div class="empty">No feeds found.</div>';
        return;
    }
    
    list.innerHTML = feeds.map(feed => `
        <div class="feed-item" data-id="${feed.id}">
            <div class="feed-info">
                <div class="feed-name">${escapeHtml(feed.name)}</div>
                <div class="feed-meta">
                    ${feed.category} • ${truncate(feed.url, 50)} • 
                    ${feed.article_count} articles
                    ${feed.last_fetch ? '• Updated ' + timeAgo(feed.last_fetch) : ''}
                </div>
            </div>
            <div class="feed-status">
                <span class="status-badge ${feed.status}">${feed.status}</span>
                <button class="btn btn-sm btn-secondary" onclick="editFeed(${feed.id})">Edit</button>
                <button class="btn btn-sm ${feed.enabled ? 'btn-secondary' : 'btn-primary'}" 
                        onclick="toggleFeed(${feed.id}, ${!feed.enabled})">
                    ${feed.enabled ? 'Disable' : 'Enable'}
                </button>
            </div>
        </div>
    `).join('');
}

function updateStats(feeds) {
    const total = feeds.length;
    const healthy = feeds.filter(f => f.status === 'healthy').length;
    const stale = feeds.filter(f => f.status === 'stale').length;
    const broken = feeds.filter(f => f.status === 'broken').length;
    
    updateElement('totalCount', total);
    updateElement('healthyCount', healthy);
    updateElement('staleCount', stale);
    updateElement('brokenCount', broken);
}

function filterFeeds() {
    const status = document.getElementById('statusFilter').value;
    const category = document.getElementById('categoryFilter').value;
    const search = document.getElementById('searchFeeds').value.toLowerCase();
    
    let filtered = feedsData;
    
    if (status) {
        filtered = filtered.filter(f => f.status === status);
    }
    if (category) {
        filtered = filtered.filter(f => f.category === category);
    }
    if (search) {
        filtered = filtered.filter(f => 
            f.name.toLowerCase().includes(search) ||
            f.url.toLowerCase().includes(search)
        );
    }
    
    renderFeeds(filtered);
}

async function handleAddFeed(e) {
    e.preventDefault();
    
    const url = document.getElementById('feedUrl').value;
    const name = document.getElementById('feedName').value;
    const category = document.getElementById('feedCategory').value;
    
    try {
        const formData = new FormData();
        formData.append('url', url);
        formData.append('name', name);
        formData.append('category', category);
        
        const response = await fetch('/api/feeds', {
            method: 'POST',
            body: formData
        });
        
        if (response.ok) {
            closeModal('addFeedModal');
            e.target.reset();
            loadFeeds();
            showNotification('Feed added successfully', 'success');
        } else {
            throw new Error('Failed to add feed');
        }
    } catch (error) {
        console.error('Error adding feed:', error);
        showNotification('Failed to add feed', 'error');
    }
}

async function toggleFeed(id, enable) {
    try {
        const endpoint = enable ? `/api/feeds/${id}/enable` : `/api/feeds/${id}/disable`;
        const response = await fetch(endpoint, { method: 'POST' });
        
        if (response.ok) {
            loadFeeds();
            showNotification(enable ? 'Feed enabled' : 'Feed disabled', 'success');
        }
    } catch (error) {
        console.error('Error toggling feed:', error);
        showNotification('Failed to update feed', 'error');
    }
}

function editFeed(id) {
    // TODO: Implement edit modal
    showNotification('Edit feature coming soon', 'info');
}

// Utility functions
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function updateElement(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

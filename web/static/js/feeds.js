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

    // Import feeds button
    const importBtn = document.getElementById('importFeedsBtn');
    if (importBtn) {
        importBtn.addEventListener('click', () => openModal('importFeedsModal'));
    }

    // Close modals
    const closeAddModal = document.getElementById('closeAddModal');
    if (closeAddModal) {
        closeAddModal.addEventListener('click', () => closeModal('addFeedModal'));
    }

    const closeImportModal = document.getElementById('closeImportModal');
    if (closeImportModal) {
        closeImportModal.addEventListener('click', () => closeModal('importFeedsModal'));
    }

    // Cancel buttons
    const cancelAdd = document.getElementById('cancelAdd');
    if (cancelAdd) {
        cancelAdd.addEventListener('click', () => closeModal('addFeedModal'));
    }

    const cancelImport = document.getElementById('cancelImport');
    if (cancelImport) {
        cancelImport.addEventListener('click', () => closeModal('importFeedsModal'));
    }

    // Forms
    const addForm = document.getElementById('addFeedForm');
    if (addForm) {
        addForm.addEventListener('submit', handleAddFeed);
    }

    const importForm = document.getElementById('importFeedsForm');
    if (importForm) {
        importForm.addEventListener('submit', handleImportFeeds);
    }

    // File input change
    const importFile = document.getElementById('importFile');
    if (importFile) {
        importFile.addEventListener('change', handleFileSelect);
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
        const data = await api('/api/v1/feeds');
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
        const response = await fetch('/api/v1/feeds', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                url: url,
                name: name,
                category: category,
                reliability: 0.7
            })
        });

        if (response.ok) {
            closeModal('addFeedModal');
            e.target.reset();
            loadFeeds();
            showNotification('Feed added successfully', 'success');
        } else {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to add feed');
        }
    } catch (error) {
        console.error('Error adding feed:', error);
        showNotification('Failed to add feed: ' + error.message, 'error');
    }
}

async function toggleFeed(id, enable) {
    try {
        const endpoint = enable ? `/api/v1/feeds/${id}/enable` : `/api/v1/feeds/${id}/disable`;
        const response = await fetch(endpoint, { method: 'POST' });

        if (response.ok) {
            loadFeeds();
            showNotification(enable ? 'Feed enabled' : 'Feed disabled', 'success');
        } else {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to update feed');
        }
    } catch (error) {
        console.error('Error toggling feed:', error);
        showNotification('Failed to update feed: ' + error.message, 'error');
    }
}

function editFeed(id) {
    // TODO: Implement edit modal
    showNotification('Edit feature coming soon', 'info');
}

// Import functionality
let feedsToImport = [];

function handleFileSelect(e) {
    const file = e.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = function(event) {
        try {
            const content = event.target.result;
            const fileType = file.name.toLowerCase();

            if (fileType.endsWith('.json')) {
                feedsToImport = parseJsonFeeds(content);
            } else if (fileType.endsWith('.opml') || fileType.endsWith('.xml')) {
                feedsToImport = parseOpmlFeeds(content);
            } else {
                throw new Error('Unsupported file format');
            }

            showImportPreview(feedsToImport);
            document.getElementById('confirmImport').disabled = feedsToImport.length === 0;
        } catch (error) {
            console.error('Error parsing file:', error);
            showNotification('Error parsing file: ' + error.message, 'error');
            feedsToImport = [];
            document.getElementById('confirmImport').disabled = true;
        }
    };
    reader.readAsText(file);
}

function parseJsonFeeds(content) {
    const data = JSON.parse(content);
    if (data.feeds && Array.isArray(data.feeds)) {
        return data.feeds.map(f => ({
            url: f.url || f.feed_url || f.link,
            name: f.name || f.title || 'Unnamed Feed',
            category: f.category || 'general'
        })).filter(f => f.url);
    }
    throw new Error('Invalid JSON format: expected "feeds" array');
}

function parseOpmlFeeds(content) {
    const parser = new DOMParser();
    const doc = parser.parseFromString(content, 'text/xml');
    const outlines = doc.querySelectorAll('outline[type="rss"], outline[xmlUrl]');

    return Array.from(outlines).map(outline => ({
        url: outline.getAttribute('xmlUrl'),
        name: outline.getAttribute('title') || outline.getAttribute('text') || 'Unnamed Feed',
        category: 'general'
    })).filter(f => f.url);
}

function showImportPreview(feeds) {
    const preview = document.getElementById('importPreview');
    if (feeds.length === 0) {
        preview.innerHTML = '<p class="placeholder">No valid feeds found in file.</p>';
        return;
    }

    preview.innerHTML = `
        <p><strong>${feeds.length} feeds found:</strong></p>
        <ul class="import-list">
            ${feeds.slice(0, 10).map(f => `<li>${escapeHtml(f.name)} <span class="url">${truncate(f.url, 40)}</span></li>`).join('')}
            ${feeds.length > 10 ? `<li class="more">... and ${feeds.length - 10} more</li>` : ''}
        </ul>
    `;
}

async function handleImportFeeds(e) {
    e.preventDefault();

    if (feedsToImport.length === 0) {
        showNotification('No feeds to import', 'error');
        return;
    }

    const defaultCategory = document.getElementById('importCategory').value;
    const confirmBtn = document.getElementById('confirmImport');
    confirmBtn.disabled = true;
    confirmBtn.textContent = 'Importing...';

    let success = 0;
    let failed = 0;

    for (const feed of feedsToImport) {
        try {
            const response = await fetch('/api/v1/feeds', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    url: feed.url,
                    name: feed.name,
                    category: feed.category || defaultCategory,
                    reliability: 0.7
                })
            });

            if (response.ok) {
                success++;
            } else {
                failed++;
            }
        } catch (error) {
            console.error('Error importing feed:', error);
            failed++;
        }
    }

    closeModal('importFeedsModal');
    e.target.reset();
    feedsToImport = [];
    document.getElementById('importPreview').innerHTML = '<p class="placeholder">Select a file to preview feeds...</p>';

    loadFeeds();
    showNotification(`Imported ${success} feeds (${failed} failed)`, success > 0 ? 'success' : 'warning');

    confirmBtn.disabled = false;
    confirmBtn.textContent = 'Import Feeds';
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

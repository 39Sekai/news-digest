/**
 * Dashboard page JavaScript
 */

document.addEventListener('DOMContentLoaded', () => {
    loadDashboardStats();
    loadFeedHealth();
    
    // Preview button
    const previewBtn = document.getElementById('previewBtn');
    if (previewBtn) {
        previewBtn.addEventListener('click', showPreview);
    }
    
    // Close modal
    const closeModal = document.getElementById('closeModal');
    if (closeModal) {
        closeModal.addEventListener('click', () => {
            document.getElementById('previewModal').classList.remove('active');
        });
    }
});

async function loadDashboardStats() {
    try {
        const stats = await api('/api/v1/stats');

        // Update stats cards
        updateElement('totalFeeds', formatNumber(stats.feeds.total));
        updateElement('brokenFeeds', formatNumber(stats.feeds.broken));
        updateElement('pendingBriefs', formatNumber(stats.articles.pending_briefs));
        updateElement('curatedBriefs', formatNumber(stats.articles.curated));

        // Update brief badge
        const briefBadge = document.getElementById('briefBadge');
        if (briefBadge) {
            briefBadge.textContent = stats.articles.pending_briefs;
            briefBadge.style.display = stats.articles.pending_briefs > 0 ? 'block' : 'none';
        }

        // Highlight action if pending briefs
        const briefAction = document.getElementById('briefAction');
        if (briefAction && stats.articles.pending_briefs > 0) {
            briefAction.classList.add('urgent');
        }

    } catch (error) {
        console.error('Failed to load stats:', error);
    }
}

async function loadFeedHealth() {
    try {
        // Fetch actual feeds to compute health
        const data = await api('/api/v1/feeds');
        const feeds = data.feeds;
        
        const total = feeds.length;
        const healthy = feeds.filter(f => f.enabled && (f.error_count || 0) === 0).length;
        const withErrors = feeds.filter(f => f.enabled && (f.error_count || 0) > 0 && (f.error_count || 0) < 5).length;
        const disabled = feeds.filter(f => !f.enabled).length;
        
        // Update feed health widget
        const feedHealthEl = document.getElementById('feedHealthWidget');
        if (feedHealthEl) {
            feedHealthEl.innerHTML = `
                <div class="health-stat healthy">
                    <span class="health-number">${healthy}</span>
                    <span class="health-label">✅ Healthy</span>
                </div>
                <div class="health-stat warning">
                    <span class="health-number">${withErrors}</span>
                    <span class="health-label">⚠️ Errors</span>
                </div>
                <div class="health-stat disabled">
                    <span class="health-number">${disabled}</span>
                    <span class="health-label">❌ Disabled</span>
                </div>
                <div class="health-stat total">
                    <span class="health-number">${total}</span>
                    <span class="health-label">📡 Total</span>
                </div>
            `;
        }

        // Also update legacy elements
        updateElement('healthyCount', formatNumber(healthy));
        updateElement('errorCount', formatNumber(withErrors));
        updateElement('disabledCount', formatNumber(disabled));
        updateElement('totalCount', formatNumber(total));

    } catch (error) {
        console.error('Failed to load feed health:', error);
    }
}

async function showPreview() {
    try {
        const preview = await api('/api/v1/briefs/preview');

        const previewEl = document.getElementById('discordPreview');
        previewEl.innerHTML = renderDiscordPreview(preview);

        openModal('previewModal');
    } catch (error) {
        console.error('Failed to load preview:', error);
        showNotification('Failed to load preview', 'error');
    }
}

function renderDiscordPreview(data) {
    const articles = data.articles.map(a => 
        `<div class="discord-article">• ${escapeHtml(a.brief)} — <span class="discord-source">${escapeHtml(a.source)}</span></div>`
    ).join('');
    
    return `
        <div class="discord-header">📰 Tech News — ${escapeHtml(data.date)}</div>
        ${articles}
        <div class="discord-footer">_Total: ${data.total} articles from ${data.feed_count} sources_</div>
    `;
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

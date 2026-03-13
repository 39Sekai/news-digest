/**
 * Brief editor page JavaScript
 */

let briefQueue = [];

document.addEventListener('DOMContentLoaded', () => {
    loadBriefQueue();
    
    // Preview button
    const previewBtn = document.getElementById('previewBtn');
    if (previewBtn) {
        previewBtn.addEventListener('click', showPreview);
    }
    
    // Auto-fill button
    const autoBtn = document.getElementById('autoBriefBtn');
    if (autoBtn) {
        autoBtn.addEventListener('click', autoFillBriefs);
    }
    
    // Close modal
    const closeModal = document.getElementById('closeModal');
    if (closeModal) {
        closeModal.addEventListener('click', () => {
            document.getElementById('previewModal').classList.remove('active');
        });
    }
    
    // Update timer
    updatePostTimer();
});

async function loadBriefQueue() {
    try {
        const data = await api('/api/briefs/queue');
        briefQueue = data.articles;
        renderBriefQueue(briefQueue);
        updateProgress();
    } catch (error) {
        console.error('Failed to load brief queue:', error);
        const queue = document.getElementById('briefQueue');
        queue.innerHTML = '<div class="error">Failed to load articles. <button onclick="loadBriefQueue()">Retry</button></div>';
    }
}

function renderBriefQueue(articles) {
    const queue = document.getElementById('briefQueue');
    
    if (articles.length === 0) {
        queue.innerHTML = '<div class="empty">No articles pending for today.</div>';
        return;
    }
    
    queue.innerHTML = articles.map(article => `
        <div class="brief-item ${article.brief ? 'curated' : 'needs-brief'}" data-id="${article.id}">
            <div class="brief-header">
                <div class="brief-source">
                    <span class="source-name">${escapeHtml(article.source_name)}</span>
                    <span class="time">${timeAgo(article.published_at)}</span>
                </div>
                <span class="brief-score">${(article.score * 100).toFixed(0)}%</span>
            </div>
            <div class="original-title">${escapeHtml(article.original_title)}</div>
            <div class="brief-input-group">
                <input type="text" 
                       class="brief-input" 
                       placeholder="Write one-liner brief..."
                       value="${escapeHtml(article.brief || '')}"
                       onchange="saveBrief(${article.id}, this.value)"
                       onkeypress="handleBriefKeypress(event, ${article.id}, this)">
                <button class="btn btn-primary" onclick="saveBrief(${article.id}, this.previousElementSibling.value)">Save</button>
                <button class="btn btn-secondary" onclick="skipArticle(${article.id})">Skip</button>
            </div>
        </div>
    `).join('');
}

function updateProgress() {
    const total = briefQueue.length;
    const curated = briefQueue.filter(a => a.brief).length;
    const percentage = total > 0 ? Math.round((curated / total) * 100) : 0;
    
    updateElement('briefProgress', `${curated} of ${total} briefs written`);
    updateElement('progressPercent', `${percentage}%`);
    
    const fill = document.getElementById('progressFill');
    if (fill) fill.style.width = `${percentage}%`;
}

async function saveBrief(articleId, brief) {
    if (!brief.trim()) return;
    
    try {
        const formData = new FormData();
        formData.append('brief', brief.trim());
        
        const response = await fetch(`/api/briefs/${articleId}`, {
            method: 'POST',
            body: formData
        });
        
        if (response.ok) {
            // Update local data
            const article = briefQueue.find(a => a.id === articleId);
            if (article) {
                article.brief = brief.trim();
            }
            
            // Update UI
            const item = document.querySelector(`.brief-item[data-id="${articleId}"]`);
            if (item) {
                item.classList.remove('needs-brief');
                item.classList.add('curated');
            }
            
            updateProgress();
            showNotification('Brief saved', 'success');
        }
    } catch (error) {
        console.error('Error saving brief:', error);
        showNotification('Failed to save brief', 'error');
    }
}

async function skipArticle(articleId) {
    try {
        const response = await fetch(`/api/briefs/${articleId}/skip`, {
            method: 'POST'
        });
        
        if (response.ok) {
            // Remove from queue
            briefQueue = briefQueue.filter(a => a.id !== articleId);
            renderBriefQueue(briefQueue);
            updateProgress();
            showNotification('Article skipped', 'info');
        }
    } catch (error) {
        console.error('Error skipping article:', error);
        showNotification('Failed to skip article', 'error');
    }
}

function handleBriefKeypress(event, articleId, input) {
    if (event.key === 'Enter') {
        saveBrief(articleId, input.value);
        // Move to next input
        const items = document.querySelectorAll('.brief-input');
        const currentIndex = Array.from(items).indexOf(input);
        if (currentIndex < items.length - 1) {
            items[currentIndex + 1].focus();
        }
    }
}

async function autoFillBriefs() {
    // Auto-fill all empty briefs with original titles (fallback)
    const inputs = document.querySelectorAll('.brief-item.needs-brief .brief-input');
    
    for (const input of inputs) {
        const item = input.closest('.brief-item');
        const articleId = parseInt(item.dataset.id);
        const article = briefQueue.find(a => a.id === articleId);
        
        if (article && !input.value) {
            // Truncate title to reasonable length for one-liner
            const title = article.original_title;
            input.value = title.length > 100 ? title.substring(0, 97) + '...' : title;
            await saveBrief(articleId, input.value);
        }
    }
    
    showNotification('Auto-filled with original titles', 'success');
}

async function showPreview() {
    try {
        const preview = await api('/api/briefs/preview');
        
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

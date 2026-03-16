/**
 * Settings page JavaScript
 */

let currentSettings = {};

document.addEventListener('DOMContentLoaded', () => {
    loadSettings();
    
    // Filter mode toggle
    const filterMode = document.getElementById('filterMode');
    if (filterMode) {
        filterMode.addEventListener('change', toggleFilterMode);
    }
    
    // Form submission
    const form = document.getElementById('settingsForm');
    if (form) {
        form.addEventListener('submit', saveSettings);
    }
    
    // Reset button
    const resetBtn = document.getElementById('resetBtn');
    if (resetBtn) {
        resetBtn.addEventListener('click', resetSettings);
    }
    
    // Cancel button
    const cancelBtn = document.getElementById('cancelBtn');
    if (cancelBtn) {
        cancelBtn.addEventListener('click', () => {
            loadSettings(); // Reload to discard changes
            showNotification('Changes discarded', 'info');
        });
    }
});

async function loadSettings() {
    try {
        const settings = await api('/api/v1/settings');
        currentSettings = settings;
        populateForm(settings);
    } catch (error) {
        console.error('Failed to load settings:', error);
        showNotification('Failed to load settings', 'error');
    }
}

function populateForm(settings) {
    // Posting schedule
    setValue('postTime', settings.post_time);
    setValue('timezone', settings.timezone);
    
    // Filtering
    setValue('filterMode', settings.filter_mode);
    setValue('topNLimit', settings.top_n_limit);
    setValue('binaryThreshold', settings.binary_threshold);
    setValue('maxArticleAge', settings.max_article_age);
    
    // Scoring (read-only)
    setValue('semanticWeight', settings.semantic_weight || 0.6);
    setValue('recencyWeight', settings.recency_weight || 0.2);
    setValue('sourceWeight', settings.source_weight || 0.1);
    setValue('noveltyWeight', settings.novelty_weight || 0.1);
    
    // Feed health
    setValue('maxFeedErrors', settings.max_feed_errors);
    setValue('staleFeedHours', settings.stale_feed_hours);
    setChecked('alertOnFeedFailure', settings.alert_on_feed_failure);
    
    // Deduplication
    setValue('dedupeThreshold', settings.dedupe_threshold);
    
    // Categories
    document.querySelectorAll('input[name="enabled_categories"]').forEach(cb => {
        cb.checked = settings.enabled_categories?.includes(cb.value) || false;
    });
    
    // Update filter mode visibility
    toggleFilterMode();
}

function toggleFilterMode() {
    const mode = document.getElementById('filterMode').value;
    const topNGroup = document.getElementById('topNGroup');
    const thresholdGroup = document.getElementById('thresholdGroup');
    
    if (mode === 'top_n') {
        topNGroup?.classList.remove('hidden');
        thresholdGroup?.classList.add('hidden');
    } else {
        topNGroup?.classList.add('hidden');
        thresholdGroup?.classList.remove('hidden');
    }
}

async function saveSettings(e) {
    e.preventDefault();

    const settings = collectFormData();

    // Validate weights sum to 1.0
    const weightSum = settings.semantic_weight + settings.recency_weight +
                      settings.source_weight + settings.novelty_weight;
    if (Math.abs(weightSum - 1.0) > 0.001) {
        showNotification('Scoring weights must sum to 1.0', 'error');
        return;
    }

    try {
        const response = await fetch('/api/v1/settings', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(settings)
        });

        if (response.ok) {
            currentSettings = settings;
            showNotification('Settings saved successfully', 'success');
        } else {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to save settings');
        }
    } catch (error) {
        console.error('Error saving settings:', error);
        showNotification('Failed to save settings: ' + error.message, 'error');
    }
}

async function resetSettings() {
    if (!confirm('Reset all settings to defaults?')) return;

    try {
        const response = await fetch('/api/v1/settings/reset', {
            method: 'POST'
        });

        if (response.ok) {
            const settings = await response.json();
            currentSettings = settings.settings;
            populateForm(currentSettings);
            showNotification('Settings reset to defaults', 'success');
        } else {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to reset settings');
        }
    } catch (error) {
        console.error('Error resetting settings:', error);
        showNotification('Failed to reset settings: ' + error.message, 'error');
    }
}

function collectFormData() {
    const enabledCategories = Array.from(
        document.querySelectorAll('input[name="enabled_categories"]:checked')
    ).map(cb => cb.value);
    
    return {
        post_time: getValue('postTime'),
        timezone: getValue('timezone'),
        max_article_age: parseInt(getValue('maxArticleAge')),
        filter_mode: getValue('filterMode'),
        top_n_limit: parseInt(getValue('topNLimit')),
        binary_threshold: parseFloat(getValue('binaryThreshold')),
        semantic_weight: parseFloat(getValue('semanticWeight')),
        recency_weight: parseFloat(getValue('recencyWeight')),
        source_weight: parseFloat(getValue('sourceWeight')),
        novelty_weight: parseFloat(getValue('noveltyWeight')),
        max_feed_errors: parseInt(getValue('maxFeedErrors')),
        stale_feed_hours: parseInt(getValue('staleFeedHours')),
        alert_on_feed_failure: getChecked('alertOnFeedFailure'),
        dedupe_threshold: parseFloat(getValue('dedupeThreshold')),
        enabled_categories: enabledCategories
    };
}

// Form helpers
function setValue(id, value) {
    const el = document.getElementById(id);
    if (el) el.value = value;
}

function getValue(id) {
    const el = document.getElementById(id);
    return el ? el.value : '';
}

function setChecked(id, checked) {
    const el = document.getElementById(id);
    if (el) el.checked = checked;
}

function getChecked(id) {
    const el = document.getElementById(id);
    return el ? el.checked : false;
}

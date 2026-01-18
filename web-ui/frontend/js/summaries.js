// Summaries browsing and search functionality

const API_BASE = '/api';

async function loadSummaries() {
    const container = document.getElementById('summaries-list');
    container.innerHTML = '<div class="empty-state"><p>Loading summaries...</p></div>';

    try {
        const response = await fetch(`${API_BASE}/summaries`);
        if (!response.ok) throw new Error('Failed to load summaries');

        const data = await response.json();
        renderSummaries(data.summaries);
    } catch (error) {
        console.error('Error loading summaries:', error);
        container.innerHTML = `<div class="empty-state"><h3>Error loading summaries</h3><p>${error.message}</p></div>`;
    }
}

function renderSummaries(summaries) {
    const container = document.getElementById('summaries-list');

    if (summaries.length === 0) {
        container.innerHTML = '<div class="empty-state"><h3>No summaries found</h3><p>Try a different search or create a new summary.</p></div>';
        return;
    }

    container.innerHTML = summaries.map(summary => `
        <div class="summary-card" data-filename="${escapeHtml(summary.filename)}">
            <h3>${escapeHtml(summary.title)}</h3>
            <p class="preview">${escapeHtml(summary.preview)}</p>
            <p class="date">${formatDate(summary.modified_date)}</p>
        </div>
    `).join('');

    // Add click handlers
    container.querySelectorAll('.summary-card').forEach(card => {
        card.addEventListener('click', () => viewSummary(card.dataset.filename));
    });
}

async function viewSummary(filename) {
    const listContainer = document.getElementById('summaries-list');
    const viewer = document.getElementById('summary-viewer');
    const contentEl = document.getElementById('summary-content');

    try {
        // Show loading state
        contentEl.innerHTML = '<p>Loading...</p>';
        listContainer.classList.add('hidden');
        viewer.classList.remove('hidden');

        const response = await fetch(`${API_BASE}/summaries/${encodeURIComponent(filename)}`);
        if (!response.ok) throw new Error('Failed to load summary');

        const summary = await response.json();

        // Render markdown content using marked.js
        contentEl.innerHTML = marked.parse(summary.content);
    } catch (error) {
        console.error('Error loading summary:', error);
        contentEl.innerHTML = `<div class="empty-state"><h3>Error loading summary</h3><p>${error.message}</p></div>`;
    }
}

// Search functionality
document.getElementById('search-btn').addEventListener('click', async () => {
    const query = document.getElementById('search-input').value.trim();
    if (!query) {
        loadSummaries();
        return;
    }

    const container = document.getElementById('summaries-list');
    container.innerHTML = '<div class="empty-state"><p>Searching...</p></div>';

    try {
        const response = await fetch(`${API_BASE}/summaries/search?q=${encodeURIComponent(query)}`);
        if (!response.ok) throw new Error('Search failed');

        const data = await response.json();
        renderSummaries(data.summaries);
    } catch (error) {
        console.error('Error searching:', error);
        container.innerHTML = `<div class="empty-state"><h3>Search error</h3><p>${error.message}</p></div>`;
    }
});

// Search on Enter key
document.getElementById('search-input').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
        document.getElementById('search-btn').click();
    }
});

// Clear search
document.getElementById('clear-search-btn').addEventListener('click', () => {
    document.getElementById('search-input').value = '';
    loadSummaries();
});

// Back button
document.getElementById('back-btn').addEventListener('click', () => {
    document.getElementById('summaries-list').classList.remove('hidden');
    document.getElementById('summary-viewer').classList.add('hidden');
});

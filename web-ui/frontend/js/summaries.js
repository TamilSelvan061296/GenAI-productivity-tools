// Summaries browsing and search functionality

const API_BASE = '/api';

// Store all summaries for client-side category filtering
let allSummaries = [];
let activeCategory = 'all';

async function loadSummaries() {
    const container = document.getElementById('summaries-list');
    container.innerHTML = '<div class="empty-state"><p>Loading summaries...</p></div>';

    try {
        const response = await fetch(`${API_BASE}/summaries`);
        if (!response.ok) throw new Error('Failed to load summaries');

        const data = await response.json();
        allSummaries = data.summaries;
        renderSummaries(filterByCategory(allSummaries, activeCategory));
    } catch (error) {
        console.error('Error loading summaries:', error);
        container.innerHTML = `<div class="empty-state"><h3>Error loading summaries</h3><p>${error.message}</p></div>`;
    }
}

function filterByCategory(summaries, category) {
    if (category === 'all') return summaries;
    return summaries.filter(s => s.category === category);
}

function renderSummaries(summaries) {
    const container = document.getElementById('summaries-list');

    if (summaries.length === 0) {
        container.innerHTML = '<div class="empty-state"><h3>No summaries found</h3><p>Try a different search or category.</p></div>';
        return;
    }

    // Group summaries by category
    const grouped = {};
    summaries.forEach(summary => {
        const cat = summary.category || 'uncategorized';
        if (!grouped[cat]) grouped[cat] = [];
        grouped[cat].push(summary);
    });

    // Define category display order and labels
    const categoryOrder = ['tech', 'business', 'science', 'culture', 'general', 'uncategorized'];
    const categoryLabels = {
        tech: 'Tech',
        business: 'Business',
        science: 'Science',
        culture: 'Culture',
        general: 'General',
        uncategorized: 'Uncategorized'
    };

    let html = '';
    for (const cat of categoryOrder) {
        if (!grouped[cat] || grouped[cat].length === 0) continue;

        html += `<div class="category-section">`;
        html += `<h2 class="category-heading"><span class="category-badge badge-${cat}">${categoryLabels[cat]}</span> <span class="category-count">${grouped[cat].length}</span></h2>`;
        html += `<div class="category-grid">`;
        html += grouped[cat].map(summary => `
            <div class="summary-card" data-filename="${escapeHtml(summary.filename)}">
                <h3>${escapeHtml(summary.title)}</h3>
                <p class="preview">${escapeHtml(summary.preview)}</p>
                <div class="card-footer">
                    <span class="category-badge badge-${summary.category || 'uncategorized'}">${categoryLabels[summary.category || 'uncategorized']}</span>
                    <span class="date">${formatDate(summary.modified_date)}</span>
                </div>
            </div>
        `).join('');
        html += `</div></div>`;
    }

    container.innerHTML = html;

    // Add click handlers
    container.querySelectorAll('.summary-card').forEach(card => {
        card.addEventListener('click', () => viewSummary(card.dataset.filename));
    });
}

async function viewSummary(filename) {
    const listContainer = document.getElementById('summaries-list');
    const filterContainer = document.getElementById('category-filters');
    const viewer = document.getElementById('summary-viewer');
    const contentEl = document.getElementById('summary-content');

    try {
        // Show loading state
        contentEl.innerHTML = '<p>Loading...</p>';
        listContainer.classList.add('hidden');
        filterContainer.classList.add('hidden');
        viewer.classList.remove('hidden');

        const response = await fetch(`${API_BASE}/summaries/${encodeURIComponent(filename)}`);
        if (!response.ok) throw new Error('Failed to load summary');

        const summary = await response.json();

        // Render markdown content using marked.js
        contentEl.innerHTML = marked.parse(summary.content);

        // Load and apply saved highlights
        await loadHighlights(filename);
    } catch (error) {
        console.error('Error loading summary:', error);
        contentEl.innerHTML = `<div class="empty-state"><h3>Error loading summary</h3><p>${error.message}</p></div>`;
    }
}

// Category filter handlers
document.querySelectorAll('.category-pill').forEach(pill => {
    pill.addEventListener('click', () => {
        document.querySelectorAll('.category-pill').forEach(p => p.classList.remove('active'));
        pill.classList.add('active');
        activeCategory = pill.dataset.category;
        renderSummaries(filterByCategory(allSummaries, activeCategory));
    });
});

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
        allSummaries = data.summaries;
        renderSummaries(filterByCategory(allSummaries, activeCategory));
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
    // Reset category filter to "All"
    document.querySelectorAll('.category-pill').forEach(p => p.classList.remove('active'));
    document.querySelector('.category-pill[data-category="all"]').classList.add('active');
    activeCategory = 'all';
    loadSummaries();
});

// Back button
document.getElementById('back-btn').addEventListener('click', () => {
    document.getElementById('summaries-list').classList.remove('hidden');
    document.getElementById('category-filters').classList.remove('hidden');
    document.getElementById('summary-viewer').classList.add('hidden');
});

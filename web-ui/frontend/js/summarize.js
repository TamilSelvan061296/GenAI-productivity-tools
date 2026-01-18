// New video summarization functionality

document.getElementById('summarize-btn').addEventListener('click', async () => {
    const urlInput = document.getElementById('youtube-url');
    const statusEl = document.getElementById('summarize-status');
    const btn = document.getElementById('summarize-btn');
    const url = urlInput.value.trim();

    // Validate URL
    if (!url) {
        statusEl.textContent = 'Please enter a YouTube URL';
        statusEl.className = 'status-message error';
        return;
    }

    if (!url.includes('youtube.com/watch') && !url.includes('youtu.be/')) {
        statusEl.textContent = 'Please enter a valid YouTube URL (e.g., https://www.youtube.com/watch?v=...)';
        statusEl.className = 'status-message error';
        return;
    }

    // Show loading state
    statusEl.textContent = 'Fetching transcript and generating summary... This may take a minute.';
    statusEl.className = 'status-message loading';
    btn.disabled = true;

    try {
        const response = await fetch('/api/summarize', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ youtube_url: url })
        });

        const result = await response.json();

        if (response.ok) {
            statusEl.textContent = 'Summary created successfully! ' + (result.message || '');
            statusEl.className = 'status-message success';
            urlInput.value = '';

            // Refresh summaries list
            loadSummaries();
        } else {
            statusEl.textContent = 'Error: ' + (result.detail || 'Failed to create summary');
            statusEl.className = 'status-message error';
        }
    } catch (error) {
        statusEl.textContent = 'Network error: ' + error.message;
        statusEl.className = 'status-message error';
    } finally {
        btn.disabled = false;
    }
});

// Allow Enter key to submit
document.getElementById('youtube-url').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
        document.getElementById('summarize-btn').click();
    }
});

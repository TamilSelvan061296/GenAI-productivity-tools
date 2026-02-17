// Text highlighting functionality for summary viewer

const HIGHLIGHT_API = '/api/summaries';
let currentSummaryFilename = null;

// Show toolbar near text selection
function showHighlightToolbar() {
    const selection = window.getSelection();
    if (!selection || selection.isCollapsed || !selection.toString().trim()) {
        hideHighlightToolbar();
        return;
    }

    // Only show if selection is inside #summary-content
    const contentEl = document.getElementById('summary-content');
    if (!contentEl || !contentEl.contains(selection.anchorNode)) {
        return;
    }

    const range = selection.getRangeAt(0);
    const rect = range.getBoundingClientRect();
    const toolbar = document.getElementById('highlight-toolbar');

    toolbar.style.top = `${rect.top + window.scrollY - 45}px`;
    toolbar.style.left = `${rect.left + window.scrollX + (rect.width / 2) - 70}px`;
    toolbar.classList.remove('hidden');
}

function hideHighlightToolbar() {
    document.getElementById('highlight-toolbar').classList.add('hidden');
}

// Apply highlight to current selection
function applyHighlight(color) {
    const selection = window.getSelection();
    if (!selection || selection.isCollapsed) return;

    const contentEl = document.getElementById('summary-content');
    if (!contentEl || !contentEl.contains(selection.anchorNode)) return;

    const range = selection.getRangeAt(0);
    const selectedText = selection.toString().trim();
    if (!selectedText) return;

    // Trim the range to exclude leading/trailing whitespace
    trimRange(range);

    // Wrap selection in a mark element
    const mark = document.createElement('mark');
    mark.className = 'user-highlight';
    mark.dataset.color = color;
    mark.style.backgroundColor = color;

    try {
        range.surroundContents(mark);
    } catch (e) {
        // If selection spans multiple elements, use extractContents approach
        const fragment = range.extractContents();
        mark.appendChild(fragment);
        range.insertNode(mark);
    }

    selection.removeAllRanges();
    hideHighlightToolbar();
    saveHighlights();
}

// Trim whitespace from start/end of a range
function trimRange(range) {
    const text = range.toString();
    const leadingSpaces = text.length - text.trimStart().length;
    const trailingSpaces = text.length - text.trimEnd().length;

    if (leadingSpaces > 0) {
        for (let i = 0; i < leadingSpaces; i++) {
            try { range.setStart(range.startContainer, range.startOffset + 1); } catch(e) { break; }
        }
    }
    if (trailingSpaces > 0) {
        for (let i = 0; i < trailingSpaces; i++) {
            try { range.setEnd(range.endContainer, range.endOffset - 1); } catch(e) { break; }
        }
    }
}

// Remove a highlight on click
function removeHighlight(markEl) {
    const parent = markEl.parentNode;
    while (markEl.firstChild) {
        parent.insertBefore(markEl.firstChild, markEl);
    }
    parent.removeChild(markEl);
    parent.normalize(); // Merge adjacent text nodes
    saveHighlights();
}

// Collect all highlights from the DOM and save to backend
async function saveHighlights() {
    if (!currentSummaryFilename) return;

    const contentEl = document.getElementById('summary-content');
    const marks = contentEl.querySelectorAll('mark.user-highlight');
    const highlights = [];

    marks.forEach(mark => {
        const text = mark.textContent.trim();
        const color = mark.dataset.color;
        // Get text offset within the content element for disambiguation
        const offset = getTextOffset(contentEl, mark);
        highlights.push({ text, color, offset });
    });

    try {
        await fetch(`${HIGHLIGHT_API}/${encodeURIComponent(currentSummaryFilename)}/highlights`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ highlights }),
        });
    } catch (error) {
        console.error('Error saving highlights:', error);
    }
}

// Get the character offset of a node within the content element (counts only trimmed text)
function getTextOffset(root, targetNode) {
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    let offset = 0;
    while (walker.nextNode()) {
        if (targetNode.contains(walker.currentNode)) {
            return offset;
        }
        offset += walker.currentNode.textContent.length;
    }
    return offset;
}

// Load and apply saved highlights after rendering markdown
async function loadHighlights(filename) {
    currentSummaryFilename = filename;

    try {
        const response = await fetch(`${HIGHLIGHT_API}/${encodeURIComponent(filename)}/highlights`);
        if (!response.ok) return;

        const data = await response.json();
        if (!data.highlights || data.highlights.length === 0) return;

        const contentEl = document.getElementById('summary-content');

        // Sort highlights by offset descending so we apply from end to start
        // (applying from end first prevents offset shifts)
        const sorted = [...data.highlights].sort((a, b) => b.offset - a.offset);
        sorted.forEach(hl => {
            applyHighlightToText(contentEl, hl.text.trim(), hl.color, hl.offset);
        });
    } catch (error) {
        console.error('Error loading highlights:', error);
    }
}

// Find and wrap matching text in the rendered HTML
function applyHighlightToText(root, text, color, targetOffset) {
    // Strategy: walk text nodes, build cumulative offset, find the node(s) containing
    // the target text. Use a tolerance window for offset matching.
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    let currentOffset = 0;
    const nodes = [];

    // Collect all text nodes with their offsets
    while (walker.nextNode()) {
        const node = walker.currentNode;
        nodes.push({ node, start: currentOffset, end: currentOffset + node.textContent.length });
        currentOffset += node.textContent.length;
    }

    // Try exact offset match first, then fuzzy search
    if (tryApplyAtOffset(nodes, text, color, targetOffset)) return true;

    // Fuzzy: search nearby offsets (within 50 chars tolerance)
    for (let tolerance = 1; tolerance <= 50; tolerance++) {
        if (tryApplyAtOffset(nodes, text, color, targetOffset + tolerance)) return true;
        if (tryApplyAtOffset(nodes, text, color, targetOffset - tolerance)) return true;
    }

    // Last resort: find the text anywhere by content matching
    return tryApplyByContent(nodes, text, color);
}

function tryApplyAtOffset(nodes, text, color, offset) {
    for (const { node, start, end } of nodes) {
        if (offset >= start && offset < end) {
            const localStart = offset - start;
            const nodeText = node.textContent;

            if (localStart + text.length <= nodeText.length) {
                if (nodeText.substring(localStart, localStart + text.length) === text) {
                    wrapTextNode(node, localStart, text.length, color);
                    return true;
                }
            }
        }
    }
    return false;
}

function tryApplyByContent(nodes, text, color) {
    // First try single-node match
    for (const { node } of nodes) {
        const idx = node.textContent.indexOf(text);
        if (idx !== -1) {
            wrapTextNode(node, idx, text.length, color);
            return true;
        }
    }

    // Multi-node match: build concatenated text and find spanning range
    let fullText = '';
    for (const { node } of nodes) {
        fullText += node.textContent;
    }
    const matchIdx = fullText.indexOf(text);
    if (matchIdx === -1) return false;

    // Find start and end nodes/offsets for this range
    let currentPos = 0;
    let startNode = null, startOffset = 0, endNode = null, endOffset = 0;
    const matchEnd = matchIdx + text.length;

    for (const { node } of nodes) {
        const nodeLen = node.textContent.length;
        const nodeEnd = currentPos + nodeLen;

        if (!startNode && matchIdx < nodeEnd) {
            startNode = node;
            startOffset = matchIdx - currentPos;
        }
        if (matchEnd <= nodeEnd) {
            endNode = node;
            endOffset = matchEnd - currentPos;
            break;
        }
        currentPos += nodeLen;
    }

    if (startNode && endNode) {
        try {
            const range = document.createRange();
            range.setStart(startNode, startOffset);
            range.setEnd(endNode, endOffset);

            const mark = document.createElement('mark');
            mark.className = 'user-highlight';
            mark.dataset.color = color;
            mark.style.backgroundColor = color;

            const fragment = range.extractContents();
            mark.appendChild(fragment);
            range.insertNode(mark);
            return true;
        } catch (e) {
            console.warn('Failed to apply multi-node highlight:', e);
        }
    }
    return false;
}

function wrapTextNode(node, startIdx, length, color) {
    const range = document.createRange();
    range.setStart(node, startIdx);
    range.setEnd(node, startIdx + length);

    const mark = document.createElement('mark');
    mark.className = 'user-highlight';
    mark.dataset.color = color;
    mark.style.backgroundColor = color;
    range.surroundContents(mark);
}

// Event: show toolbar on text selection within summary content
document.addEventListener('mouseup', (e) => {
    // Don't show toolbar if clicking on the toolbar itself
    if (e.target.closest('#highlight-toolbar')) return;

    // Small delay to let selection finalize
    setTimeout(showHighlightToolbar, 10);
});

// Event: hide toolbar when clicking outside
document.addEventListener('mousedown', (e) => {
    if (!e.target.closest('#highlight-toolbar') && !e.target.closest('#summary-content')) {
        hideHighlightToolbar();
    }
});

// Event: color button clicks
document.querySelectorAll('.hl-color').forEach(btn => {
    btn.addEventListener('mousedown', (e) => {
        e.preventDefault(); // Prevent losing selection
        applyHighlight(btn.dataset.color);
    });
});

// Event: click on highlight to remove it
document.getElementById('summary-content').addEventListener('click', (e) => {
    const mark = e.target.closest('mark.user-highlight');
    if (mark) {
        removeHighlight(mark);
    }
});

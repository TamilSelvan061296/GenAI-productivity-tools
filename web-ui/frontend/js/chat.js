// Chat WebSocket functionality

let ws = null;
let conversationId = null;
window.chatInitialized = false;

function initChat() {
    if (window.chatInitialized) return;

    const statusEl = document.getElementById('chat-status');
    statusEl.textContent = 'Connecting...';
    statusEl.className = 'chat-status';

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${protocol}//${window.location.host}/api/chat/ws`);

    ws.onopen = () => {
        console.log('WebSocket connected');
        window.chatInitialized = true;
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);

        switch (data.type) {
            case 'connected':
                conversationId = data.conversation_id;
                statusEl.textContent = 'Connected';
                statusEl.className = 'chat-status connected';
                break;
            case 'typing':
                showTypingIndicator();
                break;
            case 'message':
                hideTypingIndicator();
                addMessage('assistant', data.content);
                break;
            case 'error':
                hideTypingIndicator();
                addMessage('error', data.content);
                break;
        }
    };

    ws.onclose = () => {
        console.log('WebSocket disconnected');
        statusEl.textContent = 'Disconnected. Reconnecting...';
        statusEl.className = 'chat-status error';
        window.chatInitialized = false;

        // Reconnect after delay
        setTimeout(() => {
            if (document.getElementById('chat-tab').classList.contains('active')) {
                initChat();
            }
        }, 3000);
    };

    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        statusEl.textContent = 'Connection error';
        statusEl.className = 'chat-status error';
    };
}

function addMessage(role, content) {
    const container = document.getElementById('chat-messages');
    const msgEl = document.createElement('div');
    msgEl.className = `message ${role}`;

    // Render markdown for assistant messages
    if (role === 'assistant') {
        msgEl.innerHTML = marked.parse(content);
    } else {
        msgEl.innerHTML = `<p>${escapeHtml(content)}</p>`;
    }

    container.appendChild(msgEl);
    scrollToBottom();
}

function showTypingIndicator() {
    hideTypingIndicator(); // Remove any existing indicator

    const container = document.getElementById('chat-messages');
    const indicator = document.createElement('div');
    indicator.id = 'typing-indicator';
    indicator.className = 'message assistant typing-indicator';
    indicator.innerHTML = '<p>Thinking...</p>';
    container.appendChild(indicator);
    scrollToBottom();
}

function hideTypingIndicator() {
    const indicator = document.getElementById('typing-indicator');
    if (indicator) {
        indicator.remove();
    }
}

function sendMessage() {
    const input = document.getElementById('chat-input');
    const message = input.value.trim();

    if (!message) return;

    if (!ws || ws.readyState !== WebSocket.OPEN) {
        addMessage('error', 'Not connected. Please wait for reconnection.');
        return;
    }

    // Display user message
    addMessage('user', message);

    // Send to server
    ws.send(JSON.stringify({ message }));

    // Clear input
    input.value = '';
}

function scrollToBottom() {
    const container = document.getElementById('chat-messages');
    container.scrollTop = container.scrollHeight;
}

// Event listeners
document.getElementById('send-btn').addEventListener('click', sendMessage);

document.getElementById('chat-input').addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

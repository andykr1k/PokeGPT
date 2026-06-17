document.addEventListener("DOMContentLoaded", () => {
    const statusDot = document.querySelector('.status-dot');
    const statusText = document.getElementById('connection-status');
    const chatHistory = document.getElementById('chat-history');

    // Connect to WebSocket
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    
    let ws = null;

    function connect() {
        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            statusDot.classList.add('connected');
            statusText.textContent = 'Connected';
            addSystemMessage("Connected to PokeGPT backend.");
        };

        ws.onclose = () => {
            statusDot.classList.remove('connected');
            statusText.textContent = 'Disconnected. Reconnecting...';
            setTimeout(connect, 3000);
        };

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                handleAction(data);
            } catch (e) {
                console.error("Failed to parse websocket message:", e);
            }
        };
    }

    function handleAction(data) {
        const { reasoning, button } = data;

        // 1. Highlight Button
        if (button) {
            highlightButton(button);
        }

        // 2. Add Chat Message
        if (reasoning) {
            addChatMessage(reasoning, button);
        }
    }

    function highlightButton(buttonName) {
        const btnId = `btn-${buttonName.toUpperCase()}`;
        const btnEl = document.getElementById(btnId);
        
        if (btnEl) {
            btnEl.classList.add('active');
            // Remove highlight after a short delay
            setTimeout(() => {
                btnEl.classList.remove('active');
            }, 500);
        }
    }

    function addChatMessage(reasoning, button) {
        const msgDiv = document.createElement('div');
        msgDiv.className = 'chat-message';
        
        const timeString = new Date().toLocaleTimeString();
        
        let actionHtml = '';
        if (button) {
            actionHtml = `<div class="action">Action: Pressed ${button.toUpperCase()}</div>`;
        }

        msgDiv.innerHTML = `
            <div class="meta">
                <span>Qwen 3.5 (4B)</span>
                <span>${timeString}</span>
            </div>
            <div class="content">${escapeHtml(reasoning)}</div>
            ${actionHtml}
        `;

        chatHistory.appendChild(msgDiv);
        
        // Auto-scroll to bottom
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }

    function addSystemMessage(text) {
        const msgDiv = document.createElement('div');
        msgDiv.className = 'chat-message system';
        msgDiv.textContent = text;
        chatHistory.appendChild(msgDiv);
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }

    function escapeHtml(unsafe) {
        return unsafe
             .replace(/&/g, "&amp;")
             .replace(/</g, "&lt;")
             .replace(/>/g, "&gt;")
             .replace(/"/g, "&quot;")
             .replace(/'/g, "&#039;");
    }

    // Start connection
    connect();
});

/**
 * Chemistry Laboratory Safety & Compound Assistant
 * Chat interface — integrates with POST /send_message
 */

(function () {
    'use strict';

    const chatMessages = document.getElementById('chatMessages');
    const chatForm = document.getElementById('chatForm');
    const messageInput = document.getElementById('messageInput');
    const sendBtn = document.getElementById('sendBtn');
    const chatWelcome = document.getElementById('chatWelcome');
    const sidebar = document.getElementById('chatSidebar');
    const sidebarOverlay = document.getElementById('sidebarOverlay');
    const sidebarToggle = document.getElementById('sidebarToggle');

    let isSending = false;

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function formatMessage(text) {
        return escapeHtml(text)
            .replace(/\n/g, '<br>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    }

    function getCurrentTime() {
        return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }

    function scrollToBottom() {
        if (chatMessages) {
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
    }

    function hideWelcome() {
        if (chatWelcome) {
            chatWelcome.remove();
        }
    }

    function createUserMessage(text) {
        hideWelcome();
        const el = document.createElement('div');
        el.className = 'message user';
        el.innerHTML = `
            <div class="message-avatar"><i class="fas fa-user"></i></div>
            <div>
                <div class="message-bubble">${formatMessage(text)}</div>
                <div class="message-time">${getCurrentTime()}</div>
            </div>
        `;
        chatMessages.appendChild(el);
        scrollToBottom();
        return el;
    }

    function createBotMessage(text) {
        const el = document.createElement('div');
        el.className = 'message bot';
        el.innerHTML = `
            <div class="message-avatar"><i class="fas fa-flask"></i></div>
            <div>
                <div class="message-bubble">${formatMessage(text)}</div>
                <div class="message-time">${getCurrentTime()}</div>
            </div>
        `;
        chatMessages.appendChild(el);
        scrollToBottom();
        return el;
    }

    function showTypingIndicator() {
        hideWelcome();
        const el = document.createElement('div');
        el.className = 'typing-indicator';
        el.id = 'typingIndicator';
        el.innerHTML = `
            <div class="message-avatar" style="background: var(--gradient-hero); color: white; width: 36px; height: 36px; border-radius: 10px; display: flex; align-items: center; justify-content: center;">
                <i class="fas fa-flask" style="font-size: 0.85rem;"></i>
            </div>
            <div class="typing-bubble">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>
        `;
        chatMessages.appendChild(el);
        scrollToBottom();
    }

    function hideTypingIndicator() {
        const el = document.getElementById('typingIndicator');
        if (el) el.remove();
    }

    function setSendingState(sending) {
        isSending = sending;
        sendBtn.disabled = sending;
        messageInput.disabled = sending;
    }

    async function sendMessage(text) {
        const message = text.trim();
        if (!message || isSending) return;

        createUserMessage(message);
        messageInput.value = '';
        autoResizeInput();
        setSendingState(true);
        showTypingIndicator();

        try {
            const response = await fetch('/send_message', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: message })
            });

            const data = await response.json();
            hideTypingIndicator();

            if (data.success) {
                createBotMessage(data.answer);
            } else {
                createBotMessage(data.message || 'Something went wrong. Please try again.');
            }
        } catch (err) {
            hideTypingIndicator();
            createBotMessage('Unable to reach the server. Please check your connection and try again.');
        } finally {
            setSendingState(false);
            messageInput.focus();
        }
    }

    function autoResizeInput() {
        messageInput.style.height = 'auto';
        messageInput.style.height = Math.min(messageInput.scrollHeight, 120) + 'px';
    }

    function toggleSidebar() {
        sidebar.classList.toggle('open');
        sidebarOverlay.classList.toggle('open');
    }

    function closeSidebar() {
        sidebar.classList.remove('open');
        sidebarOverlay.classList.remove('open');
    }

    // Form submit
    if (chatForm) {
        chatForm.addEventListener('submit', function (e) {
            e.preventDefault();
            sendMessage(messageInput.value);
        });
    }

    // Enter to send, Shift+Enter for newline
    if (messageInput) {
        messageInput.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                chatForm.dispatchEvent(new Event('submit'));
            }
        });

        messageInput.addEventListener('input', autoResizeInput);
    }

    // Sidebar toggle
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', toggleSidebar);
    }
    if (sidebarOverlay) {
        sidebarOverlay.addEventListener('click', closeSidebar);
    }

    // Suggestion chips & quick prompts
    document.querySelectorAll('.suggestion-chip, .quick-prompt').forEach(function (btn) {
        btn.addEventListener('click', function () {
            const prompt = this.getAttribute('data-prompt');
            if (prompt) {
                closeSidebar();
                messageInput.value = prompt;
                autoResizeInput();
                sendMessage(prompt);
            }
        });
    });

    // URL query parameter pre-fill (?q=...)
    const urlParams = new URLSearchParams(window.location.search);
    const prefillQuery = urlParams.get('q');
    if (prefillQuery && !chatMessages.querySelector('.message')) {
        sendMessage(decodeURIComponent(prefillQuery.replace(/\+/g, ' ')));
        window.history.replaceState({}, '', window.location.pathname);
    }

    // Auto-scroll on load if history exists
    scrollToBottom();
    messageInput.focus();
})();

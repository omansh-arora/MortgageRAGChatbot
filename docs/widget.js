
(function () {
  'use strict';
  window.MORTGAGE_BOT_API_URL = 'https://mortgageragchatbot-production.up.railway.app';
  const CONFIG = {
    API_URL: window.MORTGAGE_BOT_API_URL || 'http://localhost:8000',
    WIDGET_TITLE: 'AI Mortgage Assistant',
    WELCOME_MESSAGE:
      "Welcome to our mortgage desk! \n\nWhether you're curious about rates, pre-approvals, or first-time buyer programs, I've got you covered. What would you like to know?",
    PLACEHOLDER: 'Ask anything about mortgages…',
    PRIMARY_COLOR: '#0f172a',
    ACCENT_COLOR: '#3b82f6',
    GRADIENT_START: '#2563eb',
    GRADIENT_END: '#1d4ed8',
  };

  let hasSentFirstMessage = false;

  function init() {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', createWidget);
    } else {
      createWidget();
    }
  }

  function createWidget() {
    injectStyles();

    const widgetContainer = document.createElement('div');
    widgetContainer.id = 'mortgage-chat-widget';
    widgetContainer.innerHTML = getWidgetHTML();
    document.body.appendChild(widgetContainer);

    attachEventListeners();
    addMessage(CONFIG.WELCOME_MESSAGE, 'bot');
    addQuickReplies([
      'What rate could I qualify for?',
      'How much can I afford?',
      'Explain first-time buyer programs',
    ]);
  }

  function injectStyles() {
    const style = document.createElement('style');
    style.textContent = `
      html, body {
        width: 100%;
        height: 100%;
        overflow: hidden;
        position: fixed;
        margin: 0;
        padding: 0;
      }

      #mortgage-chat-widget * {
        box-sizing: border-box;
        margin: 0;
      }

      #mortgage-chat-widget {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        z-index: 9999;
      }

      .chat-window {
        display: flex;
        flex-direction: column;
        width: 100%;
        height: 100vh;
        height: 100dvh;
        padding: 0;
        border-radius: 0;
        background: radial-gradient(circle at top, #4f46e5 0%, #1d4ed8 40%, #312e81 100%);
        box-shadow: none;
        animation: none;
      }

      .chat-shell {
        display: flex;
        flex-direction: column;
        width: 100%;
        height: 100vh;
        height: 100dvh;
        background: radial-gradient(circle at 0 0, #eff6ff 0%, #e5e7eb 45%, #f9fafb 100%);
        border-radius: 0;
        overflow: hidden;
        box-shadow: none;
      }

      @keyframes slideUp {
        from {
          opacity: 0;
          transform: translateY(30px) scale(0.95);
        }
        to {
          opacity: 1;
          transform: translateY(0) scale(1);
        }
      }

      .chat-header {
        flex-shrink: 0;
        position: relative;
        padding: 16px 18px;
        background: linear-gradient(135deg, ${CONFIG.GRADIENT_START}, ${CONFIG.GRADIENT_END});
        color: #ffffff;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 10px 30px rgba(15, 23, 42, 0.4);
        z-index: 2;
      }

      .chat-header::after {
        content: '';
        position: absolute;
        inset: 0;
        background:
          radial-gradient(circle at 0 0, rgba(239, 246, 255, 0.3), transparent 55%),
          radial-gradient(circle at 100% 0, rgba(191, 219, 254, 0.35), transparent 55%);
        opacity: 0.7;
        pointer-events: none;
      }

      .chat-header-inner {
        position: relative;
        display: flex;
        align-items: center;
        gap: 12px;
        z-index: 1;
      }

      .chat-header-avatar {
        width: 40px;
        height: 40px;
        border-radius: 14px;
        background: rgba(15, 23, 42, 0.18);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 22px;
        box-shadow: 0 6px 16px rgba(15, 23, 42, 0.5);
      }

      .chat-header-text h3 {
        font-size: 16px;
        font-weight: 600;
        margin-bottom: 2px;
      }

      .chat-header-text span {
        font-size: 12px;
        opacity: 0.9;
        display: flex;
        align-items: center;
        gap: 6px;
      }

      .chat-status-dot {
        width: 8px;
        height: 8px;
        border-radius: 999px;
        background: #22c55e;
        box-shadow: 0 0 0 6px rgba(34, 197, 94, 0.3);
      }

      .close-btn {
        position: relative;
        background: rgba(15, 23, 42, 0.25);
        border: none;
        color: #e5e7eb;
        cursor: pointer;
        width: 30px;
        height: 30px;
        border-radius: 999px;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: all 0.2s;
        font-size: 18px;
        z-index: 1;
      }

      .close-btn:hover {
        background: rgba(15, 23, 42, 0.4);
        transform: scale(1.05);
      }

      .chat-body {
        position: relative;
        flex: 1;
        min-height: 0;
        display: flex;
        flex-direction: column;
        gap: 10px;
      }

      .chat-card {
        flex: 1;
        min-height: 0;
        display: flex;
        flex-direction: column;
        background: #ffffff;
        border-radius: 0px;
        box-shadow:
          0 16px 40px rgba(15, 23, 42, 0.18),
          0 0 0 1px rgba(148, 163, 184, 0.25);
        overflow: hidden;
      }

      .chat-messages {
        flex: 1;
        min-height: 0;
        overflow-y: auto;
        -webkit-overflow-scrolling: touch;
        padding: 16px 18px 20px;
        background: linear-gradient(180deg, #f8fafc 0%, #eef2ff 40%, #f9fafb 100%);
      }

      .chat-messages::-webkit-scrollbar {
        width: 6px;
      }

      .chat-messages::-webkit-scrollbar-track {
        background: transparent;
      }

      .chat-messages::-webkit-scrollbar-thumb {
        background: #cbd5e1;
        border-radius: 999px;
      }

      .message {
        margin-bottom: 18px;
        display: flex;
        animation: messageIn 0.25s cubic-bezier(0.16, 1, 0.3, 1);
      }
        .chat-shell,
        .chat-body,
        .chat-card {
        min-height: 0;
        }

      @keyframes messageIn {
        from {
          opacity: 0;
          transform: translateY(8px);
        }
        to {
          opacity: 1;
          transform: translateY(0);
        }
      }

      .message.user {
        justify-content: flex-end;
        padding-top: 15px;
        padding-bottom: 15px;
      }

      .message.bot {
        justify-content: flex-start;
        padding-top: 15px;
        padding-bottom: 15px;
      }

      .message.bot .bubble-wrapper {
        display: flex;
        align-items: flex-end;
        gap: 8px;
        max-width: 80%;
      }

      .bot-avatar-sm {
        width: 26px;
        height: 26px;
        border-radius: 10px;
        background: #eff6ff;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 16px;
        box-shadow: 0 4px 10px rgba(148, 163, 184, 0.6);
        flex-shrink: 0;
      }

      .message-content {
        max-width: 80%;
        padding: 18px 22px !important;
        font-size: 14px;
        line-height: 1.6;
      }

      .message.bot .message-content {
        background: #ffffff;
        color: #1f2937;
        border-radius: 18px 18px 18px 6px;
        box-shadow:
          0 8px 20px rgba(15, 23, 42, 0.08),
          0 0 0 1px rgba(209, 213, 219, 0.6);
        padding: 18px 22px !important;
      }

      .message.user .message-content {
        background: linear-gradient(135deg, ${CONFIG.ACCENT_COLOR}, #2563eb);
        color: #eff6ff;
        border-radius: 18px 18px 6px 18px;
        box-shadow:
          0 10px 26px rgba(37, 99, 235, 0.5),
          0 0 0 1px rgba(191, 219, 254, 0.4);
        margin-right: 4px;
        padding: 18px 22px !important;
      }

      .message.bot .message-content p {
        margin-bottom: 8px;
      }

      .message.bot .message-content p:last-child {
        margin-bottom: 0;
      }

      .message.bot .message-content ul,
      .message.bot .message-content ol {
        margin: 8px 0;
        padding-left: 20px;
      }

      .message.bot .message-content li {
        margin-bottom: 6px;
      }

      .message.bot .message-content strong {
        font-weight: 600;
        color: #0f172a;
      }

      .message.bot .message-content code {
        background: #e5e7eb;
        padding: 2px 6px;
        border-radius: 6px;
        font-size: 12px;
        font-family: 'SF Mono', Menlo, Monaco, monospace;
      }

      .message.bot .message-content h1,
      .message.bot .message-content h2,
      .message.bot .message-content h3 {
        margin: 10px 0 6px;
        font-weight: 600;
        color: #0f172a;
      }

      .message.bot .message-content h1 { font-size: 17px; }
      .message.bot .message-content h2 { font-size: 16px; }
      .message.bot .message-content h3 { font-size: 15px; }

      .message.bot .message-content a {
        color: ${CONFIG.ACCENT_COLOR};
        text-decoration: none;
        font-weight: 500;
        transition: opacity 0.2s;
      }

      .message.bot .message-content a:hover {
        opacity: 0.8;
      }

      .typing-indicator {
        display: flex;
        align-items: center;
        gap: 5px;
        padding: 8px 10px;
        background: #ffffff;
        border-radius: 999px;
        box-shadow:
          0 8px 18px rgba(148, 163, 184, 0.5),
          0 0 0 1px rgba(226, 232, 240, 0.8);
        max-width: 70px;
      }

      .typing-indicator span {
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background: #94a3b8;
        animation: bounce 1.4s infinite ease-in-out;
      }

      .typing-indicator span:nth-child(1) { animation-delay: 0s; }
      .typing-indicator span:nth-child(2) { animation-delay: 0.18s; }
      .typing-indicator span:nth-child(3) { animation-delay: 0.36s; }

      @keyframes bounce {
        0%, 60%, 100% { transform: translateY(0); }
        30% { transform: translateY(-6px); }
      }

      .chat-input-container {
        flex-shrink: 0;
        padding: 10px 14px 12px 12px;
        background: #f9fafb;
        border-top: 1px solid rgba(226, 232, 240, 0.9);
      }

      .quick-replies {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        padding-bottom: 8px;
      }

      .quick-reply-btn {
        border: none;
        border-radius: 999px;
        padding: 10px 18px !important;
        font-size: 13px;
        background: #e0f2fe;
        color: #0369a1;
        cursor: pointer;
        display: inline-flex;
        align-items: center;
        gap: 6px;
        box-shadow: 0 6px 14px rgba(148, 163, 184, 0.6);
        transition: all 0.18s ease-out;
        white-space: nowrap;
      }

      .quick-reply-btn::before {
        content: '💡';
        font-size: 13px;
      }

      .quick-reply-btn:hover {
        transform: translateY(-1px);
        background: #bfdbfe;
      }

      .chat-input-wrapper {
        display: flex;
        gap: 10px;
        align-items: center;
        background: #e5e7eb;
        border-radius: 16px;
        padding: 10px 10px 10px 20px !important;
        transition: all 0.2s;
        border: 1px solid rgba(148, 163, 184, 0.7);
      }

      .chat-input-wrapper:focus-within {
        background: #f9fafb;
        border-color: ${CONFIG.ACCENT_COLOR};
        box-shadow: 0 0 0 1px rgba(59, 130, 246, 0.4);
      }

      .chat-input {
        flex: 1;
        padding: 8px 6px;
        border: none;
        background: transparent;
        font-size: 16px;
        outline: none;
        color: #111827;
        -webkit-appearance: none;
        -moz-appearance: none;
        appearance: none;
      }

      .chat-input::placeholder {
        color: #9ca3af;
      }

      .send-btn {
        background: linear-gradient(135deg, ${CONFIG.ACCENT_COLOR}, #2563eb);
        color: white;
        border: none;
        width: 40px;
        height: 40px;
        border-radius: 14px;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: all 0.2s;
        flex-shrink: 0;
        box-shadow:
          0 12px 26px rgba(37, 99, 235, 0.6),
          0 0 0 1px rgba(191, 219, 254, 0.5);
      }

      .send-btn:hover:not(:disabled) {
        transform: translateY(-1px) scale(1.02);
      }

      .send-btn:disabled {
        opacity: 0.5;
        cursor: not-allowed;
        box-shadow: none;
      }

      .send-btn svg {
        width: 18px;
        height: 18px;
        fill: white;
      }

      .chat-footer-meta {
        padding-top: 6px;
        font-size: 11px;
        color: #9ca3af;
        display: flex;
        justify-content: center;
        gap: 4px;
      }

    `;
    document.head.appendChild(style);
  }

  function getWidgetHTML() {
    return `
      <div class="chat-window" id="chat-window">
        <div class="chat-shell">
          <div class="chat-header">
            <div class="chat-header-inner">
              <div class="chat-header-avatar">🏠</div>
              <div class="chat-header-text">
                <h3>${CONFIG.WIDGET_TITLE}</h3>
                <span>
                  <span class="chat-status-dot"></span>
                  Available
                </span>
              </div>
            </div>
          </div>

          <div class="chat-body">
            <div class="chat-card">
              <div class="chat-messages" id="chat-messages"></div>
              <div class="chat-input-container">
                <div class="quick-replies" id="quick-replies"></div>
                <div class="chat-input-wrapper">
                  <input
                    type="text"
                    class="chat-input"
                    id="chat-input"
                    placeholder="${CONFIG.PLACEHOLDER}"
                    maxlength="500"
                    autocomplete="off"
                    autocorrect="off"
                    autocapitalize="off"
                    spellcheck="false"
                  />
                  <button class="send-btn" id="send-btn">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
                      <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
                    </svg>
                  </button>
                </div>
                <div class="chat-footer-meta">
                  <span>Information shared is for general education and not financial, legal, or professional advice.</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  function attachEventListeners() {
    const sendBtn = document.getElementById('send-btn');
    const input = document.getElementById('chat-input');

    sendBtn.addEventListener('click', sendMessage);
    input.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') sendMessage();
    });
  }

  async function sendMessage() {
    const input = document.getElementById('chat-input');
    const message = input.value.trim();

    if (!message) return;

    if (!hasSentFirstMessage) {
      hasSentFirstMessage = true;
      hideQuickReplies();
    }

    addMessage(message, 'user');
    input.value = '';

    showTypingIndicator();

    try {
      const response = await fetch(`${CONFIG.API_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message }),
      });

      if (!response.ok) throw new Error('Network response was not ok');

      const data = await response.json();

      hideTypingIndicator();
      addMessage(data.answer, 'bot');
    } catch (error) {
      console.error('Error:', error);
      hideTypingIndicator();
      addMessage(
        "I'm having trouble connecting right now. Please try again shortly or reach out directly to our mortgage team.",
        'bot'
      );
    }
  }

  function parseMarkdown(text) {
    const urlPlaceholders = [];
    let html = text.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (match, linkText, url) => {
      const placeholder = `URLPLACEHOLDER${urlPlaceholders.length}ENDURL`;
      urlPlaceholders.push(
        `<a href="${url}" target="_blank" rel="noopener noreferrer">${linkText}</a>`
      );
      return placeholder;
    });

    html = html.replace(/(https?:\/\/[^\s<>\[\]]+)/g, (match, url) => {
      const placeholder = `URLPLACEHOLDER${urlPlaceholders.length}ENDURL`;
      urlPlaceholders.push(
        `<a href="${url}" target="_blank" rel="noopener noreferrer">${url}</a>`
      );
      return placeholder;
    });

    html = html
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/^### (.+)$/gm, '<h3>$1</h3>')
      .replace(/^## (.+)$/gm, '<h2>$1</h2>')
      .replace(/^# (.+)$/gm, '<h1>$1</h1>')
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/__([^_]+)__/g, '<strong>$1</strong>')
      .replace(/\*([^*]+)\*/g, '<em>$1</em>')
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      .replace(/^[\*\-] (.+)$/gm, '<li>$1</li>')
      .replace(/^\d+\. (.+)$/gm, '<li>$1</li>')
      .replace(/\n\n/g, '</p><p>')
      .replace(/\n/g, '<br>');

    urlPlaceholders.forEach((urlHtml, i) => {
      html = html.replace(`URLPLACEHOLDER${i}ENDURL`, urlHtml);
    });

    html = html.replace(/(<li>.*?<\/li>)(?:<br>)?/g, '$1');
    html = html.replace(/(<li>.*?<\/li>)+/g, '<ul>$&</ul>');

    if (!html.match(/^<(h[1-3]|ul|ol|p)/)) {
      html = '<p>' + html + '</p>';
    }

    html = html.replace(/<p><\/p>/g, '');
    html = html.replace(/<p><br><\/p>/g, '');

    return html;
  }

  function addMessage(text, sender) {
    const messagesContainer = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}`;

    if (sender === 'bot') {
      const wrapper = document.createElement('div');
      wrapper.className = 'bubble-wrapper';

      const avatar = document.createElement('div');
      avatar.className = 'bot-avatar-sm';
      avatar.textContent = '🏠';

      const contentDiv = document.createElement('div');
      contentDiv.className = 'message-content';
      contentDiv.innerHTML = parseMarkdown(text);

      wrapper.appendChild(avatar);
      wrapper.appendChild(contentDiv);
      messageDiv.appendChild(wrapper);
    } else {
      const contentDiv = document.createElement('div');
      contentDiv.className = 'message-content';
      contentDiv.textContent = text;
      messageDiv.appendChild(contentDiv);
    }

    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }

  function showTypingIndicator() {
    const messagesContainer = document.getElementById('chat-messages');
    const typingDiv = document.createElement('div');
    typingDiv.className = 'message bot';
    typingDiv.id = 'typing-indicator';
    typingDiv.innerHTML = `
      <div class="bubble-wrapper">
        <div class="bot-avatar-sm">🏠</div>
        <div class="typing-indicator">
          <span></span>
          <span></span>
          <span></span>
        </div>
      </div>
    `;
    messagesContainer.appendChild(typingDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }

  function hideTypingIndicator() {
    const typingIndicator = document.getElementById('typing-indicator');
    if (typingIndicator) typingIndicator.remove();
  }

  function addQuickReplies(labels) {
    const container = document.getElementById('quick-replies');
    if (!container) return;

    container.innerHTML = '';
    labels.forEach((label) => {
      const btn = document.createElement('button');
      btn.className = 'quick-reply-btn';
      btn.textContent = label;
      btn.addEventListener('click', () => {
        const input = document.getElementById('chat-input');
        input.value = label;
        sendMessage();
      });
      container.appendChild(btn);
    });
  }

  function hideQuickReplies() {
    const container = document.getElementById('quick-replies');
    if (container) container.style.display = 'none';
  }

  init();
})();


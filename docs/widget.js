(function () {
  "use strict";

  const CONFIG = {
    API_URL: window.MORTGAGE_BOT_API_URL || "http://localhost:8000",
    WIDGET_TITLE: "Mortgage Assistant",
    WELCOME_MESSAGE:
      "Welcome to our mortgage desk! 💬\n\nWhether you're curious about rates, pre-approvals, or first-time buyer programs, I’ve got you covered. What would you like to know?",
    PLACEHOLDER: "Ask anything about mortgages…",
    PRIMARY_COLOR: "#0f172a",
    ACCENT_COLOR: "#3b82f6",
    GRADIENT_START: "#2563eb",
    GRADIENT_END: "#1d4ed8",
  };

  function init() {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", createWidget);
    } else {
      createWidget();
    }
  }

  /* --------------------- MAIN WIDGET SETUP --------------------- */

  function createWidget() {
    injectStyles();

    const container = document.getElementById("mortgage-widget");
    container.innerHTML = getWidgetHTML();

    attachEventListeners();
    addMessage(CONFIG.WELCOME_MESSAGE, "bot");
    addQuickReplies([
      "What rate could I qualify for?",
      "How much can I afford?",
      "Explain first-time buyer programs",
    ]);

    // Open immediately (no toggle button)
    document.getElementById("chat-window").classList.add("open");
  }

  /* --------------------- STYLES --------------------- */

  function injectStyles() {
    const style = document.createElement("style");
    style.textContent = `
      #mortgage-widget * {
        box-sizing: border-box;
        margin: 0;
      }

      .chat-window {
        position: fixed;
        bottom: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: radial-gradient(circle at top, #4f46e5, #1d4ed8 50%, #312e81);
        display: none;
        padding: 10px;
      }

      .chat-window.open {
        display: flex;
      }

      .chat-shell {
        display: flex;
        flex-direction: column;
        width: 100%;
        height: 100%;
        background: #f3f4f6;
        border-radius: 18px;
        overflow: hidden;
      }

      .chat-header {
        padding: 16px;
        background: linear-gradient(135deg, ${CONFIG.GRADIENT_START}, ${CONFIG.GRADIENT_END});
        color: white;
        display: flex;
        align-items: center;
        justify-content: space-between;
      }

      .chat-header-avatar {
        width: 40px;
        height: 40px;
        border-radius: 12px;
        background: rgba(255,255,255,0.2);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 22px;
      }

      .chat-body {
        flex: 1;
        display: flex;
        flex-direction: column;
      }

      .chat-card {
        flex: 1;
        display: flex;
        flex-direction: column;
        background: white;
        border-radius: 0;
        overflow: hidden;
      }

      .chat-messages {
        flex: 1;
        padding: 18px;
        overflow-y: auto;
      }

      .message {
        margin-bottom: 16px;
        display: flex;
      }

      .message.bot .bubble-wrapper {
        display: flex;
        align-items: flex-start;
        gap: 8px;
        max-width: 85%;
      }

      .bot-avatar-sm {
        width: 26px;
        height: 26px;
        border-radius: 8px;
        background: #e0e7ff;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 16px;
      }

      .message-content {
        padding: 14px 18px;
        border-radius: 14px;
        font-size: 14px;
        line-height: 1.5;
      }

      .message.bot .message-content {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        color: #111827;
      }

      .message.user {
        justify-content: flex-end;
      }

      .message.user .message-content {
        background: ${CONFIG.ACCENT_COLOR};
        color: white;
        border-radius: 14px 14px 4px 14px;
      }

      .chat-input-container {
        padding: 12px;
        background: #f3f4f6;
      }

      .chat-input-wrapper {
        display: flex;
        gap: 10px;
        background: #e5e7eb;
        padding: 10px;
        border-radius: 16px;
      }

      .chat-input {
        flex: 1;
        border: none;
        background: transparent;
        outline: none;
      }

      .send-btn {
        background: ${CONFIG.ACCENT_COLOR};
        color: white;
        border: none;
        width: 40px;
        height: 40px;
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
      }

      .quick-replies {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
        margin-bottom: 10px;
      }

      .quick-reply-btn {
        border: none;
        padding: 8px 16px;
        border-radius: 999px;
        background: #e0f2fe;
        color: #0369a1;
        cursor: pointer;
      }
    `;
    document.head.appendChild(style);
  }

  /* --------------------- HTML TEMPLATE --------------------- */

  function getWidgetHTML() {
    return `
      <div class="chat-window" id="chat-window">
        <div class="chat-shell">

          <div class="chat-header">
            <div style="display:flex; align-items:center; gap:10px;">
              <div class="chat-header-avatar">🏠</div>
              <div>
                <h3 style="margin:0; font-size:16px;">${CONFIG.WIDGET_TITLE}</h3>
                <small style="opacity:0.9;">We reply immediately</small>
              </div>
            </div>
          </div>

          <div class="chat-body">
            <div class="chat-card">
              <div id="chat-messages" class="chat-messages"></div>

              <div class="chat-input-container">
                <div id="quick-replies" class="quick-replies"></div>

                <div class="chat-input-wrapper">
                  <input id="chat-input" class="chat-input" placeholder="${CONFIG.PLACEHOLDER}" />
                  <button id="send-btn" class="send-btn">➤</button>
                </div>
              </div>
            </div>
          </div>

        </div>
      </div>
    `;
  }

  /* --------------------- EVENTS --------------------- */

  function attachEventListeners() {
    document.getElementById("send-btn").addEventListener("click", sendMessage);
    document.getElementById("chat-input").addEventListener("keypress", (e) => {
      if (e.key === "Enter") sendMessage();
    });
  }

  /* --------------------- MESSAGE HANDLING --------------------- */

  function addMessage(text, sender) {
    const container = document.getElementById("chat-messages");

    const div = document.createElement("div");
    div.className = `message ${sender}`;

    if (sender === "bot") {
      div.innerHTML = `
        <div class="bubble-wrapper">
          <div class="bot-avatar-sm">🏠</div>
          <div class="message-content">${text}</div>
        </div>
      `;
    } else {
      div.innerHTML = `<div class="message-content">${text}</div>`;
    }

    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
  }

  async function sendMessage() {
    const input = document.getElementById("chat-input");
    const msg = input.value.trim();
    if (!msg) return;

    addMessage(msg, "user");
    input.value = "";

    try {
      const res = await fetch(`${CONFIG.API_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: msg }),
      });

      const data = await res.json();
      addMessage(data.answer, "bot");
    } catch (err) {
      addMessage("Sorry, I'm having trouble responding right now.", "bot");
    }
  }

  function addQuickReplies(list) {
    const container = document.getElementById("quick-replies");
    container.innerHTML = "";

    list.forEach((label) => {
      const btn = document.createElement("button");
      btn.className = "quick-reply-btn";
      btn.textContent = label;
      btn.onclick = () => {
        document.getElementById("chat-input").value = label;
        sendMessage();
      };
      container.appendChild(btn);
    });
  }

  init();
})();

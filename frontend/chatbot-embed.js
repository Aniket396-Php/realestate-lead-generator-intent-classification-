/**
 * Property Doors AI Chatbot - Embeddable Widget
 * Add to any page with just 2 lines:
 *
 *   <script>
 *     window.CHATBOT_CONFIG = { apiUrl: "http://YOUR_SERVER:8000", companyName: "Property Doors" };
 *   </script>
 *   <script src="http://YOUR_SERVER:8000/widget.js" defer></script>
 */

(function () {
  "use strict";

  const cfg = window.CHATBOT_CONFIG || {};
  const API_URL = cfg.apiUrl || "http://localhost:8000";
  const PRIMARY = cfg.primaryColor || "#4ADE80";   // Property Doors light green
  const COMPANY = cfg.companyName || "Property Doors";
  const SESSION_ID = "sess_" + Math.random().toString(36).slice(2);
  let currentUser = null;
  let activity = {
    pages: [window.location.pathname],
    propertyCount: 0,
    startTime: Date.now()
  };

  // -- Styles ------------------------------------------------------------------
  const STYLES = `
    @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap');

    #pb-chat-widget * { box-sizing: border-box; font-family: 'Manrope', sans-serif; }

    #pb-chat-toggle {
      position: fixed; bottom: 28px; right: 28px; z-index: 999999;
      width: 64px; height: 64px; border-radius: 50%;
      background: ${PRIMARY};
      border: none; cursor: pointer;
      display: flex; align-items: center; justify-content: center;
      box-shadow: 0 8px 32px ${PRIMARY}88;
      transition: transform 0.3s, box-shadow 0.3s;
    }
    #pb-chat-toggle:hover { transform: scale(1.08); box-shadow: 0 12px 45px ${PRIMARY}BB; }
    #pb-chat-toggle:active { transform: scale(0.95); }
    #pb-chat-toggle::after {
      content: ''; position: absolute; inset: -4px; border-radius: 50%;
      border: 2px solid ${PRIMARY}55;
      animation: pb-pulse 2.5s ease-out infinite;
    }
    @keyframes pb-pulse {
      0% { transform: scale(1); opacity: 0.8; }
      60%, 100% { transform: scale(1.4); opacity: 0; }
    }

    #pb-chat-window {
      position: fixed; bottom: 108px; right: 28px; z-index: 999998;
      width: 385px; height: 590px;
      background: #FFFFFF; border-radius: 22px;
      box-shadow: 0 24px 70px rgba(0,0,0,0.18), 0 0 0 1px ${PRIMARY}22;
      display: flex; flex-direction: column; overflow: hidden;
      transform-origin: bottom right;
      transform: scale(0.85) translateY(20px); opacity: 0; pointer-events: none;
      transition: transform 0.3s cubic-bezier(0.4,0,0.2,1), opacity 0.3s;
      border: 1px solid ${PRIMARY}22;
    }
    #pb-chat-window.open {
      transform: scale(1) translateY(0); opacity: 1; pointer-events: all;
    }

    /* Header */
    #pb-header {
      background: ${PRIMARY};
      padding: 14px 18px;
      display: flex; align-items: center; gap: 12px;
      flex-shrink: 0;
    }
    .pb-avatar {
      width: 40px; height: 40px; border-radius: 50%;
      background: rgba(0,0,0,0.1);
      display: flex; align-items: center; justify-content: center;
      font-size: 20px; flex-shrink: 0; border: 2px solid rgba(0,0,0,0.15);
    }
    .pb-header-info { flex: 1; }
    .pb-header-name { font-size: 14px; font-weight: 700; color: #000; letter-spacing: -0.01em; }
    .pb-header-status { font-size: 11px; color: rgba(0,0,0,0.7); display: flex; align-items: center; gap: 4px; margin-top: 2px; }
    .pb-dot { width: 6px; height: 6px; border-radius: 50%; background: #86EFAC; box-shadow: 0 0 6px #86EFAC; animation: pb-blink 1.8s infinite; }
    @keyframes pb-blink { 0%,100% { opacity:1; } 50% { opacity:0.3; } }
    .pb-close { background: rgba(0,0,0,0.08); border: none; color: #000; cursor: pointer; border-radius: 8px; padding: 5px 10px; font-size: 16px; transition: all 0.2s; }
    .pb-close:hover { background: rgba(0,0,0,0.15); }

    /* Messages */
    #pb-messages {
      flex: 1; overflow-y: auto; padding: 16px;
      display: flex; flex-direction: column; gap: 12px;
      scroll-behavior: smooth; background: #F8FAFC;
    }
    #pb-messages::-webkit-scrollbar { width: 4px; }
    #pb-messages::-webkit-scrollbar-thumb { background: ${PRIMARY}33; border-radius: 10px; }

    .pb-msg { display: flex; flex-direction: column; max-width: 85%; animation: pb-slide 0.3s ease both; }
    @keyframes pb-slide { from { opacity:0; transform:translateY(10px); } to { opacity:1; transform:translateY(0); } }
    .pb-msg.user { align-self: flex-end; align-items: flex-end; }
    .pb-msg.bot  { align-self: flex-start; align-items: flex-start; }

    .pb-bubble {
      padding: 10px 14px; border-radius: 16px;
      font-size: 13.5px; line-height: 1.55; word-break: break-word;
    }
    .pb-msg.user .pb-bubble {
      background: ${PRIMARY};
      color: #000; border-bottom-right-radius: 4px;
    }
    .pb-msg.bot .pb-bubble {
      background: #FFFFFF; color: #1E293B;
      border-bottom-left-radius: 4px;
      border: 1px solid #E2E8F0;
      box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    }
    .pb-time { font-size: 10px; color: #94A3B8; margin-top: 3px; padding: 0 4px; }

    /* Text formatting */
    .pb-bubble p { margin: 0 0 5px 0; }
    .pb-bubble p:last-child { margin: 0; }
    .pb-list { margin: 6px 0 0 0; padding: 0; list-style: none; display: flex; flex-direction: column; gap: 5px; counter-reset: pb-counter; }
    .pb-list li {
      display: flex; align-items: flex-start; gap: 8px;
      padding: 7px 9px; background: ${PRIMARY}08; border-radius: 8px;
      border-left: 2px solid ${PRIMARY}44; font-size: 13px; line-height: 1.5;
      counter-increment: pb-counter;
    }
    ol.pb-list li::before {
      content: counter(pb-counter);
      min-width: 20px; height: 20px;
      background: ${PRIMARY};
      border-radius: 50%; display: flex; align-items: center; justify-content: center;
      font-size: 10px; font-weight: 700; color: #000; flex-shrink: 0; margin-top: 1px;
    }
    ul.pb-list li::before {
      content: ''; min-width: 6px; height: 6px; border-radius: 50%;
      background: ${PRIMARY}; flex-shrink: 0; margin-top: 5px;
    }

    /* Property Cards */
    .pb-cards { display: flex; flex-direction: column; gap: 8px; width: 100%; max-width: 330px; }
    .pb-card-intro { font-size: 12px; color: #64748B; margin-bottom: 2px; font-weight: 500; }
    .pb-card {
      background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 14px;
      padding: 12px; cursor: pointer; transition: all 0.25s; position: relative; overflow: hidden;
      text-decoration: none; display: block;
      box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    }
    .pb-card::before {
      content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
      background: ${PRIMARY};
      transform: scaleX(0); transform-origin: left; transition: transform 0.3s;
    }
    .pb-card:hover { border-color: ${PRIMARY}55; transform: translateY(-2px); box-shadow: 0 8px 24px rgba(14,165,233,0.15); }
    .pb-card:hover::before { transform: scaleX(1); }
    .pb-card-row { display: flex; justify-content: space-between; align-items: flex-start; gap: 8px; margin-bottom: 4px; }
    .pb-card-title { font-size: 12.5px; font-weight: 700; color: #1E293B; line-height: 1.3; flex: 1; }
    .pb-card-price { font-size: 12px; font-weight: 700; color: ${PRIMARY}; background: ${PRIMARY}12; padding: 2px 8px; border-radius: 20px; white-space: nowrap; }
    .pb-card-loc { font-size: 11px; color: #64748B; margin-bottom: 6px; }
    .pb-card-meta { display: flex; gap: 5px; flex-wrap: wrap; margin-bottom: 6px; }
    .pb-meta-tag { font-size: 10.5px; color: #475569; background: #F1F5F9; padding: 2px 7px; border-radius: 20px; }
    .pb-card-reason { font-size: 11px; color: ${PRIMARY}; border-top: 1px solid #F1F5F9; padding-top: 6px; margin-top: 4px; line-height: 1.4; font-weight: 500; }
    .pb-view-btn { display: inline-flex; align-items: center; gap: 3px; font-size: 11px; color: ${PRIMARY}; margin-top: 6px; font-weight: 600; text-decoration: none; }
    .pb-enquire-btn {
      display: block; width: 100%; margin-top: 8px; background: ${PRIMARY};
      color: black; border: none; padding: 7px 0; border-radius: 6px; font-weight: 700; font-size: 12px;
      cursor: pointer; text-align: center; transition: all 0.2s;
    }
    .pb-enquire-btn:active { transform: scale(0.98); }

    /* Typing indicator */
    .pb-typing {
      align-self: flex-start; background: #FFFFFF; border: 1px solid #E2E8F0;
      border-radius: 16px; border-bottom-left-radius: 4px;
      padding: 12px 16px; display: flex; align-items: center; gap: 5px;
      box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    }
    .pb-typing span { width: 6px; height: 6px; background: #94A3B8; border-radius: 50%; animation: pb-bounce 1.4s infinite; }
    .pb-typing span:nth-child(2) { animation-delay: 0.2s; }
    .pb-typing span:nth-child(3) { animation-delay: 0.4s; }
    @keyframes pb-bounce { 0%,60%,100% { transform:translateY(0); opacity:0.4; } 30% { transform:translateY(-6px); opacity:1; } }

    /* Navigation card */
    .pb-nav-card {
      background: #FFFFFF; border: 1px solid ${PRIMARY}33; border-radius: 14px;
      padding: 13px 15px; max-width: 280px;
      box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    }
    .pb-nav-msg { font-size: 13px; color: #334155; margin-bottom: 10px; line-height: 1.5; }
    .pb-nav-btn {
      display: inline-block; background: ${PRIMARY};
      color: black; text-decoration: none; padding: 8px 18px; border-radius: 8px;
      font-size: 12px; font-weight: 700; cursor: pointer; border: none; transition: opacity 0.2s;
    }
    .pb-nav-btn:hover { opacity: 0.9; }

    /* Quick prompts */
    #pb-quick { display: flex; flex-wrap: wrap; gap: 6px; padding: 0 14px 10px; flex-shrink: 0; background: #F8FAFC; border-top: 1px solid #F1F5F9; padding-top: 10px; }
    .pb-qbtn {
      font-size: 11.5px; padding: 5px 11px; border-radius: 20px;
      border: 1px solid ${PRIMARY}33; background: #fff;
      color: ${PRIMARY}; cursor: pointer; transition: all 0.2s; white-space: nowrap;
      font-weight: 600;
    }
    .pb-qbtn:hover { background: ${PRIMARY}10; border-color: ${PRIMARY}66; transform: translateY(-1px); }

    /* Input area */
    #pb-input-area {
      padding: 10px 14px 14px; border-top: 1px solid #E2E8F0;
      background: #FFFFFF; flex-shrink: 0;
    }
    .pb-input-row {
      display: flex; align-items: flex-end; gap: 8px;
      background: #F8FAFC; border: 1.5px solid #E2E8F0;
      border-radius: 14px; padding: 8px 12px; transition: border-color 0.2s;
    }
    .pb-input-row:focus-within { border-color: ${PRIMARY}; box-shadow: 0 0 0 3px ${PRIMARY}15; }
    #pb-input {
      flex: 1; background: transparent; border: none; outline: none;
      color: #1E293B; font-size: 13.5px; resize: none;
      max-height: 90px; min-height: 20px; line-height: 1.5; font-family: 'Manrope', sans-serif;
    }
    #pb-input::placeholder { color: #94A3B8; }
    #pb-send {
      width: 34px; height: 34px; border-radius: 50%;
      background: ${PRIMARY};
      border: none; cursor: pointer; display: flex; align-items: center; justify-content: center;
      flex-shrink: 0; transition: all 0.2s; box-shadow: 0 3px 12px ${PRIMARY}55;
    }
    #pb-send:hover { transform: scale(1.1); }
    #pb-send:disabled { opacity: 0.4; cursor: not-allowed; transform: none; }
    .pb-footer { text-align: center; font-size: 10px; color: #94A3B8; padding: 5px 0 2px; }
    .pb-footer strong { color: ${PRIMARY}; }

    @media (max-width: 440px) {
      #pb-chat-window { width: calc(100vw - 16px); right: 8px; bottom: 96px; height: 72vh; }
    }

    /* Inline Action Buttons inside bubbles */
    .pb-inline-options { display: flex; flex-direction: column; gap: 8px; margin-top: 12px; counter-reset: pb-btn-counter; width: 100%; }
    .pb-inline-btn {
      display: flex; align-items: flex-start; gap: 8px; width: 100%; border: none; outline: none;
      padding: 10px 12px; background: ${PRIMARY}15; border-radius: 8px;
      font-size: 13px; line-height: 1.4; color: #1E293B; cursor: pointer;
      text-align: left; transition: all 0.2s; font-family: 'Manrope', sans-serif; font-weight: 500;
    }
    .pb-inline-btn.numbered { counter-increment: pb-btn-counter; }
    .pb-inline-btn.numbered::before {
      content: counter(pb-btn-counter);
      min-width: 22px; height: 22px; background: ${PRIMARY};
      border-radius: 50%; display: flex; align-items: center; justify-content: center;
      font-size: 11px; font-weight: 700; color: #000; flex-shrink: 0; margin-top: 1px;
    }
    .pb-inline-btn:hover { background: ${PRIMARY}33; transform: translateX(3px); }
  `;

  const styleEl = document.createElement("style");
  styleEl.textContent = STYLES;
  document.head.appendChild(styleEl);

  // -- Build Widget HTML -------------------------------------------------------
  const widget = document.createElement("div");
  widget.id = "pb-chat-widget";
  widget.innerHTML = `
    <button id="pb-chat-toggle" aria-label="Open Property Doors chat assistant">
      <svg width="28" height="28" viewBox="0 0 24 24" fill="white">
        <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-2 12H6v-2h12v2zm0-3H6V9h12v2zm0-3H6V6h12v2z"/>
      </svg>
    </button>

    <div id="pb-chat-window">
      <div id="pb-header">
        <div class="pb-avatar">&#x1F3E0;</div>
        <div class="pb-header-info">
          <div class="pb-header-name">${COMPANY} AI</div>
          <div class="pb-header-status"><span class="pb-dot"></span> Online &middot; Typically replies instantly</div>
        </div>
        <button class="pb-close" id="pb-close-btn" aria-label="Close chat">&times;</button>
      </div>

      <div id="pb-messages"></div>

      <div id="pb-quick"></div>

      <div id="pb-input-area">
        <div class="pb-input-row">
          <textarea id="pb-input" rows="1" placeholder="Ask about properties, loans, locations..."></textarea>
          <button id="pb-send">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="black">
              <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
            </svg>
          </button>
        </div>
        <div class="pb-footer">Powered by <strong>Property Doors AI</strong></div>
      </div>
    </div>
  `;
  document.body.appendChild(widget);

  // -- References -------------------------------------------------------------
  const toggle = document.getElementById("pb-chat-toggle");
  const win = document.getElementById("pb-chat-window");
  const msgs = document.getElementById("pb-messages");
  const input = document.getElementById("pb-input");
  const send = document.getElementById("pb-send");
  const close = document.getElementById("pb-close-btn");

  let isOpen = false;

  // -- Helpers ----------------------------------------------------------------
  function esc(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function formatText(raw) {
    if (!raw) return "";
    const lines = raw.split(/\r?\n/).map(l => l.trim()).filter(l => l.length > 0);
    const isNumbered = lines.some(l => /^\d+[.)]\s+/.test(l));
    const isBullet = lines.some(l => /^[-*\u2022]\s+/.test(l));

    if (isNumbered || isBullet) {
      let html = "", inList = false;
      const tag = isNumbered ? "ol" : "ul";
      lines.forEach(line => {
        const nm = line.match(/^\d+[.)]\s+(.+)/);
        const bm = line.match(/^[-*\u2022]\s+(.+)/);
        if (nm || bm) {
          if (!inList) { html += `<${tag} class="pb-list">`; inList = true; }
          html += `<li>${esc(nm ? nm[1] : bm[1])}</li>`;
        } else {
          if (inList) { html += `</${tag}>`; inList = false; }
          html += `<p>${esc(line)}</p>`;
        }
      });
      if (inList) html += `</${tag}>`;
      return html;
    }
    return lines.map(l => `<p>${esc(l)}</p>`).join("");
  }

  function now() {
    return new Date().toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" });
  }

  function scrollBottom() { msgs.scrollTop = msgs.scrollHeight; }

  function addMsg(role, contentEl) {
    const wrap = document.createElement("div");
    wrap.className = `pb-msg ${role}`;
    const bubble = document.createElement("div");
    bubble.className = "pb-bubble";
    if (typeof contentEl === "string") {
      bubble.innerHTML = formatText(contentEl);
    } else {
      bubble.style.cssText = "padding:0;background:none;border:none;box-shadow:none;";
      bubble.appendChild(contentEl);
    }
    const time = document.createElement("div");
    time.className = "pb-time";
    time.textContent = now();
    wrap.appendChild(bubble);
    wrap.appendChild(time);
    msgs.appendChild(wrap);
    scrollBottom();
    return bubble;
  }

  function showTyping() {
    const el = document.createElement("div");
    el.className = "pb-typing";
    el.innerHTML = `<span></span><span></span><span></span>`;
    el.id = "pb-typing";
    msgs.appendChild(el);
    scrollBottom();
    return el;
  }

  function renderPropertyCards(data) {
    const container = document.createElement("div");
    container.className = "pb-cards";
    const intro = document.createElement("div");
    intro.className = "pb-card-intro";
    intro.textContent = data.message || `Found ${data.results.length} properties`;
    container.appendChild(intro);

    data.results.forEach(p => {
      const card = document.createElement("div");
      card.className = "pb-card";
      card.innerHTML = `
        <a href="${p.url || "#"}" target="_blank" rel="noopener" style="text-decoration:none; color:inherit; display:block;">
          <div class="pb-card-row">
            <div class="pb-card-title">${esc(p.title)}</div>
            <div class="pb-card-price">${esc(p.price)}</div>
          </div>
          <div class="pb-card-loc">&#x1F4CD; ${esc(p.location)}</div>
          <div class="pb-card-meta">
            ${p.bedrooms ? `<span class="pb-meta-tag">&#x1F6CF; ${p.bedrooms} BHK</span>` : ""}
            ${p.bathrooms ? `<span class="pb-meta-tag">&#x1F6BF; ${p.bathrooms} Bath</span>` : ""}
            ${p.area_sqft ? `<span class="pb-meta-tag">&#x1F4D0; ${p.area_sqft} sqft</span>` : ""}
            ${p.status ? `<span class="pb-meta-tag" style="color:#16A34A;background:#F0FDF4">&#x2705; ${esc(p.status)}</span>` : ""}
          </div>
          ${p.amenities && p.amenities.length ? `<div class="pb-card-meta">${p.amenities.slice(0, 3).map(a => `<span class="pb-meta-tag">${esc(a)}</span>`).join("")}</div>` : ""}
          ${p.reason ? `<div class="pb-card-reason">&#x2728; ${esc(p.reason)}</div>` : ""}
          <div class="pb-view-btn">View Details &rarr;</div>
        </a>
        <button class="pb-enquire-btn" data-id="${esc(p.id)}">Enquire Now</button>
      `;

      const enquireBtn = card.querySelector(".pb-enquire-btn");
      enquireBtn.addEventListener("click", async (e) => {
        e.preventDefault();
        e.stopPropagation();
        activity.propertyCount++;
        enquireBtn.textContent = "Sending...";
        enquireBtn.disabled = true;
        try {
          const res = await fetch(`${API_URL}/enquire`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ property_id: p.id, user: currentUser })
          });
          if (res.ok) {
            enquireBtn.textContent = "Enquiry Sent \u2705";
            enquireBtn.style.background = "#16A34A";
          } else {
            throw new Error("Failed");
          }
        } catch (e) {
          enquireBtn.textContent = "Error, try again";
          enquireBtn.disabled = false;
        }
      });
      container.appendChild(card);
    });
    return container;
  }

  function renderNavigation(data) {
    const card = document.createElement("div");
    card.className = "pb-nav-card";
    card.innerHTML = `
      <div class="pb-nav-msg">${esc(data.message || "Here's the link you need:")}</div>
      <a href="${esc(data.url)}" class="pb-nav-btn" target="_blank">Go to ${esc(data.label || "Page")} &rarr;</a>
    `;
    return card;
  }

  // -- Inline Options Renderer ------------------------------------------------
  function disableAllOptionButtons() {
    document.querySelectorAll('#pb-messages .pb-inline-btn').forEach(b => {
      b.disabled = true;
      b.style.opacity = '0.45';
      b.style.cursor = 'not-allowed';
      b.style.pointerEvents = 'none';
    });
  }

  function renderInlineOptions(bubble, options, numbered = false) {
    if (!options || !options.length) return;
    const list = document.createElement("div");
    list.className = "pb-inline-options";
    options.forEach((opt) => {
      const btn = document.createElement("button");
      btn.className = "pb-inline-btn" + (numbered ? " numbered" : "");
      btn.innerHTML = `<span>${esc(opt.label)}</span>`;
      btn.onclick = () => {
        disableAllOptionButtons();
        if (!isOpen) {
          isOpen = true;
          win.classList.add("open");
        }
        sendMessage(opt.msg, opt.label);
      };
      list.appendChild(btn);
    });
    bubble.appendChild(list);
    scrollBottom();
  }

  // -- Persistent Quick-Access Bar --------------------------------------------
  function setupQuickBar() {
    const quickDiv = document.getElementById('pb-quick');
    quickDiv.innerHTML = '';
    const QUICK = [
      { label: '\u{1F3E0} Property Search', msg: 'MENU_FIND_PROPERTIES' },
      { label: '\u2753 FAQs',               msg: 'MENU_ASK_FAQ' },
      { label: '\u{1F517} Navigate',         msg: 'MENU_NAVIGATE' },
    ];
    QUICK.forEach(q => {
      const btn = document.createElement('button');
      btn.className = 'pb-qbtn';
      btn.textContent = q.label;
      btn.onclick = () => { disableAllOptionButtons(); sendMessage(q.msg, q.label); };
      quickDiv.appendChild(btn);
    });
  }

  // -- Welcome Message --------------------------------------------------------
  function showWelcome() {
    const bubble = addMsg("bot",
      `\u{1F44B} Hi! I'm the ${COMPANY} AI assistant.\n\n` +
      `I can help you with:`
    );
    renderInlineOptions(bubble, [
      { label: "Find properties in Mumbai, Pune, Bangalore & more", msg: "MENU_FIND_PROPERTIES" },
      { label: "Answer questions about home loans, RERA & charges", msg: "MENU_ASK_FAQ" },
      { label: "Navigate to any section of propertydoors.com",      msg: "MENU_NAVIGATE" }
    ], true);
  }

  // -- Send Message -----------------------------------------------------------
  async function sendMessage(text, display_text = null) {
    text = text.trim();
    if (!text) return;

    addMsg("user", display_text ? display_text : text);
    input.value = "";
    input.style.height = "auto";
    send.disabled = true;

    const typing = showTyping();

    try {
      const res = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, session_id: SESSION_ID, user: currentUser }),
      });

      typing.remove();

      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      let botBubble = null;
      if (data.type === "property_results") {
        botBubble = addMsg("bot", renderPropertyCards(data));
      } else if (data.type === "navigate") {
        botBubble = addMsg("bot", renderNavigation(data));
      } else {
        botBubble = addMsg("bot", data.message || "Sorry, I couldn't get a response.");
      }

      if (data.options && data.options.length > 0) {
        renderInlineOptions(botBubble, data.options, false);
      }

    } catch (err) {
      typing.remove();
      addMsg("bot", "\u26A0\uFE0F I'm having trouble connecting right now. Please try again in a moment.");
      console.error("[Property Doors Chatbot] Error:", err);
    }

    send.disabled = false;
  }

  // -- Event Listeners --------------------------------------------------------
  toggle.addEventListener("click", () => {
    isOpen = !isOpen;
    win.classList.toggle("open", isOpen);
    if (isOpen && msgs.children.length === 0) {
      setupQuickBar();
      showWelcome();
    }
  });

  close.addEventListener("click", () => {
    isOpen = false;
    win.classList.remove("open");
  });

  send.addEventListener("click", () => sendMessage(input.value));

  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input.value);
    }
  });

  input.addEventListener("input", () => {
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 90) + "px";
  });

  // -- Activity Tracking ------------------------------------------------------
  async function trackActivity() {
    if (!currentUser) return;
    const timeSpent = Math.floor((Date.now() - activity.startTime) / 1000) + "s";

    try {
      await fetch(`${API_URL}/track-activity`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: SESSION_ID,
          user_id: currentUser.id,
          pages: activity.pages,
          property_count: activity.propertyCount,
          time_spent: timeSpent
        })
      });
    } catch (e) {
      console.warn("Activity tracking failed", e);
    }
  }

  setInterval(trackActivity, 30000);
  window.addEventListener("beforeunload", trackActivity);

  // -- Auth Handling ----------------------------------------------------------
  function updateAuthState(user) {
    if (user) {
      currentUser = {
        id: user.id,
        email: user.email,
        name: user.user_metadata?.name || user.user_metadata?.full_name || "Guest",
        phone: user.phone || user.user_metadata?.phone || null
      };
    } else {
      currentUser = {
        id: `guest_${SESSION_ID}`,
        email: `guest_${SESSION_ID}@propertydoors.local`,
        name: "Guest",
        phone: "N/A"
      };
    }
    input.disabled = false;
    send.disabled = false;
  }

  if (window.supabase && window.supabase.auth) {
    window.supabase.auth.getSession().then(({ data: { session } }) => {
      updateAuthState(session?.user);
    }).catch(err => {
      console.warn("Supabase session check failed:", err);
      updateAuthState(null);
    });

    window.supabase.auth.onAuthStateChange((_event, session) => {
      updateAuthState(session?.user);
    });
  } else {
    updateAuthState(null);
  }

})();

/*
  script.js - EyeTrackerWeb static script
  Responsibilities:
  - Establish live Socket.IO connection to Flask backend
  - Dynamically update video feed and UI images
  - Render AI suggestions/chips and handle selection
  - Handle keyboard key click visual feedback
  - Manage user profile modal open/close
  Structure: modular functions + event listeners for future extension
*/

/* =====================
   Globals and Utilities
   ===================== */
const ETW = {
  sockets: {},
  state: {
    connected: false,
    lastFrame: null,
    user: null,
  },
  els: {
    // Expected element IDs in template (make optional-safe)
    videoImg: () => document.getElementById('video-feed'), // <img id="video-feed" />
    uiImg: () => document.getElementById('ui-overlay'),     // <img id="ui-overlay" />
    suggestionsWrap: () => document.getElementById('ai-suggestions'), // <div id="ai-suggestions" />
    keysContainer: () => document.getElementById('keys'),   // container that includes key buttons
    profileBtn: () => document.getElementById('profile-btn'),
    profileModal: () => document.getElementById('profile-modal'),
    profileClose: () => document.getElementById('profile-close'),
  },
};

function safeGet(elGetter) {
  try { return elGetter && elGetter(); } catch { return null; }
}

/* =====================
   Socket.IO Connection
   ===================== */
function initSocket() {
  if (typeof io === 'undefined') {
    console.warn('Socket.IO client (io) not found. Make sure to include socket.io.js from Flask-SocketIO.');
    return;
  }

  // Auto-detect namespace and endpoint
  const loc = window.location;
  const baseURL = `${loc.protocol}//${loc.hostname}${loc.port ? ':' + loc.port : ''}`;

  // Connect to root namespace
  const socket = io(baseURL, {
    transports: ['websocket', 'polling'],
    withCredentials: true,
    autoConnect: true,
  });

  ETW.sockets.main = socket;

  socket.on('connect', () => {
    ETW.state.connected = true;
    console.info('[SocketIO] connected', socket.id);
  });

  socket.on('disconnect', (reason) => {
    ETW.state.connected = false;
    console.warn('[SocketIO] disconnected:', reason);
  });

  socket.on('connect_error', (err) => {
    console.error('[SocketIO] connect_error:', err.message || err);
  });

  // Server emits base64 frames for video and ui overlays
  socket.on('video_frame', (payload) => {
    // payload: { frame: 'data:image/jpeg;base64,...' } or raw base64
    updateVideoFrame(payload);
  });

  socket.on('ui_frame', (payload) => {
    updateUIFrame(payload);
  });

  // AI suggestions array of strings/objects
  socket.on('ai_suggestions', (suggestions) => {
    renderAISuggestions(suggestions);
  });

  // Example: server feedback when a suggestion is chosen
  socket.on('suggestion_ack', (data) => {
    console.debug('[SocketIO] suggestion_ack:', data);
  });
}

/* =====================
   Video/UI image updates
   ===================== */
function normalizeDataURL(input, mime = 'image/jpeg') {
  if (!input) return null;
  // Accept already-prefixed data URLs or raw base64
  if (typeof input === 'string' && input.startsWith('data:image')) return input;
  if (typeof input === 'string') return `data:${mime};base64,${input}`;
  if (input && typeof input.frame === 'string') return normalizeDataURL(input.frame, mime);
  return null;
}

function updateImgEl(imgEl, dataUrl) {
  if (!imgEl || !dataUrl) return;
  // Avoid layout trashing by only updating when changed
  if (imgEl.dataset.lastSrc !== dataUrl) {
    imgEl.src = dataUrl;
    imgEl.dataset.lastSrc = dataUrl;
  }
}

function updateVideoFrame(payload) {
  const img = safeGet(ETW.els.videoImg);
  const dataUrl = normalizeDataURL(payload, 'image/jpeg');
  updateImgEl(img, dataUrl);
}

function updateUIFrame(payload) {
  const img = safeGet(ETW.els.uiImg);
  const dataUrl = normalizeDataURL(payload, 'image/png');
  updateImgEl(img, dataUrl);
}

/* =====================
   AI Suggestions / Chips
   ===================== */
function renderAISuggestions(suggestions) {
  const wrap = safeGet(ETW.els.suggestionsWrap);
  if (!wrap) return;

  // Normalize to array of { id, label }
  const norm = (suggestions || []).map((s, idx) =>
    typeof s === 'string' ? { id: `s-${idx}`, label: s } : { id: s.id || `s-${idx}`, label: s.label || String(s.text || s) }
  );

  wrap.innerHTML = '';
  norm.forEach((item) => {
    const chip = document.createElement('button');
    chip.className = 'chip suggestion-chip';
    chip.type = 'button';
    chip.textContent = item.label;
    chip.dataset.id = item.id;
    chip.addEventListener('click', () => onSuggestionClick(item));
    wrap.appendChild(chip);
  });

  if (norm.length === 0) {
    const empty = document.createElement('div');
    empty.className = 'chips-empty';
    empty.textContent = 'No suggestions available';
    wrap.appendChild(empty);
  }
}

function onSuggestionClick(item) {
  // Emit to server
  const socket = ETW.sockets.main;
  if (socket && ETW.state.connected) {
    socket.emit('suggestion_click', { id: item.id, label: item.label });
  }
}

/* =====================
   Keyboard key clicks
   ===================== */
function initKeyboardClicks() {
  const container = safeGet(ETW.els.keysContainer);
  if (!container) return;

  container.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-key]');
    if (!btn) return;
    const key = btn.dataset.key;

    // Visual feedback
    btn.classList.add('key-active');
    setTimeout(() => btn.classList.remove('key-active'), 120);

    // Emit event to backend
    const socket = ETW.sockets.main;
    if (socket && ETW.state.connected) {
      socket.emit('key_press', { key });
    }
  });
}

/* =====================
   User profile modal
   ===================== */
function initProfileModal() {
  const btn = safeGet(ETW.els.profileBtn);
  const modal = safeGet(ETW.els.profileModal);
  const closeBtn = safeGet(ETW.els.profileClose);
  if (!btn || !modal) return;

  function openModal() {
    modal.classList.add('open');
    document.body.style.overflow = 'hidden';
  }

  function closeModal() {
    modal.classList.remove('open');
    document.body.style.overflow = '';
  }

  btn.addEventListener('click', openModal);
  if (closeBtn) closeBtn.addEventListener('click', closeModal);
  modal.addEventListener('click', (e) => {
    // close when clicking backdrop
    if (e.target === modal) closeModal();
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && modal.classList.contains('open')) closeModal();
  });
}

/* =====================
   Bootstrapping
   ===================== */
function initEventListeners() {
  // Optional: request initial suggestions
  const socket = ETW.sockets.main;
  if (socket) {
    socket.on('connect', () => socket.emit('client_ready'));
  }
}

function init() {
  initSocket();
  initKeyboardClicks();
  initProfileModal();
  initEventListeners();
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}

/* =====================
   Extension Points
   ===================== */
// window.ETW can be used for debugging or future hooks
window.ETW = ETW;

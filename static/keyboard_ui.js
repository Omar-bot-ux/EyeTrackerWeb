'use strict';
/*
 keyboard_ui.js
 On-screen keyboard module with gaze/mouse selection, key highlighting, Socket.IO
 backend communication, and AI suggestions display.

 Structure:
 - KeyboardLayout: defines rows/keys and utility for rendering
 - KeyboardUI: renders DOM, handles hover/focus, input selection, and emits events
 - SuggestionBar: renders AI suggestions and handles selection
 - SocketBridge: minimal Socket.IO wrapper for backend comms
 - initKeyboardUI: bootstrap attaching to a container

 Assumptions:
 - A container element exists in the DOM where the keyboard will be injected.
 - Socket.IO client library is available globally as io (or dynamically loaded).
 - Eye-gaze selection can be simulated by dwell timers over keys.
*/

(function () {
  // ---------------------- Utilities ----------------------
  const qs = (sel, root = document) => root.querySelector(sel);
  const qsa = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  function ensureSocketIO(url) {
    return new Promise((resolve, reject) => {
      if (window.io) return resolve(window.io);
      const script = document.createElement('script');
      script.src = url || '/socket.io/socket.io.js';
      script.async = true;
      script.onload = () => resolve(window.io);
      script.onerror = reject;
      document.head.appendChild(script);
    });
  }

  // ---------------------- Layout ----------------------
  const DEFAULT_LAYOUT = [
    [
      { label: '1' }, { label: '2' }, { label: '3' }, { label: '4' }, { label: '5' },
      { label: '6' }, { label: '7' }, { label: '8' }, { label: '9' }, { label: '0' },
      { label: 'Backspace', code: 'Backspace', w: 2 }
    ],
    [
      { label: 'q' }, { label: 'w' }, { label: 'e' }, { label: 'r' }, { label: 't' },
      { label: 'y' }, { label: 'u' }, { label: 'i' }, { label: 'o' }, { label: 'p' }
    ],
    [
      { label: 'Caps', code: 'CapsLock', w: 1.5 },
      { label: 'a' }, { label: 's' }, { label: 'd' }, { label: 'f' }, { label: 'g' },
      { label: 'h' }, { label: 'j' }, { label: 'k' }, { label: 'l' },
      { label: 'Enter', code: 'Enter', w: 1.8 }
    ],
    [
      { label: 'Shift', code: 'Shift', w: 1.6 },
      { label: 'z' }, { label: 'x' }, { label: 'c' }, { label: 'v' }, { label: 'b' },
      { label: 'n' }, { label: 'm' }, { label: ',' }, { label: '.' }, { label: '?' },
      { label: 'Shift', code: 'Shift', w: 1.6 }
    ],
    [
      { label: 'Space', code: 'Space', w: 6 },
      { label: 'Left', code: 'ArrowLeft' },
      { label: 'Right', code: 'ArrowRight' }
    ]
  ];

  class KeyboardLayout {
    constructor(layout = DEFAULT_LAYOUT) { this.layout = layout; }
    forEachKey(cb) {
      this.layout.forEach((row, rIdx) => row.forEach((key, kIdx) => cb(key, rIdx, kIdx)));
    }
  }

  // ---------------------- Socket Bridge ----------------------
  class SocketBridge {
    constructor(namespace = '/') {
      this.namespace = namespace;
      this.socket = null;
    }
    async connect() {
      const io = await ensureSocketIO();
      this.socket = io(this.namespace);
      return this.socket;
    }
    emit(type, payload) {
      if (this.socket) this.socket.emit(type, payload);
    }
    on(event, handler) {
      if (this.socket) this.socket.on(event, handler);
    }
  }

  // ---------------------- Suggestion Bar ----------------------
  class SuggestionBar {
    constructor(container) {
      this.el = document.createElement('div');
      this.el.className = 'kb-suggestions';
      container.appendChild(this.el);
      this.current = [];
      this.onPick = null; // function(text)
    }

    setSuggestions(list) {
      this.current = list || [];
      this.render();
    }

    render() {
      this.el.innerHTML = '';
      const wrap = document.createElement('div');
      wrap.className = 'kb-suggestions-wrap';
      this.current.slice(0, 5).forEach((sug, i) => {
        const btn = document.createElement('button');
        btn.className = 'kb-suggestion';
        btn.type = 'button';
        btn.textContent = typeof sug === 'string' ? sug : (sug.text || '');
        btn.dataset.index = String(i);
        btn.addEventListener('click', () => this.onPick && this.onPick(btn.textContent));
        btn.addEventListener('mouseenter', () => btn.classList.add('hover'));
        btn.addEventListener('mouseleave', () => btn.classList.remove('hover'));
        wrap.appendChild(btn);
      });
      this.el.appendChild(wrap);
    }
  }

  // ---------------------- Keyboard UI ----------------------
  class KeyboardUI {
    constructor(container, layout = new KeyboardLayout(), options = {}) {
      this.container = container;
      this.layout = layout;
      this.options = Object.assign({ dwellMs: 900 }, options);
      this.state = { caps: false, shift: false };
      this.socket = new SocketBridge(options.namespace || '/');

      this.root = document.createElement('div');
      this.root.className = 'kb-root';

      // Suggestions on top
      this.suggestions = new SuggestionBar(this.root);
      this.suggestions.onPick = (text) => this.commitText(text + ' ');

      // Keyboard area
      this.keysWrap = document.createElement('div');
      this.keysWrap.className = 'kb-keys';
      this.root.appendChild(this.keysWrap);

      this.container.appendChild(this.root);

      this._dwellTimers = new Map();

      this.render();
      this.bindSocket();
    }

    async bindSocket() {
      await this.socket.connect();
      // Listen for AI suggestions from backend
      this.socket.on('suggestions', (payload) => {
        const list = Array.isArray(payload) ? payload : (payload && payload.items) || [];
        this.suggestions.setSuggestions(list.map(item => typeof item === 'string' ? item : (item.text || '')));
      });
    }

    keyLabelForDisplay(key) {
      if (key.code === 'Space') return '␣';
      return this.applyShiftCaps(key.label);
    }

    applyShiftCaps(ch) {
      if (!ch) return ch;
      if (ch.length === 1 && /[a-z]/i.test(ch)) {
        const upper = (this.state.caps ^ this.state.shift) === 1;
        return upper ? ch.toUpperCase() : ch.toLowerCase();
      }
      // simple symbol shift mapping
      const map = {
        '1': '!', '2': '@', '3': '#', '4': '$', '5': '%',
        '6': '^', '7': '&', '8': '*', '9': '(', '0': ')',
        ',': '<', '.': '>', '?': '?'
      };
      if (this.state.shift && map[ch]) return map[ch];
      return ch;
    }

    render() {
      this.keysWrap.innerHTML = '';
      this.layout.layout.forEach((row) => {
        const rowEl = document.createElement('div');
        rowEl.className = 'kb-row';
        row.forEach((key) => {
          const btn = document.createElement('button');
          btn.type = 'button';
          btn.className = 'kb-key';
          if (key.w) btn.style.flex = String(key.w);
          btn.dataset.code = key.code || key.label;
          btn.dataset.label = key.label;
          btn.textContent = this.keyLabelForDisplay(key);
          this.attachInteractions(btn, key);
          rowEl.appendChild(btn);
        });
        this.keysWrap.appendChild(rowEl);
      });
      this.refreshToggles();
    }

    refreshToggles() {
      qsa('.kb-key', this.keysWrap).forEach(btn => {
        const code = btn.dataset.code;
        btn.classList.toggle('active',
          (code === 'CapsLock' && this.state.caps) ||
          (code === 'Shift' && this.state.shift)
        );
      });
    }

    attachInteractions(btn, key) {
      // hover highlight
      btn.addEventListener('mouseenter', () => btn.classList.add('hover'));
      btn.addEventListener('mouseleave', () => btn.classList.remove('hover'));
      btn.addEventListener('focus', () => btn.classList.add('hover'));
      btn.addEventListener('blur', () => btn.classList.remove('hover'));

      // click
      btn.addEventListener('click', () => this.handleKeyPress(key));

      // dwell for eye-gaze
      btn.addEventListener('mouseenter', () => this.startDwell(btn, key));
      btn.addEventListener('mouseleave', () => this.cancelDwell(btn));
      btn.addEventListener('blur', () => this.cancelDwell(btn));
    }

    startDwell(btn, key) {
      this.cancelDwell(btn);
      const ms = this.options.dwellMs;
      const timeout = setTimeout(() => {
        // Add a brief visual pulse to indicate selection
        btn.classList.add('selected');
        this.handleKeyPress(key);
        setTimeout(() => btn.classList.remove('selected'), 150);
      }, ms);
      this._dwellTimers.set(btn, timeout);
      // progress ring via CSS var
      btn.style.setProperty('--dwell-ms', `${ms}ms`);
      btn.classList.add('dwell');
    }

    cancelDwell(btn) {
      const t = this._dwellTimers.get(btn);
      if (t) clearTimeout(t);
      this._dwellTimers.delete(btn);
      btn.classList.remove('dwell');
    }

    handleKeyPress(key) {
      const code = key.code || key.label;
      switch (code) {
        case 'Backspace':
          this.emitInput({ type: 'backspace' });
          break;
        case 'Enter':
          this.emitInput({ type: 'enter' });
          break;
        case 'Space':
          this.emitInput({ type: 'text', text: ' ' });
          break;
        case 'CapsLock':
          this.state.caps = !this.state.caps;
          this.render();
          break;
        case 'Shift':
          this.state.shift = !this.state.shift;
          this.render();
          break;
        case 'ArrowLeft':
          this.emitInput({ type: 'move', dir: 'left' });
          break;
        case 'ArrowRight':
          this.emitInput({ type: 'move', dir: 'right' });
          break;
        default:
          // printable
          const ch = this.applyShiftCaps(key.label);
          if (ch) this.commitText(ch);
          // one-shot shift if not caps
          if (this.state.shift && !this.state.caps) {
            this.state.shift = false;
            this.render();
          }
      }

      // Ask backend for new suggestions after any input
      this.socket.emit('need_suggestions', { context: 'text' });
    }

    commitText(text) {
      this.emitInput({ type: 'text', text });
    }

    emitInput(payload) {
      // Emit to backend
      this.socket.emit('key_input', payload);
      // Also dispatch a DOM event for app-level listeners
      this.root.dispatchEvent(new CustomEvent('kb-input', { detail: payload }));
    }
  }

  // ---------------------- Styles (light-weight) ----------------------
  const STYLE = `
  .kb-root { font-family: system-ui, sans-serif; user-select: none; }
  .kb-suggestions { margin-bottom: 8px; }
  .kb-suggestions-wrap { display: flex; gap: 6px; flex-wrap: wrap; }
  .kb-suggestion { padding: 6px 10px; border-radius: 8px; border: 1px solid #ccc; background: #fafafa; cursor: pointer; }
  .kb-suggestion.hover, .kb-suggestion:focus { outline: 2px solid #9ad; }
  .kb-keys { display: flex; flex-direction: column; gap: 6px; }
  .kb-row { display: flex; gap: 6px; }
  .kb-key { flex: 1; padding: 12px; border-radius: 8px; border: 1px solid #bbb; background: #fff; cursor: pointer; position: relative; }
  .kb-key.hover, .kb-key:focus { outline: 2px solid #4a90e2; }
  .kb-key.active { background: #eef6ff; border-color: #4a90e2; }
  .kb-key.dwell::after { content: ''; position: absolute; inset: 0; border-radius: 8px; border: 2px solid #4a90e2; animation: kb-dwell var(--dwell-ms, 900ms) linear forwards; }
  .kb-key.selected { background: #d7f5d7; }
  @keyframes kb-dwell { from { transform: scale(1); opacity: .4;} to { transform: scale(0.9); opacity: 1;} }
  `;

  function injectStyle(css = STYLE) {
    const style = document.createElement('style');
    style.textContent = css;
    document.head.appendChild(style);
  }

  // ---------------------- Bootstrap ----------------------
  function initKeyboardUI({ container, namespace, dwellMs } = {}) {
    injectStyle();
    const el = typeof container === 'string' ? qs(container) : container;
    if (!el) throw new Error('Keyboard container not found');
    const ui = new KeyboardUI(el, new KeyboardLayout(), { namespace, dwellMs });
    return ui;
  }

  // Expose globally
  window.KeyboardUI = KeyboardUI;
  window.KeyboardLayout = KeyboardLayout;
  window.initKeyboardUI = initKeyboardUI;
})();

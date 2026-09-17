// Minimal DOM / browser stub for Node.js behavioral testing
// Conforms to presentation-only GUI contracts and zero-dependency rule.

class ClassList {
  constructor() {
    this._classes = new Set();
  }
  add(...names) { names.forEach(n => this._classes.add(n)); }
  remove(...names) { names.forEach(n => this._classes.delete(n)); }
  contains(name) { return this._classes.has(name); }
  toggle(name, force) {
    if (typeof force === 'boolean') {
      if (force) this._classes.add(name);
      else this._classes.delete(name);
      return force;
    }
    if (this._classes.has(name)) {
      this._classes.delete(name);
      return false;
    }
    this._classes.add(name);
    return true;
  }
}

class StyleMap {
  constructor() {
    this._props = new Map();
    this.cursor = '';
  }
  setProperty(name, value) { this._props.set(name, String(value)); }
  getPropertyValue(name) { return this._props.get(name) || ''; }
}

export class MockElement {
  constructor(tagName = 'div') {
    this.tagName = tagName.toUpperCase();
    this.attributes = new Map();
    this.classList = new ClassList();
    this.style = new StyleMap();
    this.children = [];
    this.parentElement = null;
    this.listeners = new Map();
    this._value = '';
    this.hidden = false;
    this.disabled = false;
    this.textContent = '';
    this.id = '';
    this.dataset = new Proxy({}, {
      get: (_, prop) => {
        const attr = 'data-' + String(prop).replace(/([A-Z])/g, '-$1').toLowerCase();
        return this.getAttribute(attr);
      },
      set: (_, prop, val) => {
        const attr = 'data-' + String(prop).replace(/([A-Z])/g, '-$1').toLowerCase();
        this.setAttribute(attr, val);
        return true;
      },
      deleteProperty: (_, prop) => {
        const attr = 'data-' + String(prop).replace(/([A-Z])/g, '-$1').toLowerCase();
        this.removeAttribute(attr);
        return true;
      }
    });
  }

  get value() { return this._value; }
  set value(v) { this._value = String(v); }

  get className() { return Array.from(this.classList._classes).join(' '); }
  set className(v) {
    this.classList._classes.clear();
    String(v || '').split(/\s+/).filter(Boolean).forEach(c => this.classList.add(c));
  }

  setAttribute(name, val) {
    this.attributes.set(name, String(val));
    if (name === 'id') this.id = String(val);
    if (name === 'class') this.className = String(val);
    if (name === 'hidden') this.hidden = true;
    if (name === 'disabled') this.disabled = true;
  }

  getAttribute(name) {
    return this.attributes.has(name) ? this.attributes.get(name) : null;
  }

  hasAttribute(name) {
    return this.attributes.has(name);
  }

  removeAttribute(name) {
    this.attributes.delete(name);
    if (name === 'id') this.id = '';
    if (name.startsWith('data-')) {
      const key = name.slice(5).replace(/-([a-z])/g, (_, c) => c.toUpperCase());
      delete this.dataset[key];
    }
    if (name === 'hidden') this.hidden = false;
    if (name === 'disabled') this.disabled = false;
  }

  append(...items) {
    for (const item of items) {
      if (typeof item === 'string') {
        const textNode = new MockElement('#text');
        textNode.textContent = item;
        textNode.parentElement = this;
        this.children.push(textNode);
      } else if (item instanceof MockElement) {
        item.parentElement = this;
        this.children.push(item);
      }
    }
  }

  replaceChildren(...items) {
    this.children = [];
    this.append(...items);
  }

  remove() {
    if (this.parentElement) {
      const idx = this.parentElement.children.indexOf(this);
      if (idx !== -1) this.parentElement.children.splice(idx, 1);
      this.parentElement = null;
    }
  }

  addEventListener(type, fn) {
    if (!this.listeners.has(type)) this.listeners.set(type, []);
    this.listeners.get(type).push(fn);
  }

  removeEventListener(type, fn) {
    if (!this.listeners.has(type)) return;
    const list = this.listeners.get(type).filter(f => f !== fn);
    this.listeners.set(type, list);
  }

  dispatchEvent(event) {
    event.target = this;
    const list = this.listeners.get(event.type) || [];
    for (const fn of list) {
      fn(event);
    }
    return true;
  }

  click() {
    this.dispatchEvent(new CustomEvent('click', { bubbles: true }));
  }

  focus() {}
  select() {}

  showModal() { this.setAttribute('open', ''); }
  close() { this.removeAttribute('open'); }

  querySelector(selector) {
    return this.querySelectorAll(selector)[0] || null;
  }

  querySelectorAll(selector) {
    const results = [];
    const walk = (node) => {
      for (const child of node.children) {
        if (matchesSelector(child, selector)) {
          results.push(child);
        }
        walk(child);
      }
    };
    walk(this);
    return results;
  }
}

function matchesSelector(el, selector) {
  if (!el || el.tagName === '#TEXT') return false;
  if (selector.startsWith('#')) {
    return el.id === selector.slice(1);
  }
  if (selector.startsWith('.')) {
    return el.classList.contains(selector.slice(1));
  }
  if (selector.includes('[') && selector.includes(']')) {
    const tagMatch = selector.match(/^([a-zA-Z0-9_-]+)\[/);
    if (tagMatch && el.tagName.toLowerCase() !== tagMatch[1].toLowerCase()) {
      return false;
    }
    const m = selector.match(/\[([a-zA-Z0-9_-]+)(?:="([^"]*)")?\]/);
    if (m) {
      const [, attr, val] = m;
      if (val !== undefined) return el.getAttribute(attr) === val;
      return el.hasAttribute(attr);
    }
  }
  return el.tagName.toLowerCase() === selector.toLowerCase();
}

class MockStorage {
  constructor() {
    this._store = new Map();
  }
  getItem(k) { return this._store.has(k) ? this._store.get(k) : null; }
  setItem(k, v) { this._store.set(k, String(v)); }
  removeItem(k) { this._store.delete(k); }
  clear() { this._store.clear(); }
}

export function setupMockDOM() {
  const root = new MockElement('html');
  const body = new MockElement('body');
  root.append(body);

  const listeners = new Map();
  const doc = {
    documentElement: root,
    body,
    createElement: (tag) => new MockElement(tag),
    createElementNS: (_, tag) => new MockElement(tag),
    createTextNode: (text) => {
      const el = new MockElement('#text');
      el.textContent = text;
      return el;
    },
    querySelector: (sel) => root.querySelector(sel),
    querySelectorAll: (sel) => root.querySelectorAll(sel),
    addEventListener: (type, fn) => {
      if (!listeners.has(type)) listeners.set(type, []);
      listeners.get(type).push(fn);
    },
    removeEventListener: (type, fn) => {
      if (!listeners.has(type)) return;
      listeners.set(type, listeners.get(type).filter(f => f !== fn));
    },
    dispatchEvent: (event) => {
      const list = listeners.get(event.type) || [];
      for (const fn of list) fn(event);
      return true;
    }
  };

  const winListeners = new Map();
  const win = {
    document: doc,
    location: { hash: '', origin: 'http://127.0.0.1:8080' },
    history: { replaceState: (_, __, hash) => { win.location.hash = hash; } },
    matchMedia: () => ({ matches: false, addEventListener: () => {} }),
    addEventListener: (type, fn) => {
      if (!winListeners.has(type)) winListeners.set(type, []);
      winListeners.get(type).push(fn);
    },
    removeEventListener: (type, fn) => {
      if (!winListeners.has(type)) return;
      winListeners.set(type, winListeners.get(type).filter(f => f !== fn));
    },
    dispatchEvent: (event) => {
      const list = winListeners.get(event.type) || [];
      for (const fn of list) fn(event);
      return true;
    },
    getComputedStyle: (el) => ({
      getPropertyValue: (prop) => el.style.getPropertyValue(prop) || ''
    })
  };

  const storage = new MockStorage();

  const mockRoutes = new Map();
  const mockFetch = async (url, init = {}) => {
    const method = (init.method || 'GET').toUpperCase();
    const urlStr = typeof url === 'string' ? url : url.toString();
    const parsedPath = urlStr.split('?')[0];
    for (const [key, handler] of mockRoutes.entries()) {
      const [m, p] = key.split(':');
      if (m === method && (parsedPath === p || (p.endsWith('*') && parsedPath.startsWith(p.slice(0, -1))))) {
        let body = {};
        if (init.body) {
          try { body = JSON.parse(init.body); } catch (_) {}
        }
        const res = await handler({ url: urlStr, path: parsedPath, method, body, headers: init.headers || {} });
        const status = res?.status || 200;
        return {
          ok: status >= 200 && status < 300,
          status,
          json: async () => res?.body !== undefined ? res.body : {}
        };
      }
    }
    if (globalThis.__mockMutate && method === 'POST') {
      let body = {};
      if (init.body) {
        try { body = JSON.parse(init.body); } catch (_) {}
      }
      const res = await globalThis.__mockMutate(parsedPath, body);
      return {
        ok: true,
        status: 200,
        json: async () => res !== undefined ? res : {}
      };
    }
    if (parsedPath === '/api/v2/session') {
      return { ok: true, status: 200, json: async () => ({ csrf_token: 'test_csrf_token_001' }) };
    }
    if (parsedPath === '/api/v2/threads' && method === 'GET') {
      const threads = globalThis.__getAppState?.()?.threads || [];
      return { ok: true, status: 200, json: async () => ({ threads }) };
    }
    if (parsedPath.startsWith('/api/v2/threads/') && method === 'GET') {
      const threadId = decodeURIComponent(parsedPath.slice('/api/v2/threads/'.length));
      const threads = globalThis.__getAppState?.()?.threads || [];
      const th = threads.find(t => t.thread_id === threadId);
      return { ok: true, status: 200, json: async () => (th || { thread_id: threadId, title: 'Thread', status: 'ACTIVE' }) };
    }
    return { ok: true, status: 200, json: async () => ({}) };
  };

  mockFetch.setRoute = (method, path, handler) => {
    mockRoutes.set(`${method.toUpperCase()}:${path}`, handler);
  };
  mockFetch.clearRoutes = () => {
    mockRoutes.clear();
  };

  globalThis.window = win;
  globalThis.document = doc;
  globalThis.localStorage = storage;
  globalThis.fetch = mockFetch;
  if (!globalThis.crypto) {
    globalThis.crypto = {
      getRandomValues: (arr) => {
        for (let i = 0; i < arr.length; i++) arr[i] = Math.floor(Math.random() * 256);
        return arr;
      }
    };
  }
  globalThis.CustomEvent = class CustomEvent {
    constructor(type, init = {}) {
      this.type = type;
      this.detail = init.detail;
      this.bubbles = Boolean(init.bubbles);
    }
  };
  globalThis.Event = class Event {
    constructor(type) {
      this.type = type;
    }
  };

  return { root, body, doc, win, storage, fetch: mockFetch };
}

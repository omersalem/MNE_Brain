/**
 * MNE_Brain Release 2 — Client Presentation Preferences Manager
 * Governed versioned localStorage record: mne-ui-preferences-v1
 * Architectural Rule: Presentation preferences ONLY.
 * Validation, authorization, and policy remain 100% server-side.
 */

const PREFS_KEY = 'mne-ui-preferences-v1';

export const CANONICAL_THEMES = Object.freeze(['system', 'dark', 'light']);
export const CANONICAL_ACCENTS = Object.freeze(['cyan', 'teal', 'blue', 'amber']);
export const CANONICAL_DENSITIES = Object.freeze(['comfortable', 'compact']);
export const CANONICAL_FONT_SIZES = Object.freeze(['sm', 'md', 'lg']);
export const CANONICAL_MOTIONS = Object.freeze(['system', 'reduce', 'no-preference']);
export const CANONICAL_SORTS = Object.freeze(['updated_desc', 'created_desc', 'alpha']);
export const CANONICAL_ENGINES = Object.freeze(['', 'codex', 'opencode', 'antigravity']);

export const DEFAULT_PREFS = Object.freeze({
  version: 1,
  theme: 'dark', // 'system' | 'dark' | 'light'
  accent: 'cyan', // 'cyan' | 'teal' | 'blue' | 'amber'
  density: 'comfortable', // 'comfortable' | 'compact'
  fontSize: 'md', // 'sm' | 'md' | 'lg'
  reducedMotion: 'system', // 'system' | 'reduce' | 'no-preference'
  codeWrap: false,
  enterToSend: true, // Enter sends, Shift+Enter newline
  showTimestamps: true,
  autoOpenEvidence: false,
  restoreLastConversation: true,
  conversationsSort: 'updated_desc', // 'updated_desc' | 'created_desc' | 'alpha'
  showArchived: false,
  sidebarWidth: 280, // integer 240..600
  sidebarEnlarged: false,
  defaultEngine: '', // '' | 'codex' | 'opencode' | 'antigravity'
  defaultModel: '', // string
});

export function normalizePreferences(raw) {
  if (!raw || typeof raw !== 'object') {
    return { ...DEFAULT_PREFS };
  }

  let theme = raw.theme;
  if (!CANONICAL_THEMES.includes(theme)) theme = DEFAULT_PREFS.theme;

  let accent = raw.accent;
  if (accent === 'indigo') accent = 'blue';
  if (!CANONICAL_ACCENTS.includes(accent)) accent = DEFAULT_PREFS.accent;

  let density = raw.density;
  if (!CANONICAL_DENSITIES.includes(density)) density = DEFAULT_PREFS.density;

  let fontSize = raw.fontSize;
  if (fontSize === 'normal') fontSize = 'md';
  if (fontSize === 'large') fontSize = 'lg';
  if (!CANONICAL_FONT_SIZES.includes(fontSize)) fontSize = DEFAULT_PREFS.fontSize;

  let reducedMotion = raw.reducedMotion;
  if (reducedMotion === 'default') reducedMotion = 'no-preference';
  if (reducedMotion === 'reduced') reducedMotion = 'reduce';
  if (!CANONICAL_MOTIONS.includes(reducedMotion)) reducedMotion = DEFAULT_PREFS.reducedMotion;

  let conversationsSort = raw.conversationsSort;
  if (!CANONICAL_SORTS.includes(conversationsSort)) conversationsSort = DEFAULT_PREFS.conversationsSort;

  let sidebarWidth = parseInt(raw.sidebarWidth, 10);
  if (isNaN(sidebarWidth) || sidebarWidth < 240 || sidebarWidth > 600) {
    if (raw.sidebarEnlarged) {
      sidebarWidth = 440;
    } else {
      sidebarWidth = DEFAULT_PREFS.sidebarWidth;
    }
  }

  let defaultEngine = typeof raw.defaultEngine === 'string' ? raw.defaultEngine.trim().slice(0, 64) : '';

  let defaultModel = typeof raw.defaultModel === 'string' ? raw.defaultModel.trim().slice(0, 512) : '';

  return {
    version: 1,
    theme,
    accent,
    density,
    fontSize,
    reducedMotion,
    codeWrap: Boolean(raw.codeWrap),
    enterToSend: raw.enterToSend !== false,
    showTimestamps: raw.showTimestamps !== false,
    autoOpenEvidence: Boolean(raw.autoOpenEvidence),
    restoreLastConversation: raw.restoreLastConversation !== false,
    conversationsSort,
    showArchived: Boolean(raw.showArchived),
    sidebarWidth,
    sidebarEnlarged: sidebarWidth >= 440,
    defaultEngine,
    defaultModel,
  };
}

export function loadPreferences() {
  try {
    const raw = localStorage.getItem(PREFS_KEY);
    if (!raw) return { ...DEFAULT_PREFS };
    const parsed = JSON.parse(raw);
    return normalizePreferences(parsed);
  } catch (_) {
    return { ...DEFAULT_PREFS };
  }
}

export function savePreferences(patch) {
  try {
    const current = loadPreferences();
    const merged = { ...current, ...(patch && typeof patch === 'object' ? patch : {}) };
    const normalized = normalizePreferences(merged);
    localStorage.setItem(PREFS_KEY, JSON.stringify(normalized));
    applyPreferences(normalized);
    document.dispatchEvent(new CustomEvent('preferences-changed', { detail: normalized }));
    return normalized;
  } catch (e) {
    console.warn('Could not save preferences:', e);
    return loadPreferences();
  }
}

export function applyPreferences(prefs = loadPreferences()) {
  const root = document.documentElement;

  // Theme resolution
  let effectiveTheme = prefs.theme;
  if (effectiveTheme === 'system') {
    effectiveTheme = window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
  }
  root.setAttribute('data-theme', effectiveTheme);
  root.setAttribute('data-accent', prefs.accent);
  root.setAttribute('data-density', prefs.density);
  root.setAttribute('data-font-size', prefs.fontSize);
  root.setAttribute('data-motion', prefs.reducedMotion);

  root.setAttribute('data-code-wrap', String(Boolean(prefs.codeWrap)));
  root.classList.toggle('show-timestamps', Boolean(prefs.showTimestamps));

  const sidebarW = prefs.sidebarWidth || 280;
  root.style.setProperty('--sidebar-width', `${sidebarW}px`);
  root.classList.toggle('sidebar-enlarged', sidebarW >= 440);
}

// Listen for system theme changes if theme is set to system
window.matchMedia('(prefers-color-scheme: light)').addEventListener('change', () => {
  const prefs = loadPreferences();
  if (prefs.theme === 'system') {
    applyPreferences(prefs);
  }
});

// Initial application on script load
applyPreferences();

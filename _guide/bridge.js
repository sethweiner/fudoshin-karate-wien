/**
 * TOKEN BRIDGE — shared nervous system between the design guide and the live site.
 *
 * Both pages include this script. It:
 * 1. Reads token overrides from localStorage on load
 * 2. Applies them as :root CSS custom properties
 * 3. Listens for `storage` events — when the guide changes a token,
 *    the site tab receives it instantly (cross-tab, no refresh)
 * 4. Provides an API for the guide to set/get/log tokens
 * 5. Maintains a session log of all changes
 *
 * Usage:
 *   <script src="_guide/bridge.js"></script>          (from site pages)
 *   <script src="bridge.js"></script>                 (from guide)
 */

(function () {
  'use strict';

  const STORAGE_KEY = 'fudoshin-token-overrides';
  const LOG_KEY     = 'fudoshin-session-log';
  const THEME_KEY   = 'fudoshin-theme';

  // ── Read overrides from localStorage ──
  function getOverrides() {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEY)) || {};
    } catch { return {}; }
  }

  // ── Write overrides to localStorage ──
  function setOverrides(obj) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(obj));
  }

  // ── Apply all overrides to :root ──
  function applyAll() {
    const overrides = getOverrides();
    const root = document.documentElement;
    Object.entries(overrides).forEach(([prop, val]) => {
      root.style.setProperty(prop, val);
    });
  }

  // ── Set a single token ──
  function setToken(prop, value) {
    const overrides = getOverrides();
    overrides[prop] = value;
    setOverrides(overrides);
    document.documentElement.style.setProperty(prop, value);
    logChange(prop, value);
  }

  // ── Remove a single override (revert to CSS default) ──
  function clearToken(prop) {
    const overrides = getOverrides();
    delete overrides[prop];
    setOverrides(overrides);
    document.documentElement.style.removeProperty(prop);
    logChange(prop, '(reset)');
  }

  // ── Clear all overrides ──
  function clearAll() {
    localStorage.removeItem(STORAGE_KEY);
    const root = document.documentElement;
    const overrides = getOverrides();
    Object.keys(overrides).forEach(prop => root.style.removeProperty(prop));
    logChange('ALL', '(reset)');
  }

  // ── Session log ──
  function getLog() {
    try {
      return JSON.parse(localStorage.getItem(LOG_KEY)) || [];
    } catch { return []; }
  }

  function logChange(prop, value) {
    const log = getLog();
    log.push({
      time: new Date().toISOString().slice(11, 19),
      prop,
      value,
    });
    // Keep last 200 entries
    if (log.length > 200) log.splice(0, log.length - 200);
    localStorage.setItem(LOG_KEY, JSON.stringify(log));
    // Dispatch custom event for the guide's log UI
    window.dispatchEvent(new CustomEvent('bridge-log', { detail: { prop, value } }));
  }

  function clearLog() {
    localStorage.removeItem(LOG_KEY);
  }

  function getLogFormatted() {
    const log = getLog();
    if (!log.length) return '(no changes logged)';
    const lines = log.map(e => `${e.time}  ${e.prop}: ${e.value}`);
    return `## Token Adjustments — ${new Date().toISOString().slice(0, 10)}\n\`\`\`\n${lines.join('\n')}\n\`\`\``;
  }

  // ── Cross-tab sync via storage event ──
  window.addEventListener('storage', e => {
    if (e.key === STORAGE_KEY) {
      applyAll();
      window.dispatchEvent(new CustomEvent('bridge-sync'));
    }
    if (e.key === THEME_KEY) {
      document.documentElement.setAttribute('data-theme', e.newValue);
      window.dispatchEvent(new CustomEvent('bridge-theme', { detail: e.newValue }));
    }
  });

  // ── Theme sync ──
  function syncTheme(theme) {
    localStorage.setItem(THEME_KEY, theme);
    document.documentElement.setAttribute('data-theme', theme);
  }

  // ── CHECKPOINT SYSTEM — undo/redo/named snapshots ──
  const CHECKPOINTS_KEY = 'fudoshin-checkpoints';
  const CURSOR_KEY      = 'fudoshin-checkpoint-cursor';

  function getCheckpoints() {
    try { return JSON.parse(localStorage.getItem(CHECKPOINTS_KEY)) || []; }
    catch { return []; }
  }

  function getCursor() {
    const c = parseInt(localStorage.getItem(CURSOR_KEY), 10);
    return isNaN(c) ? -1 : c;
  }

  function saveCheckpoint(name) {
    const cps = getCheckpoints();
    let cursor = getCursor();

    // If we're not at the end, truncate future (fork)
    if (cursor >= 0 && cursor < cps.length - 1) {
      cps.splice(cursor + 1);
    }

    cps.push({
      id: Date.now(),
      name: name || null,
      time: new Date().toISOString().slice(0, 19).replace('T', ' '),
      overrides: { ...getOverrides() },
      theme: document.documentElement.getAttribute('data-theme') || 'dark',
    });

    // Keep max 50
    if (cps.length > 50) cps.splice(0, cps.length - 50);

    localStorage.setItem(CHECKPOINTS_KEY, JSON.stringify(cps));
    localStorage.setItem(CURSOR_KEY, String(cps.length - 1));

    window.dispatchEvent(new CustomEvent('bridge-checkpoint', { detail: { action: 'save' } }));
    return cps.length - 1;
  }

  function restoreCheckpoint(index) {
    const cps = getCheckpoints();
    if (index < 0 || index >= cps.length) return false;

    const cp = cps[index];

    // Clear current overrides
    const current = getOverrides();
    const root = document.documentElement;
    Object.keys(current).forEach(prop => root.style.removeProperty(prop));

    // Apply checkpoint overrides
    setOverrides(cp.overrides);
    Object.entries(cp.overrides).forEach(([prop, val]) => {
      root.style.setProperty(prop, val);
    });

    // Restore theme
    root.setAttribute('data-theme', cp.theme);
    localStorage.setItem(THEME_KEY, cp.theme);

    localStorage.setItem(CURSOR_KEY, String(index));
    logChange('RESTORE', cp.name || `checkpoint #${index}`);
    window.dispatchEvent(new CustomEvent('bridge-checkpoint', { detail: { action: 'restore', index } }));
    return true;
  }

  function undo() {
    const cursor = getCursor();
    if (cursor > 0) return restoreCheckpoint(cursor - 1);
    return false;
  }

  function redo() {
    const cursor = getCursor();
    const cps = getCheckpoints();
    if (cursor < cps.length - 1) return restoreCheckpoint(cursor + 1);
    return false;
  }

  function nameCheckpoint(index, name) {
    const cps = getCheckpoints();
    if (cps[index]) {
      cps[index].name = name;
      localStorage.setItem(CHECKPOINTS_KEY, JSON.stringify(cps));
      window.dispatchEvent(new CustomEvent('bridge-checkpoint', { detail: { action: 'rename' } }));
    }
  }

  function clearCheckpoints() {
    localStorage.removeItem(CHECKPOINTS_KEY);
    localStorage.removeItem(CURSOR_KEY);
  }

  // ── Apply on load ──
  applyAll();

  // ── Expose API ──
  window.tokenBridge = {
    // Token operations
    set: setToken,
    clear: clearToken,
    clearAll,
    getOverrides,
    applyAll,

    // Log
    getLog,
    getLogFormatted,
    clearLog,

    // Theme
    syncTheme,

    // Checkpoints (undo/redo/snapshots)
    save: saveCheckpoint,
    restore: restoreCheckpoint,
    undo,
    redo,
    getCheckpoints,
    getCursor,
    nameCheckpoint,
    clearCheckpoints,
  };
})();

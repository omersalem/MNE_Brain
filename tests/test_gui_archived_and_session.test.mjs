import test from 'node:test';
import assert from 'node:assert/strict';
import { setupMockDOM, MockElement } from './gui_dom_stub.mjs';

test('Task 7 & 8: Archived thread lock and session-expiry recovery', async (t) => {
  const { root, doc, win, storage } = setupMockDOM();

  // Setup DOM elements for auth, composer, threads
  const loginGate = new MockElement('div');
  loginGate.id = 'login-gate';
  loginGate.hidden = true;
  const loginForm = new MockElement('form');
  loginForm.id = 'owner-login-form';
  const loginStatus = new MockElement('div');
  loginStatus.id = 'login-status';
  const usernameInput = new MockElement('input');
  usernameInput.id = 'owner-username';
  const passwordInput = new MockElement('input');
  passwordInput.id = 'owner-password';
  const loginSubmit = new MockElement('button');
  loginSubmit.setAttribute('type', 'submit');
  loginForm.append(usernameInput, passwordInput, loginSubmit);
  loginGate.append(loginForm, loginStatus);

  const logoutBtn = new MockElement('button');
  logoutBtn.id = 'logout-button';

  const composer = new MockElement('form');
  composer.id = 'composer';
  const composerInput = new MockElement('textarea');
  composerInput.id = 'composer-input';
  const sendTurnBtn = new MockElement('button');
  sendTurnBtn.id = 'send-turn';
  sendTurnBtn.setAttribute('type', 'submit');
  const attachBtn = new MockElement('button');
  attachBtn.id = 'attach-file-btn';
  const turnStatus = new MockElement('span');
  turnStatus.id = 'turn-status';
  const archivedBanner = new MockElement('div');
  archivedBanner.id = 'composer-archived-banner';
  archivedBanner.hidden = true;
  const unarchiveBtn = new MockElement('button');
  unarchiveBtn.id = 'composer-unarchive-btn';
  archivedBanner.append(unarchiveBtn);

  const threadList = new MockElement('div');
  threadList.id = 'thread-list';

  const modelPickerBtn = new MockElement('button');
  modelPickerBtn.id = 'model-picker-btn';
  modelPickerBtn.setAttribute('aria-expanded', 'true');
  const modelPickerDropdown = new MockElement('div');
  modelPickerDropdown.id = 'model-picker-dropdown';

  const openDialog = new MockElement('dialog');
  openDialog.setAttribute('open', '');

  const providerSelect = new MockElement('select');
  providerSelect.id = 'provider-select';
  const modelSelect = new MockElement('select');
  modelSelect.id = 'model-select';

  root.append(
    loginGate, logoutBtn, composer, composerInput, sendTurnBtn, attachBtn,
    turnStatus, archivedBanner, threadList, modelPickerBtn, modelPickerDropdown,
    openDialog, providerSelect, modelSelect
  );

  const apiModule = await import('../gui/scripts/api.js');
  const prefsModule = await import('../gui/scripts/preferences.js');
  const providersModule = await import('../gui/scripts/providers.js');
  const threadsModule = await import('../gui/scripts/threads.js');
  const authModule = await import('../gui/scripts/auth.js');

  globalThis.__getAppState = () => apiModule.appState();
  globalThis.__mockMutate = async (path, body) => {
    if (typeof apiModule.appState()._mockMutate === 'function') {
      return await apiModule.appState()._mockMutate(path, body);
    }
    return {};
  };

  await t.test('Task 7: Selecting an archived thread locks composer and displays archived status', async () => {
    await new Promise(r => setTimeout(r, 25));
    const archivedThread = {
      thread_id: 'thr_archived_01',
      title: 'Past Investigation',
      status: 'ARCHIVED',
      engine_id: 'codex',
      model_id: 'gpt-4o',
      turn_ids: ['trn_01'],
      turns: [{ turn_id: 'trn_01', status: 'COMPLETED' }]
    };
    apiModule.appState().threads = [archivedThread];

    await threadsModule.selectThread(archivedThread.thread_id);

    assert.strictEqual(composerInput.disabled, true, 'Composer input must be disabled on archived thread');
    assert.strictEqual(sendTurnBtn.disabled, true, 'Send button must be disabled on archived thread');
    assert.strictEqual(attachBtn.disabled, true, 'Attach button must be disabled on archived thread');
    assert.ok(turnStatus.textContent.includes('Archived') || !archivedBanner.hidden, 'Archived status must be shown');
  });

  await t.test('Task 7: Selecting an active thread restores composer controls', async () => {
    const activeThread = {
      thread_id: 'thr_active_02',
      title: 'Current Work',
      status: 'ACTIVE',
      engine_id: 'codex',
      model_id: 'gpt-4o',
      turn_ids: []
    };
    apiModule.appState().threads = [activeThread];

    await threadsModule.selectThread(activeThread.thread_id);

    assert.strictEqual(composerInput.disabled, false, 'Composer input must be enabled on active thread');
    assert.strictEqual(sendTurnBtn.disabled, false, 'Send button must be enabled on active thread');
    assert.strictEqual(attachBtn.disabled, false, 'Attach button must be enabled on active thread');
    assert.strictEqual(archivedBanner.hidden, true, 'Archived banner must be hidden');
  });

  await t.test('Task 7: Archiving current thread switches conversation when archived threads are hidden', async () => {
    prefsModule.savePreferences({ showArchived: false });
    const th1 = { thread_id: 'thr_to_archive', title: 'Th1', status: 'ACTIVE', turn_ids: [] };
    const th2 = { thread_id: 'thr_remaining_active', title: 'Th2', status: 'ACTIVE', turn_ids: [] };
    apiModule.appState().threads = [th1, th2];
    apiModule.appState().currentThread = th1;

    apiModule.appState()._mockMutate = async (path) => {
      if (path.includes('/archive')) {
        th1.status = 'ARCHIVED';
        return { ...th1, status: 'ARCHIVED' };
      }
      return {};
    };

    // Trigger archive on current thread
    await threadsModule.archiveThreadAction(th1);

    assert.strictEqual(apiModule.appState().currentThread?.thread_id, th2.thread_id, 'Must switch to next active thread when current is archived and hidden');
  });

  await t.test('Task 8: owner-auth-required closes dialogs, closes model picker, sets aria-expanded="false" on #model-picker-btn, and preserves draft', () => {
    openDialog.setAttribute('open', '');
    modelPickerBtn.setAttribute('aria-expanded', 'true');
    composerInput.value = 'Unsent critical question regarding F5 certificates';

    doc.dispatchEvent(new CustomEvent('owner-auth-required', { detail: { session_expired: true } }));

    assert.strictEqual(openDialog.hasAttribute('open'), false, 'All open dialogs must be closed on session expiry');
    assert.strictEqual(modelPickerBtn.getAttribute('aria-expanded'), 'false', '#model-picker-btn aria-expanded must be false');
    assert.strictEqual(loginGate.hidden, false, 'Login gate must be visible');
    assert.strictEqual(authModule.getPreservedDraft(), 'Unsent critical question regarding F5 certificates', 'Draft must be preserved');
  });

  await t.test('Task 8: owner-authenticated rehydration is idempotent and restores preserved draft', async () => {
    composerInput.value = '';
    let rehydrateCalls = 0;

    // Dispatch owner-authenticated twice concurrently
    await Promise.all([
      authModule.rehydrateSession(),
      authModule.rehydrateSession()
    ]);

    assert.strictEqual(composerInput.value, 'Unsent critical question regarding F5 certificates', 'Preserved draft must be restored');
  });
});

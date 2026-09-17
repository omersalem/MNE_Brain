import test from 'node:test';
import assert from 'node:assert/strict';
import { setupMockDOM, MockElement } from './gui_dom_stub.mjs';

test('Task 1, 2, 3: Engine selection, repinning, and fallback behavior', async (t) => {
  const { root, doc, win, storage } = setupMockDOM();

  // Populate DOM elements required by threads.js and providers.js
  const threadList = new MockElement('div');
  threadList.id = 'thread-list';
  const composerInput = new MockElement('textarea');
  composerInput.id = 'composer-input';
  const provSelect = new MockElement('select');
  provSelect.id = 'provider-select';
  const modSelect = new MockElement('select');
  modSelect.id = 'model-select';
  const provStatus = new MockElement('div');
  provStatus.id = 'provider-status';
  const statusEl = new MockElement('div');
  statusEl.id = 'status';

  // Settings elements
  const defaultEngineSelect = new MockElement('select');
  defaultEngineSelect.id = 'pref-default-engine-select';
  const defaultModelSelect = new MockElement('select');
  defaultModelSelect.id = 'pref-default-model-select';
  const defaultEngineWarning = new MockElement('div');
  defaultEngineWarning.id = 'pref-default-engine-warning';
  const enginePill = new MockElement('span');
  enginePill.className = 'warning-pill';
  defaultEngineWarning.append(enginePill);

  const defaultModelWarning = new MockElement('div');
  defaultModelWarning.id = 'pref-default-model-warning';
  const modelPill = new MockElement('span');
  modelPill.className = 'warning-pill';
  defaultModelWarning.append(modelPill);

  root.append(
    threadList, composerInput, provSelect, modSelect, provStatus, statusEl,
    defaultEngineSelect, defaultModelSelect, defaultEngineWarning, defaultModelWarning
  );

  const apiModule = await import('../gui/scripts/api.js');
  const prefsModule = await import('../gui/scripts/preferences.js');
  const providersModule = await import('../gui/scripts/providers.js');
  const threadsModule = await import('../gui/scripts/threads.js');

  globalThis.__getAppState = () => apiModule.appState();
  globalThis.__mockMutate = async (path, body) => {
    if (typeof apiModule.appState()._mockMutate === 'function') {
      return await apiModule.appState()._mockMutate(path, body);
    }
    return {};
  };

  const sampleEngines = [
    {
      engine_id: 'codex',
      label: 'Codex App Server',
      status: 'READY',
      default_model: 'codex-account-default',
      models: [{ id: 'codex-account-default', label: 'Default' }, { id: 'gpt-4o', label: 'GPT-4o' }]
    },
    {
      engine_id: 'antigravity',
      label: 'Antigravity CLI',
      status: 'READY',
      default_model: 'gemini-3.8-flash-high',
      models: [{ id: 'gemini-3.8-flash-high', label: 'Gemini 3.8 Flash' }]
    },
    {
      engine_id: 'opencode',
      label: 'OpenCode',
      status: 'AUTHENTICATION_REQUIRED',
      default_model: 'select-model',
      models: []
    }
  ];

  await t.test('Task 1: No current conversation and no preference creates conversation with server default', async () => {
    storage.clear();
    apiModule.appState().currentThread = null;
    apiModule.appState().threads = [];
    apiModule.appState().engines = sampleEngines;

    let createdPayload = null;
    const origMutate = apiModule.mutateJSON;
    // Mock mutateJSON for thread creation
    apiModule.appState()._mockMutate = async (path, body) => {
      if (path === '/api/v2/threads') {
        createdPayload = body;
        const newTh = {
          thread_id: 'thr_new_default_01',
          title: body.title,
          engine_id: body.engine_id,
          model_id: body.model_id,
          status: 'ACTIVE',
          turn_ids: []
        };
        apiModule.appState().threads = [newTh];
        return newTh;
      }
      return {};
    };

    // newThread should succeed without throwing
    await assert.doesNotReject(async () => {
      await threadsModule.newThread();
    });

    assert.ok(createdPayload, 'Thread creation API must be called');
    assert.strictEqual(createdPayload.engine_id, 'codex');
    assert.strictEqual(createdPayload.model_id, 'codex-account-default');
  });

  await t.test('Task 1: No current conversation with valid preferred engine/model creates directly without repin', async () => {
    storage.clear();
    prefsModule.savePreferences({ defaultEngine: 'antigravity', defaultModel: 'gemini-3.8-flash-high' });
    apiModule.appState().currentThread = null;
    apiModule.appState().threads = [];
    apiModule.appState().engines = sampleEngines;

    let createdPayload = null;
    let repinCalled = false;
    apiModule.appState()._mockMutate = async (path, body) => {
      if (path === '/api/v2/threads') {
        createdPayload = body;
        const newTh = {
          thread_id: 'thr_new_pref_02',
          title: body.title,
          engine_id: body.engine_id,
          model_id: body.model_id,
          status: 'ACTIVE',
          turn_ids: []
        };
        apiModule.appState().threads = [newTh];
        return newTh;
      }
      if (path.includes('/engine')) {
        repinCalled = true;
      }
      return {};
    };

    await threadsModule.newThread();
    assert.ok(createdPayload, 'Thread must be created');
    assert.strictEqual(createdPayload.engine_id, 'antigravity');
    assert.strictEqual(createdPayload.model_id, 'gemini-3.8-flash-high');
    assert.strictEqual(repinCalled, false, 'Nonexistent conversation must NOT be repinned');
  });

  await t.test('Task 1: Repeated concurrent initialization creates at most one conversation', async () => {
    storage.clear();
    apiModule.appState().currentThread = null;
    apiModule.appState().threads = [];
    apiModule.appState().engines = sampleEngines;

    let createCount = 0;
    apiModule.appState()._mockMutate = async (path, body) => {
      if (path === '/api/v2/threads') {
        createCount++;
        await new Promise(res => setTimeout(res, 20));
        const newTh = {
          thread_id: `thr_concurrent_${createCount}`,
          title: body.title,
          engine_id: body.engine_id,
          model_id: body.model_id,
          status: 'ACTIVE',
          turn_ids: []
        };
        apiModule.appState().threads.push(newTh);
        return newTh;
      }
      return {};
    };

    // Run two concurrent newThread calls
    await Promise.all([
      threadsModule.newThread(),
      threadsModule.newThread()
    ]);

    assert.strictEqual(createCount, 1, 'Exactly one thread must be created during concurrent initialization');
  });

  await t.test('Task 2: Same engine, different valid model repins empty conversation', async () => {
    storage.clear();
    prefsModule.savePreferences({ defaultEngine: 'codex', defaultModel: 'gpt-4o' });
    apiModule.appState().engines = sampleEngines;

    const existingEmpty = {
      thread_id: 'thr_empty_codex',
      title: 'Conversation 1',
      engine_id: 'codex',
      model_id: 'codex-account-default',
      status: 'ACTIVE',
      turn_ids: []
    };
    apiModule.appState().currentThread = existingEmpty;
    apiModule.appState().threads = [existingEmpty];

    let repinPayload = null;
    apiModule.appState()._mockMutate = async (path, body) => {
      if (path.includes('/engine')) {
        repinPayload = body;
        return { ...existingEmpty, ...body };
      }
      return {};
    };

    await threadsModule.newThread();
    assert.ok(repinPayload, 'Repin must occur when model differs even if engine is the same');
    assert.strictEqual(repinPayload.engine_id, 'codex');
    assert.strictEqual(repinPayload.model_id, 'gpt-4o');
  });

  await t.test('Task 2: Conversation with history is NEVER repinned', async () => {
    storage.clear();
    prefsModule.savePreferences({ defaultEngine: 'antigravity', defaultModel: 'gemini-3.8-flash-high' });
    apiModule.appState().engines = sampleEngines;

    const existingWithTurns = {
      thread_id: 'thr_active_turns',
      title: 'Investigation',
      engine_id: 'codex',
      model_id: 'codex-account-default',
      status: 'ACTIVE',
      turn_ids: ['trn_001']
    };
    apiModule.appState().currentThread = existingWithTurns;
    apiModule.appState().threads = [existingWithTurns];

    let repinCalled = false;
    let createCalled = false;
    apiModule.appState()._mockMutate = async (path, body) => {
      if (path.includes('/engine')) {
        repinCalled = true;
      }
      if (path === '/api/v2/threads') {
        createCalled = true;
        const newTh = { thread_id: 'thr_brand_new', ...body, turn_ids: [] };
        apiModule.appState().threads.push(newTh);
        return newTh;
      }
      return {};
    };

    await threadsModule.newThread();
    assert.strictEqual(repinCalled, false, 'Conversation with turns must never be repinned');
    assert.strictEqual(createCalled, true, 'New conversation must be created instead');
  });

  await t.test('Task 3: Stale preferred engine displays warning and falls back to server default', () => {
    storage.clear();
    prefsModule.savePreferences({ defaultEngine: 'nonexistent_engine' });
    apiModule.appState().engines = sampleEngines;

    providersModule.refreshDefaultEngineControls();

    assert.strictEqual(defaultEngineWarning.hidden, false, 'Engine warning must be visible for stale engine');
    assert.ok(enginePill.textContent.includes('not available in catalog'), 'Warning must state engine is not available');
    assert.strictEqual(defaultEngineSelect.value, 'nonexistent_engine', 'Stale preference must be preserved in selector');
  });

  await t.test('Task 3: Engine present but not ready displays readiness warning and falls back', () => {
    storage.clear();
    prefsModule.savePreferences({ defaultEngine: 'opencode' }); // opencode status is AUTHENTICATION_REQUIRED
    apiModule.appState().engines = sampleEngines;

    providersModule.refreshDefaultEngineControls();

    assert.strictEqual(defaultEngineWarning.hidden, false, 'Engine warning must be visible when engine not ready');
    assert.ok(enginePill.textContent.includes('not ready') || enginePill.textContent.includes('AUTHENTICATION_REQUIRED'));
  });

  await t.test('Task 3: Ready engine clears warning automatically', () => {
    storage.clear();
    prefsModule.savePreferences({ defaultEngine: 'codex' }); // codex is READY
    apiModule.appState().engines = sampleEngines;

    providersModule.refreshDefaultEngineControls();

    assert.strictEqual(defaultEngineWarning.hidden, true, 'Engine warning must be hidden when engine is READY');
  });
});

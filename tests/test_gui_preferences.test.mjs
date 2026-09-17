import test from 'node:test';
import assert from 'node:assert/strict';
import { setupMockDOM } from './gui_dom_stub.mjs';

test('Task 4 & 5: Preferences and sidebar width behavioral tests', async (t) => {
  const { root, storage } = setupMockDOM();
  const prefsModule = await import('../gui/scripts/preferences.js');

  await t.test('sidebarWidth normalization handles presets and boundaries', () => {
    // Presets
    for (const preset of [280, 360, 440, 520]) {
      const res = prefsModule.normalizePreferences({ sidebarWidth: preset });
      assert.strictEqual(res.sidebarWidth, preset, `Preset ${preset} should be preserved`);
    }

    // Boundaries 240 and 600
    assert.strictEqual(prefsModule.normalizePreferences({ sidebarWidth: 240 }).sidebarWidth, 240);
    assert.strictEqual(prefsModule.normalizePreferences({ sidebarWidth: 600 }).sidebarWidth, 600);

    // Custom width 487px
    assert.strictEqual(prefsModule.normalizePreferences({ sidebarWidth: 487 }).sidebarWidth, 487);

    // Out of bounds: < 240 or > 600 should fallback to default (280)
    assert.strictEqual(prefsModule.normalizePreferences({ sidebarWidth: 100 }).sidebarWidth, 280);
    assert.strictEqual(prefsModule.normalizePreferences({ sidebarWidth: 999 }).sidebarWidth, 280);
    assert.strictEqual(prefsModule.normalizePreferences({ sidebarWidth: 'invalid' }).sidebarWidth, 280);
  });

  await t.test('legacy preference migration: sidebarEnlarged=true with sidebarWidth=520 preserves 520px', () => {
    // When saved width is 520px and sidebarEnlarged is true, width MUST be 520px
    const res = prefsModule.normalizePreferences({ sidebarEnlarged: true, sidebarWidth: 520 });
    assert.strictEqual(res.sidebarWidth, 520, 'Saved 520px width must not be overwritten by sidebarEnlarged=true');
  });

  await t.test('applyPreferences sets exact CSS width for custom 487px and 520px without forcing 440px', () => {
    // 520px
    prefsModule.applyPreferences({ ...prefsModule.DEFAULT_PREFS, sidebarWidth: 520, sidebarEnlarged: true });
    assert.strictEqual(root.style.getPropertyValue('--sidebar-width'), '520px', '520px must be applied to --sidebar-width even when sidebarEnlarged is true');

    // 487px
    prefsModule.applyPreferences({ ...prefsModule.DEFAULT_PREFS, sidebarWidth: 487, sidebarEnlarged: true });
    assert.strictEqual(root.style.getPropertyValue('--sidebar-width'), '487px', '487px must be applied to --sidebar-width');
  });

  await t.test('savePreferences and reload preserves exact 520px and 487px', () => {
    storage.clear();
    prefsModule.savePreferences({ sidebarWidth: 520 });
    const loaded520 = prefsModule.loadPreferences();
    assert.strictEqual(loaded520.sidebarWidth, 520);
    assert.strictEqual(root.style.getPropertyValue('--sidebar-width'), '520px');

    prefsModule.savePreferences({ sidebarWidth: 487 });
    const loaded487 = prefsModule.loadPreferences();
    assert.strictEqual(loaded487.sidebarWidth, 487);
    assert.strictEqual(root.style.getPropertyValue('--sidebar-width'), '487px');
  });

  await t.test('legacy migration: sidebarEnlarged=true with missing width migrates to 440px', () => {
    const res = prefsModule.normalizePreferences({ sidebarEnlarged: true });
    assert.strictEqual(res.sidebarWidth, 440, 'Missing width with sidebarEnlarged=true should migrate to 440px');
  });

  await t.test('Settings dropdown never shows a blank width and synchronizes custom values', async () => {
    const providersModule = await import('../gui/scripts/providers.js');
    const select = new (await import('./gui_dom_stub.mjs')).MockElement('select');
    for (const val of ['280', '360', '440', '520']) {
      const opt = new (await import('./gui_dom_stub.mjs')).MockElement('option');
      opt.value = val;
      opt.textContent = `${val}px`;
      select.append(opt);
    }

    // Preset 360
    providersModule.syncSidebarWidthSelect(select, 360);
    assert.strictEqual(select.value, '360');

    // Preset 520
    providersModule.syncSidebarWidthSelect(select, 520);
    assert.strictEqual(select.value, '520');

    // Custom 487
    providersModule.syncSidebarWidthSelect(select, 487);
    assert.strictEqual(select.value, '487');
    const customOpt = select.querySelector('option[data-custom="true"]');
    assert.ok(customOpt, 'Custom option must be created for 487px');
    assert.strictEqual(customOpt.textContent, 'Custom (487px)');

    // Switching back to 280 removes custom option
    providersModule.syncSidebarWidthSelect(select, 280);
    assert.strictEqual(select.value, '280');
    assert.strictEqual(select.querySelector('option[data-custom="true"]'), null);
  });

  await t.test('Task 5: codeWrap sets data-code-wrap="true" or "false" on documentElement', () => {
    prefsModule.applyPreferences({ ...prefsModule.DEFAULT_PREFS, codeWrap: false });
    assert.strictEqual(root.getAttribute('data-code-wrap'), 'false', 'Disabled codeWrap must set data-code-wrap="false"');

    prefsModule.applyPreferences({ ...prefsModule.DEFAULT_PREFS, codeWrap: true });
    assert.strictEqual(root.getAttribute('data-code-wrap'), 'true', 'Enabled codeWrap must set data-code-wrap="true"');
  });
});

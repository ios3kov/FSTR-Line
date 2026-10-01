import assert from 'node:assert/strict';
import { test } from 'node:test';
import { PanelController, projectionForState } from '../../dist/src/cep/panel-controller.js';
import { renderTrackView } from '../../dist/src/cep/track-view.js';
import { CEPAdapter } from '../../dist/src/host/cep/bridge.js';
import { HostResponseError } from '../../dist/src/host/protocol.js';
import { layer, snapshot } from '../../dist/tests/fixtures.js';

// Minimal DOM contract, not a Chromium/CEP visual or performance acceptance test.
class Element {
  constructor(tagName, ownerDocument) { Object.assign(this, { tagName, ownerDocument,
    children: [], dataset: {}, style: {}, textContent: '', className: '' }); }
  replaceChildren(...items) { this.children = items; }
  append(...items) { this.children.push(...items); }
}
const doc = { createElement: (name) => new Element(name, doc) };
const current = snapshot([layer(1, 1, 0, 48, { name: '<img src=x onerror=alert(1)>', selected: true })]);
const tracks = [{ trackIndex: 0, layerIds: [1] }];
const success = (data) => JSON.stringify({ protocolVersion: 1, ok: true, data });
const failure = (code) => JSON.stringify({ protocolVersion: 1, ok: false, error: { code, message: 'test' } });
const command = { type: 'moveLayers', commandVersion: 1, operationId: 'op-ui',
  guard: { compositionId: current.compositionId, revision: current.revision }, layerIds: [1], deltaFrames: 1 };

test('rendered last-known tracks survive an error and are visibly marked stale', () => {
  const output = doc.createElement('ol');
  renderTrackView(output, { status: 'ready', snapshot: current, tracks });
  assert.equal(output.children.length, 1); assert.equal(output.dataset.stale, 'false');
  renderTrackView(output, { status: 'error', message: 'host unavailable', snapshot: current, tracks });
  assert.equal(output.children.length, 1); assert.equal(output.dataset.stale, 'true');
  const clip = output.children[0].children[1].children[0];
  assert.equal(clip.textContent, current.layers[0].name); assert.equal(clip.tagName, 'span');
  assert.equal(clip.children.length, 0); assert.equal(clip.style.left, '0%'); assert.equal(clip.style.width, '20%');
  renderTrackView(output, { status: 'no-composition' }); assert.equal(output.children.length, 0);
});
test('negative and out-of-composition clips retain geometric proportions without minimum-width overlap', () => {
  const output = doc.createElement('ol');
  const input = snapshot([layer(1, 1, -60, 0), layer(2, 2, 0, 300)]);
  renderTrackView(output, { status: 'ready', snapshot: input, tracks: [{ trackIndex: 0, layerIds: [1, 2] }] });
  const clips = output.children[0].children[1].children;
  assert.equal(parseFloat(clips[0].style.left), 0);
  assert.ok(Math.abs(parseFloat(clips[0].style.width) - 100 / 6) < 1e-9);
  assert.equal(clips[1].style.left, clips[0].style.width);
});
test('controller preserves the projection through repeated failures, but clears it for no active comp', async () => {
  let result = current; const output = doc.createElement('ol');
  const controller = new PanelController({ readSnapshot: async () => {
    if (result instanceof Error) throw result; return result;
  } }, { render: (state) => renderTrackView(output, state) });
  await controller.refresh();
  for (let index = 0; index < 3; index++) {
    result = new Error('disconnected'); await controller.refresh();
    assert.equal(controller.getState().status, 'error');
    assert.equal(projectionForState(controller.getState()).snapshot, current);
    assert.equal(output.children.length, 1); assert.equal(output.dataset.stale, 'true');
  }
  result = new HostResponseError('NO_ACTIVE_COMP', 'closed'); await controller.refresh();
  assert.equal(output.children.length, 0); assert.equal(projectionForState(controller.getState()), undefined);
});
for (const mode of ['timeout', 'empty', 'invalid', 'wrong-operation', 'rollback-failed']) {
  test(`uncertain ${mode} command disables later writes even after a successful read`, async () => {
    const scripts = [];
    let late;
    const bridge = { evalScript(script, callback) {
      scripts.push(script);
      if (script === 'fstrLineHost.readSnapshot()') { callback(success(current)); return; }
      if (mode === 'timeout') { late = callback; return; }
      if (mode === 'empty') callback('');
      if (mode === 'invalid') callback('not JSON');
      if (mode === 'wrong-operation') callback(success({ operationId: 'other', changed: true, snapshot: current }));
      if (mode === 'rollback-failed') callback(failure('ROLLBACK_FAILED'));
    } };
    const adapter = new CEPAdapter(bridge, { timeoutMs: 5 });
    await assert.rejects(adapter.execute(command));
    if (mode === 'timeout') {
      await assert.rejects(adapter.readSnapshot(), /HOST_CALL_PENDING/);
      // Host completion permits reads; it cannot clear uncertain-write state.
      late(success({ operationId: 'op-ui', changed: true, snapshot: current }));
    }
    await adapter.readSnapshot();
    await assert.rejects(adapter.execute(command), /UNKNOWN_COMMAND_OUTCOME/);
    assert.equal(scripts.filter((script) => script.startsWith('fstrLineHost.executeCommand')).length, 1);
  });
}
test('known preflight rejection does not prohibit a later explicit valid command', async () => {
  let writes = 0;
  const adapter = new CEPAdapter({ evalScript(script, callback) {
    writes++; callback(writes === 1 ? failure('STALE_SNAPSHOT') : success({ operationId: 'op-ui', changed: true, snapshot: current }));
  } });
  await assert.rejects(adapter.execute(command), /STALE_SNAPSHOT/);
  assert.equal((await adapter.execute(command)).operationId, 'op-ui'); assert.equal(writes, 2);
});

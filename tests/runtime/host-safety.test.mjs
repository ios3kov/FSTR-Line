import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import { test } from 'node:test';

// Executes actual JSX. Setter coupling and faults are models, NOT real AE evidence.
const source = readFileSync(process.env.FSTR_HOST_SOURCE || new URL('../../src/host/cep/host.jsx', import.meta.url), 'utf8');
function layer(id, options = {}) {
  const values = { startTime: 0, inPoint: 2, outPoint: 10, enabled: true,
    solo: false, locked: false, audioEnabled: false, selected: false, ...options.values };
  const result = { id, index: id, name: `Layer ${id}`, label: 1, hasVideo: true, hasAudio: false, writes: [] };
  for (const key of Object.keys(values)) Object.defineProperty(result, key, {
    get() { return values[key]; },
    set(value) {
      result.writes.push([key, value]);
      if (options.reject?.(key, value, values)) throw Error(`Injected ${key} failure`);
      if (options.ignore?.(key, value, values)) return;
      if (key === 'startTime' && options.coupled) {
        const delta = value - values.startTime;
        values.inPoint += delta; values.outPoint += delta;
      }
      values[key] = value;
    },
  });
  return result;
}
class CompItem {
  constructor(layers, fps = 25) {
    this.id = 1; this.name = 'Fixture'; this.layers = layers; this.numLayers = layers.length;
    this.frameRate = fps; this.frameDuration = 1 / fps;
    this.duration = 500 * this.frameDuration; this.time = 0;
  }
  layer(index) { return this.layers[index - 1]; }
}
function host(layers, fps = 25) {
  const comp = new CompItem(layers, fps);
  const app = { project: { activeItem: comp }, version: 'SIMULATED, not AE', groups: 0, opened: 0,
    beginUndoGroup() { this.groups++; this.opened++; }, endUndoGroup() { this.groups--; } };
  const ctx = vm.createContext({ app, CompItem });
  vm.runInContext(source, ctx, { filename: 'src/host/cep/host.jsx' });
  return ctx;
}
function snapshot(ctx) {
  const reply = JSON.parse(ctx.fstrLineHost.readSnapshot());
  assert.equal(reply.ok, true, JSON.stringify(reply));
  return reply.data;
}
function command(ctx, overrides = {}) {
  const current = snapshot(ctx);
  return { type: 'moveLayers', commandVersion: 1, operationId: 'fixture-op',
    guard: { compositionId: current.compositionId, revision: current.revision },
    layerIds: [1], deltaFrames: 25, ...overrides };
}
function execute(ctx, cmd) { return JSON.parse(ctx.fstrLineHost.executeCommand(cmd)); }
function timing(target) { return [target.startTime, target.inPoint, target.outPoint]; }

for (const coupled of [false, true]) test(`move uses pre-captured absolute targets; coupled=${coupled}`, () => {
  const target = layer(1, { coupled }); const ctx = host([target]);
  const reply = execute(ctx, command(ctx));
  assert.equal(reply.ok, true); assert.deepEqual(timing(target), [1, 3, 11]);
  assert.equal(ctx.app.groups, 0); assert.equal(ctx.app.opened, 1);
});
for (const fps of [24000 / 1001, 24, 25, 30000 / 1001, 30, 50, 60000 / 1001, 60]) {
  test(`move/trim modeled frame roundtrip at ${fps} fps`, () => {
    const fd = 1 / fps;
    const target = layer(1, { coupled: true, values: { startTime: -20 * fd, inPoint: 10 * fd, outPoint: 150 * fd } });
    const ctx = host([target], fps);
    assert.equal(execute(ctx, command(ctx, { deltaFrames: 7 })).ok, true);
    let current = snapshot(ctx).layers[0];
    assert.deepEqual([current.startFrame, current.inFrame, current.outFrame], [-13, 17, 157]);
    assert.equal(execute(ctx, command(ctx, { type: 'trimLayerIn', layerId: 1, newInFrame: 18 })).ok, true);
    assert.equal(execute(ctx, command(ctx, { type: 'trimLayerOut', layerId: 1, newOutFrame: 156 })).ok, true);
    current = snapshot(ctx).layers[0]; assert.equal(current.inFrame, 18); assert.equal(current.outFrame, 156);
    assert.equal(ctx.app.groups, 0);
  });
}
test('rollback never writes unrelated locked layers', () => {
  const background = layer(1, { values: { locked: true }, reject: () => true });
  const first = layer(2, { coupled: true }); let failed = false;
  const second = layer(3, { reject: (field) => { if (field === 'startTime' && !failed) { failed = true; return true; } return false; } });
  const ctx = host([background, first, second]);
  const reply = execute(ctx, command(ctx, { layerIds: [2, 3] }));
  assert.equal(reply.ok, false); assert.deepEqual(timing(first), [0, 2, 10]);
  assert.deepEqual(timing(second), [0, 2, 10]); assert.deepEqual(background.writes, []);
  assert.equal(ctx.app.groups, 0);
});
test('failed restoration continues with other targets and disables later writes', () => {
  const first = layer(1);
  const second = layer(2, { reject: (field, value, current) =>
    (field === 'outPoint' && value === 11) || (field === 'startTime' && value === 0 && current.startTime !== 0) });
  const ctx = host([first, second]);
  const reply = execute(ctx, command(ctx, { layerIds: [1, 2] }));
  assert.equal(reply.ok, false); assert.equal(reply.error.code, 'ROLLBACK_FAILED');
  assert.deepEqual(timing(first), [0, 2, 10]); assert.equal(ctx.app.groups, 0);
  const count = first.writes.length;
  const next = execute(ctx, command(ctx));
  assert.equal(next.error.code, 'RECOVERY_REQUIRED'); assert.equal(first.writes.length, count);
});
test('same numeric IDs in another project cannot satisfy an old guard', () => {
  const original = layer(1); const ctx = host([original]); const pending = command(ctx);
  const replacement = layer(1); ctx.app.project = { activeItem: new CompItem([replacement]) };
  const reply = execute(ctx, pending);
  assert.equal(reply.ok, false); assert.equal(reply.error.code, 'STALE_SNAPSHOT');
  assert.deepEqual(replacement.writes, []); assert.deepEqual(original.writes, []);
});
test('replacement composition with matching IDs in the same project rejects stale command', () => {
  const ctx = host([layer(1)]); const pending = command(ctx); const replacement = layer(1);
  ctx.app.project.activeItem = new CompItem([replacement]);
  assert.equal(execute(ctx, pending).error.code, 'STALE_SNAPSHOT'); assert.deepEqual(replacement.writes, []);
});
test('revision covers selection, names, labels and playhead; unchanged reads remain stable', () => {
  const target = layer(1); const ctx = host([target]);
  let previous = snapshot(ctx).revision; assert.equal(snapshot(ctx).revision, previous);
  for (const change of [() => { target.selected = true; }, () => { target.name = 'new'; },
    () => { target.label = 2; }, () => { ctx.app.project.activeItem.time = 1; },
    () => { ctx.app.project.activeItem.name = 'new comp'; }]) {
    change(); const next = snapshot(ctx).revision; assert.notEqual(next, previous); previous = next;
  }
});
test('zero-delta move does not write or create an Undo group', () => {
  const target = layer(1); const ctx = host([target]);
  const reply = execute(ctx, command(ctx, { deltaFrames: 0 }));
  assert.equal(reply.ok, true); assert.equal(reply.data.changed, false);
  assert.deepEqual(target.writes, []); assert.equal(ctx.app.opened, 0);
});
test('all targets are preflighted before the first write', () => {
  const first = layer(1); const second = layer(2, { values: { locked: true } }); const ctx = host([first, second]);
  assert.equal(execute(ctx, command(ctx, { layerIds: [1, 2] })).error.code, 'LOCKED_LAYER');
  assert.deepEqual(first.writes, []); assert.equal(ctx.app.opened, 0);
});
test('trim rollback only touches the edited property', () => {
  const target = layer(1, { ignore: (field, value) => field === 'inPoint' && value === 3 }); const ctx = host([target]);
  const reply = execute(ctx, command(ctx, { type: 'trimLayerIn', layerId: 1, newInFrame: 75 }));
  assert.equal(reply.error.code, 'HOST_POSTCONDITION'); assert.deepEqual(timing(target), [0, 2, 10]);
  assert.ok(target.writes.every(([field]) => field === 'inPoint')); assert.equal(ctx.app.groups, 0);
});
test('failed Undo group opening leaves the project untouched', () => {
  const target = layer(1); const ctx = host([target]); ctx.app.beginUndoGroup = () => { throw Error('busy'); };
  assert.equal(execute(ctx, command(ctx)).ok, false); assert.deepEqual(target.writes, []); assert.equal(ctx.app.groups, 0);
});
test('failed Undo group closure is an uncertain outcome, not success', () => {
  const ctx = host([layer(1)]); ctx.app.endUndoGroup = () => { throw Error('close failed'); };
  assert.equal(execute(ctx, command(ctx)).error.code, 'RECOVERY_REQUIRED');
  assert.equal(execute(ctx, command(ctx)).error.code, 'RECOVERY_REQUIRED');
});
test('reject malformed operation ID, unsafe integer, string layer ID and nonboolean switch', () => {
  for (const override of [{ operationId: '' }, { deltaFrames: 9007199254740992 }, { layerIds: ['1'] },
    { type: 'setLayerSwitch', layerId: 1, layerSwitch: 'enabled', value: 'false' }]) {
    const target = layer(1); const ctx = host([target]); assert.equal(execute(ctx, command(ctx, override)).ok, false);
    assert.deepEqual(target.writes, []); assert.equal(ctx.app.opened, 0);
  }
});
test('unsupported subframe snapshot is explicit and never silently rounded', () => {
  const ctx = host([layer(1, { values: { inPoint: 2.02 } })]);
  const reply = JSON.parse(ctx.fstrLineHost.readSnapshot());
  assert.equal(reply.ok, false); assert.equal(reply.error.code, 'SUBFRAME_TIMING');
});

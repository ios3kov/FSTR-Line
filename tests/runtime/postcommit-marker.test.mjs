import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import fs from 'node:fs';

const source = fs.readFileSync(new URL('../../research/ae-notifications/FSTR-PostCommit-Marker.jsx', import.meta.url), 'utf8');

function run({ mutationError = false, beginError = false, endError = false } = {}) {
  let begins = 0, ends = 0, enabled = true;
  const lines = [];
  const layer = {
    get enabled() { return enabled; },
    set enabled(value) { if (mutationError) throw new Error('mutation failed'); enabled = value; }
  };
  function CompItem() { this.numLayers = 1; this.selectedLayers = [layer]; }
  function File() {
    this.path = '/fixture';
    this.open = () => true;
    this.read = () => '/fixture/marker.txt';
    this.writeln = line => lines.push(line);
    this.close = () => {};
  }
  let error;
  try {
    vm.runInNewContext(source, {
      File, CompItem, $: { fileName: '/fixture/marker.jsx' },
      app: {
        project: { activeItem: new CompItem() },
        beginUndoGroup() { begins++; if (beginError) throw new Error('begin failed'); },
        endUndoGroup() { ends++; if (endError) throw new Error('end failed'); }
      }
    });
  } catch (caught) { error = caught; }
  return { begins, ends, enabled, lines, error };
}

test('marker closes an opened Undo group after mutation error', () => {
  const result = run({ mutationError: true });
  assert.equal(result.ends, 1);
  assert.match(result.error.message, /mutation failed/);
  assert.equal(result.lines.length, 0);
});
test('marker never closes a group that failed to open', () => {
  const result = run({ beginError: true });
  assert.equal(result.ends, 0);
  assert.match(result.error.message, /begin failed/);
});
test('marker does not publish successful markers after closure failure', () => {
  const result = run({ endError: true });
  assert.equal(result.ends, 1);
  assert.match(result.error.message, /end failed/);
  assert.equal(result.lines.length, 0);
});
test('successful marker preserves operation and three marker order', () => {
  const result = run();
  assert.equal(result.error, undefined);
  assert.equal(result.ends, 1);
  assert.equal(result.enabled, false);
  assert.deepEqual(result.lines.map(line => line.split('|')[0]),
    ['before', 'after-mutation', 'after-end-undo']);
});

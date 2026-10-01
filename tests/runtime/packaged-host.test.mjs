import { readFile, mkdtemp, cp, writeFile, rm, symlink } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { execFileSync } from 'node:child_process';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { verifyCEP } from '../../scripts/verify-cep.mjs';

// Run after build:cep. Executes the exact generated payload, not just raw JSX.
test('packaged host works without global JSON and leaves unrelated globals untouched', async () => {
  const source = await readFile('dist/cep/host/host.jsx', 'utf8');
  class CompItem { constructor() { Object.assign(this, { id: 1, name: 'Empty', frameRate: 25,
    frameDuration: 0.04, duration: 4, time: 0, numLayers: 0 }); } }
  for (const externalJSON of [undefined, null, { sentinel: true }]) {
    const app = { project: { activeItem: new CompItem() }, version: 'SIMULATED' };
    const ctx = vm.createContext({ app, CompItem, JSON: externalJSON });
    vm.runInContext(source, ctx);
    assert.equal(ctx.JSON, externalJSON);
    const reply = JSON.parse(ctx.fstrLineHost.readSnapshot());
    assert.equal(reply.ok, true); assert.equal(reply.data.layers.length, 0);
    const diagnostic = JSON.parse(ctx.fstrLineHost.diagnostics());
    assert.equal(diagnostic.ok, true); assert.equal(diagnostic.data.writesDisabled, false);
    assert.equal(diagnostic.data.build.gitCommit, execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim());
  }
});
test('package verifier rejects edits, stale files, symlinks, path traversal and dirty identity', async () => {
  const directory = await mkdtemp(join(tmpdir(), 'fstr-package-test-'));
  const commit = execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim();
  try {
    const original = await verifyCEP('dist/cep', commit);
    for (const kind of ['edited', 'stale', 'symlink', 'traversal', 'dirty']) {
      const target = join(directory, kind); await cp('dist/cep', target, { recursive: true });
      if (kind === 'edited') await writeFile(join(target, 'host/host.jsx'), 'tampered');
      if (kind === 'stale') await writeFile(join(target, 'stale.js'), 'extra');
      if (kind === 'symlink') { await rm(join(target, 'host/host.jsx')); await symlink('/dev/null', join(target, 'host/host.jsx')); }
      if (kind === 'traversal' || kind === 'dirty') {
        const changed = structuredClone(original);
        if (kind === 'traversal') changed.artifacts['../outside'] = '0'.repeat(64); else changed.dirty = true;
        await writeFile(join(target, 'build-manifest.json'), JSON.stringify(changed));
      }
      await assert.rejects(verifyCEP(target, commit), undefined, kind);
    }
  } finally { await rm(directory, { recursive: true, force: true }); }
});

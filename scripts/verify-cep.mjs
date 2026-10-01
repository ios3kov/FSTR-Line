import { readdir, readFile, lstat } from 'node:fs/promises';
import { resolve, join } from 'node:path';
import { pathToFileURL } from 'node:url';
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import assert from 'node:assert/strict';

const expected = ['CSXS/manifest.xml', 'THIRD_PARTY_NOTICES.txt', 'client/CSInterface.js',
  'client/app.js', 'client/index.html', 'client/styles.css', 'host/host.jsx'].sort();
export async function verifyCEP(directory, commit) {
  assert.equal((await lstat(directory)).isSymbolicLink(), false, 'Package root cannot be a symlink');
  const manifest = JSON.parse(await readFile(join(directory, 'build-manifest.json'), 'utf8'));
  assert.equal(manifest.dirty, false, 'Dirty package is not a clean candidate');
  assert.equal(manifest.gitCommit, commit, 'Package is not from the expected commit');
  assert.match(commit, /^[a-f0-9]{40}$/);
  assert.equal(manifest.buildId, `fstr-cep-${commit.slice(0, 12)}`);
  assert.equal(manifest.artifactType, 'CEP-panel-directory');
  assert.deepEqual(Object.keys(manifest.artifacts).sort(), expected, 'Unexpected manifest file set');
  const found = [];
  async function walk(relative = '') {
    for (const entry of await readdir(join(directory, relative), { withFileTypes: true })) {
      const name = relative ? `${relative}/${entry.name}` : entry.name;
      assert.equal(entry.isSymbolicLink(), false, 'Symlinks are not allowed');
      if (entry.isDirectory()) await walk(name);
      else { assert.equal(entry.isFile(), true, 'Only regular payload files are allowed'); found.push(name); }
    }
  }
  await walk();
  assert.deepEqual(found.sort(), [...expected, 'build-manifest.json'].sort(), 'Missing or stale payload files');
  for (const name of expected) {
    const actual = createHash('sha256').update(await readFile(join(directory, name))).digest('hex');
    assert.equal(actual, manifest.artifacts[name], `Hash mismatch: ${name}`);
  }
  return manifest;
}
if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  const commit = execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim();
  const manifest = await verifyCEP(resolve('dist/cep'), commit);
  console.log(`PASS exact payload + SHA-256 + clean identity: ${manifest.buildId}; not an AE runtime PASS`);
}

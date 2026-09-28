import { mkdir, readFile, writeFile, copyFile, rm } from 'node:fs/promises';
import { build } from 'esbuild';
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';

const gitCommit = execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim();
const dirty = execFileSync('git', ['status', '--porcelain'], { encoding: 'utf8' }).trim().length > 0;
const identity = { buildId: `fstr-cep-${gitCommit.slice(0, 12)}${dirty ? '-dirty' : ''}`,
  gitCommit, dirty, version: JSON.parse(await readFile('package.json', 'utf8')).version };
await mkdir('cep/host', { recursive: true });
await build({ entryPoints: ['src/cep/client-entry.ts'], bundle: true, format: 'iife',
  platform: 'browser', target: ['chrome88'], outfile: 'cep/client/app.js',
  define: { FSTR_BUILD: JSON.stringify(identity) } });
// Private JSON implementation: neither depends on nor overwrites another panel's
// global JSON. Source and polyfill are embedded; installed package needs no include.
const host = `var fstrLineHost = (function () {\nvar FSTR_BUILD = ${JSON.stringify(identity)};\nvar JSON;\n${await readFile('vendor/json2.js', 'utf8')}\n${await readFile('src/host/cep/host.jsx', 'utf8')}\nreturn fstrLineHost;\n}());\n`;
await writeFile('cep/host/host.jsx', host);
const inputs = ['CSXS/manifest.xml', 'client/index.html', 'client/styles.css',
  'client/CSInterface.js', 'client/app.js', 'host/host.jsx'];
const artifacts = {};
for (const relative of inputs) artifacts[relative] = createHash('sha256').update(await readFile(`cep/${relative}`)).digest('hex');
const notices = `${await readFile('THIRD_PARTY_NOTICES.md', 'utf8')}\n\n${await readFile('vendor/README.md', 'utf8')}`;
artifacts['THIRD_PARTY_NOTICES.txt'] = createHash('sha256').update(notices).digest('hex');
const manifest = JSON.stringify({ ...identity, artifactType: 'CEP-panel-directory', artifacts }, null, 2) + '\n';
await writeFile('cep/build-manifest.json', manifest);
// Only this generated staging directory is replaced; cep source/user data are not removed.
await rm('dist/cep', { recursive: true, force: true });
for (const directory of ['CSXS', 'client', 'host']) await mkdir(`dist/cep/${directory}`, { recursive: true });
for (const relative of inputs) await copyFile(`cep/${relative}`, `dist/cep/${relative}`);
await writeFile('dist/cep/THIRD_PARTY_NOTICES.txt', notices);
await writeFile('dist/cep/build-manifest.json', manifest);
console.log(`Built ${identity.buildId}; clean install payload: dist/cep (runtime gate still required)`);

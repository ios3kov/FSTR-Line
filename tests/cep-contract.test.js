const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");

const manifest = fs.readFileSync("CSXS/manifest.xml", "utf8");
const host = fs.readFileSync("host/cep/host.jsx", "utf8");
const html = fs.readFileSync("index.html", "utf8");

test("manifest targets AE 22+ and stays dockable", () => {
  assert.match(manifest, /Host Name="AEFT" Version="\[22\.0,99\.9\]"/);
  assert.match(manifest, /<Type>Panel<\/Type>/);
  assert.match(manifest, /<ScriptPath>\.\/host\/cep\/host\.jsx<\/ScriptPath>/);
});

test("manifest does not enable Node or remote networking", () => {
  assert.doesNotMatch(manifest, /enable-nodejs/i);
  assert.doesNotMatch(manifest, /CEFCommandLine/);
  assert.match(html, /connect-src 'none'/);
});

test("mutating host commands use one native AE undo wrapper", () => {
  assert.match(
    host,
    /function withUndo\(label, fn\)\s*\{[\s\S]*?app\.beginUndoGroup\(label\);[\s\S]*?finally\s*\{\s*app\.endUndoGroup\(\);/
  );
  assert.match(host, /withUndo\("FSTR Line: Move Clip"/);
  assert.match(host, /withUndo\("FSTR Line: Trim In"/);
  assert.match(host, /withUndo\("FSTR Line: Trim Out"/);
});

test("panel load path is self-contained", () => {
  assert.match(host, /#include "\.\.\/\.\.\/vendor\/json2\.js"/);
  assert.match(html, /\.\/vendor\/CSInterface\.js/);
  assert.match(html, /\.\/core\/timeline-core\.js/);
  assert.match(html, /\.\/host\/cep\/cep-adapter\.js/);
});

test("clean installer verifies package before deleting installed copies", () => {
  const installer = fs.readFileSync("scripts/install-dev.mjs", "utf8");
  const verifyIndex = installer.indexOf("await verifyPackage()");
  const targetDeleteIndex = installer.indexOf("await fs.rm(target");

  assert.notEqual(verifyIndex, -1);
  assert.notEqual(targetDeleteIndex, -1);
  assert.ok(verifyIndex < targetDeleteIndex);
  assert.match(installer, /perUserDuplicates/);
});

test("Build Identity is exposed by host, adapter, panel and package flow", () => {
  const adapter = fs.readFileSync("host/cep/cep-adapter.js", "utf8");
  const panel = fs.readFileSync("ui/panel.js", "utf8");
  const packager = fs.readFileSync("scripts/package-extension.mjs", "utf8");
  const verifier = fs.readFileSync("scripts/verify-package.mjs", "utf8");

  assert.match(host, /api\.getBuildInfo/);
  assert.match(adapter, /getBuildInfo/);
  assert.match(html, /diagnostics-toggle/);
  assert.match(panel, /buildIdentityMismatch/);
  assert.match(panel, /Browser\/host Build Identity mismatch/);
  assert.match(packager, /gitState/);
  assert.match(packager, /path\.join\(generatedDir, "build-info\.json"\)/);
  assert.match(verifier, /Refusing milestone\/test package from dirty Git state/);
  assert.match(verifier, /Build Identity mismatch between manifest and generated metadata/);
});

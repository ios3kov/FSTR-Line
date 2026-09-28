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

test("mutating host commands use native AE undo groups", () => {
  assert.match(host, /beginUndoGroup\("FSTR Line: Move Clip"\)/);
  assert.match(host, /beginUndoGroup\("FSTR Line: Trim In"\)/);
  assert.match(host, /beginUndoGroup\("FSTR Line: Trim Out"\)/);
  assert.match(host, /finally\s*\{\s*app\.endUndoGroup\(\)/);
});

test("panel load path is self-contained", () => {
  assert.match(host, /#include "\.\.\/\.\.\/vendor\/json2\.js"/);
  assert.match(html, /\.\/vendor\/CSInterface\.js/);
  assert.match(html, /\.\/core\/timeline-core\.js/);
  assert.match(html, /\.\/host\/cep\/cep-adapter\.js/);
});

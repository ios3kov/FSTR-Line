import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

test("CEP manifest declares a dockable AE panel and packaged host path", async () => {
  const manifest = await readFile("cep/CSXS/manifest.xml", "utf8");
  assert.match(manifest, /<Host Name="AEFT" Version="\[22\.0,99\.9\]" \/>/);
  assert.match(manifest, /<Type>Panel<\/Type>/);
  assert.match(manifest, /<MainPath>\.\/client\/index\.html<\/MainPath>/);
  assert.match(manifest, /<ScriptPath>\.\/host\/host\.jsx<\/ScriptPath>/);
});

test("CEP client declares the Adobe bridge as an explicit vendor artifact", async () => {
  const html = await readFile("cep/client/index.html", "utf8");
  const bridge = await readFile("cep/client/CSInterface.js", "utf8");
  assert.match(html, /<script src="\.\/CSInterface\.js"><\/script>/);
  assert.match(bridge, /CSInterface - v12\.0\.0/);
  assert.match(bridge, /ADOBE SYSTEMS INCORPORATED/);
});

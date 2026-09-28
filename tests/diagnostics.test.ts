import assert from "node:assert/strict";
import test from "node:test";
import { matchingBuilds, parseDiagnostics } from "../src/host/diagnostics.js";
import { CEPAdapter } from "../src/host/cep/bridge.js";

const build = { buildId: "fstr-cep-123", gitCommit: "a".repeat(40), dirty: false, version: "0.1.0" };
const envelope = (data: unknown) => JSON.stringify({ protocolVersion: 1, ok: true, data });

test("diagnostics reads loaded host identity using the queued bridge", async () => {
  const scripts: string[] = [];
  const adapter = new CEPAdapter({ evalScript(script, callback) {
    scripts.push(script);
    callback(envelope({ build, aeVersion: "25.6" }));
  } });
  assert.deepEqual(await adapter.readDiagnostics(), { build, aeVersion: "25.6" });
  assert.deepEqual(scripts, ["fstrLineHost.diagnostics()"]);
});

test("diagnostics rejects missing, malformed and incompatible metadata", () => {
  for (const data of [null, {}, { build }, { build: { ...build, dirty: "false" }, aeVersion: "25.6" }]) {
    assert.throws(() => parseDiagnostics(envelope(data)), /Malformed/);
  }
  assert.throws(() => parseDiagnostics("null"), /must be an object/);
  assert.throws(() => parseDiagnostics('{"protocolVersion":2}'), /protocol version/);
});

test("build matching detects stale host commits and dirty identities", () => {
  assert.equal(matchingBuilds(build, { ...build }), true);
  assert.equal(matchingBuilds(build, { ...build, gitCommit: "b".repeat(40) }), false);
  assert.equal(matchingBuilds(build, { ...build, dirty: true }), false);
});

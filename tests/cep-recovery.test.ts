import assert from "node:assert/strict";
import test from "node:test";
import { CEPAdapter, type BridgeAttempt } from "../src/host/cep/bridge.js";
import { createMoveLayersCommand } from "../src/core/index.js";
import { layer, snapshot } from "./fixtures.js";

const current = snapshot([layer(1, 1, 0, 4)]);
const reply = JSON.stringify({ protocolVersion: 1, ok: true, data: current });

test("empty read recovers and keeps later requests behind retries", async () => {
  const scripts: string[] = [];
  const attempts: BridgeAttempt[] = [];
  const adapter = new CEPAdapter({ evalScript(script, callback) {
    scripts.push(script);
    callback(scripts.length === 1 ? "" : reply);
  } }, { onAttempt: (attempt) => attempts.push(attempt) });
  const results = await Promise.all([adapter.readSnapshot(), adapter.readSnapshot()]);
  assert.deepEqual(results, [current, current]);
  assert.deepEqual(attempts.map((a) => [a.attempt, a.outcome]), [[1, "empty"], [2, "response"], [1, "response"]]);
});

test("persistent empty replies stop after three attempts; manual read can recover", async () => {
  let calls = 0;
  const adapter = new CEPAdapter({ evalScript(_script, callback) { callback(++calls <= 3 ? "" : reply); } });
  await assert.rejects(adapter.readSnapshot(), /after 3 snapshot attempts/);
  assert.equal(calls, 3);
  assert.deepEqual(await adapter.readSnapshot(), current);
});

test("errors and malformed replies are not retried", async () => {
  for (const raw of ["EvalScript error.", "bad JSON", JSON.stringify({ protocolVersion: 1, ok: false, error: { code: "NO_ACTIVE_COMP", message: "No comp" } })]) {
    let calls = 0;
    const adapter = new CEPAdapter({ evalScript(_script, callback) { calls++; callback(raw); } });
    await assert.rejects(adapter.readSnapshot());
    assert.equal(calls, 1);
  }
});

test("commands with an empty response are never replayed", async () => {
  let calls = 0;
  const adapter = new CEPAdapter({ evalScript(_script, callback) { calls++; callback(""); } });
  await assert.rejects(adapter.execute(createMoveLayersCommand(current, [1], 1, "retry-test")), /empty response/);
  assert.equal(calls, 1);
});

test("timeouts are not retried and late callbacks cannot resolve the read", async () => {
  let calls = 0;
  let late: ((reply: string) => void) | undefined;
  const attempts: BridgeAttempt[] = [];
  const adapter = new CEPAdapter({ evalScript(_script, callback) { calls++; late = callback; } },
    { timeoutMs: 5, onAttempt: (attempt) => attempts.push(attempt) });
  await assert.rejects(adapter.readSnapshot(), /timed out/);
  late?.(reply);
  assert.equal(calls, 1);
  assert.deepEqual(attempts.map((a) => a.outcome), ["transport-error"]);
});

test("diagnostics observer failures do not fail reads", async () => {
  const adapter = new CEPAdapter({ evalScript(_script, callback) { callback(reply); } },
    { onAttempt() { throw new Error("view failure"); } });
  assert.deepEqual(await adapter.readSnapshot(), current);
});

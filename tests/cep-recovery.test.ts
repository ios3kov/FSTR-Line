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

test("timed-out host read prevents subsequent reads, diagnostics and unsent writes until callback", async () => {
  const callbacks: ((value: string) => void)[] = [];
  const adapter = new CEPAdapter({ evalScript(_script, callback) { callbacks.push(callback); } }, { timeoutMs: 5 });
  const first = adapter.readSnapshot();
  const queued = adapter.readSnapshot();
  const rejected = assert.rejects(queued, /HOST_CALL_PENDING/);
  await assert.rejects(first, /timed out/);
  await rejected;
  await assert.rejects(adapter.readDiagnostics(), /HOST_CALL_PENDING/);
  const command = createMoveLayersCommand(current, [1], 1, "not-sent");
  await assert.rejects(adapter.execute(command), /HOST_CALL_PENDING/);
  assert.equal(callbacks.length, 1);
  callbacks[0]!(reply);
  const recovered = adapter.readSnapshot();
  await Promise.resolve(); await Promise.resolve();
  callbacks[1]!(reply);
  assert.deepEqual(await recovered, current);
  // A command refused before dispatch must not acquire mutation uncertainty.
  const write = adapter.execute(command);
  await Promise.resolve(); await Promise.resolve();
  callbacks[2]!(JSON.stringify({ protocolVersion: 1, ok: true,
    data: { operationId: command.operationId, changed: true, snapshot: current } }));
  assert.equal((await write).operationId, command.operationId);
});

test("a duplicate late callback cannot clear another call's pending guard", async () => {
  const callbacks: ((value: string) => void)[] = [];
  const adapter = new CEPAdapter({ evalScript(_script, callback) { callbacks.push(callback); } }, { timeoutMs: 5 });
  await assert.rejects(adapter.readSnapshot(), /timed out/);
  callbacks[0]!(reply);
  await assert.rejects(adapter.readSnapshot(), /timed out/);
  callbacks[0]!(reply);
  await assert.rejects(adapter.readSnapshot(), /HOST_CALL_PENDING/);
  assert.equal(callbacks.length, 2);
  callbacks[1]!(reply);
});

test("synchronous dispatch exception retains the guard until a possible late callback", async () => {
  let callback!: (value: string) => void;
  let calls = 0;
  const adapter = new CEPAdapter({ evalScript(_script, received) {
    calls += 1; callback = received; throw new Error("dispatch outcome unknown");
  } });
  await assert.rejects(adapter.readSnapshot(), /dispatch outcome unknown/);
  await assert.rejects(adapter.readSnapshot(), /HOST_CALL_PENDING/);
  assert.equal(calls, 1);
  callback(reply);
});

test("notification read retains its pending promise after deadline until the host callback", async () => {
  let callback!: (value: string) => void;
  let calls = 0;
  const adapter = new CEPAdapter({ evalScript(_script, received) { calls += 1; callback = received; } }, { timeoutMs: 5 });
  const read = adapter.readNotificationSnapshot();
  let settled = false;
  const observed = read.then(() => { settled = true; }, () => { settled = true; });
  await new Promise((resolve) => setTimeout(resolve, 20));
  assert.equal(settled, false);
  await assert.rejects(adapter.readSnapshot(), /HOST_CALL_PENDING/);
  assert.equal(calls, 1);
  callback(reply);
  await assert.rejects(read, /timed out/);
  await observed;
  assert.equal(settled, true);
});

test("notification read passes successful snapshots and completed host errors normally", async () => {
  let next = reply;
  const adapter = new CEPAdapter({ evalScript(_script, callback) { callback(next); } });
  assert.deepEqual(await adapter.readNotificationSnapshot(), current);
  next = JSON.stringify({ protocolVersion: 1, ok: false, error: { code: "NO_ACTIVE_COMP", message: "closed" } });
  await assert.rejects(adapter.readNotificationSnapshot(), /closed/);
});

import assert from "node:assert/strict";
import test from "node:test";
import { NotificationDelivery, type DeliveryClock, type NotificationHandshake,
  type NotificationIdentity } from "../src/host/notification-delivery.js";
import { CEPAdapter } from "../src/host/cep/bridge.js";
import { snapshot } from "./fixtures.js";

// Synthetic identities deliberately do not approve any installed AE binary.
const identity: NotificationIdentity = {
  protocol: 1, buildId: "test-build", aeBuild: "25.6.0.101", architecture: "arm64",
  beeUuid: "test-bee", beeSha256: "a".repeat(64),
  afterFxUuid: "test-afterfx", afterFxSha256: "b".repeat(64),
};
function handshake(sessionId = "session-1", sequence = 0): NotificationHandshake {
  return { ...identity, sessionId, sequence, committedDelivery: true };
}
function event(sequence: number, kind = "changed", sessionId = "session-1", phase = "committed") {
  return JSON.stringify({ protocol: 1, sessionId, sequence, kind, phase });
}
function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: Error) => void;
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}
const settle = async () => { for (let i = 0; i < 8; i += 1) await Promise.resolve(); };
class Clock implements DeliveryClock {
  readonly jobs = new Map<number, () => void>();
  private next = 0;
  schedule(callback: () => void): unknown {
    const id = ++this.next; this.jobs.set(id, callback); return id;
  }
  cancel(handle: unknown): void { this.jobs.delete(handle as number); }
  expire(): void { for (const callback of [...this.jobs.values()]) callback(); }
}
function fixture() {
  const clock = new Clock();
  const reads: ReturnType<typeof deferred<string>>[] = [];
  const published: string[] = [];
  let invalidations = 0;
  const delivery = new NotificationDelivery(identity, {
    read() { const read = deferred<string>(); reads.push(read); return read.promise; },
    invalidate() { invalidations += 1; },
    publish(value) { published.push(value); },
  }, clock);
  return { delivery, reads, published, clock, invalidations: () => invalidations };
}

test("ND-01 refuses every compatibility mismatch and unproven commit capability before reads", () => {
  for (const key of Object.keys(identity)) {
    const f = fixture();
    assert.equal(f.delivery.open({ ...handshake(), [key]: "unknown" }), false, key);
    assert.equal(f.reads.length, 0);
    assert.equal(f.delivery.getState().status, "blocked");
    assert.equal(f.delivery.open(handshake()), true);
    assert.equal(f.reads.length, 1);
  }
  for (const value of [null, {}, { ...handshake(), committedDelivery: false },
    { ...handshake(), sequence: -1 }, { ...handshake(), sessionId: "" }]) {
    const f = fixture();
    assert.equal(f.delivery.open(value), false);
    assert.equal(f.reads.length, 0);
  }
});

test("ND-02 initial read settles without any recurring work or idle reads", async () => {
  const f = fixture();
  f.delivery.open(handshake());
  assert.equal(f.clock.jobs.size, 1); // read deadline only
  f.reads[0]!.resolve("initial"); await settle();
  assert.deepEqual(f.published, ["initial"]);
  assert.equal(f.clock.jobs.size, 0);
  assert.equal(f.reads.length, 1);
  assert.equal(f.delivery.getDiagnostics().pending, false);
});

test("ND-03 invalid event fields fail closed without trusting claimed commit state", async () => {
  const invalid = ["{", "x".repeat(2049), "null", "[]", "{}", event(0), event(-1),
    event(1.1), event(Number.MAX_SAFE_INTEGER + 1), event(1, "unknown"),
    event(1, "changed", "session-1", "before-commit"),
    JSON.stringify({ protocol: 2, sessionId: "session-1", sequence: 1, kind: "changed", phase: "committed" })];
  for (const raw of invalid) {
    const f = fixture(); f.delivery.open(handshake());
    f.delivery.receive(raw);
    assert.equal(f.delivery.getState().status, "blocked", raw);
    f.reads[0]!.resolve("obsolete"); await settle();
    assert.deepEqual(f.published, []);
    assert.equal(f.reads.length, 1);
  }
});

test("ND-03 ignores duplicates, out-of-order delivery and foreign sessions", async () => {
  const f = fixture(); f.delivery.open(handshake("session-1", 20));
  f.reads[0]!.resolve("initial"); await settle();
  for (const raw of [event(20), event(19), event(21, "changed", "old-session")]) f.delivery.receive(raw);
  assert.equal(f.reads.length, 1);
  assert.equal(f.delivery.getDiagnostics().duplicates, 2);
  assert.equal(f.delivery.getDiagnostics().gaps, 0);
});

test("ND-04 burst suppresses obsolete read and performs exactly one trailing read", async () => {
  const f = fixture(); f.delivery.open(handshake());
  for (let i = 1; i <= 10000; i += 1) f.delivery.receive(event(i));
  assert.equal(f.reads.length, 1);
  assert.equal(f.invalidations(), 2);
  f.reads[0]!.resolve("stale"); await settle();
  assert.deepEqual(f.published, []);
  assert.equal(f.reads.length, 2);
  f.reads[1]!.resolve("after-burst"); await settle();
  assert.deepEqual(f.published, ["after-burst"]);
  assert.equal(f.reads.length, 2);
  assert.equal(f.clock.jobs.size, 0);
});

test("ND-04 changes during the trailing read cannot publish another stale snapshot", async () => {
  const f = fixture(); f.delivery.open(handshake());
  f.delivery.receive(event(1)); f.reads[0]!.resolve("old"); await settle();
  f.delivery.receive(event(2)); f.reads[1]!.resolve("also-old"); await settle();
  f.reads[2]!.resolve("current"); await settle();
  assert.deepEqual(f.published, ["current"]);
});

test("ND-05 observable gap and explicit overflow force reconciliation, even on noop", async () => {
  const f = fixture(); f.delivery.open(handshake());
  f.reads[0]!.resolve("initial"); await settle();
  f.delivery.receive(event(3, "noop"));
  assert.equal(f.reads.length, 2);
  f.reads[1]!.resolve("reconciled-gap"); await settle();
  f.delivery.receive(event(4, "overflow"));
  f.reads[2]!.resolve("reconciled-overflow"); await settle();
  assert.deepEqual(f.published, ["initial", "reconciled-gap", "reconciled-overflow"]);
  assert.equal(f.delivery.getDiagnostics().gaps, 2);
});

test("ND-06 no-op/cancel with no mutation advances sequence without refresh", async () => {
  const f = fixture(); f.delivery.open(handshake());
  f.delivery.receive(event(1, "noop"));
  f.reads[0]!.resolve("initial"); await settle();
  f.delivery.receive(event(2, "noop"));
  assert.equal(f.reads.length, 1);
  assert.equal(f.invalidations(), 1);
  f.delivery.receive(event(3)); // failed operation with partial state change
  assert.equal(f.reads.length, 2);
  assert.equal(f.delivery.getDiagnostics().gaps, 0);
});

test("ND-07 read error blocks queued changes and recovers only via a fresh handshake", async () => {
  const f = fixture(); f.delivery.open(handshake());
  f.delivery.receive(event(1));
  f.reads[0]!.reject(new Error("host unavailable")); await settle();
  assert.deepEqual(f.delivery.getState(), { status: "blocked", reason: "READ_OR_PUBLICATION_FAILED" });
  f.delivery.receive(event(2)); assert.equal(f.reads.length, 1);
  assert.equal(f.delivery.open(handshake()), false);
  assert.equal(f.delivery.open(handshake("session-2")), true);
  f.reads[1]!.resolve("recovered"); await settle();
  assert.deepEqual(f.published, ["recovered"]);
});

test("ND-08 close suppresses late success and failure, closed events do not read", async () => {
  for (const fail of [false, true]) {
    const f = fixture(); f.delivery.open(handshake()); f.delivery.close();
    f.delivery.receive(event(1));
    if (fail) f.reads[0]!.reject(new Error("late")); else f.reads[0]!.resolve("late");
    await settle();
    assert.deepEqual(f.published, []);
    assert.equal(f.delivery.getState().status, "closed");
    assert.equal(f.reads.length, 1);
    assert.equal(f.clock.jobs.size, 0);
  }
});

test("ND-08 reconnect while a read is pending stays single-flight and rejects old result", async () => {
  for (const fail of [false, true]) {
    const f = fixture(); f.delivery.open(handshake()); f.delivery.close();
    f.delivery.open(handshake("session-2"));
    assert.equal(f.reads.length, 1);
    if (fail) f.reads[0]!.reject(new Error("old")); else f.reads[0]!.resolve("old");
    await settle(); assert.equal(f.reads.length, 2);
    f.delivery.receive(event(99, "changed", "session-1"));
    f.reads[1]!.resolve("new"); await settle();
    assert.deepEqual(f.published, ["new"]);
  }
});

test("ND-09 timeout refuses overlap and late result; settled transport can explicitly recover", async () => {
  const f = fixture(); f.delivery.open(handshake()); f.clock.expire();
  assert.deepEqual(f.delivery.getState(), { status: "blocked", reason: "READ_TIMEOUT" });
  assert.equal(f.delivery.open(handshake("session-2")), false);
  f.delivery.receive(event(1)); assert.equal(f.reads.length, 1);
  f.reads[0]!.resolve("late"); await settle();
  assert.deepEqual(f.published, []);
  assert.equal(f.delivery.open(handshake("session-3")), true);
  f.reads[1]!.resolve("recovered"); await settle();
  assert.deepEqual(f.published, ["recovered"]);
});

test("ND-09 deadline follows outstanding operation through close and reopen", async () => {
  const f = fixture(); f.delivery.open(handshake()); f.delivery.close();
  f.delivery.open(handshake("session-2")); f.clock.expire();
  assert.equal(f.delivery.getState().status, "blocked");
  f.reads[0]!.resolve("old"); await settle();
  assert.equal(f.reads.length, 1);
  assert.deepEqual(f.published, []);
});

test("delivery callbacks fail closed rather than starting a retry storm", async () => {
  for (const failure of ["invalidate", "publish", "read"]) {
    let reads = 0;
    const delivery = new NotificationDelivery(identity, {
      read() { reads += 1; if (failure === "read") throw new Error(); return Promise.resolve("state"); },
      invalidate() { if (failure === "invalidate") throw new Error(); },
      publish() { if (failure === "publish") throw new Error(); },
    }, new Clock());
    delivery.open(handshake()); await settle();
    assert.equal(delivery.getState().status, "blocked");
    delivery.receive(event(1)); await settle();
    assert.equal(reads, failure === "invalidate" ? 0 : 1);
  }
});

test("configuration and public state cannot silently mutate the compatibility policy", () => {
  assert.throws(() => new NotificationDelivery({ ...identity, beeSha256: "short" },
    { read: async () => "", invalidate() {}, publish() {} }, new Clock()));
  const expected = { ...identity };
  const delivery = new NotificationDelivery(expected,
    { read: async () => "", invalidate() {}, publish() {} }, new Clock());
  expected.buildId = "changed-policy";
  assert.equal(delivery.open(handshake()), true);
  const state = delivery.getState() as { status: string };
  state.status = "closed";
  assert.equal(delivery.getState().status, "active");
});

test("deadline cleanup failure blocks delivery without an unhandled rejection or new reads", async () => {
  let reads = 0;
  const delivery = new NotificationDelivery(identity, {
    async read() { reads += 1; return "state"; }, invalidate() {}, publish() {},
  }, { schedule() { return 1; }, cancel() { throw new Error("clock failure"); } });
  delivery.open(handshake()); await settle();
  assert.deepEqual(delivery.getState(), { status: "blocked", reason: "DEADLINE_CLEANUP_FAILED" });
  delivery.receive(event(1));
  assert.equal(reads, 1);
  assert.equal(delivery.getDiagnostics().pending, false);
});

test("a cancelled deadline callback cannot block a later session", async () => {
  const f = fixture(); f.delivery.open(handshake());
  const oldDeadline = [...f.clock.jobs.values()][0]!;
  f.reads[0]!.resolve("initial"); await settle();
  f.delivery.close(); f.delivery.open(handshake("session-2"));
  oldDeadline();
  assert.equal(f.delivery.getState().status, "active");
  f.reads[1]!.resolve("new"); await settle();
  assert.deepEqual(f.published, ["initial", "new"]);
});

test("CEP completion adapter keeps delivery single-flight across transport timeout and recovery", async () => {
  const callbacks: ((value: string) => void)[] = [];
  const adapter = new CEPAdapter({ evalScript(_script, callback) { callbacks.push(callback); } }, { timeoutMs: 5 });
  const clock = new Clock();
  const values: unknown[] = [];
  const delivery = new NotificationDelivery(identity, {
    read: () => adapter.readNotificationSnapshot(), invalidate() {},
    publish(value) { values.push(value); },
  }, clock);
  delivery.open(handshake());
  await new Promise((resolve) => setTimeout(resolve, 20));
  assert.equal(delivery.getDiagnostics().pending, true);
  clock.expire();
  assert.equal(delivery.open(handshake("session-2")), false);
  assert.equal(callbacks.length, 1);
  const current = snapshot([]);
  const reply = JSON.stringify({ protocolVersion: 1, ok: true, data: current });
  callbacks[0]!(reply);
  await settle();
  assert.equal(delivery.getDiagnostics().pending, false);
  assert.deepEqual(values, []);
  assert.equal(delivery.open(handshake("session-3")), true);
  await settle();
  callbacks[1]!(reply);
  await settle(); await settle();
  assert.deepEqual(values, [current]);
});

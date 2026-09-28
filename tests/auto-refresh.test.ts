import assert from "node:assert/strict";
import test from "node:test";
import { AutoRefresh } from "../src/cep/auto-refresh.js";
import { PanelController } from "../src/cep/panel-controller.js";
import { HostResponseError } from "../src/host/protocol.js";
import { snapshot } from "./fixtures.js";

const tick = async () => { await Promise.resolve(); await Promise.resolve(); };

test("continuous sync schedules after completion and disabling cancels it", async () => {
  let callback: (() => void) | undefined;
  let calls = 0;
  const auto = new AutoRefresh(async () => { calls++; return { status: "ready", snapshot: snapshot([]), tracks: [] }; }, {
    schedule(fn, delay) { assert.equal(delay, 2000); callback = fn; return 1; },
    cancel() { callback = undefined; },
  }, () => true);
  auto.setContinuous(true); await tick();
  assert.equal(calls, 1);
  const fn = callback; callback = undefined; fn?.(); await tick();
  assert.equal(calls, 2);
  auto.setContinuous(false);
  assert.equal(callback, undefined);
});

test("suspending during a continuous read prevents rescheduling", async () => {
  let finish: (() => void) | undefined;
  const auto = new AutoRefresh(async () => {
    await new Promise<void>((resolve) => { finish = resolve; });
    return { status: "no-composition" };
  }, { schedule() { throw new Error("unexpected schedule"); }, cancel() {} }, () => true);
  auto.setContinuous(true); auto.suspend(); finish?.(); await tick();
});

test("continuous sync stops on errors", async () => {
  let scheduled = false;
  const auto = new AutoRefresh(async () => ({ status: "error", message: "host unavailable" }), {
    schedule() { scheduled = true; return 1; }, cancel() {},
  }, () => true);
  auto.setContinuous(true); await tick();
  assert.equal(scheduled, false);
});

test("startup discovery is bounded and stops on disposal", async () => {
  let callback: (() => void) | undefined;
  let calls = 0;
  const auto = new AutoRefresh(async () => { calls++; return { status: "no-composition" }; }, {
    schedule(fn, delay) { assert.equal(delay, 2000); callback = fn; return 1; },
    cancel() { callback = undefined; },
  }, () => true);
  auto.request();
  for (let i = 0; i < 20; i++) {
    await tick();
    const fn = callback; callback = undefined; fn?.();
  }
  assert.equal(calls, 15);
  auto.request(); await tick(); auto.dispose();
  assert.equal(callback, undefined);
  auto.request(); assert.equal(calls, 16);
});

test("hidden panels do not read; successful reads stop discovery", async () => {
  let visible = false;
  let calls = 0;
  const auto = new AutoRefresh(async () => { calls++; return { status: "ready", snapshot: snapshot([]), tracks: [] }; }, {
    schedule() { throw new Error("Should not schedule after ready"); }, cancel() {},
  }, () => visible);
  auto.request(); assert.equal(calls, 0);
  visible = true; auto.request(); auto.request(); await tick();
  assert.equal(calls, 1);
});

test("missing active composition clears old snapshot and can recover", async () => {
  let missing = false;
  const controller = new PanelController({
    async readSnapshot() { if (missing) throw new HostResponseError("NO_ACTIVE_COMP", "No comp"); return snapshot([]); },
    async execute() { throw new Error("unused"); },
  }, { render() {} });
  assert.equal((await controller.refresh()).status, "ready");
  missing = true;
  assert.deepEqual(await controller.refresh(), { status: "no-composition" });
  missing = false;
  assert.equal((await controller.refresh()).status, "ready");
});

import assert from "node:assert/strict";
import test from "node:test";
import { PanelController, type PanelState, type PanelView } from "../src/cep/panel-controller.js";
import type { HostAdapter, HostOperationResult } from "../src/host/host-adapter.js";
import type { CompositionSnapshot, TimelineCommand } from "../src/core/types.js";
import { layer, snapshot } from "./fixtures.js";

class RecordingView implements PanelView {
  readonly states: PanelState[] = [];

  render(state: PanelState): void {
    this.states.push(state);
  }
}

class FixtureHost implements HostAdapter {
  constructor(
    private readonly result: CompositionSnapshot | Error,
    private readonly delayMs = 0,
  ) {}

  async readSnapshot(): Promise<CompositionSnapshot> {
    await new Promise((resolve) => setTimeout(resolve, this.delayMs));
    if (this.result instanceof Error) {
      throw this.result;
    }
    return this.result;
  }

  async execute(_command: TimelineCommand): Promise<HostOperationResult> {
    throw new Error("not used in panel controller tests");
  }
}

class MutableFixtureHost implements HostAdapter {
  constructor(private result: CompositionSnapshot | Error) {}

  setResult(result: CompositionSnapshot | Error): void {
    this.result = result;
  }

  async readSnapshot(): Promise<CompositionSnapshot> {
    if (this.result instanceof Error) {
      throw this.result;
    }
    return this.result;
  }

  async execute(_command: TimelineCommand): Promise<HostOperationResult> {
    throw new Error("not used in panel controller tests");
  }
}

test("PanelController transitions from no composition to ready and renders packing", async () => {
  const view = new RecordingView();
  const controller = new PanelController(
    new FixtureHost(snapshot([layer(1, 1, 0, 4), layer(2, 2, 4, 8)])),
    view,
  );

  const result = await controller.refresh();
  assert.equal(result.status, "ready");
  assert.equal(controller.getState().status, "ready");
  assert.deepEqual(view.states.map((state) => state.status), ["no-composition", "loading", "ready"]);
  assert.equal(result.status === "ready" ? result.tracks.length : 0, 1);
});

test("PanelController coalesces concurrent refresh requests", async () => {
  const view = new RecordingView();
  const controller = new PanelController(
    new FixtureHost(snapshot([layer(1, 1, 0, 4)]), 5),
    view,
  );

  const first = controller.refresh();
  const second = controller.refresh();
  assert.strictEqual(first, second);
  await first;
  assert.deepEqual(view.states.map((state) => state.status), ["no-composition", "loading", "ready"]);
});

test("PanelController preserves the previous projection when refresh fails", async () => {
  const view = new RecordingView();
  const host = new MutableFixtureHost(snapshot([layer(1, 1, 0, 4)]));
  const controller = new PanelController(host, view);
  await controller.refresh();

  host.setResult(new Error("host unavailable"));
  await controller.refresh();
  const failedState = controller.getState();
  assert.equal(failedState.status, "error");
  assert.match(failedState.status === "error" ? failedState.message : "", /host unavailable/);
  assert.equal(failedState.status === "error" ? failedState.snapshot?.layers.length : 0, 1);
  assert.equal(failedState.status === "error" ? failedState.tracks?.length : 0, 1);
});

test("PanelController ignores an in-flight result after invalidation", async () => {
  const view = new RecordingView();
  const controller = new PanelController(
    new FixtureHost(snapshot([layer(1, 1, 0, 4)]), 10),
    view,
  );
  const refresh = controller.refresh();
  controller.invalidate();
  const result = await refresh;

  assert.equal(controller.getState().status, "no-composition");
  assert.equal(result.status, "no-composition");
  assert.deepEqual(view.states.map((state) => state.status), ["no-composition", "loading", "no-composition"]);
});

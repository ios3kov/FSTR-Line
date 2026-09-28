import assert from "node:assert/strict";
import test from "node:test";
import {
  CoreError,
  createMoveLayersCommand,
  createSetLayerSwitchCommand,
  createTrimLayerInCommand,
  validateCommandAgainstSnapshot,
} from "../src/core/index.js";
import { layer, snapshot } from "./fixtures.js";

test("creates deterministic guarded multi-layer move commands", () => {
  const current = snapshot([
    layer(2, 2, 4, 8),
    layer(1, 1, 0, 4),
  ]);
  const command = createMoveLayersCommand(current, [2, 1, 2], 3, "op-1");

  assert.deepEqual(command, {
    type: "moveLayers",
    commandVersion: 1,
    operationId: "op-1",
    guard: { compositionId: "comp-1", revision: "revision-1" },
    layerIds: [1, 2],
    deltaFrames: 3,
  });
  validateCommandAgainstSnapshot(current, command);
});

test("rejects a command created from a stale snapshot", () => {
  const command = createMoveLayersCommand(
    snapshot([layer(1, 1, 0, 4)]),
    [1],
    1,
    "op-stale",
  );
  const changed = { ...snapshot([layer(1, 1, 0, 4)]), revision: "revision-2" };

  assert.throws(
    () => validateCommandAgainstSnapshot(changed, command),
    (error: unknown) => error instanceof CoreError && error.code === "STALE_SNAPSHOT",
  );
});

test("rejects locked layers and invalid trim ranges", () => {
  const lockedSnapshot = snapshot([
    layer(1, 1, 0, 4, { locked: true }),
  ]);
  assert.throws(
    () => createMoveLayersCommand(lockedSnapshot, [1], 1, "op-locked"),
    (error: unknown) => error instanceof CoreError && error.code === "LOCKED_LAYER",
  );

  assert.throws(
    () => createTrimLayerInCommand(snapshot([layer(1, 1, 0, 4)]), 1, 4, "op-trim"),
    (error: unknown) => error instanceof CoreError && error.code === "INVALID_TIMING",
  );
});

test("allows unlocking a locked layer while rejecting other locked-layer switches", () => {
  const current = snapshot([layer(1, 1, 0, 4, { locked: true })]);
  const unlock = createSetLayerSwitchCommand(current, 1, "locked", false, "op-unlock");
  assert.equal(unlock.type, "setLayerSwitch");

  assert.throws(
    () => createSetLayerSwitchCommand(current, 1, "enabled", false, "op-disable"),
    (error: unknown) => error instanceof CoreError && error.code === "LOCKED_LAYER",
  );
});

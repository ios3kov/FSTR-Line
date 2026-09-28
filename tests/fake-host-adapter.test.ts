import assert from "node:assert/strict";
import test from "node:test";
import {
  CoreError,
  createMoveLayersCommand,
  createTrimLayerOutCommand,
} from "../src/core/index.js";
import { FakeHostAdapter } from "../src/host/fake-host-adapter.js";
import { layer, snapshot } from "./fixtures.js";

test("FakeHostAdapter validates and commits a guarded operation as one result", async () => {
  const adapter = new FakeHostAdapter(snapshot([layer(1, 1, 0, 4)]));
  const initial = await adapter.readSnapshot();
  const command = createMoveLayersCommand(initial, [1], 2, "op-move");
  const result = await adapter.execute(command);

  assert.equal(result.operationId, "op-move");
  assert.equal(result.changed, true);
  assert.deepEqual(result.snapshot.layers[0], {
    ...initial.layers[0],
    startFrame: 2,
    inFrame: 2,
    outFrame: 6,
  });
});

test("FakeHostAdapter applies no changes when a command is stale", async () => {
  const adapter = new FakeHostAdapter(snapshot([layer(1, 1, 0, 4)]));
  const initial = await adapter.readSnapshot();
  const command = createTrimLayerOutCommand(initial, 1, 6, "op-trim");
  await adapter.execute(command);
  const afterFirstOperation = await adapter.readSnapshot();

  await assert.rejects(
    () => adapter.execute(command),
    (error: unknown) => error instanceof CoreError && error.code === "STALE_SNAPSHOT",
  );
  assert.deepEqual(await adapter.readSnapshot(), afterFirstOperation);
});

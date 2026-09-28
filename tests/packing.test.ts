import assert from "node:assert/strict";
import test from "node:test";
import { CoreError, packLayers } from "../src/core/index.js";
import { layer, snapshot } from "./fixtures.js";

test("packs sequential clips on one track and treats zero-gap as non-overlap", () => {
  const result = packLayers(snapshot([
    layer(1, 1, 0, 4),
    layer(2, 2, 4, 8),
    layer(3, 3, 8, 12),
  ]));

  assert.deepEqual(result.tracks, [{ trackIndex: 0, layerIds: [1, 2, 3] }]);
});

test("places overlapping layers below their AE compositing predecessor", () => {
  const result = packLayers(snapshot([
    layer(1, 1, 0, 8),
    layer(2, 2, 4, 10),
  ]));

  assert.deepEqual(result.tracks, [
    { trackIndex: 0, layerIds: [1] },
    { trackIndex: 1, layerIds: [2] },
  ]);
});

test("handles staggered overlap constraints rather than only direct overlap", () => {
  const result = packLayers(snapshot([
    layer(1, 1, 0, 5),
    layer(2, 2, 1, 10),
    layer(3, 3, 6, 8),
  ]));

  assert.deepEqual(result.tracks, [
    { trackIndex: 0, layerIds: [1] },
    { trackIndex: 1, layerIds: [2] },
    { trackIndex: 2, layerIds: [3] },
  ]);
});

test("packing is deterministic when input layers are shuffled", () => {
  const ordered = [
    layer(1, 1, 0, 5),
    layer(2, 2, 1, 10),
    layer(3, 3, 6, 8),
  ];
  const first = packLayers(snapshot(ordered));
  const second = packLayers(snapshot([ordered[2]!, ordered[0]!, ordered[1]!]));

  assert.deepEqual(second.tracks, first.tracks);
});

test("rejects invalid and duplicate layer ranges before packing", () => {
  assert.throws(
    () => packLayers(snapshot([layer(1, 1, 4, 4)])),
    (error: unknown) => error instanceof CoreError && error.code === "INVALID_RANGE",
  );

  assert.throws(
    () => packLayers(snapshot([layer(1, 1, 0, 4), layer(1, 2, 4, 8)])),
    (error: unknown) => error instanceof CoreError && error.code === "DUPLICATE_LAYER_ID",
  );
});

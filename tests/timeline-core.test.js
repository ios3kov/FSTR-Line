const test = require("node:test");
const assert = require("node:assert/strict");
const core = require("../core/timeline-core.js");

function layer(id, index, inFrame, outFrame) {
  return { id, index, inFrame, outFrame };
}

test("sequential clips share one track", () => {
  const result = core.packLayers([
    layer(1, 1, 0, 4),
    layer(2, 2, 4, 8),
    layer(3, 3, 8, 12)
  ]);

  assert.equal(result.trackCount, 1);
  assert.deepEqual(result.placements.map((p) => p.track), [0, 0, 0]);
  assert.deepEqual(core.validatePacking(result), { ok: true });
});

test("overlapping layers preserve AE compositing order", () => {
  const result = core.packLayers([
    layer(1, 1, 0, 8),
    layer(2, 2, 4, 10)
  ]);

  assert.deepEqual(result.placements.map((p) => p.track), [0, 1]);
  assert.deepEqual(core.validatePacking(result), { ok: true });
});

test("overlap chain cannot use naive first-free-track packing", () => {
  const result = core.packLayers([
    layer(1, 1, 0, 2),
    layer(2, 2, 1, 4),
    layer(3, 3, 2, 3)
  ]);

  assert.deepEqual(result.placements.map((p) => p.track), [0, 1, 2]);
  assert.deepEqual(core.validatePacking(result), { ok: true });
});

test("nested ranges remain strictly ordered", () => {
  const result = core.packLayers([
    layer(1, 1, 0, 20),
    layer(2, 2, 2, 18),
    layer(3, 3, 4, 16),
    layer(4, 4, 6, 14)
  ]);

  assert.deepEqual(result.placements.map((p) => p.track), [0, 1, 2, 3]);
  assert.deepEqual(core.validatePacking(result), { ok: true });
});

test("zero-gap clips do not overlap", () => {
  assert.equal(
    core.overlaps(layer(1, 1, -10, 0), layer(2, 2, 0, 10)),
    false
  );
});

test("negative frames are supported", () => {
  const result = core.packLayers([
    layer(1, 1, -20, -10),
    layer(2, 2, -10, 0),
    layer(3, 3, -15, -5)
  ]);

  assert.deepEqual(result.placements.map((p) => p.track), [0, 0, 1]);
  assert.deepEqual(core.validatePacking(result), { ok: true });
});

test("frame conversion is stable at fractional frame rates", () => {
  const frameDuration = 1001 / 24000;
  const start = -2;
  const frame = 173;

  const seconds = core.frameToSeconds(frame, start, frameDuration);
  assert.equal(core.secondsToFrame(seconds, start, frameDuration), frame);
});

test("normalization converts timing to frame coordinates without mutating input", () => {
  const snapshot = {
    comp: { frameDuration: 1 / 25, displayStartTime: 0 },
    layers: [{
      id: 10,
      index: 1,
      name: "A",
      inPoint: 1,
      outPoint: 2,
      startTime: 0.5,
      label: 1,
      selected: false,
      enabled: true,
      solo: false,
      locked: false,
      audioEnabled: true,
      type: "av"
    }]
  };

  const normalized = core.normalizeSnapshot(snapshot);
  assert.equal(normalized.layers[0].inFrame, 25);
  assert.equal(normalized.layers[0].outFrame, 50);
  assert.equal(normalized.layers[0].startFrame, 13);
  assert.equal(snapshot.layers[0].inFrame, undefined);
});
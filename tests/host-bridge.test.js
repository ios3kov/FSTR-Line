const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const hostSource = fs
  .readFileSync("host/cep/host.jsx", "utf8")
  .replace(/^#include[^\n]*$/gm, "");

class BaseLayer {
  constructor(options) {
    this.id = options.id;
    this.index = options.index;
    this.name = options.name;
    this._startTime = options.startTime;
    this.inPoint = options.inPoint;
    this.outPoint = options.outPoint;
    this.label = options.label || 1;
    this.selected = !!options.selected;
    this.enabled = options.enabled !== false;
    this.solo = !!options.solo;
    this.locked = !!options.locked;
    this.audioEnabled = options.audioEnabled !== false;
    this.source = options.source || null;
  }

  get startTime() {
    return this._startTime;
  }

  set startTime(value) {
    if (this.failOnStartTimeSet) {
      throw new Error("Injected host setter failure.");
    }

    const delta = value - this._startTime;
    this._startTime = value;
    this.inPoint += delta;
    this.outPoint += delta;
  }
}

class AVLayer extends BaseLayer {}
class TextLayer extends AVLayer {}
class ShapeLayer extends AVLayer {}
class CameraLayer extends BaseLayer {}
class LightLayer extends BaseLayer {}

class CompItem {
  constructor(layers, frameRate = 25) {
    this.id = 500;
    this.name = "Mock Comp";
    this.duration = 10;
    this.frameRate = frameRate;
    this.frameDuration = 1 / frameRate;
    this.displayStartTime = 0;
    this.displayStartFrame = 0;
    this.time = 0;
    this.layers = layers;
    for (let i = 0; i < layers.length; i += 1) {
      layers[i].index = i + 1;
    }
  }

  get numLayers() {
    return this.layers.length;
  }

  layer(index) {
    return this.layers[index - 1];
  }

  get selectedLayers() {
    return this.layers.filter((layer) => layer.selected);
  }
}

function createHost(frameRate = 25) {
  const layers = [
    new AVLayer({
      id: 101,
      name: "Video",
      startTime: 0,
      inPoint: 1,
      outPoint: 4,
      selected: true,
      source: { id: 901 }
    }),
    new TextLayer({
      id: 102,
      name: "Title",
      startTime: 2,
      inPoint: 2,
      outPoint: 5
    })
  ];

  const comp = new CompItem(layers, frameRate);
  const undo = [];
  const app = {
    project: { activeItem: comp },
    beginUndoGroup(label) {
      undo.push(["begin", label]);
    },
    endUndoGroup() {
      undo.push(["end"]);
    }
  };

  const context = vm.createContext({
    $: {},
    app,
    CompItem,
    AVLayer,
    TextLayer,
    ShapeLayer,
    CameraLayer,
    LightLayer
  });

  vm.runInContext(hostSource, context, { filename: "host/cep/host.jsx" });

  return {
    api: context.$._fstr,
    app,
    comp,
    layers,
    undo
  };
}

function result(raw) {
  return JSON.parse(raw);
}

test("snapshot is read-only and exposes persistent layer IDs", () => {
  const host = createHost();
  const before = host.layers.map((layer) => ({
    id: layer.id,
    startTime: layer.startTime,
    inPoint: layer.inPoint,
    outPoint: layer.outPoint,
    selected: layer.selected
  }));

  const response = result(host.api.getSnapshot());

  assert.equal(response.ok, true);
  assert.equal(response.data.comp.id, 500);
  assert.deepEqual(
    response.data.layers.map((layer) => layer.id),
    [101, 102]
  );

  const after = host.layers.map((layer) => ({
    id: layer.id,
    startTime: layer.startTime,
    inPoint: layer.inPoint,
    outPoint: layer.outPoint,
    selected: layer.selected
  }));
  assert.deepEqual(after, before);
  assert.deepEqual(host.undo, []);
});

test("selection updates AE state without creating an undo group", () => {
  const host = createHost();
  const response = result(host.api.selectLayer(102, false));

  assert.equal(response.ok, true);
  assert.equal(host.layers[0].selected, false);
  assert.equal(host.layers[1].selected, true);
  assert.deepEqual(host.undo, []);
});

test("move uses startTime and one native undo group", () => {
  const host = createHost();
  const response = result(host.api.moveLayerFrames(101, 2));

  assert.equal(response.ok, true);
  assert.equal(host.layers[0].startTime, 0.08);
  assert.equal(host.layers[0].inPoint, 1.08);
  assert.equal(host.layers[0].outPoint, 4.08);
  assert.deepEqual(host.undo, [
    ["begin", "FSTR Line: Move Clip"],
    ["end"]
  ]);
});

test("trim changes only the requested edge", () => {
  const host = createHost();

  let response = result(host.api.trimLayerInFrames(101, 1));
  assert.equal(response.ok, true);
  assert.equal(host.layers[0].startTime, 0);
  assert.equal(host.layers[0].inPoint, 1.04);
  assert.equal(host.layers[0].outPoint, 4);

  host.undo.length = 0;
  response = result(host.api.trimLayerOutFrames(101, -1));
  assert.equal(response.ok, true);
  assert.equal(host.layers[0].startTime, 0);
  assert.equal(host.layers[0].inPoint, 1.04);
  assert.equal(host.layers[0].outPoint, 3.96);
  assert.deepEqual(host.undo, [
    ["begin", "FSTR Line: Trim Out"],
    ["end"]
  ]);
});

test("invalid trim is rejected with a structured error", () => {
  const host = createHost();
  const response = result(host.api.trimLayerInFrames(101, 1000));

  assert.equal(response.ok, false);
  assert.match(response.error.message, /duration zero or negative/i);
  assert.deepEqual(host.undo, []);
});

test("no active composition returns an empty snapshot, not a bridge failure", () => {
  const host = createHost();
  host.app.project.activeItem = null;

  const response = result(host.api.getSnapshot());
  assert.deepEqual(response, { ok: true, data: null, error: null });
});

test("host move and trims are frame-safe across the production FPS matrix", () => {
  const frameRates = [
    24000 / 1001,
    24,
    25,
    30000 / 1001,
    30,
    50,
    60000 / 1001,
    60
  ];

  for (const frameRate of frameRates) {
    const host = createHost(frameRate);
    const frame = host.comp.frameDuration;
    const tolerance = frame / 1000000;
    const layer = host.layers[0];

    let response = result(host.api.moveLayerFrames(101, 17));
    assert.equal(response.ok, true);
    assert.ok(Math.abs(layer.startTime - 17 * frame) <= tolerance);
    assert.ok(Math.abs(layer.inPoint - (1 + 17 * frame)) <= tolerance);
    assert.ok(Math.abs(layer.outPoint - (4 + 17 * frame)) <= tolerance);

    response = result(host.api.trimLayerInFrames(101, 3));
    assert.equal(response.ok, true);
    assert.ok(Math.abs(layer.startTime - 17 * frame) <= tolerance);
    assert.ok(Math.abs(layer.inPoint - (1 + 20 * frame)) <= tolerance);

    response = result(host.api.trimLayerOutFrames(101, -5));
    assert.equal(response.ok, true);
    assert.ok(Math.abs(layer.outPoint - (4 + 12 * frame)) <= tolerance);
  }
});


test("exception inside Undo Group always closes the group and bridge remains reusable", () => {
  const host = createHost();
  host.layers[0].failOnStartTimeSet = true;

  let response = result(host.api.moveLayerFrames(101, 1));
  assert.equal(response.ok, false);
  assert.match(response.error.message, /Injected host setter failure/);
  assert.deepEqual(host.undo, [
    ["begin", "FSTR Line: Move Clip"],
    ["end"]
  ]);

  host.layers[0].failOnStartTimeSet = false;
  host.undo.length = 0;

  response = result(host.api.moveLayerFrames(101, 1));
  assert.equal(response.ok, true);
  assert.deepEqual(host.undo, [
    ["begin", "FSTR Line: Move Clip"],
    ["end"]
  ]);
});

test("deleted or stale layer ID fails before opening an Undo Group", () => {
  const host = createHost();
  host.comp.layers.shift();

  const response = result(host.api.moveLayerFrames(101, 1));

  assert.equal(response.ok, false);
  assert.match(response.error.message, /was not found/);
  assert.deepEqual(host.undo, []);
});

test("repeated move execution leaves no open or duplicate Undo transaction", () => {
  const host = createHost();
  const iterations = 100;

  for (let i = 0; i < iterations; i += 1) {
    const response = result(host.api.moveLayerFrames(101, 1));
    assert.equal(response.ok, true);
  }

  assert.equal(host.undo.length, iterations * 2);

  for (let i = 0; i < iterations; i += 1) {
    assert.deepEqual(host.undo[i * 2], ["begin", "FSTR Line: Move Clip"]);
    assert.deepEqual(host.undo[i * 2 + 1], ["end"]);
  }

  const expected = iterations * host.comp.frameDuration;
  assert.ok(Math.abs(host.layers[0].startTime - expected) < 1e-9);
});

test("failed operation followed by repeated trims stays recoverable", () => {
  const host = createHost();

  let response = result(host.api.trimLayerInFrames(101, 1000));
  assert.equal(response.ok, false);
  assert.deepEqual(host.undo, []);

  for (let i = 0; i < 20; i += 1) {
    response = result(host.api.trimLayerOutFrames(101, -1));
    assert.equal(response.ok, true);
  }

  assert.equal(host.undo.length, 40);
  assert.equal(
    host.undo.filter((entry) => entry[0] === "begin").length,
    host.undo.filter((entry) => entry[0] === "end").length
  );
});

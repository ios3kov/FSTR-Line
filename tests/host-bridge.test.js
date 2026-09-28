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
  constructor(layers) {
    this.id = 500;
    this.name = "Mock Comp";
    this.duration = 10;
    this.frameRate = 25;
    this.frameDuration = 1 / 25;
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

function createHost() {
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

  const comp = new CompItem(layers);
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

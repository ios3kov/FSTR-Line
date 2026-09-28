const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const adapterSource = fs.readFileSync("host/cep/cep-adapter.js", "utf8");

function createAdapter(responder) {
  const calls = [];

  function CSInterface() {}
  CSInterface.prototype.evalScript = function (expression, callback) {
    calls.push(expression);
    callback(responder(expression));
  };

  const window = {
    CSInterface,
    Promise,
    JSON,
    Error,
    TypeError,
    isFinite,
    Math
  };

  const context = vm.createContext({ window });
  vm.runInContext(adapterSource, context, { filename: "host/cep/cep-adapter.js" });

  return {
    adapter: window.FSTRLineCEPAdapter,
    calls
  };
}

function ok(data) {
  return JSON.stringify({ ok: true, data, error: null });
}

test("adapter emits numeric-only host expressions", async () => {
  const harness = createAdapter(() => ok({ synced: true }));

  await harness.adapter.selectLayer(42, true);
  await harness.adapter.moveLayerFrames(42, -1);
  await harness.adapter.trimLayerInFrames(42, 1);
  await harness.adapter.trimLayerOutFrames(42, -2);

  assert.deepEqual(harness.calls, [
    "$._fstr.selectLayer(42,true)",
    "$._fstr.moveLayerFrames(42,-1)",
    "$._fstr.trimLayerInFrames(42,1)",
    "$._fstr.trimLayerOutFrames(42,-2)"
  ]);
});

test("adapter rejects non-integer arguments before evalScript", async () => {
  const harness = createAdapter(() => ok(null));

  await assert.rejects(
    harness.adapter.moveLayerFrames(42, 0.5),
    /deltaFrames must be an integer/
  );
  assert.deepEqual(harness.calls, []);
});

test("adapter surfaces structured host errors", async () => {
  const harness = createAdapter(() => JSON.stringify({
    ok: false,
    data: null,
    error: { message: "Layer is locked." }
  }));

  await assert.rejects(
    harness.adapter.getSnapshot(),
    /Layer is locked/
  );
});

test("adapter rejects malformed evalScript responses", async () => {
  const harness = createAdapter(() => "not-json");

  await assert.rejects(
    harness.adapter.getSnapshot(),
    /Invalid response/
  );
});

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");

const smoke = fs.readFileSync("tests/ae/runtime-smoke.jsx", "utf8");
const runner = fs.readFileSync("scripts/run-ae-smoke.mjs", "utf8");

test("real-AE smoke refuses non-clean projects", () => {
  assert.match(
    smoke,
    /app\.project\.numItems === 0 && app\.project\.file === null/
  );
});

test("real-AE smoke exercises the production host bridge", () => {
  assert.match(smoke, /host\/cep\/host\.jsx/);
  assert.match(smoke, /\$\._fstr\.getSnapshot\(\)/);
  assert.match(smoke, /\$\._fstr\.selectLayer/);
  assert.match(smoke, /\$\._fstr\.moveLayerFrames/);
  assert.match(smoke, /\$\._fstr\.trimLayerInFrames/);
  assert.match(smoke, /\$\._fstr\.trimLayerOutFrames/);
});

test("real-AE smoke checks save-reopen identity", () => {
  assert.match(smoke, /app\.project\.save\(tempFile\)/);
  assert.match(smoke, /app\.open\(tempFile\)/);
  assert.match(smoke, /Layer\.id survives save\/reopen/);
});

test("real-AE smoke closes test projects without saving", () => {
  assert.match(
    smoke,
    /app\.project\.close\(CloseOptions\.DO_NOT_SAVE_CHANGES\)/
  );
});

test("mac runner refuses to reuse a running AE session", () => {
  assert.match(runner, /After Effects is already running/);
  assert.match(runner, /pgrep/);
  assert.match(runner, /ae\.doscriptfile/);
  assert.match(runner, /ae\.doscript\('\$\._fstrRuntimeResult;'\)/);
});

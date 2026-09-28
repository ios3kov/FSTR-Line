const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");

const smoke = fs.readFileSync("tests/ae/runtime-smoke.jsx", "utf8");
const runner = fs.readFileSync("scripts/run-ae-smoke.mjs", "utf8");
const installedVerifier = fs.readFileSync("scripts/installed-payload.mjs", "utf8");

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

test("real-AE smoke profiles host scaling to 1000 layers", () => {
  assert.match(smoke, /var scaleCounts = \[10, 50, 200, 500, 1000\]/);
  assert.match(smoke, /snapshotMicroseconds/);
  assert.match(smoke, /selectBottomMicroseconds/);
  assert.match(smoke, /moveBottomMicroseconds/);
});

test("mac runner retries AE startup and falls back from DoScriptFile", () => {
  assert.match(runner, /attempt < 20/);
  assert.match(runner, /helper\.delay\(0\.5\)/);
  assert.match(runner, /ae\.doscriptfile\(smokePath\)/);
  assert.match(runner, /\$\.evalFile\(new File/);
});

test("runtime smoke exposes process exit code and memory baseline", () => {
  assert.match(smoke, /app\.exitCode = report\.pass \? 0 : 1/);
  assert.match(smoke, /app\.exitAfterLaunchAndEval = true/);
  assert.match(smoke, /startBytes: app\.memoryInUse/);
  assert.match(smoke, /scaleDeltaBytes/);
});

test("runtime launcher supports Windows AfterFX -r", () => {
  assert.match(runner, /discoverWindowsExe/);
  assert.match(runner, /AfterFX\.exe/);
  assert.match(runner, /\["-r", test\.wrapperPath\]/);
  assert.match(runner, /process\.platform === "win32"/);
});

test("real-AE smoke is bound to the installed Build Identity", () => {
  assert.match(smoke, /\$\._fstrTestConfig/);
  assert.match(smoke, /Runtime Build ID matches installed artifact/);
  assert.match(smoke, /Runtime Git commit matches installed artifact/);
  assert.match(smoke, /\$\._fstr\.getBuildInfo\(\)/);
  assert.doesNotMatch(smoke, /parent\.parent\.parent/);

  assert.match(runner, /verifyInstalledPayload/);
  assert.match(runner, /installed-payload\.mjs/);
  assert.match(installedVerifier, /BUILD_MANIFEST\.json/);
  assert.match(runner, /runtime-smoke-runner\.jsx/);
  assert.match(runner, /testRunId/);
  assert.match(runner, /Runtime report Test Run ID mismatch/);
  assert.match(installedVerifier, /Installed payload hash mismatch/);
  assert.match(installedVerifier, /Installed payload file set mismatch/);
});

test("real-AE runner writes immutable Test Run evidence records", () => {
  assert.match(runner, /EVIDENCE_ROOT/);
  assert.match(runner, /test-record\.json/);
  assert.match(runner, /status: "PASS"/);
  assert.match(runner, /status: "BLOCKED"/);
  assert.match(runner, /Installed FSTR Line CEP runtime smoke/);
  assert.match(runner, /artifactManifestSha256/);
  assert.match(runner, /CEP browser-panel docking\/rendering is not proven/);
});

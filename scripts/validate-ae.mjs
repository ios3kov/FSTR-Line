import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

function run(script) {
  const result = spawnSync(process.execPath, [path.join(ROOT, "scripts", script)], {
    stdio: "inherit",
    timeout: 600000
  });

  if (result.error) {
    throw result.error;
  }

  if (result.status !== 0) {
    throw new Error(script + " failed with exit code " + result.status);
  }
}

run("install-dev.mjs");
run("run-ae-smoke.mjs");

console.log("FSTR Line clean AE validation completed.");

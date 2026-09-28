import fs from "node:fs/promises";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const SMOKE_SCRIPT = path.join(ROOT, "tests", "ae", "runtime-smoke.jsx");

function command(command, args, options) {
  return spawnSync(command, args, {
    encoding: "utf8",
    timeout: 180000,
    ...options
  });
}

function aeIsRunning() {
  if (process.platform === "darwin") {
    const result = command("pgrep", ["-f", "Adobe After Effects"], { timeout: 5000 });
    return result.status === 0 && result.stdout.trim().length > 0;
  }

  if (process.platform === "win32") {
    const result = command("tasklist", ["/FI", "IMAGENAME eq AfterFX.exe"], { timeout: 5000 });
    return result.status === 0 && /AfterFX\.exe/i.test(result.stdout);
  }

  return false;
}

function naturalVersion(name) {
  const match = name.match(/(20\d{2}|\d+(?:\.\d+)?)/g);
  if (!match || match.length === 0) {
    return 0;
  }
  const value = match[match.length - 1];
  return Number(value.replace(".", "")) || 0;
}

async function discoverMacApp() {
  if (process.env.FSTR_AE_APP) {
    return process.env.FSTR_AE_APP;
  }

  const applications = "/Applications";
  const entries = await fs.readdir(applications, { withFileTypes: true });
  const candidates = [];

  for (const entry of entries) {
    if (!entry.isDirectory() || !/^Adobe After Effects/i.test(entry.name)) {
      continue;
    }

    const folder = path.join(applications, entry.name);
    const children = await fs.readdir(folder, { withFileTypes: true });

    for (const child of children) {
      if (child.isDirectory() && /Adobe After Effects.*\.app$/i.test(child.name)) {
        candidates.push(path.join(folder, child.name));
      }
    }
  }

  candidates.sort(function (a, b) {
    return naturalVersion(b) - naturalVersion(a) || b.localeCompare(a);
  });

  if (candidates.length === 0) {
    throw new Error(
      "After Effects was not found in /Applications. Set FSTR_AE_APP to the .app path."
    );
  }

  return candidates[0];
}

function jxaString(value) {
  return JSON.stringify(value);
}

async function runMacSmoke() {
  const appPath = await discoverMacApp();
  const appName = path.basename(appPath, ".app");

  const jxa = [
    "const ae = Application(" + jxaString(appName) + ");",
    "let result = null;",
    "try {",
    "  ae.activate();",
    "  ae.doscriptfile(" + jxaString(SMOKE_SCRIPT) + ");",
    "  result = ae.doscript('$._fstrRuntimeResult;');",
    "  console.log(result);",
    "} finally {",
    "  try { ae.quit(); } catch (e) {}",
    "}"
  ].join("\n");

  const result = command("osascript", ["-l", "JavaScript", "-e", jxa]);

  if (result.error) {
    throw result.error;
  }

  if (result.status !== 0) {
    throw new Error(
      "osascript failed: " + (result.stderr || result.stdout || "").trim()
    );
  }

  const lines = result.stdout
    .split(/\r?\n/)
    .map(function (line) { return line.trim(); })
    .filter(Boolean);

  if (lines.length === 0) {
    throw new Error("After Effects returned no runtime-smoke result.");
  }

  let report;
  try {
    report = JSON.parse(lines[lines.length - 1]);
  } catch (error) {
    throw new Error(
      "Could not parse After Effects runtime-smoke result: " +
      lines[lines.length - 1]
    );
  }

  if (report.tempProject) {
    await fs.rm(report.tempProject, { force: true }).catch(function () {});
  }

  console.log(JSON.stringify(report, null, 2));

  if (!report.pass) {
    process.exitCode = 1;
  }
}

async function main() {
  if (aeIsRunning()) {
    throw new Error(
      "After Effects is already running. Close it first so the runtime smoke starts clean."
    );
  }

  if (process.platform === "darwin") {
    await runMacSmoke();
    return;
  }

  throw new Error(
    "Automated runtime-smoke launching is currently implemented for macOS only. " +
    "The JSX test itself is platform-independent."
  );
}

main().catch(function (error) {
  console.error(error.stack || error);
  process.exitCode = 1;
});

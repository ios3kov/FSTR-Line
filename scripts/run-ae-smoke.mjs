import fs from "node:fs/promises";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const SMOKE_SCRIPT = path.join(ROOT, "tests", "ae", "runtime-smoke.jsx");

function command(command, args, options) {
  return spawnSync(command, args, {
    encoding: "utf8",
    timeout: 300000,
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

async function discoverWindowsExe() {
  if (process.env.FSTR_AE_EXE) {
    return process.env.FSTR_AE_EXE;
  }

  const programFiles = process.env.ProgramFiles || "C:\\Program Files";
  const adobeRoot = path.join(programFiles, "Adobe");
  const entries = await fs.readdir(adobeRoot, { withFileTypes: true });
  const candidates = [];

  for (const entry of entries) {
    if (!entry.isDirectory() || !/^Adobe After Effects/i.test(entry.name)) {
      continue;
    }

    const executable = path.join(adobeRoot, entry.name, "Support Files", "AfterFX.exe");
    try {
      await fs.access(executable);
      candidates.push(executable);
    } catch {
    }
  }

  candidates.sort(function (a, b) {
    return naturalVersion(b) - naturalVersion(a) || b.localeCompare(a);
  });

  if (candidates.length === 0) {
    throw new Error(
      "After Effects was not found under Program Files/Adobe. " +
      "Set FSTR_AE_EXE to AfterFX.exe."
    );
  }

  return candidates[0];
}

function parseRuntimeMarker(output) {
  const lines = String(output || "").split(/\r?\n/);
  for (let i = lines.length - 1; i >= 0; i -= 1) {
    const marker = "FSTR_LINE_RUNTIME_RESULT=";
    const index = lines[i].indexOf(marker);
    if (index !== -1) {
      try {
        return JSON.parse(lines[i].slice(index + marker.length));
      } catch {
        return null;
      }
    }
  }
  return null;
}

async function runWindowsSmoke() {
  const executable = await discoverWindowsExe();
  const result = command(executable, ["-r", SMOKE_SCRIPT], { timeout: 300000 });

  if (result.error) {
    throw result.error;
  }

  const output = [result.stdout || "", result.stderr || ""].join("\n");
  const report = parseRuntimeMarker(output);

  if (report && report.tempProject) {
    await fs.rm(report.tempProject, { force: true }).catch(function () {});
  }

  if (report) {
    console.log(JSON.stringify(report, null, 2));
  } else if (output.trim()) {
    console.log(output.trim());
  }

  if (result.status !== 0) {
    throw new Error(
      "After Effects runtime smoke failed with exit code " +
      result.status +
      (output.trim() ? ": " + output.trim() : "")
    );
  }

  console.log("After Effects runtime smoke passed on Windows.");
}

async function runMacSmoke() {
  const appPath = await discoverMacApp();
  const appName = path.basename(appPath, ".app");

  const jxa = [
    "const helper = Application.currentApplication();",
    "helper.includeStandardAdditions = true;",
    "const ae = Application(" + jxaString(appName) + ");",
    "const smokePath = " + jxaString(SMOKE_SCRIPT) + ";",
    "function pause() { helper.delay(0.5); }",
    "function executeSmoke() {",
    "  let lastError = null;",
    "  for (let attempt = 0; attempt < 20; attempt += 1) {",
    "    try {",
    "      ae.activate();",
    "      try {",
    "        ae.doscriptfile(smokePath);",
    "      } catch (fileError) {",
    "        ae.doscript('$.evalFile(new File(' + JSON.stringify(smokePath) + '));');",
    "      }",
    "      return;",
    "    } catch (error) {",
    "      lastError = error;",
    "      pause();",
    "    }",
    "  }",
    "  throw lastError || new Error('After Effects did not accept the runtime smoke script.');",
    "}",
    "function readResult() {",
    "  let lastError = null;",
    "  for (let attempt = 0; attempt < 20; attempt += 1) {",
    "    try {",
    "      return ae.doscript('$._fstrRuntimeResult;');",
    "    } catch (error) {",
    "      lastError = error;",
    "      pause();",
    "    }",
    "  }",
    "  throw lastError || new Error('After Effects runtime result is unavailable.');",
    "}",
    "let result = null;",
    "try {",
    "  executeSmoke();",
    "  result = readResult();",
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

  if (process.platform === "win32") {
    await runWindowsSmoke();
    return;
  }

  throw new Error("Automated runtime smoke supports macOS and Windows only.");
}

main().catch(function (error) {
  console.error(error.stack || error);
  process.exitCode = 1;
});

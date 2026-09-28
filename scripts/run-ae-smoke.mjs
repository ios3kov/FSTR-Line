import crypto from "node:crypto";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const SMOKE_SCRIPT = path.join(ROOT, "tests", "ae", "runtime-smoke.jsx");

function command(commandName, args, options) {
  return spawnSync(commandName, args, {
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

function userExtensionRoot() {
  if (process.platform === "darwin") {
    return path.join(os.homedir(), "Library", "Application Support", "Adobe", "CEP", "extensions");
  }
  if (process.platform === "win32") {
    if (!process.env.APPDATA) {
      throw new Error("APPDATA is not defined.");
    }
    return path.join(process.env.APPDATA, "Adobe", "CEP", "extensions");
  }
  throw new Error("Automated runtime smoke supports macOS and Windows only.");
}

function naturalVersion(name) {
  const match = name.match(/(20\d{2}|\d+(?:\.\d+)?)/g);
  if (!match || match.length === 0) {
    return 0;
  }
  const value = match[match.length - 1];
  return Number(value.replace(".", "")) || 0;
}

async function sha256(filePath) {
  const data = await fs.readFile(filePath);
  return crypto.createHash("sha256").update(data).digest("hex");
}

async function verifyInstalledPayload(extensionRoot) {
  const manifestPath = path.join(extensionRoot, "BUILD_MANIFEST.json");
  const buildInfoPath = path.join(extensionRoot, "generated", "build-info.json");
  const manifest = JSON.parse(await fs.readFile(manifestPath, "utf8"));
  const buildInfo = JSON.parse(await fs.readFile(buildInfoPath, "utf8"));

  if (
    !manifest.buildIdentity ||
    manifest.buildIdentity.buildId !== buildInfo.buildId ||
    manifest.buildIdentity.gitCommit !== buildInfo.gitCommit
  ) {
    throw new Error("Installed Build Identity metadata is inconsistent.");
  }

  for (const entry of manifest.files || []) {
    const installedPath = path.join(extensionRoot, ...entry.path.split("/"));
    const actual = await sha256(installedPath);
    if (actual !== entry.sha256) {
      throw new Error("Installed payload hash mismatch: " + entry.path);
    }
  }

  return {
    buildInfo,
    manifestSha256: await sha256(manifestPath)
  };
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

function verifyReport(report, expected) {
  if (!report) {
    throw new Error("After Effects returned no structured runtime report.");
  }
  if (report.testRunId !== expected.testRunId) {
    throw new Error("Runtime report Test Run ID mismatch.");
  }
  if (!report.runtimeBuildInfo) {
    throw new Error("Runtime report has no Build Identity.");
  }
  if (report.runtimeBuildInfo.buildId !== expected.expectedBuildId) {
    throw new Error("Runtime Build ID mismatch.");
  }
  if (report.runtimeBuildInfo.gitCommit !== expected.expectedGitCommit) {
    throw new Error("Runtime Git commit mismatch.");
  }
  if (!report.pass) {
    throw new Error(
      "After Effects runtime smoke reported FAIL: " +
      (report.error && report.error.message ? report.error.message : "unknown error")
    );
  }
}

async function createTestWorkspace(installed) {
  const testRunId =
    "ae-smoke-" +
    Date.now() +
    "-" +
    crypto.randomBytes(6).toString("hex");
  const workspace = path.join(os.tmpdir(), "fstr-line-ae-smoke", testRunId);
  await fs.rm(workspace, { recursive: true, force: true });
  await fs.mkdir(workspace, { recursive: true });

  const config = {
    schemaVersion: 1,
    testRunId,
    extensionRoot: installed.extensionRoot,
    expectedBuildId: installed.buildInfo.buildId,
    expectedGitCommit: installed.buildInfo.gitCommit,
    tempProjectPath: path.join(workspace, "runtime-smoke.aep")
  };

  const wrapperPath = path.join(workspace, "runtime-smoke-runner.jsx");
  const wrapper =
    "$._fstrTestConfig = " +
    JSON.stringify(config) +
    ";\n$.evalFile(new File(" +
    JSON.stringify(SMOKE_SCRIPT) +
    "));\n";

  await fs.writeFile(wrapperPath, wrapper, "utf8");
  return { testRunId, workspace, wrapperPath, config };
}

function jxaString(value) {
  return JSON.stringify(value);
}

async function runWindowsSmoke(executable, test) {
  const result = command(executable, ["-r", test.wrapperPath], { timeout: 300000 });

  if (result.error) {
    throw result.error;
  }

  const output = [result.stdout || "", result.stderr || ""].join("\n");
  const report = parseRuntimeMarker(output);

  if (result.status !== 0 && !report) {
    throw new Error(
      "After Effects runtime smoke failed with exit code " +
      result.status +
      (output.trim() ? ": " + output.trim() : "")
    );
  }

  return report;
}

async function runMacSmoke(appPath, test) {
  const appName = path.basename(appPath, ".app");

  const jxa = [
    "const helper = Application.currentApplication();",
    "helper.includeStandardAdditions = true;",
    "const ae = Application(" + jxaString(appName) + ");",
    "const smokePath = " + jxaString(test.wrapperPath) + ";",
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

  try {
    return JSON.parse(lines[lines.length - 1]);
  } catch {
    throw new Error(
      "Could not parse After Effects runtime-smoke result for the current Test Run."
    );
  }
}

async function main() {
  if (aeIsRunning()) {
    throw new Error(
      "BLOCKED: After Effects is already running. " +
      "The smoke runner will not terminate a process that may contain unsaved work."
    );
  }

  const extensionRoot =
    process.env.FSTR_EXTENSION_ROOT ||
    path.join(userExtensionRoot(), "FSTR-Line");
  const installed = await verifyInstalledPayload(extensionRoot);
  installed.extensionRoot = extensionRoot;

  const test = await createTestWorkspace(installed);

  console.log("Test Run ID: " + test.testRunId);
  console.log("Expected Build ID: " + installed.buildInfo.buildId);
  console.log("Expected commit: " + installed.buildInfo.gitCommit);
  console.log("Installed BUILD_MANIFEST SHA-256: " + installed.manifestSha256);

  try {
    let report;

    if (process.platform === "darwin") {
      report = await runMacSmoke(await discoverMacApp(), test);
    } else if (process.platform === "win32") {
      report = await runWindowsSmoke(await discoverWindowsExe(), test);
    } else {
      throw new Error("Automated runtime smoke supports macOS and Windows only.");
    }

    verifyReport(report, test.config);
    console.log(JSON.stringify(report, null, 2));
    console.log("After Effects runtime smoke PASS for Test Run ID: " + test.testRunId);
  } finally {
    await fs.rm(test.workspace, { recursive: true, force: true }).catch(function () {});
  }
}

main().catch(function (error) {
  console.error(error.stack || error);
  process.exitCode = 1;
});

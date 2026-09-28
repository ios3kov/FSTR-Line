import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { DIST_DIR, packageExtension } from "./package-extension.mjs";
import { verifyPackage } from "./verify-package.mjs";

const BUNDLE_ID = "com.fstr.line";
const EXTENSION_ID = "com.fstr.line.panel";
const INSTALL_FOLDER = "FSTR-Line";

function run(command, args) {
  return spawnSync(command, args, { encoding: "utf8" });
}

function afterEffectsIsRunning() {
  if (process.platform === "darwin") {
    const result = run("pgrep", ["-f", "Adobe After Effects"]);
    return result.status === 0 && result.stdout.trim().length > 0;
  }

  if (process.platform === "win32") {
    const result = run("tasklist", ["/FI", "IMAGENAME eq AfterFX.exe"]);
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
  throw new Error("Development install is supported on macOS and Windows only.");
}

function systemExtensionRoots() {
  if (process.platform === "darwin") {
    return ["/Library/Application Support/Adobe/CEP/extensions"];
  }
  if (process.platform === "win32") {
    return [
      path.join(process.env.ProgramFiles || "C:\\Program Files", "Common Files", "Adobe", "CEP", "extensions"),
      path.join(process.env["ProgramFiles(x86)"] || "C:\\Program Files (x86)", "Common Files", "Adobe", "CEP", "extensions")
    ];
  }
  return [];
}

async function findBundleDuplicates(root) {
  let entries;
  try {
    entries = await fs.readdir(root, { withFileTypes: true });
  } catch {
    return [];
  }

  const matches = [];
  for (const entry of entries) {
    if (!entry.isDirectory()) {
      continue;
    }

    const manifestPath = path.join(root, entry.name, "CSXS", "manifest.xml");
    try {
      const manifest = await fs.readFile(manifestPath, "utf8");
      if (manifest.includes('ExtensionBundleId="' + BUNDLE_ID + '"')) {
        matches.push(path.join(root, entry.name));
      }
    } catch {
    }
  }

  return matches;
}

async function isFstrBundle(folder) {
  try {
    const manifest = await fs.readFile(
      path.join(folder, "CSXS", "manifest.xml"),
      "utf8"
    );
    return manifest.includes('ExtensionBundleId="' + BUNDLE_ID + '"');
  } catch {
    return false;
  }
}

async function pathExists(target) {
  try {
    await fs.access(target);
    return true;
  } catch {
    return false;
  }
}

async function removeEntriesContaining(root, needle) {
  let entries;
  try {
    entries = await fs.readdir(root, { withFileTypes: true });
  } catch {
    return 0;
  }

  let removed = 0;
  for (const entry of entries) {
    const fullPath = path.join(root, entry.name);

    if (entry.name.includes(needle)) {
      await fs.rm(fullPath, { recursive: true, force: true });
      removed += 1;
      continue;
    }

    if (entry.isDirectory()) {
      removed += await removeEntriesContaining(fullPath, needle);
    }
  }

  return removed;
}

function unsignedDevelopmentEnabled() {
  const versions = ["11", "12"];

  if (process.platform === "darwin") {
    return versions.some(function (version) {
      const result = run("defaults", [
        "read",
        "com.adobe.CSXS." + version,
        "PlayerDebugMode"
      ]);
      return result.status === 0 && String(result.stdout || "").trim() === "1";
    });
  }

  if (process.platform === "win32") {
    return versions.some(function (version) {
      const result = run("reg", [
        "query",
        "HKCU\\Software\\Adobe\\CSXS." + version,
        "/v",
        "PlayerDebugMode"
      ]);
      return (
        result.status === 0 &&
        /PlayerDebugMode\s+REG_SZ\s+1/i.test(String(result.stdout || ""))
      );
    });
  }

  return false;
}

async function cleanFstrCepCache() {
  let cacheRoot;

  if (process.platform === "darwin") {
    cacheRoot = path.join(os.homedir(), "Library", "Caches", "CSXS", "cep_cache");
  } else if (process.platform === "win32") {
    cacheRoot = path.join(os.tmpdir(), "cep_cache");
  } else {
    return 0;
  }

  return removeEntriesContaining(cacheRoot, EXTENSION_ID);
}

if (afterEffectsIsRunning()) {
  throw new Error(
    "BLOCKED: After Effects is already running. " +
    "The clean installer will not terminate a process that may contain unsaved work."
  );
}

const packageResult = await packageExtension();
const verification = await verifyPackage({ requireClean: true });

if (!unsignedDevelopmentEnabled()) {
  throw new Error(
    "BLOCKED: unsigned CEP development is disabled. " +
    "FSTR Line will not change PlayerDebugMode automatically. " +
    "Explicit permission or a signed CEP package is required before runtime installation."
  );
}

const installRoot = userExtensionRoot();
const target = path.join(installRoot, INSTALL_FOLDER);

for (const root of systemExtensionRoots()) {
  const duplicates = await findBundleDuplicates(root);
  if (duplicates.length > 0) {
    throw new Error(
      "BLOCKED: a system-level FSTR Line bundle would override the test install: " +
      duplicates.map(function (item) { return path.basename(item); }).join(", ")
    );
  }
}

await fs.mkdir(installRoot, { recursive: true });

const perUserDuplicates = await findBundleDuplicates(installRoot);
const unexpectedDuplicates = perUserDuplicates.filter(function (item) {
  return path.resolve(item) !== path.resolve(target);
});

if (unexpectedDuplicates.length > 0) {
  throw new Error(
    "BLOCKED: additional per-user FSTR Line bundles exist and will not be deleted automatically: " +
    unexpectedDuplicates.map(function (item) { return path.basename(item); }).join(", ")
  );
}

let backup = null;
if (await pathExists(target)) {
  if (!(await isFstrBundle(target))) {
    throw new Error(
      "BLOCKED: target install folder exists but is not an identifiable FSTR Line bundle."
    );
  }

  backup = path.join(
    os.tmpdir(),
    "fstr-line-install-backup-" + process.pid + "-" + Date.now()
  );
  await fs.cp(target, backup, { recursive: true, force: true });
}

try {
  await fs.rm(target, { recursive: true, force: true });
  const removedCacheEntries = await cleanFstrCepCache();
  await fs.cp(DIST_DIR, target, { recursive: true, force: true });

  console.log("Installed Build ID: " + verification.buildIdentity.buildId);
  console.log("Installed commit: " + verification.buildIdentity.gitCommit);
  console.log("Cleaned FSTR Line CEP cache entries: " + removedCacheEntries);
  console.log("Clean development install complete: per-user FSTR-Line CEP bundle.");
} catch (error) {
  await fs.rm(target, { recursive: true, force: true }).catch(function () {});
  if (backup) {
    await fs.cp(backup, target, { recursive: true, force: true });
  }
  throw error;
} finally {
  if (backup) {
    await fs.rm(backup, { recursive: true, force: true }).catch(function () {});
  }
}

console.log(
  "Installed " +
  packageResult.files +
  " production files plus BUILD_MANIFEST.json"
);

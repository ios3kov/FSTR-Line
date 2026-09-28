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
  const result = spawnSync(command, args, { encoding: "utf8" });
  if (result.status !== 0) {
    const details = (result.stderr || result.stdout || "").trim();
    throw new Error(command + " failed" + (details ? ": " + details : ""));
  }
}

function afterEffectsIsRunning() {
  if (process.platform === "darwin") {
    const result = spawnSync("pgrep", ["-f", "Adobe After Effects"], { encoding: "utf8" });
    return result.status === 0 && result.stdout.trim().length > 0;
  }

  if (process.platform === "win32") {
    const result = spawnSync("tasklist", ["/FI", "IMAGENAME eq AfterFX.exe"], { encoding: "utf8" });
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
      if (manifest.includes("ExtensionBundleId=\"" + BUNDLE_ID + "\"")) {
        matches.push(path.join(root, entry.name));
      }
    } catch {
    }
  }

  return matches;
}

async function removeFilesContaining(root, needle) {
  let entries;
  try {
    entries = await fs.readdir(root, { withFileTypes: true });
  } catch {
    return 0;
  }

  let removed = 0;
  for (const entry of entries) {
    const fullPath = path.join(root, entry.name);
    if (entry.isDirectory()) {
      removed += await removeFilesContaining(fullPath, needle);
    } else if (entry.isFile() && entry.name.includes(needle)) {
      await fs.rm(fullPath, { force: true });
      removed += 1;
    }
  }
  return removed;
}

function enableUnsignedDevelopment() {
  if (process.platform === "darwin") {
    for (const version of ["11", "12"]) {
      run("defaults", ["write", "com.adobe.CSXS." + version, "PlayerDebugMode", "-string", "1"]);
    }
    return;
  }

  if (process.platform === "win32") {
    for (const version of ["11", "12"]) {
      run("reg", [
        "add",
        "HKCU\\Software\\Adobe\\CSXS." + version,
        "/v",
        "PlayerDebugMode",
        "/t",
        "REG_SZ",
        "/d",
        "1",
        "/f"
      ]);
    }
  }
}

async function cleanFstrCepState() {
  let cacheRoot;
  let logRoot;

  if (process.platform === "darwin") {
    cacheRoot = path.join(os.homedir(), "Library", "Caches", "CSXS", "cep_cache");
    logRoot = path.join(os.homedir(), "Library", "Logs", "CSXS");
  } else if (process.platform === "win32") {
    cacheRoot = path.join(os.tmpdir(), "cep_cache");
    logRoot = os.tmpdir();
  } else {
    return;
  }

  await removeFilesContaining(cacheRoot, EXTENSION_ID);
  await removeFilesContaining(logRoot, EXTENSION_ID);
}

if (afterEffectsIsRunning()) {
  throw new Error("Close After Effects before a clean FSTR Line development install.");
}

for (const root of systemExtensionRoots()) {
  const duplicates = await findBundleDuplicates(root);
  if (duplicates.length > 0) {
    throw new Error(
      "A system-level FSTR Line copy would override the clean per-user build: " +
      duplicates.join(", ")
    );
  }
}

const packageResult = await packageExtension();
const installRoot = userExtensionRoot();
const target = path.join(installRoot, INSTALL_FOLDER);

await fs.mkdir(installRoot, { recursive: true });
await fs.rm(target, { recursive: true, force: true });
await cleanFstrCepState();
await fs.cp(DIST_DIR, target, { recursive: true, force: true });
enableUnsignedDevelopment();

console.log("Clean development install complete: " + target);
console.log("Installed " + packageResult.files + " source files plus BUILD_MANIFEST.json");

import crypto from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";
import { DIST_DIR } from "./package-extension.mjs";

const REQUIRED_FILES = [
  "CSXS/manifest.xml",
  "core/timeline-core.js",
  "host/cep/host.jsx",
  "host/cep/cep-adapter.js",
  "index.html",
  "ui/panel.css",
  "ui/panel.js",
  "vendor/CSInterface.js",
  "vendor/json2.js"
];

async function listFiles(root, current) {
  current = current || "";
  const directory = path.join(root, current);
  const entries = await fs.readdir(directory, { withFileTypes: true });
  let output = [];

  for (const entry of entries) {
    const relative = path.join(current, entry.name);
    if (entry.isDirectory()) {
      output = output.concat(await listFiles(root, relative));
    } else if (entry.isFile()) {
      output.push(relative.split(path.sep).join("/"));
    }
  }

  return output.sort();
}

async function digest(relativePath) {
  const data = await fs.readFile(path.join(DIST_DIR, relativePath));
  return {
    sha256: crypto.createHash("sha256").update(data).digest("hex"),
    size: data.length
  };
}

const manifestPath = path.join(DIST_DIR, "BUILD_MANIFEST.json");
const buildManifest = JSON.parse(await fs.readFile(manifestPath, "utf8"));
const actualFiles = await listFiles(DIST_DIR);
const expectedFiles = buildManifest.files.map(function (entry) {
  return entry.path;
}).sort();
const packageFiles = actualFiles.filter(function (file) {
  return file !== "BUILD_MANIFEST.json";
});

if (JSON.stringify(packageFiles) !== JSON.stringify(expectedFiles)) {
  throw new Error("Package contains files not represented by BUILD_MANIFEST.json.");
}

for (const required of REQUIRED_FILES) {
  if (!packageFiles.includes(required)) {
    throw new Error("Missing required packaged file: " + required);
  }
}

for (const forbiddenPrefix of [".git/", ".github/", "tests/", "scripts/", "docs/", "dist/"]) {
  if (packageFiles.some(function (file) { return file.startsWith(forbiddenPrefix); })) {
    throw new Error("Development-only path leaked into package: " + forbiddenPrefix);
  }
}

for (const entry of buildManifest.files) {
  const actual = await digest(entry.path);
  if (actual.sha256 !== entry.sha256 || actual.size !== entry.size) {
    throw new Error("Hash mismatch for packaged file: " + entry.path);
  }
}

const manifestXml = await fs.readFile(path.join(DIST_DIR, "CSXS", "manifest.xml"), "utf8");
if (!/Host Name="AEFT" Version="\[22\.0,99\.9\]"/.test(manifestXml)) {
  throw new Error("Packaged manifest has the wrong After Effects range.");
}
if (!/<RequiredRuntime Name="CSXS" Version="11\.0"\/>/.test(manifestXml)) {
  throw new Error("Packaged manifest has the wrong CSXS compatibility floor.");
}
if (/enable-nodejs|CEFCommandLine/i.test(manifestXml)) {
  throw new Error("Packaged manifest unexpectedly enables privileged CEF options.");
}

console.log("Verified clean package: " + packageFiles.length + " files");

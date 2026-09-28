import crypto from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { DIST_DIR } from "./package-extension.mjs";

const REQUIRED_FILES = [
  "CSXS/manifest.xml",
  "core/timeline-core.js",
  "generated/build-info.js",
  "generated/build-info.json",
  "generated/build-info.jsx",
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

export async function verifyPackage(options) {
  options = options || {};
  const requireClean = options.requireClean !== false;

  const manifestPath = path.join(DIST_DIR, "BUILD_MANIFEST.json");
  const buildManifest = JSON.parse(await fs.readFile(manifestPath, "utf8"));
  const buildInfo = JSON.parse(
    await fs.readFile(path.join(DIST_DIR, "generated", "build-info.json"), "utf8")
  );
  const actualFiles = await listFiles(DIST_DIR);
  const expectedFiles = buildManifest.files.map(function (entry) {
    return entry.path;
  }).sort();
  const packageFiles = actualFiles.filter(function (file) {
    return file !== "BUILD_MANIFEST.json";
  });

  if (buildManifest.formatVersion !== 2) {
    throw new Error("Unexpected BUILD_MANIFEST format version.");
  }

  if (
    !buildManifest.buildIdentity ||
    buildManifest.buildIdentity.buildId !== buildInfo.buildId ||
    buildManifest.buildIdentity.gitCommit !== buildInfo.gitCommit
  ) {
    throw new Error("Build Identity mismatch between manifest and generated metadata.");
  }

  if (
    typeof buildInfo.gitCommit !== "string" ||
    !/^[0-9a-f]{40}$/.test(buildInfo.gitCommit) ||
    typeof buildInfo.buildId !== "string" ||
    !buildInfo.buildId
  ) {
    throw new Error("Build Identity is incomplete.");
  }

  if (requireClean && buildInfo.gitState !== "clean") {
    throw new Error(
      "Refusing milestone/test package from dirty Git state: " + buildInfo.buildId
    );
  }

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

  const packagedHost = await fs.readFile(
    path.join(DIST_DIR, "host", "cep", "host.jsx"),
    "utf8"
  );
  const packagedHtml = await fs.readFile(path.join(DIST_DIR, "index.html"), "utf8");

  if (!packagedHost.includes('#include "../../generated/build-info.jsx"')) {
    throw new Error("Packaged host.jsx does not load Build Identity metadata.");
  }

  if (!packagedHtml.includes("./generated/build-info.js")) {
    throw new Error("Packaged panel does not load Build Identity metadata.");
  }

  const manifestDigest = crypto
    .createHash("sha256")
    .update(await fs.readFile(manifestPath))
    .digest("hex");

  return {
    files: packageFiles.length,
    buildIdentity: buildInfo,
    manifestSha256: manifestDigest
  };
}

const currentFile = fileURLToPath(import.meta.url);
if (process.argv[1] && path.resolve(process.argv[1]) === currentFile) {
  verifyPackage({ requireClean: true })
    .then(function (result) {
      console.log("Verified Build ID: " + result.buildIdentity.buildId);
      console.log("Git commit: " + result.buildIdentity.gitCommit);
      console.log("Git state: " + result.buildIdentity.gitState);
      console.log("BUILD_MANIFEST SHA-256: " + result.manifestSha256);
      console.log("Verified clean package: " + result.files + " files");
    })
    .catch(function (error) {
      console.error(error.stack || error);
      process.exitCode = 1;
    });
}

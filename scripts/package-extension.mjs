import crypto from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
export const ROOT_DIR = path.resolve(SCRIPT_DIR, "..");
export const DIST_DIR = path.join(ROOT_DIR, "dist", "FSTR-Line");

const SOURCE_ENTRIES = [
  "CSXS",
  "core",
  "host",
  "ui",
  "vendor",
  "index.html"
];

function git(args) {
  return execFileSync("git", args, {
    cwd: ROOT_DIR,
    encoding: "utf8",
    stdio: ["ignore", "pipe", "pipe"]
  }).trim();
}

async function createBuildIdentity() {
  const packageJson = JSON.parse(
    await fs.readFile(path.join(ROOT_DIR, "package.json"), "utf8")
  );
  const gitCommit = git(["rev-parse", "HEAD"]);
  const gitStatus = git(["status", "--porcelain", "--untracked-files=normal"]);
  const gitState = gitStatus ? "dirty" : "clean";
  const shortCommit = gitCommit.slice(0, 12);

  return {
    schemaVersion: 1,
    product: "FSTR Line",
    version: packageJson.version,
    artifactType: "cep-extension",
    extensionId: "com.fstr.line.panel",
    gitCommit: gitCommit,
    gitState: gitState,
    buildId:
      "FSTR-Line@" +
      packageJson.version +
      "+" +
      shortCommit +
      "." +
      gitState +
      ".cep",
    target: {
      host: "After Effects 22+",
      runtime: "CEP/CSXS 11+",
      platforms: ["macOS", "Windows"]
    },
    toolchain: {
      node: process.version,
      buildPlatform: process.platform,
      buildArch: process.arch
    }
  };
}

async function copyEntry(relativePath) {
  const source = path.join(ROOT_DIR, relativePath);
  const destination = path.join(DIST_DIR, relativePath);

  await fs.cp(source, destination, {
    recursive: true,
    force: true,
    filter: function (src) {
      return path.basename(src) !== ".DS_Store";
    }
  });
}

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

async function sha256(filePath) {
  const data = await fs.readFile(filePath);
  return {
    sha256: crypto.createHash("sha256").update(data).digest("hex"),
    size: data.length
  };
}

async function writeBuildIdentityFiles(buildIdentity) {
  const generatedDir = path.join(DIST_DIR, "generated");
  await fs.mkdir(generatedDir, { recursive: true });

  const json = JSON.stringify(buildIdentity, null, 2) + "\n";
  const compact = JSON.stringify(buildIdentity);

  await fs.writeFile(
    path.join(generatedDir, "build-info.json"),
    json,
    "utf8"
  );
  await fs.writeFile(
    path.join(generatedDir, "build-info.js"),
    "window.FSTRLineBuildInfo = " + compact + ";\n",
    "utf8"
  );
  await fs.writeFile(
    path.join(generatedDir, "build-info.jsx"),
    "$._fstrBuildInfo = " + compact + ";\n",
    "utf8"
  );

  const hostPath = path.join(DIST_DIR, "host", "cep", "host.jsx");
  const host = await fs.readFile(hostPath, "utf8");
  const hostAnchor = '#include "../../vendor/json2.js"';

  if (!host.includes(hostAnchor)) {
    throw new Error("Could not inject Build Identity into packaged host.jsx.");
  }

  await fs.writeFile(
    hostPath,
    host.replace(
      hostAnchor,
      hostAnchor + '\n#include "../../generated/build-info.jsx"'
    ),
    "utf8"
  );

  const indexPath = path.join(DIST_DIR, "index.html");
  const html = await fs.readFile(indexPath, "utf8");
  const htmlAnchor = '<script src="./vendor/CSInterface.js"></script>';

  if (!html.includes(htmlAnchor)) {
    throw new Error("Could not inject Build Identity into packaged index.html.");
  }

  await fs.writeFile(
    indexPath,
    html.replace(
      htmlAnchor,
      htmlAnchor + '\n  <script src="./generated/build-info.js"></script>'
    ),
    "utf8"
  );
}

export async function packageExtension() {
  await fs.rm(DIST_DIR, { recursive: true, force: true });
  await fs.mkdir(DIST_DIR, { recursive: true });

  for (const entry of SOURCE_ENTRIES) {
    await copyEntry(entry);
  }

  const buildIdentity = await createBuildIdentity();
  await writeBuildIdentityFiles(buildIdentity);

  const packagedFiles = await listFiles(DIST_DIR);
  const manifestFiles = [];

  for (const relativePath of packagedFiles) {
    const metadata = await sha256(path.join(DIST_DIR, relativePath));
    manifestFiles.push({
      path: relativePath,
      sha256: metadata.sha256,
      size: metadata.size
    });
  }

  const buildManifest = {
    formatVersion: 2,
    package: "FSTR-Line",
    extensionId: "com.fstr.line.panel",
    buildIdentity: buildIdentity,
    sourceEntries: SOURCE_ENTRIES,
    files: manifestFiles
  };

  const manifestPath = path.join(DIST_DIR, "BUILD_MANIFEST.json");
  await fs.writeFile(
    manifestPath,
    JSON.stringify(buildManifest, null, 2) + "\n",
    "utf8"
  );

  const manifestMetadata = await sha256(manifestPath);

  return {
    directory: DIST_DIR,
    files: manifestFiles.length,
    buildIdentity: buildIdentity,
    manifestSha256: manifestMetadata.sha256
  };
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  packageExtension()
    .then(function (result) {
      console.log("Build ID: " + result.buildIdentity.buildId);
      console.log("Git commit: " + result.buildIdentity.gitCommit);
      console.log("Git state: " + result.buildIdentity.gitState);
      console.log("BUILD_MANIFEST SHA-256: " + result.manifestSha256);
      console.log("Packaged " + result.files + " source files into " + result.directory);
    })
    .catch(function (error) {
      console.error(error.stack || error);
      process.exitCode = 1;
    });
}

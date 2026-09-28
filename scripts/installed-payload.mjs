import crypto from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";

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

async function digest(filePath) {
  const data = await fs.readFile(filePath);
  return {
    sha256: crypto.createHash("sha256").update(data).digest("hex"),
    size: data.length
  };
}

function resolveManifestEntry(extensionRoot, relativePath) {
  if (
    typeof relativePath !== "string" ||
    relativePath.length === 0 ||
    path.isAbsolute(relativePath)
  ) {
    throw new Error("Installed manifest contains an unsafe file path.");
  }

  const root = path.resolve(extensionRoot);
  const resolved = path.resolve(root, ...relativePath.split("/"));

  if (resolved !== root && !resolved.startsWith(root + path.sep)) {
    throw new Error("Installed manifest path escapes the extension root.");
  }

  return resolved;
}

export async function verifyInstalledPayload(extensionRoot) {
  const root = path.resolve(extensionRoot);
  const manifestPath = path.join(root, "BUILD_MANIFEST.json");
  const buildInfoPath = path.join(root, "generated", "build-info.json");

  const manifest = JSON.parse(await fs.readFile(manifestPath, "utf8"));
  const buildInfo = JSON.parse(await fs.readFile(buildInfoPath, "utf8"));

  if (manifest.formatVersion !== 2) {
    throw new Error("Installed BUILD_MANIFEST format is unsupported.");
  }

  if (
    !manifest.buildIdentity ||
    manifest.buildIdentity.buildId !== buildInfo.buildId ||
    manifest.buildIdentity.gitCommit !== buildInfo.gitCommit
  ) {
    throw new Error("Installed Build Identity metadata is inconsistent.");
  }

  if (
    typeof buildInfo.gitCommit !== "string" ||
    !/^[0-9a-f]{40}$/.test(buildInfo.gitCommit) ||
    typeof buildInfo.buildId !== "string" ||
    buildInfo.buildId.length === 0
  ) {
    throw new Error("Installed Build Identity is incomplete.");
  }

  if (buildInfo.gitState !== "clean") {
    throw new Error("Installed payload is not a clean Build Identity.");
  }

  const entries = manifest.files || [];
  const expectedFiles = ["BUILD_MANIFEST.json"];

  for (const entry of entries) {
    resolveManifestEntry(root, entry.path);
    expectedFiles.push(entry.path);
  }

  expectedFiles.sort();
  const actualFiles = await listFiles(root);

  if (JSON.stringify(actualFiles) !== JSON.stringify(expectedFiles)) {
    const expectedSet = new Set(expectedFiles);
    const actualSet = new Set(actualFiles);
    const unexpected = actualFiles.filter((file) => !expectedSet.has(file));
    const missing = expectedFiles.filter((file) => !actualSet.has(file));

    throw new Error(
      "Installed payload file set mismatch." +
      (unexpected.length ? " Unexpected: " + unexpected.join(", ") + "." : "") +
      (missing.length ? " Missing: " + missing.join(", ") + "." : "")
    );
  }

  for (const entry of entries) {
    const installedPath = resolveManifestEntry(root, entry.path);
    const actual = await digest(installedPath);

    if (actual.sha256 !== entry.sha256 || actual.size !== entry.size) {
      throw new Error("Installed payload hash mismatch: " + entry.path);
    }
  }

  const manifestDigest = await digest(manifestPath);

  return {
    buildInfo,
    manifestSha256: manifestDigest.sha256,
    verifiedFileCount: entries.length
  };
}

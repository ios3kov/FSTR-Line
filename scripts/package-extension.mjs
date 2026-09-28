import crypto from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";
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

export async function packageExtension() {
  await fs.rm(DIST_DIR, { recursive: true, force: true });
  await fs.mkdir(DIST_DIR, { recursive: true });

  for (const entry of SOURCE_ENTRIES) {
    await copyEntry(entry);
  }

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
    formatVersion: 1,
    package: "FSTR-Line",
    extensionId: "com.fstr.line.panel",
    sourceEntries: SOURCE_ENTRIES,
    files: manifestFiles
  };

  await fs.writeFile(
    path.join(DIST_DIR, "BUILD_MANIFEST.json"),
    JSON.stringify(buildManifest, null, 2) + "\n",
    "utf8"
  );

  return {
    directory: DIST_DIR,
    files: manifestFiles.length
  };
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  packageExtension()
    .then(function (result) {
      console.log("Packaged " + result.files + " source files into " + result.directory);
    })
    .catch(function (error) {
      console.error(error.stack || error);
      process.exitCode = 1;
    });
}

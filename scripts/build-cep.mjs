import { copyFile, mkdir, readFile, writeFile } from "node:fs/promises";
import { createHash } from "node:crypto";
import { execFileSync } from "node:child_process";

await mkdir("cep/host", { recursive: true });
await copyFile("src/host/cep/host.jsx", "cep/host/host.jsx");

const gitCommit = execFileSync("git", ["rev-parse", "HEAD"], { encoding: "utf8" }).trim();
const dirty = execFileSync("git", ["status", "--porcelain"], { encoding: "utf8" }).trim().length > 0;
const files = ["cep/CSXS/manifest.xml", "cep/client/index.html", "cep/client/styles.css", "cep/client/CSInterface.js", "cep/client/app.js", "cep/host/host.jsx"];
const artifacts = {};
for (const file of files) {
  const contents = await readFile(file);
  artifacts[file] = createHash("sha256").update(contents).digest("hex");
}

await writeFile("cep/build-manifest.json", `${JSON.stringify({
  buildId: `fstr-cep-${gitCommit.slice(0, 12)}`,
  gitCommit,
  dirty,
  version: "0.1.0",
  artifactType: "CEP-panel-directory",
  artifacts,
}, null, 2)}\n`);

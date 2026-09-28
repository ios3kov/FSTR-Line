import { mkdir, readFile, writeFile } from "node:fs/promises";
import { build } from "esbuild";
import { createHash } from "node:crypto";
import { execFileSync } from "node:child_process";

await mkdir("cep/host", { recursive: true });

const gitCommit = execFileSync("git", ["rev-parse", "HEAD"], { encoding: "utf8" }).trim();
const dirty = execFileSync("git", ["status", "--porcelain"], { encoding: "utf8" }).trim().length > 0;
const identity = {
  buildId: `fstr-cep-${gitCommit.slice(0, 12)}${dirty ? "-dirty" : ""}`,
  gitCommit,
  dirty,
  version: JSON.parse(await readFile("package.json", "utf8")).version,
};
await build({
  entryPoints: ["src/cep/client-entry.ts"], bundle: true, format: "iife",
  platform: "browser", outfile: "cep/client/app.js",
  define: { FSTR_BUILD: JSON.stringify(identity) },
});
await writeFile("cep/host/host.jsx", `var FSTR_BUILD = ${JSON.stringify(identity)};\n${await readFile("src/host/cep/host.jsx", "utf8")}`);
const files = ["cep/CSXS/manifest.xml", "cep/client/index.html", "cep/client/styles.css", "cep/client/CSInterface.js", "cep/client/app.js", "cep/host/host.jsx"];
const artifacts = {};
for (const file of files) {
  const contents = await readFile(file);
  artifacts[file] = createHash("sha256").update(contents).digest("hex");
}

await writeFile("cep/build-manifest.json", `${JSON.stringify({
  ...identity,
  artifactType: "CEP-panel-directory",
  artifacts,
}, null, 2)}\n`);

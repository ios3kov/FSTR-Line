import crypto from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const OUTPUT = path.join(ROOT, "artifacts", "phase0-static-audit.json");

const checks = [];

function record(name, pass, detail) {
  checks.push({
    name,
    status: pass ? "PASS" : "FAIL",
    detail: detail || null
  });
}

async function read(relativePath) {
  return fs.readFile(path.join(ROOT, relativePath), "utf8");
}

async function collectFiles(relativeDir) {
  const root = path.join(ROOT, relativeDir);
  let entries;
  try {
    entries = await fs.readdir(root, { withFileTypes: true });
  } catch {
    return [];
  }

  let output = [];
  for (const entry of entries) {
    const relative = path.join(relativeDir, entry.name);
    if (entry.isDirectory()) {
      output = output.concat(await collectFiles(relative));
    } else if (entry.isFile()) {
      output.push(relative.split(path.sep).join("/"));
    }
  }
  return output;
}

function gitBlobSha(content) {
  const bytes = Buffer.from(content, "utf8");
  return crypto
    .createHash("sha1")
    .update("blob " + bytes.length + "\0")
    .update(bytes)
    .digest("hex");
}

const productionFiles = [
  "core/timeline-core.js",
  "host/cep/cep-adapter.js",
  "host/cep/host.jsx",
  "ui/panel.js",
  "index.html"
];

const scriptFiles = (await collectFiles("scripts"))
  .filter((file) => file !== "scripts/audit-phase0.mjs");
const testFiles = await collectFiles("tests");
const benchmarkFiles = await collectFiles("benchmarks");
const workflowFiles = await collectFiles(".github/workflows");
const codeFiles = [
  ...productionFiles,
  ...scriptFiles,
  ...testFiles,
  ...benchmarkFiles,
  ...workflowFiles,
  "CSXS/manifest.xml",
  "package.json"
];

const contents = new Map();
for (const file of codeFiles) {
  contents.set(file, await read(file));
}

const productionText = productionFiles
  .map((file) => contents.get(file))
  .join("\n");
const scriptsText = scriptFiles
  .map((file) => contents.get(file))
  .join("\n");
const codeText = codeFiles
  .map((file) => contents.get(file))
  .join("\n");

record(
  "No interactive modal calls in production code",
  !/\b(?:alert|prompt|confirm)\s*\(/.test(productionText)
);

record(
  "No network client APIs in production code",
  !/\b(?:fetch|XMLHttpRequest|WebSocket|EventSource)\b/.test(productionText)
);

const manifest = contents.get("CSXS/manifest.xml");
record(
  "CEP manifest does not enable Node/privileged CEF flags",
  !/enable-nodejs|CEFCommandLine/i.test(manifest)
);
record(
  "CEP manifest targets AE 22+ with CSXS 11 floor",
  /Host Name="AEFT" Version="\[22\.0,99\.9\]"/.test(manifest) &&
  /RequiredRuntime Name="CSXS" Version="11\.0"/.test(manifest)
);

const html = contents.get("index.html");
record(
  "Panel CSP blocks outbound network and objects",
  /connect-src 'none'/.test(html) && /object-src 'none'/.test(html)
);
record(
  "Panel HTML contains no inline executable script",
  !/<script(?![^>]*\bsrc=)[^>]*>/i.test(html)
);

record(
  "Installer never mutates PlayerDebugMode/security settings",
  !/defaults[\s\S]{0,100}"write"[\s\S]{0,160}PlayerDebugMode/.test(scriptsText) &&
  !/"reg"[\s\S]{0,100}"add"[\s\S]{0,160}PlayerDebugMode/.test(scriptsText)
);

record(
  "Tooling contains no generic user-process kill commands",
  !/\b(?:taskkill|killall|pkill)\b/i.test(scriptsText)
);

record(
  "Tooling does not enable shell execution or child_process exec",
  !/\bshell\s*:\s*true\b/.test(scriptsText) &&
  !/\bexecSync\s*\(/.test(scriptsText) &&
  !/\bexec\s*\(/.test(scriptsText)
);

const secretPatterns = [
  /-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----/,
  /\bAKIA[0-9A-Z]{16}\b/,
  /\bghp_[A-Za-z0-9]{20,}\b/,
  /\bgithub_pat_[A-Za-z0-9_]{20,}\b/,
  /\bsk-[A-Za-z0-9]{20,}\b/
];
record(
  "No obvious embedded private keys/API tokens in code and tooling",
  secretPatterns.every((pattern) => !pattern.test(codeText))
);

record(
  "No TODO/FIXME/HACK markers in production/tooling",
  !/\b(?:TODO|FIXME|HACK)\b/.test(
    productionText + "\n" + scriptsText
  )
);

const packageJson = JSON.parse(contents.get("package.json"));
record(
  "Runtime/build uses no external npm dependencies",
  !packageJson.dependencies &&
  !packageJson.devDependencies
);

const workflow = workflowFiles
  .map((file) => contents.get(file))
  .join("\n");
const uses = [...workflow.matchAll(/\buses:\s*([^\s]+)@([^\s#]+)/g)];
record(
  "GitHub Actions are pinned to immutable commit SHAs",
  uses.length > 0 &&
  uses.every((match) => /^[0-9a-f]{40}$/.test(match[2])),
  uses.map((match) => match[1] + "@" + match[2]).join(", ")
);
record(
  "GitHub Actions token has read-only repository contents permission",
  /permissions:\s*\n\s*contents:\s*read/.test(workflow)
);

const core = contents.get("core/timeline-core.js");
record(
  "Timeline Core has no CEP/host bridge dependency",
  !/CSInterface|__adobe_cep__|evalScript|\$\._fstr/.test(core)
);

const csInterface = await read("vendor/CSInterface.js");
const json2 = await read("vendor/json2.js");
record(
  "Vendored CSInterface.js exactly matches reviewed Adobe CEP 11 blob",
  gitBlobSha(csInterface) === "be1cb6076ce9808106b930d2eae5b5f03ec0b893"
);
record(
  "Vendored json2.js exactly matches reviewed JSON-js blob",
  gitBlobSha(json2) === "b43526d343e49b0f79c56bbc9a1e652a00834be7"
);
record(
  "Adobe CSInterface license notice is retained",
  /Adobe permits you to use, modify, and distribute this file/.test(csInterface) &&
  /license agreement accompanying it/.test(csInterface)
);
record(
  "json2.js Public Domain notice is retained",
  /Public Domain\./.test(json2)
);

const failed = checks.filter((check) => check.status === "FAIL");
const report = {
  schemaVersion: 1,
  name: "FSTR Line Phase 0 Static Code/Security Audit",
  status: failed.length === 0 ? "PASS" : "FAIL",
  scope: {
    productionFiles,
    toolingFiles: scriptFiles,
    workflowFiles
  },
  checks,
  limitations: [
    "Static audit does not prove behavior inside After Effects.",
    "Adobe SDK license compliance for public distribution remains governed by the upstream Adobe license agreement."
  ],
  createdAt: new Date().toISOString()
};

await fs.mkdir(path.dirname(OUTPUT), { recursive: true });
await fs.writeFile(OUTPUT, JSON.stringify(report, null, 2) + "\n", "utf8");

for (const check of checks) {
  console.log(check.status + "  " + check.name);
  if (check.detail) {
    console.log("      " + check.detail);
  }
}

console.log("Audit status: " + report.status);
console.log("Evidence: artifacts/phase0-static-audit.json");

if (failed.length > 0) {
  process.exitCode = 1;
}

const test = require("node:test");
const assert = require("node:assert/strict");
const crypto = require("node:crypto");
const fs = require("node:fs/promises");
const os = require("node:os");
const path = require("node:path");
const { pathToFileURL } = require("node:url");

async function digest(filePath) {
  const data = await fs.readFile(filePath);
  return {
    sha256: crypto.createHash("sha256").update(data).digest("hex"),
    size: data.length
  };
}

async function createFixture() {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), "fstr-installed-payload-"));
  await fs.mkdir(path.join(root, "generated"), { recursive: true });

  const buildInfo = {
    schemaVersion: 1,
    product: "FSTR Line",
    version: "0.0.1",
    artifactType: "cep-extension",
    extensionId: "com.fstr.line.panel",
    gitCommit: "a".repeat(40),
    gitState: "clean",
    buildId: "FSTR-Line@0.0.1+aaaaaaaaaaaa.clean.cep"
  };

  await fs.writeFile(
    path.join(root, "generated", "build-info.json"),
    JSON.stringify(buildInfo, null, 2) + "\n",
    "utf8"
  );
  await fs.writeFile(path.join(root, "host.txt"), "host-payload\n", "utf8");

  const paths = ["generated/build-info.json", "host.txt"];
  const files = [];
  for (const relative of paths) {
    const metadata = await digest(path.join(root, ...relative.split("/")));
    files.push({ path: relative, ...metadata });
  }

  const manifest = {
    formatVersion: 2,
    package: "FSTR-Line",
    extensionId: "com.fstr.line.panel",
    buildIdentity: buildInfo,
    files
  };

  await fs.writeFile(
    path.join(root, "BUILD_MANIFEST.json"),
    JSON.stringify(manifest, null, 2) + "\n",
    "utf8"
  );

  return { root, buildInfo, manifest };
}

async function loadVerifier() {
  const url = pathToFileURL(
    path.resolve("scripts/installed-payload.mjs")
  ).href;
  return import(url);
}

test("installed payload verifier accepts exact clean file set and hashes", async (t) => {
  const fixture = await createFixture();
  t.after(() => fs.rm(fixture.root, { recursive: true, force: true }));

  const { verifyInstalledPayload } = await loadVerifier();
  const result = await verifyInstalledPayload(fixture.root);

  assert.equal(result.buildInfo.buildId, fixture.buildInfo.buildId);
  assert.equal(result.verifiedFileCount, fixture.manifest.files.length);
  assert.match(result.manifestSha256, /^[0-9a-f]{64}$/);
});

test("installed payload verifier rejects stale unexpected files", async (t) => {
  const fixture = await createFixture();
  t.after(() => fs.rm(fixture.root, { recursive: true, force: true }));

  await fs.writeFile(path.join(fixture.root, "stale.jsx"), "stale", "utf8");

  const { verifyInstalledPayload } = await loadVerifier();
  await assert.rejects(
    verifyInstalledPayload(fixture.root),
    /Installed payload file set mismatch.*stale\.jsx/
  );
});

test("installed payload verifier rejects tampered production file", async (t) => {
  const fixture = await createFixture();
  t.after(() => fs.rm(fixture.root, { recursive: true, force: true }));

  await fs.writeFile(path.join(fixture.root, "host.txt"), "tampered\n", "utf8");

  const { verifyInstalledPayload } = await loadVerifier();
  await assert.rejects(
    verifyInstalledPayload(fixture.root),
    /Installed payload hash mismatch: host\.txt/
  );
});

test("installed payload verifier rejects dirty or mismatched Build Identity", async (t) => {
  const fixture = await createFixture();
  t.after(() => fs.rm(fixture.root, { recursive: true, force: true }));

  const dirty = { ...fixture.buildInfo, gitState: "dirty" };
  await fs.writeFile(
    path.join(fixture.root, "generated", "build-info.json"),
    JSON.stringify(dirty, null, 2) + "\n",
    "utf8"
  );

  let metadata = await digest(path.join(fixture.root, "generated", "build-info.json"));
  fixture.manifest.files = fixture.manifest.files.map((entry) =>
    entry.path === "generated/build-info.json"
      ? { path: entry.path, ...metadata }
      : entry
  );
  fixture.manifest.buildIdentity = dirty;
  await fs.writeFile(
    path.join(fixture.root, "BUILD_MANIFEST.json"),
    JSON.stringify(fixture.manifest, null, 2) + "\n",
    "utf8"
  );

  const { verifyInstalledPayload } = await loadVerifier();
  await assert.rejects(
    verifyInstalledPayload(fixture.root),
    /not a clean Build Identity/
  );
});

test("installed payload verifier rejects manifest path traversal", async (t) => {
  const fixture = await createFixture();
  t.after(() => fs.rm(fixture.root, { recursive: true, force: true }));

  fixture.manifest.files.push({
    path: "../escape.txt",
    sha256: "0".repeat(64),
    size: 1
  });
  await fs.writeFile(
    path.join(fixture.root, "BUILD_MANIFEST.json"),
    JSON.stringify(fixture.manifest, null, 2) + "\n",
    "utf8"
  );

  const { verifyInstalledPayload } = await loadVerifier();
  await assert.rejects(
    verifyInstalledPayload(fixture.root),
    /escapes the extension root/
  );
});

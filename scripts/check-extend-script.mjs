import { mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { execFileSync } from "node:child_process";

const directory = await mkdtemp(join(tmpdir(), "fstr-line-extend-script-"));
const temporaryFile = join(directory, "host.js");
try {
  await writeFile(temporaryFile, await readFile("src/host/cep/host.jsx"));
  execFileSync(process.execPath, ["--check", temporaryFile], { stdio: "inherit" });
} finally {
  await rm(directory, { recursive: true, force: true });
}

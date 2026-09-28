import { readFile, writeFile, mkdtemp, rm } from 'node:fs/promises';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { execFileSync } from 'node:child_process';
import assert from 'node:assert/strict';
import { test } from 'node:test';

test('actual C++ log formatter never labels a synthetic load record as an observed callback', async () => {
  const directory = await mkdtemp(join(tmpdir(), 'fstr-probe-log-'));
  try {
    const source = await readFile('native/command-probe/CommandProbe.cpp', 'utf8');
    const split = source.indexOf('static A_Err command_hook(');
    assert.ok(split > 0);
    // Compile the actual logger prefix only, with scalar typedefs instead of the
    // unavailable Adobe SDK. This is NOT native plugin/ABI/load verification.
    await writeFile(join(directory, 'CommandProbe.h'), 'using AEGP_PluginID = long;\nusing AEGP_Command = long;\nusing AEGP_HookPriority = unsigned long;\nusing A_Boolean = int;\nconstexpr AEGP_HookPriority AEGP_HP_BeforeAE = 1;\n');
    await writeFile(join(directory, 'ProbeBuild.h'), '#define FSTR_PROBE_BUILD_ID "logger-fixture-not-AE"\n');
    const harness = source.slice(0, split) + '\nint main(int argc, char **argv) {\n  if (argc != 2) return 2;\n  g_start = std::chrono::steady_clock::now();\n  g_log = std::fopen(argv[1], "wx");\n  if (!g_log) return 3;\n  log_event("loaded", 0, 0, 0);\n  log_event("command", 123, 7, 1);\n  log_event("death", -1, 0, 0);\n  std::fclose(g_log);\n  return 0;\n}\n';
    await writeFile(join(directory, 'logger.cpp'), harness);
    execFileSync('c++', ['-std=c++17', join(directory, 'logger.cpp'), '-o', join(directory, 'logger')], { timeout: 20000 });
    const output = join(directory, 'events.jsonl');
    execFileSync(join(directory, 'logger'), [output], { timeout: 5000 });
    const rows = (await readFile(output, 'utf8')).trim().split('\n').map(JSON.parse);
    assert.equal(rows.length, 3);
    assert.equal(rows[0].kind, 'loaded'); assert.equal(rows[0].isCommandCallback, false);
    assert.equal(rows[0].priority, null); assert.equal(rows[0].command, null);
    assert.equal(rows[1].isCommandCallback, true); assert.equal(rows[1].priority, 7);
    assert.equal(rows[1].requestedPriority, 1); assert.equal(rows[1].command, 123);
    assert.equal(rows[2].priority, null);
    assert.deepEqual(rows.map((row) => row.sequence), [1, 2, 3]);
  } finally { await rm(directory, { recursive: true, force: true }); }
});

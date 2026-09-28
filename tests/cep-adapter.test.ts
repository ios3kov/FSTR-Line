import assert from "node:assert/strict";
import test from "node:test";
import { CEPAdapter, type EvalScriptBridge } from "../src/host/cep/bridge.js";
import { HOST_PROTOCOL_VERSION } from "../src/host/protocol.js";
import { layer, snapshot } from "./fixtures.js";
import { createMoveLayersCommand } from "../src/core/index.js";

class TestBridge implements EvalScriptBridge {
  readonly scripts: string[] = [];

  constructor(private readonly response: string, private readonly delayMs = 0) {}

  evalScript(script: string, callback: (result: string) => void): void {
    this.scripts.push(script);
    setTimeout(() => callback(this.response), this.delayMs);
  }
}

test("CEPAdapter reads and validates a snapshot through the async bridge", async () => {
  const current = snapshot([layer(1, 1, 0, 4)]);
  const bridge = new TestBridge(JSON.stringify({
    protocolVersion: HOST_PROTOCOL_VERSION,
    ok: true,
    data: current,
  }));
  const adapter = new CEPAdapter(bridge);

  assert.deepEqual(await adapter.readSnapshot(), current);
  assert.deepEqual(bridge.scripts, ["fstrLineHost.readSnapshot()"]);
});

test("CEPAdapter rejects an evalScript timeout", async () => {
  const bridge = new TestBridge("unused", 25);
  const adapter = new CEPAdapter(bridge, { timeoutMs: 1 });

  await assert.rejects(() => adapter.readSnapshot(), /timed out/);
});

test("CEPAdapter sends a serialized semantic command to the named host entrypoint", async () => {
  const current = snapshot([layer(1, 1, 0, 4)]);
  const command = createMoveLayersCommand(current, [1], 2, "op-1");
  const bridge = new TestBridge(JSON.stringify({
    protocolVersion: HOST_PROTOCOL_VERSION,
    ok: true,
    data: { operationId: "op-1", changed: true, snapshot: current },
  }));
  const adapter = new CEPAdapter(bridge);

  await adapter.execute(command);
  assert.match(bridge.scripts[0] ?? "", /^fstrLineHost\.executeCommand\(/);
  assert.match(bridge.scripts[0] ?? "", /"commandVersion":1/);
});

test("CEPAdapter serializes host calls to protect snapshot ordering", async () => {
  const current = snapshot([layer(1, 1, 0, 4)]);
  const bridge = new TestBridge(JSON.stringify({
    protocolVersion: HOST_PROTOCOL_VERSION,
    ok: true,
    data: current,
  }), 5);
  const adapter = new CEPAdapter(bridge);

  await Promise.all([adapter.readSnapshot(), adapter.readSnapshot()]);
  assert.deepEqual(bridge.scripts, [
    "fstrLineHost.readSnapshot()",
    "fstrLineHost.readSnapshot()",
  ]);
});

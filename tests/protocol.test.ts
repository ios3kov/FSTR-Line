import assert from "node:assert/strict";
import test from "node:test";
import {
  HOST_PROTOCOL_VERSION,
  parseOperationResponse,
  parseSnapshotResponse,
  serializeCommandForEval,
} from "../src/host/protocol.js";
import { createMoveLayersCommand } from "../src/core/index.js";
import { layer, snapshot } from "./fixtures.js";

test("parses a versioned snapshot response and validates its payload", () => {
  const current = snapshot([layer(1, 1, 0, 4)]);
  const raw = JSON.stringify({
    protocolVersion: HOST_PROTOCOL_VERSION,
    ok: true,
    data: current,
  });

  assert.deepEqual(parseSnapshotResponse(raw), current);
});

test("rejects host protocol version mismatch and malformed JSON", () => {
  assert.throws(() => parseSnapshotResponse("{"), /invalid JSON/i);
  assert.throws(
    () => parseSnapshotResponse(JSON.stringify({ protocolVersion: 999, ok: true, data: {} })),
    /Unsupported host protocol version/,
  );
});

test("rejects a host error envelope", () => {
  const raw = JSON.stringify({
    protocolVersion: HOST_PROTOCOL_VERSION,
    ok: false,
    error: { code: "NO_ACTIVE_COMP", message: "No active composition" },
  });

  assert.throws(() => parseSnapshotResponse(raw), /NO_ACTIVE_COMP/);
});

test("rejects malformed success and error envelopes", () => {
  assert.throws(
    () => parseSnapshotResponse(JSON.stringify({ protocolVersion: HOST_PROTOCOL_VERSION, ok: true })),
    /missing data/,
  );
  assert.throws(
    () => parseSnapshotResponse(JSON.stringify({ protocolVersion: HOST_PROTOCOL_VERSION, ok: false, error: {} })),
    /error response is malformed/,
  );
});

test("validates operation response snapshots", () => {
  const current = snapshot([layer(1, 1, 0, 4)]);
  const raw = JSON.stringify({
    protocolVersion: HOST_PROTOCOL_VERSION,
    ok: true,
    data: { operationId: "op-1", changed: true, snapshot: current },
  });

  assert.deepEqual(parseOperationResponse(raw), {
    operationId: "op-1",
    changed: true,
    snapshot: current,
  });
});

test("serializes command data without executable host code", () => {
  const command = createMoveLayersCommand(
    snapshot([layer(1, 1, 0, 4)]),
    [1],
    2,
    "operation\u2028id",
  );
  const serialized = serializeCommandForEval(command);

  assert.match(serialized, /"type":"moveLayers"/);
  assert.doesNotMatch(serialized, /\u2028/);
  assert.doesNotMatch(serialized, /function|evalScript|app\./i);
});

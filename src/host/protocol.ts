import { CoreError } from "../core/errors.js";
import { validateSnapshot, type CompositionSnapshot, type TimelineCommand } from "../core/types.js";
import type { HostOperationResult } from "./host-adapter.js";

export const HOST_PROTOCOL_VERSION = 1;

export interface HostProtocolError {
  readonly code: string;
  readonly message: string;
}

export type HostResponse<T> =
  | {
      readonly protocolVersion: typeof HOST_PROTOCOL_VERSION;
      readonly ok: true;
      readonly data: T;
    }
  | {
      readonly protocolVersion: typeof HOST_PROTOCOL_VERSION;
      readonly ok: false;
      readonly error: HostProtocolError;
    };

export function parseSnapshotResponse(raw: string): CompositionSnapshot {
  const response = parseResponse<CompositionSnapshot>(raw);
  validateSnapshot(response);
  return response;
}

export function parseOperationResponse(raw: string): HostOperationResult {
  const response = parseResponse<HostOperationResult>(raw);
  if (!response.operationId || typeof response.changed !== "boolean") {
    throw new CoreError("INVALID_SNAPSHOT", "Host operation response is malformed");
  }
  validateSnapshot(response.snapshot);
  return response;
}

export function serializeCommandForEval(command: TimelineCommand): string {
  const serialized = JSON.stringify(command);
  return serialized.replace(/\u2028/g, "\\u2028").replace(/\u2029/g, "\\u2029");
}

export function parseResponse<T>(raw: string): T {
  if (!raw || raw === "EvalScript error.") {
    throw new CoreError("INVALID_SNAPSHOT", raw || "Host returned an empty response");
  }

  let response: HostResponse<T>;
  try {
    response = JSON.parse(raw) as HostResponse<T>;
  } catch {
    throw new CoreError("INVALID_SNAPSHOT", "Host returned invalid JSON");
  }

  if (!response || typeof response !== "object") {
    throw new CoreError("INVALID_SNAPSHOT", "Host response must be an object");
  }
  if (response.protocolVersion !== HOST_PROTOCOL_VERSION) {
    throw new CoreError(
      "INVALID_SNAPSHOT",
      `Unsupported host protocol version: ${String(response.protocolVersion)}`,
    );
  }
  if (response.ok !== true && response.ok !== false) {
    throw new CoreError("INVALID_SNAPSHOT", "Host response is missing an ok flag");
  }
  if (!response.ok) {
    if (!response.error || !response.error.code || !response.error.message) {
      throw new CoreError("INVALID_SNAPSHOT", "Host error response is malformed");
    }
    throw new CoreError("INVALID_COMMAND", `${response.error.code}: ${response.error.message}`);
  }
  if (response.data === undefined) {
    throw new CoreError("INVALID_SNAPSHOT", "Host success response is missing data");
  }
  return response.data;
}

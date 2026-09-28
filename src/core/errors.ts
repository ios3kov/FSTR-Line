export type CoreErrorCode =
  | "INVALID_SNAPSHOT"
  | "DUPLICATE_LAYER_ID"
  | "DUPLICATE_LAYER_INDEX"
  | "INVALID_RANGE"
  | "INVALID_FRAME"
  | "INVALID_FRAME_RATE"
  | "EMPTY_SELECTION"
  | "LAYER_NOT_FOUND"
  | "LOCKED_LAYER"
  | "UNSUPPORTED_OPERATION"
  | "INVALID_TIMING"
  | "STALE_SNAPSHOT"
  | "WRONG_COMPOSITION"
  | "INVALID_COMMAND";

export class CoreError extends Error {
  readonly code: CoreErrorCode;

  constructor(code: CoreErrorCode, message: string) {
    super(message);
    this.name = "CoreError";
    this.code = code;
  }
}

import { CoreError } from "./errors.js";

export type Frame = number;

export const CORE_CONTRACT_VERSION = 1;

export interface FrameRate {
  readonly numerator: number;
  readonly denominator: number;
}

export type LayerType =
  | "footage"
  | "still"
  | "text"
  | "shape"
  | "precomp"
  | "adjustment"
  | "null"
  | "audio"
  | "camera"
  | "light"
  | "threeD"
  | "unknown";

export interface LayerCapabilities {
  readonly canMove: boolean;
  readonly canTrimIn: boolean;
  readonly canTrimOut: boolean;
  readonly canSetSwitches: boolean;
  readonly canReorder: boolean;
}

export interface LayerSnapshot {
  readonly layerId: number;
  readonly index: number;
  readonly name: string;
  readonly type: LayerType;
  readonly startFrame: Frame;
  readonly inFrame: Frame;
  readonly outFrame: Frame;
  readonly label: number;
  readonly selected: boolean;
  readonly enabled: boolean;
  readonly solo: boolean;
  readonly locked: boolean;
  readonly audioEnabled: boolean;
  readonly capabilities: LayerCapabilities;
}

export interface CompositionSnapshot {
  readonly schemaVersion: typeof CORE_CONTRACT_VERSION;
  readonly compositionId: string;
  readonly compositionName: string;
  readonly frameRate: FrameRate;
  readonly durationFrames: Frame;
  readonly currentFrame: Frame;
  readonly layers: readonly LayerSnapshot[];
  readonly revision: string;
}

export interface CommandGuard {
  readonly compositionId: string;
  readonly revision: string;
}

export type LayerSwitch = "enabled" | "solo" | "locked" | "audioEnabled";

export interface BaseCommand {
  readonly commandVersion: typeof CORE_CONTRACT_VERSION;
  readonly operationId: string;
  readonly guard: CommandGuard;
}

export interface MoveLayersCommand extends BaseCommand {
  readonly type: "moveLayers";
  readonly layerIds: readonly number[];
  readonly deltaFrames: Frame;
}

export interface TrimLayerInCommand extends BaseCommand {
  readonly type: "trimLayerIn";
  readonly layerId: number;
  readonly newInFrame: Frame;
}

export interface TrimLayerOutCommand extends BaseCommand {
  readonly type: "trimLayerOut";
  readonly layerId: number;
  readonly newOutFrame: Frame;
}

export interface SetLayerSwitchCommand extends BaseCommand {
  readonly type: "setLayerSwitch";
  readonly layerId: number;
  readonly layerSwitch: LayerSwitch;
  readonly value: boolean;
}

export interface SelectLayersCommand extends BaseCommand {
  readonly type: "selectLayers";
  readonly layerIds: readonly number[];
}

export type TimelineCommand =
  | MoveLayersCommand
  | TrimLayerInCommand
  | TrimLayerOutCommand
  | SetLayerSwitchCommand
  | SelectLayersCommand;

export interface PackedTrack {
  readonly trackIndex: number;
  readonly layerIds: readonly number[];
}

export interface PackingResult {
  readonly tracks: readonly PackedTrack[];
  readonly trackByLayerId: ReadonlyMap<number, number>;
}

export function assertFrame(value: number, fieldName: string): asserts value is Frame {
  if (!Number.isSafeInteger(value)) {
    throw new CoreError("INVALID_FRAME", `${fieldName} must be a safe integer frame`);
  }
}

export function assertFrameRate(frameRate: FrameRate): void {
  if (
    !Number.isSafeInteger(frameRate.numerator) ||
    !Number.isSafeInteger(frameRate.denominator) ||
    frameRate.numerator <= 0 ||
    frameRate.denominator <= 0
  ) {
    throw new CoreError("INVALID_FRAME_RATE", "Frame rate must be a positive rational number");
  }
}

export function validateSnapshot(snapshot: CompositionSnapshot): void {
  if (snapshot.schemaVersion !== CORE_CONTRACT_VERSION) {
    throw new CoreError("INVALID_SNAPSHOT", `Unsupported snapshot schema version: ${snapshot.schemaVersion}`);
  }
  if (!snapshot.compositionId || !snapshot.revision || !snapshot.compositionName) {
    throw new CoreError("INVALID_SNAPSHOT", "Snapshot identity fields must be non-empty");
  }

  assertFrameRate(snapshot.frameRate);
  assertFrame(snapshot.durationFrames, "durationFrames");
  assertFrame(snapshot.currentFrame, "currentFrame");

  if (snapshot.durationFrames < 0) {
    throw new CoreError("INVALID_SNAPSHOT", "durationFrames cannot be negative");
  }

  const layerIds = new Set<number>();
  const layerIndexes = new Set<number>();

  for (const layer of snapshot.layers) {
    validateLayer(layer, layerIds, layerIndexes);
  }
}

function validateLayer(
  layer: LayerSnapshot,
  layerIds: Set<number>,
  layerIndexes: Set<number>,
): void {
  if (!Number.isSafeInteger(layer.layerId) || layer.layerId <= 0) {
    throw new CoreError("INVALID_SNAPSHOT", `Invalid layer id: ${layer.layerId}`);
  }
  if (!Number.isSafeInteger(layer.index) || layer.index <= 0) {
    throw new CoreError("INVALID_SNAPSHOT", `Invalid layer index: ${layer.index}`);
  }
  if (layerIds.has(layer.layerId)) {
    throw new CoreError("DUPLICATE_LAYER_ID", `Layer id ${layer.layerId} occurs more than once`);
  }
  if (layerIndexes.has(layer.index)) {
    throw new CoreError("DUPLICATE_LAYER_INDEX", `Layer index ${layer.index} occurs more than once`);
  }

  layerIds.add(layer.layerId);
  layerIndexes.add(layer.index);
  assertFrame(layer.startFrame, `layer ${layer.layerId} startFrame`);
  assertFrame(layer.inFrame, `layer ${layer.layerId} inFrame`);
  assertFrame(layer.outFrame, `layer ${layer.layerId} outFrame`);

  if (layer.inFrame >= layer.outFrame) {
    throw new CoreError("INVALID_RANGE", `Layer ${layer.layerId} must have inFrame < outFrame`);
  }
  if (!Number.isInteger(layer.label) || layer.label < 0) {
    throw new CoreError("INVALID_SNAPSHOT", `Invalid label for layer ${layer.layerId}`);
  }
}

import { CORE_CONTRACT_VERSION, type CompositionSnapshot, type LayerSnapshot } from "../src/core/types.js";

export function layer(
  layerId: number,
  index: number,
  inFrame: number,
  outFrame: number,
  overrides: Partial<LayerSnapshot> = {},
): LayerSnapshot {
  return {
    layerId,
    index,
    name: `Layer ${layerId}`,
    type: "footage",
    startFrame: inFrame,
    inFrame,
    outFrame,
    label: 0,
    selected: false,
    enabled: true,
    solo: false,
    locked: false,
    audioEnabled: true,
    capabilities: {
      canMove: true,
      canTrimIn: true,
      canTrimOut: true,
      canSetSwitches: true,
      canReorder: true,
    },
    ...overrides,
  };
}

export function snapshot(layers: readonly LayerSnapshot[]): CompositionSnapshot {
  return {
    schemaVersion: CORE_CONTRACT_VERSION,
    compositionId: "comp-1",
    compositionName: "Test Composition",
    frameRate: { numerator: 24, denominator: 1 },
    durationFrames: 240,
    currentFrame: 0,
    layers,
    revision: "revision-1",
  };
}

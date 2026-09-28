import {
  validateCommandAgainstSnapshot,
  type CompositionSnapshot,
  type LayerSnapshot,
  type TimelineCommand,
} from "../core/index.js";
import type { HostAdapter, HostOperationResult } from "./host-adapter.js";

export class FakeHostAdapter implements HostAdapter {
  private currentSnapshot: CompositionSnapshot;

  constructor(snapshot: CompositionSnapshot) {
    this.currentSnapshot = snapshot;
  }

  async readSnapshot(): Promise<CompositionSnapshot> {
    return this.currentSnapshot;
  }

  async execute(command: TimelineCommand): Promise<HostOperationResult> {
    validateCommandAgainstSnapshot(this.currentSnapshot, command);

    const nextLayers = this.currentSnapshot.layers.map((layer) => applyCommand(layer, command));
    this.currentSnapshot = {
      ...this.currentSnapshot,
      layers: nextLayers,
      revision: `${this.currentSnapshot.revision}:${command.operationId}`,
    };

    return {
      operationId: command.operationId,
      changed: true,
      snapshot: this.currentSnapshot,
    };
  }
}

function applyCommand(layer: LayerSnapshot, command: TimelineCommand): LayerSnapshot {
  switch (command.type) {
    case "moveLayers":
      return command.layerIds.includes(layer.layerId)
        ? {
            ...layer,
            startFrame: layer.startFrame + command.deltaFrames,
            inFrame: layer.inFrame + command.deltaFrames,
            outFrame: layer.outFrame + command.deltaFrames,
          }
        : layer;
    case "trimLayerIn":
      return command.layerId === layer.layerId
        ? { ...layer, inFrame: command.newInFrame }
        : layer;
    case "trimLayerOut":
      return command.layerId === layer.layerId
        ? { ...layer, outFrame: command.newOutFrame }
        : layer;
    case "setLayerSwitch":
      return command.layerId === layer.layerId
        ? applySwitch(layer, command.layerSwitch, command.value)
        : layer;
    case "selectLayers":
      return { ...layer, selected: command.layerIds.includes(layer.layerId) };
  }
}

function applySwitch(
  layer: LayerSnapshot,
  layerSwitch: "enabled" | "solo" | "locked" | "audioEnabled",
  value: boolean,
): LayerSnapshot {
  switch (layerSwitch) {
    case "enabled":
      return { ...layer, enabled: value };
    case "solo":
      return { ...layer, solo: value };
    case "locked":
      return { ...layer, locked: value };
    case "audioEnabled":
      return { ...layer, audioEnabled: value };
  }
}

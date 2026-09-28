import { CoreError } from "./errors.js";
import {
  assertFrame,
  CORE_CONTRACT_VERSION,
  validateSnapshot,
  type CommandGuard,
  type CompositionSnapshot,
  type Frame,
  type LayerSnapshot,
  type LayerSwitch,
  type TimelineCommand,
} from "./types.js";

export function createMoveLayersCommand(
  snapshot: CompositionSnapshot,
  layerIds: readonly number[],
  deltaFrames: Frame,
  operationId: string,
): TimelineCommand {
  validateSnapshot(snapshot);
  assertOperationId(operationId);
  assertFrame(deltaFrames, "deltaFrames");
  const targets = requireTargets(snapshot, layerIds);

  for (const layer of targets) {
    requireCapability(layer, layer.capabilities.canMove, "move");
  }

  return {
    type: "moveLayers",
    commandVersion: CORE_CONTRACT_VERSION,
    operationId,
    guard: guardFor(snapshot),
    layerIds: targets.map((layer) => layer.layerId),
    deltaFrames,
  };
}

export function createTrimLayerInCommand(
  snapshot: CompositionSnapshot,
  layerId: number,
  newInFrame: Frame,
  operationId: string,
): TimelineCommand {
  validateSnapshot(snapshot);
  assertOperationId(operationId);
  assertFrame(newInFrame, "newInFrame");
  const layer = requireTarget(snapshot, layerId);
  requireCapability(layer, layer.capabilities.canTrimIn, "trim in");
  if (newInFrame >= layer.outFrame) {
    throw new CoreError("INVALID_TIMING", "Trim in must remain before out point");
  }

  return {
    type: "trimLayerIn",
    commandVersion: CORE_CONTRACT_VERSION,
    operationId,
    guard: guardFor(snapshot),
    layerId,
    newInFrame,
  };
}

export function createTrimLayerOutCommand(
  snapshot: CompositionSnapshot,
  layerId: number,
  newOutFrame: Frame,
  operationId: string,
): TimelineCommand {
  validateSnapshot(snapshot);
  assertOperationId(operationId);
  assertFrame(newOutFrame, "newOutFrame");
  const layer = requireTarget(snapshot, layerId);
  requireCapability(layer, layer.capabilities.canTrimOut, "trim out");
  if (newOutFrame <= layer.inFrame) {
    throw new CoreError("INVALID_TIMING", "Trim out must remain after in point");
  }

  return {
    type: "trimLayerOut",
    commandVersion: CORE_CONTRACT_VERSION,
    operationId,
    guard: guardFor(snapshot),
    layerId,
    newOutFrame,
  };
}

export function createSetLayerSwitchCommand(
  snapshot: CompositionSnapshot,
  layerId: number,
  layerSwitch: LayerSwitch,
  value: boolean,
  operationId: string,
): TimelineCommand {
  validateSnapshot(snapshot);
  assertOperationId(operationId);
  const layer = requireTarget(snapshot, layerId);
  requireCapability(layer, layer.capabilities.canSetSwitches, "set layer switch");

  return {
    type: "setLayerSwitch",
    commandVersion: CORE_CONTRACT_VERSION,
    operationId,
    guard: guardFor(snapshot),
    layerId,
    layerSwitch,
    value,
  };
}

export function createSelectLayersCommand(
  snapshot: CompositionSnapshot,
  layerIds: readonly number[],
  operationId: string,
): TimelineCommand {
  validateSnapshot(snapshot);
  assertOperationId(operationId);
  const targets = requireTargets(snapshot, layerIds);

  return {
    type: "selectLayers",
    commandVersion: CORE_CONTRACT_VERSION,
    operationId,
    guard: guardFor(snapshot),
    layerIds: targets.map((layer) => layer.layerId),
  };
}

export function validateCommandAgainstSnapshot(
  snapshot: CompositionSnapshot,
  command: TimelineCommand,
): void {
  validateSnapshot(snapshot);
  assertOperationId(command.operationId);

  if (command.commandVersion !== CORE_CONTRACT_VERSION) {
    throw new CoreError("INVALID_COMMAND", `Unsupported command version: ${command.commandVersion}`);
  }

  if (command.guard.compositionId !== snapshot.compositionId) {
    throw new CoreError("WRONG_COMPOSITION", "Command targets a different composition");
  }
  if (command.guard.revision !== snapshot.revision) {
    throw new CoreError("STALE_SNAPSHOT", "Command was created from a stale snapshot");
  }

  switch (command.type) {
    case "moveLayers":
      assertFrame(command.deltaFrames, "deltaFrames");
      for (const layerId of command.layerIds) {
        const layer = requireTarget(snapshot, layerId);
        requireCapability(layer, layer.capabilities.canMove, "move");
      }
      return;
    case "trimLayerIn": {
      const layer = requireTarget(snapshot, command.layerId);
      requireCapability(layer, layer.capabilities.canTrimIn, "trim in");
      assertFrame(command.newInFrame, "newInFrame");
      if (command.newInFrame >= layer.outFrame) {
        throw new CoreError("INVALID_TIMING", "Trim in must remain before out point");
      }
      return;
    }
    case "trimLayerOut": {
      const layer = requireTarget(snapshot, command.layerId);
      requireCapability(layer, layer.capabilities.canTrimOut, "trim out");
      assertFrame(command.newOutFrame, "newOutFrame");
      if (command.newOutFrame <= layer.inFrame) {
        throw new CoreError("INVALID_TIMING", "Trim out must remain after in point");
      }
      return;
    }
    case "setLayerSwitch": {
      const layer = requireTarget(snapshot, command.layerId);
      requireCapability(layer, layer.capabilities.canSetSwitches, "set layer switch");
      return;
    }
    case "selectLayers":
      requireTargets(snapshot, command.layerIds);
      return;
  }
}

function guardFor(snapshot: CompositionSnapshot): CommandGuard {
  return {
    compositionId: snapshot.compositionId,
    revision: snapshot.revision,
  };
}

function requireTargets(
  snapshot: CompositionSnapshot,
  layerIds: readonly number[],
): LayerSnapshot[] {
  if (layerIds.length === 0) {
    throw new CoreError("EMPTY_SELECTION", "At least one layer must be selected");
  }

  const uniqueIds = [...new Set(layerIds)].sort((first, second) => first - second);
  return uniqueIds.map((layerId) => requireTarget(snapshot, layerId));
}

function requireTarget(snapshot: CompositionSnapshot, layerId: number): LayerSnapshot {
  const layer = snapshot.layers.find((candidate) => candidate.layerId === layerId);
  if (layer === undefined) {
    throw new CoreError("LAYER_NOT_FOUND", `Layer ${layerId} was not found in the snapshot`);
  }
  return layer;
}

function requireCapability(layer: LayerSnapshot, allowed: boolean, operation: string): void {
  if (layer.locked) {
    throw new CoreError("LOCKED_LAYER", `Layer ${layer.layerId} is locked`);
  }
  if (!allowed) {
    throw new CoreError("UNSUPPORTED_OPERATION", `Layer ${layer.layerId} cannot ${operation}`);
  }
}

function assertOperationId(operationId: string): void {
  if (!operationId) {
    throw new CoreError("INVALID_COMMAND", "operationId must be non-empty");
  }
}

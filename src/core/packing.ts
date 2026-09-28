import { CoreError } from "./errors.js";
import {
  validateSnapshot,
  type CompositionSnapshot,
  type LayerSnapshot,
  type PackedTrack,
  type PackingResult,
} from "./types.js";
import { rangesOverlap } from "./time.js";

export function packLayers(snapshot: CompositionSnapshot): PackingResult {
  validateSnapshot(snapshot);

  const layers = [...snapshot.layers].sort(compareLayerOrder);
  const trackByLayerId = new Map<number, number>();

  for (const layer of layers) {
    let assignedTrack = 0;

    for (const previousLayer of layers) {
      if (previousLayer.index >= layer.index) {
        break;
      }
      if (!rangesOverlap(
        previousLayer.inFrame,
        previousLayer.outFrame,
        layer.inFrame,
        layer.outFrame,
      )) {
        continue;
      }

      const previousTrack = trackByLayerId.get(previousLayer.layerId);
      if (previousTrack === undefined) {
        throw new CoreError("INVALID_SNAPSHOT", "Packing encountered an unassigned predecessor");
      }
      assignedTrack = Math.max(assignedTrack, previousTrack + 1);
    }

    trackByLayerId.set(layer.layerId, assignedTrack);
  }

  assertPackingConstraints(layers, trackByLayerId);

  const trackLayers = new Map<number, LayerSnapshot[]>();
  for (const layer of layers) {
    const trackIndex = trackByLayerId.get(layer.layerId);
    if (trackIndex === undefined) {
      throw new CoreError("INVALID_SNAPSHOT", "Packing did not assign a track");
    }
    const track = trackLayers.get(trackIndex) ?? [];
    track.push(layer);
    trackLayers.set(trackIndex, track);
  }

  const tracks: PackedTrack[] = [...trackLayers.entries()]
    .sort(([first], [second]) => first - second)
    .map(([trackIndex, track]) => ({
      trackIndex,
      layerIds: track
        .sort(compareVisualClipOrder)
        .map((layer) => layer.layerId),
    }));

  return { tracks, trackByLayerId };
}

function compareLayerOrder(first: LayerSnapshot, second: LayerSnapshot): number {
  return first.index - second.index || first.layerId - second.layerId;
}

function compareVisualClipOrder(first: LayerSnapshot, second: LayerSnapshot): number {
  return first.inFrame - second.inFrame
    || first.outFrame - second.outFrame
    || compareLayerOrder(first, second);
}

function assertPackingConstraints(
  layers: readonly LayerSnapshot[],
  trackByLayerId: ReadonlyMap<number, number>,
): void {
  for (let firstIndex = 0; firstIndex < layers.length; firstIndex += 1) {
    const first = layers[firstIndex];
    if (first === undefined) {
      continue;
    }
    const firstTrack = trackByLayerId.get(first.layerId);
    if (firstTrack === undefined) {
      throw new CoreError("INVALID_SNAPSHOT", "Packing constraint check has no first track");
    }

    for (let secondIndex = firstIndex + 1; secondIndex < layers.length; secondIndex += 1) {
      const second = layers[secondIndex];
      if (second === undefined || !rangesOverlap(
        first.inFrame,
        first.outFrame,
        second.inFrame,
        second.outFrame,
      )) {
        continue;
      }

      const secondTrack = trackByLayerId.get(second.layerId);
      if (secondTrack === undefined || firstTrack >= secondTrack) {
        throw new CoreError(
          "INVALID_SNAPSHOT",
          `Packing violated compositing order for layers ${first.layerId} and ${second.layerId}`,
        );
      }
    }
  }
}

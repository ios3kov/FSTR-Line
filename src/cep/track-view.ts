import { projectionForState, type PanelState } from "./panel-controller.js";

/** Read-only visual tracks adapted to the canonical typed snapshot, not the donor host contract. */
export function renderTrackView(output: HTMLElement, state: PanelState): void {
  output.replaceChildren();
  output.dataset.state = state.status;
  const projection = projectionForState(state);
  output.dataset.stale = state.status === "ready" ? "false" : "true";
  if (!projection) return;
  const { snapshot, tracks } = projection;
  const byId = new Map(snapshot.layers.map((layer) => [layer.layerId, layer]));
  let minimum = 0;
  let maximum = Math.max(1, snapshot.durationFrames);
  for (const layer of snapshot.layers) {
    minimum = Math.min(minimum, layer.inFrame);
    maximum = Math.max(maximum, layer.outFrame);
  }
  const span = maximum - minimum;
  const doc = output.ownerDocument;
  for (const track of tracks) {
    const row = doc.createElement("li"); row.className = "track";
    const label = doc.createElement("span"); label.className = "track-name";
    label.textContent = `V${track.trackIndex + 1}`;
    const lane = doc.createElement("div"); lane.className = "track-lane";
    for (const id of track.layerIds) {
      const layer = byId.get(id);
      if (!layer) throw new Error(`Projection refers to missing layer ${id}`);
      const clip = doc.createElement("span");
      clip.className = `clip label-${Math.min(16, layer.label)}${layer.selected ? " is-selected" : ""}${layer.enabled ? "" : " is-disabled"}`;
      clip.style.left = `${(layer.inFrame - minimum) / span * 100}%`;
      clip.style.width = `${(layer.outFrame - layer.inFrame) / span * 100}%`;
      clip.dataset.layerId = String(id);
      clip.textContent = layer.name;
      clip.title = `${layer.name} · ID ${id} · ${layer.inFrame}–${layer.outFrame}f${layer.locked ? " · locked" : ""}`;
      lane.append(clip);
    }
    row.append(label, lane);
    output.append(row);
  }
}

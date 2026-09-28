import { packLayers } from "../core/packing.js";
import type { PackedTrack } from "../core/types.js";
import { CEPAdapter, type EvalScriptBridge } from "../host/cep/bridge.js";

interface CEPWindow extends Window {
  CSInterface?: new () => EvalScriptBridge;
}

const output = document.getElementById("timeline-output");
const status = document.getElementById("status");
const refreshButton = document.getElementById("refresh");

function setStatus(message: string, isError = false): void {
  if (status === null) {
    return;
  }
  status.textContent = message;
  status.dataset.state = isError ? "error" : "ready";
}

function renderTracks(tracks: readonly PackedTrack[]): void {
  if (output === null) {
    return;
  }
  output.replaceChildren();
  for (const track of tracks) {
    const row = document.createElement("li");
    row.className = "track";
    row.textContent = `V${track.trackIndex + 1}: ${track.layerIds.join("  ·  ")}`;
    output.append(row);
  }
}

async function refresh(): Promise<void> {
  const Constructor = (window as CEPWindow).CSInterface;
  if (Constructor === undefined) {
    setStatus("CSInterface.js не загружен", true);
    return;
  }

  setStatus("Чтение активной композиции…");
  try {
    const adapter = new CEPAdapter(new Constructor());
    const snapshot = await adapter.readSnapshot();
    const packing = packLayers(snapshot);
    renderTracks(packing.tracks);
    setStatus(`${snapshot.compositionName}: ${snapshot.layers.length} layers, ${packing.tracks.length} tracks`);
  } catch (error) {
    setStatus(error instanceof Error ? error.message : "Не удалось прочитать композицию", true);
  }
}

refreshButton?.addEventListener("click", () => {
  void refresh();
});

void refresh();

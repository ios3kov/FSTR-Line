import { PanelController, type PanelState, type PanelView } from "./panel-controller.js";
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

function renderTracks(tracks: readonly { trackIndex: number; layerIds: readonly number[] }[]): void {
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

function createView(): PanelView {
  return {
    render(state: PanelState): void {
      if (state.status === "loading") {
        setStatus("Чтение активной композиции…");
        return;
      }
      if (state.status === "refreshing") {
        setStatus("Обновление композиции…");
        renderTracks(state.tracks);
        return;
      }
      if (state.status === "no-composition") {
        setStatus("Нет активной композиции", true);
        renderTracks([]);
        return;
      }
      if (state.status === "error") {
        setStatus(state.message, true);
        if (state.tracks !== undefined) {
          renderTracks(state.tracks);
        }
        return;
      }
      renderTracks(state.tracks);
      setStatus(`${state.snapshot.compositionName}: ${state.snapshot.layers.length} layers, ${state.tracks.length} tracks`);
    },
  };
}

function createController(): PanelController | undefined {
  const Constructor = (window as CEPWindow).CSInterface;
  if (Constructor === undefined) {
    setStatus("CSInterface.js не загружен", true);
    return undefined;
  }

  return new PanelController(new CEPAdapter(new Constructor()), createView());
}

const controller = createController();
refreshButton?.addEventListener("click", () => {
  void controller?.refresh();
});

void controller?.refresh();

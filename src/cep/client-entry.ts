import { PanelController, type PanelState, type PanelView } from "./panel-controller.js";
import { CEPAdapter, type EvalScriptBridge } from "../host/cep/bridge.js";
import { matchingBuilds, type BuildIdentity } from "../host/diagnostics.js";

declare const FSTR_BUILD: BuildIdentity;

interface CEPWindow extends Window {
  CSInterface?: new () => EvalScriptBridge;
}

const output = document.getElementById("timeline-output");
const status = document.getElementById("status");
const refreshButton = document.getElementById("refresh");
const buildStatus = document.getElementById("build-status");
const snapshotOutput = document.getElementById("snapshot-diagnostics");
let adapter: CEPAdapter | undefined;

async function updateBuildStatus(): Promise<void> {
  if (!buildStatus || !adapter) return;
  try {
    const host = await adapter.readDiagnostics();
    buildStatus.textContent = `${matchingBuilds(FSTR_BUILD, host.build) ? "MATCH" : "MISMATCH — reload panel / restart AE"}\nUI: ${FSTR_BUILD.buildId}\nHost: ${host.build.buildId}\nAE: ${host.aeVersion}`;
  } catch (error) {
    buildStatus.textContent = `UI: ${FSTR_BUILD.buildId}; host identity unavailable: ${String(error)}`;
  }
}

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
      if (refreshButton instanceof HTMLButtonElement) {
        refreshButton.disabled = state.status === "loading" || state.status === "refreshing";
      }
      if (snapshotOutput) {
        snapshotOutput.textContent = state.status === "ready"
          ? JSON.stringify(state.snapshot, null, 2)
          : `Snapshot unavailable or stale (${state.status}). Refresh to read current AE state.`;
      }
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
        renderTracks([]);
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

  adapter = new CEPAdapter(new Constructor());
  return new PanelController(adapter, createView());
}

const controller = createController();
refreshButton?.addEventListener("click", () => {
  void controller?.refresh();
  void updateBuildStatus();
});

void controller?.refresh();
void updateBuildStatus();

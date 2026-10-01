import { PanelController, projectionForState, type PanelState, type PanelView } from "./panel-controller.js";
import { renderTrackView } from "./track-view.js";
import { CEPAdapter, type EvalScriptBridge, type BridgeAttempt } from "../host/cep/bridge.js";
import { matchingBuilds, type BuildIdentity } from "../host/diagnostics.js";
import { AutoRefresh } from "./auto-refresh.js";

declare const FSTR_BUILD: BuildIdentity;
interface CEPWindow extends Window { CSInterface?: new () => EvalScriptBridge; }
const output = document.getElementById("timeline-output");
const status = document.getElementById("status");
const refreshButton = document.getElementById("refresh");
const buildStatus = document.getElementById("build-status");
const snapshotOutput = document.getElementById("snapshot-diagnostics");
let adapter: CEPAdapter | undefined;
const bridgeLog = document.getElementById("bridge-log");
const attempts: BridgeAttempt[] = [];
function recordAttempt(attempt: BridgeAttempt): void {
  attempts.push(attempt);
  if (attempts.length > 20) attempts.shift();
  if (bridgeLog) bridgeLog.textContent = attempts.map((entry) =>
    `${entry.operation} #${entry.attempt}: ${entry.outcome} (${entry.elapsedMs} ms)`).join("\n");
}
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
  if (!status) return;
  status.textContent = message;
  status.dataset.state = isError ? "error" : "ready";
}
function createView(): PanelView {
  return { render(state: PanelState): void {
    if (refreshButton instanceof HTMLButtonElement) refreshButton.disabled = state.status === "loading" || state.status === "refreshing";
    if (output) renderTrackView(output, state);
    const projection = projectionForState(state);
    if (snapshotOutput) snapshotOutput.textContent = projection
      ? `${state.status === "ready" ? "" : "STALE — last known data, not current AE state\n"}${JSON.stringify(projection.snapshot, null, 2)}`
      : `Snapshot unavailable (${state.status}).`;
    if (state.status === "loading") { setStatus("Чтение активной композиции…"); return; }
    if (state.status === "refreshing") { setStatus("Обновление композиции… Последние данные пока не подтверждены."); return; }
    if (state.status === "no-composition") {
      setStatus("Откройте композицию. Проверка её появления ограничена 15 попытками; затем используйте Refresh."); return;
    }
    if (state.status === "error") {
      const toggle = document.getElementById("auto-sync");
      if (toggle instanceof HTMLInputElement) toggle.checked = false;
      autoRefresh?.setContinuous(false);
      setStatus(`${state.message}${projection ? " — показаны последние данные, не актуальное состояние AE." : ""}`, true); return;
    }
    setStatus(`${state.snapshot.compositionName}: ${state.snapshot.layers.length} layers, ${state.tracks.length} tracks · read-only prototype`);
  } };
}
function createController(): PanelController | undefined {
  const Constructor = (window as CEPWindow).CSInterface;
  if (Constructor === undefined) { setStatus("CSInterface.js не загружен", true); return undefined; }
  adapter = new CEPAdapter(new Constructor(), { onAttempt: recordAttempt });
  return new PanelController(adapter, createView());
}
const controller = createController();
const autoRefresh = controller ? new AutoRefresh(() => controller.refresh(), {
  schedule: (callback, delay) => window.setTimeout(callback, delay),
  cancel: (handle) => window.clearTimeout(handle as number),
}, () => !document.hidden) : undefined;
const autoSync = document.getElementById("auto-sync");
autoSync?.addEventListener("change", () => {
  if (autoSync instanceof HTMLInputElement) autoRefresh?.setContinuous(autoSync.checked);
});
refreshButton?.addEventListener("click", () => { autoRefresh?.request(); void updateBuildStatus(); });
window.addEventListener("focus", () => autoRefresh?.request());
document.addEventListener("visibilitychange", () => {
  if (document.hidden) autoRefresh?.suspend(); else autoRefresh?.request();
});
window.addEventListener("pagehide", () => autoRefresh?.dispose());
autoRefresh?.request();
void updateBuildStatus();

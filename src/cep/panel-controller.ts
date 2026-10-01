import { packLayers } from "../core/packing.js";
import type { CompositionSnapshot, PackedTrack } from "../core/types.js";
import type { HostAdapter } from "../host/host-adapter.js";
import { HostResponseError } from "../host/protocol.js";

export interface PanelProjection {
  readonly snapshot: CompositionSnapshot;
  readonly tracks: readonly PackedTrack[];
}
export type PanelState =
  | { readonly status: "no-composition" }
  | { readonly status: "loading" }
  | ({ readonly status: "ready" | "refreshing" } & PanelProjection)
  | { readonly status: "error"; readonly message: string;
      readonly snapshot?: CompositionSnapshot; readonly tracks?: readonly PackedTrack[] };
export interface PanelView { render(state: PanelState): void; }

export function projectionForState(state: PanelState): PanelProjection | undefined {
  if ("snapshot" in state && state.snapshot && state.tracks) {
    return { snapshot: state.snapshot, tracks: state.tracks };
  }
  return undefined;
}

export class PanelController {
  private state: PanelState = { status: "no-composition" };
  private refreshPromise: Promise<PanelState> | undefined;
  private generation = 0;

  constructor(private readonly host: HostAdapter, private readonly view: PanelView) {
    this.view.render(this.state);
  }
  getState(): PanelState { return this.state; }
  refresh(): Promise<PanelState> {
    if (this.refreshPromise !== undefined) return this.refreshPromise;
    const projection = projectionForState(this.state);
    this.setState(projection ? { status: "refreshing", ...projection } : { status: "loading" });
    const generation = this.generation;
    this.refreshPromise = this.loadSnapshot(generation).finally(() => { this.refreshPromise = undefined; });
    return this.refreshPromise;
  }
  invalidate(): void {
    this.generation += 1;
    if (this.state.status !== "no-composition") this.setState({ status: "no-composition" });
  }
  private async loadSnapshot(generation: number): Promise<PanelState> {
    try {
      const snapshot = await this.host.readSnapshot();
      const tracks = packLayers(snapshot).tracks;
      if (generation !== this.generation) return this.state;
      const nextState: PanelState = { status: "ready", snapshot, tracks };
      this.setState(nextState);
      return nextState;
    } catch (error) {
      if (generation !== this.generation) return this.state;
      if (error instanceof HostResponseError && error.hostCode === "NO_ACTIVE_COMP") {
        const nextState: PanelState = { status: "no-composition" };
        this.setState(nextState);
        return nextState;
      }
      const projection = projectionForState(this.state);
      const nextState: PanelState = { status: "error",
        message: error instanceof Error ? error.message : "Unable to read composition",
        ...(projection ?? {}) };
      this.setState(nextState);
      return nextState;
    }
  }
  private setState(nextState: PanelState): void {
    this.state = nextState;
    this.view.render(nextState);
  }
}

import type { PanelState } from "./panel-controller.js";

export interface RefreshScheduler {
  schedule(callback: () => void, delayMs: number): unknown;
  cancel(handle: unknown): void;
}

/** Bounded startup/context discovery, not a continuous timeline synchronization loop. */
export class AutoRefresh {
  private timer: unknown;
  private pending = false;
  private disposed = false;
  private remaining = 0;

  constructor(
    private readonly refresh: () => Promise<PanelState>,
    private readonly scheduler: RefreshScheduler,
    private readonly visible: () => boolean,
  ) {}

  request(): void {
    if (this.disposed || this.pending || !this.visible()) return;
    this.clearTimer();
    this.remaining = 15;
    void this.run();
  }

  suspend(): void {
    this.remaining = 0;
    this.clearTimer();
  }

  dispose(): void {
    this.disposed = true;
    this.suspend();
  }

  private clearTimer(): void {
    if (this.timer !== undefined) this.scheduler.cancel(this.timer);
    this.timer = undefined;
  }

  private async run(): Promise<void> {
    this.timer = undefined;
    if (this.disposed || !this.visible() || this.remaining === 0) return;
    this.remaining -= 1;
    this.pending = true;
    try {
      const state = await this.refresh();
      if (!this.disposed && this.visible() && this.remaining > 0 && state.status === "no-composition") {
        this.timer = this.scheduler.schedule(() => { void this.run(); }, 2000);
      }
    } catch {
      // The normal controller renders errors; unexpected failures must not start a retry loop.
    } finally {
      this.pending = false;
    }
  }
}

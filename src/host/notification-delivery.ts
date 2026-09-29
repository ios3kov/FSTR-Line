/** Read-side contract only. No AE event source is registered by this module. */
export interface NotificationIdentity {
  readonly protocol: 1;
  readonly buildId: string;
  readonly aeBuild: string;
  readonly architecture: string;
  readonly beeUuid: string;
  readonly beeSha256: string;
  readonly afterFxUuid: string;
  readonly afterFxSha256: string;
}

export interface NotificationHandshake extends NotificationIdentity {
  readonly sessionId: string;
  readonly sequence: number;
  readonly committedDelivery: true;
}

export interface DeliveryClock {
  schedule(callback: () => void, delayMs: number): unknown;
  cancel(handle: unknown): void;
}

export interface SnapshotDelivery<T> {
  /** Settlement must mean the host operation ended, not just a transport timeout. */
  read(): Promise<T>;
  /** Must invalidate any editable preview before the next snapshot. */
  invalidate(): void;
  publish(snapshot: T): void;
}

export type DeliveryState =
  | { readonly status: "closed" }
  | { readonly status: "active"; readonly sessionId: string }
  | { readonly status: "blocked"; readonly reason: string };

const identityKeys = ["protocol", "buildId", "aeBuild", "architecture", "beeUuid",
  "beeSha256", "afterFxUuid", "afterFxSha256"] as const;
const token = (value: unknown): value is string =>
  typeof value === "string" && /^[A-Za-z0-9._:-]{1,128}$/.test(value);
const counter = (value: unknown): value is number =>
  typeof value === "number" && Number.isSafeInteger(value) && value >= 0;
const record = (value: unknown): value is Record<string, unknown> =>
  value !== null && typeof value === "object" && !Array.isArray(value);

/**
 * Single-flight, event-driven reconciliation. The integration owns transport,
 * authenticates the producer, and verifies actual loaded binary identities.
 * A matching message is not proof that the source is safe or post-commit.
 */
export class NotificationDelivery<T> {
  private readonly expected: NotificationIdentity;
  private state: DeliveryState = { status: "closed" };
  private generation = 0;
  private sequence = 0;
  private change = 0;
  private dirty = false;
  private pending = false;
  private timedOut = false;
  // Retain all accepted IDs for this instance. A bounded set prevents a
  // session-1 -> session-2 -> session-1 replay without unbounded growth.
  private readonly usedSessions = new Set<string>();
  private readonly maxSessions = 1024;
  private gaps = 0;
  private duplicates = 0;

  constructor(
    expected: NotificationIdentity,
    private readonly sink: SnapshotDelivery<T>,
    private readonly clock: DeliveryClock,
    private readonly timeoutMs = 5000,
  ) {
    if (expected.protocol !== 1 || identityKeys.some((key) =>
      key !== "protocol" && !token(expected[key])) ||
      !/^[a-f0-9]{64}$/.test(expected.beeSha256) ||
      !/^[a-f0-9]{64}$/.test(expected.afterFxSha256) ||
      !Number.isFinite(timeoutMs) || timeoutMs <= 0 || timeoutMs > 60000) {
      throw new Error("Invalid notification compatibility policy or deadline");
    }
    this.expected = { ...expected };
  }

  getState(): DeliveryState { return { ...this.state }; }
  getDiagnostics(): { gaps: number; duplicates: number; pending: boolean } {
    return { gaps: this.gaps, duplicates: this.duplicates, pending: this.pending };
  }

  /** Explicit open/recovery only; never call this from a periodic timer. */
  open(handshake: unknown): boolean {
    this.generation += 1;
    this.dirty = false;
    if (this.timedOut && this.pending) {
      this.block("READ_OUTCOME_PENDING");
      return false;
    }
    if (!record(handshake) || identityKeys.some((key) => handshake[key] !== this.expected[key]) ||
        handshake.committedDelivery !== true || !token(handshake.sessionId) ||
        !counter(handshake.sequence) || this.usedSessions.has(handshake.sessionId) ||
        this.usedSessions.size >= this.maxSessions) {
      this.block("INCOMPATIBLE_OR_REUSED_SESSION");
      return false;
    }
    this.usedSessions.add(handshake.sessionId);
    this.sequence = handshake.sequence;
    this.change = 0;
    this.timedOut = false;
    this.state = { status: "active", sessionId: handshake.sessionId };
    this.requestSnapshot();
    return this.state.status === "active";
  }

  close(): void {
    this.generation += 1;
    this.dirty = false;
    this.state = { status: "closed" };
    this.invalidate();
    // An outstanding read cannot be cancelled by dropping its Promise. Keep
    // the single-flight guard and deadline until it actually settles.
  }

  receive(raw: string): void {
    if (this.state.status !== "active") return;
    let event: unknown;
    try {
      if (typeof raw !== "string" || raw.length > 2048) throw new Error();
      event = JSON.parse(raw);
    } catch {
      this.block("INVALID_EVENT");
      return;
    }
    if (!record(event) || !token(event.sessionId)) {
      this.block("INVALID_EVENT");
      return;
    }
    if (event.sessionId !== this.state.sessionId) return;
    if (event.protocol !== 1 || !counter(event.sequence) || event.sequence === 0 ||
        event.phase !== "committed" ||
        !["changed", "noop", "overflow"].includes(event.kind as string)) {
      this.block("INVALID_EVENT");
      return;
    }
    if (event.sequence <= this.sequence) {
      this.duplicates = Math.min(Number.MAX_SAFE_INTEGER, this.duplicates + 1);
      return;
    }
    const gap = event.sequence - this.sequence > 1;
    this.sequence = event.sequence;
    if (gap || event.kind === "overflow") {
      this.gaps = Math.min(Number.MAX_SAFE_INTEGER, this.gaps + 1);
    }
    if (gap || event.kind !== "noop") this.requestSnapshot();
  }

  private invalidate(): boolean {
    try { this.sink.invalidate(); return true; }
    catch {
      this.state = { status: "blocked", reason: "INVALIDATION_FAILED" };
      this.dirty = false;
      this.generation += 1;
      return false;
    }
  }

  private block(reason: string): void {
    this.generation += 1;
    this.dirty = false;
    this.state = { status: "blocked", reason };
    this.invalidate();
  }

  private requestSnapshot(): void {
    // Bounded state, regardless of the number of notifications in a burst.
    this.change += 1;
    const alreadyDirty = this.dirty;
    this.dirty = true;
    if (!alreadyDirty && !this.invalidate()) return;
    void this.drain();
  }

  private async drain(): Promise<void> {
    if (this.pending || !this.dirty || this.state.status !== "active") return;
    this.pending = true;
    this.dirty = false;
    const generation = this.generation;
    const change = this.change;
    let deadline: unknown;
    let outstanding = true;
    try {
      deadline = this.clock.schedule(() => {
        if (!outstanding) return;
        // Applies to the outstanding operation even after close/reopen.
        this.timedOut = true;
        if (this.state.status !== "closed") this.block("READ_TIMEOUT");
      }, this.timeoutMs);
      const snapshot = await this.sink.read();
      if (!this.timedOut && this.state.status === "active" &&
          generation === this.generation && change === this.change) {
        this.sink.publish(snapshot);
      }
    } catch {
      if (generation === this.generation && this.state.status === "active") {
        this.block("READ_OR_PUBLICATION_FAILED");
      }
    } finally {
      outstanding = false;
      try { if (deadline !== undefined) this.clock.cancel(deadline); }
      catch {
        this.timedOut = true;
        this.block("DEADLINE_CLEANUP_FAILED");
      }
      this.pending = false;
      // Only an actual queued change or explicit reconnect permits another read.
      if (!this.timedOut) void this.drain();
    }
  }
}

import type { TimelineCommand, CompositionSnapshot } from "../../core/types.js";
import { HostResponseError, parseOperationResponse, parseSnapshotResponse, serializeCommandForEval } from "../protocol.js";
import type { HostAdapter, HostOperationResult } from "../host-adapter.js";
import { parseDiagnostics, type HostDiagnostics } from "../diagnostics.js";

export interface EvalScriptBridge { evalScript(script: string, callback: (result: string) => void): void; }
export interface CEPAdapterOptions {
  readonly timeoutMs?: number;
  readonly onAttempt?: (attempt: BridgeAttempt) => void;
}
export interface BridgeAttempt {
  readonly operation: "snapshot" | "diagnostics" | "command";
  readonly attempt: number;
  readonly elapsedMs: number;
  readonly outcome: "empty" | "response" | "transport-error";
}
export class CEPAdapter implements HostAdapter {
  private readonly timeoutMs: number;
  private operationTail: Promise<void> = Promise.resolve();
  private readonly onAttempt: CEPAdapterOptions["onAttempt"];
  private writeOutcomeUncertain = false;
  // A rejected JS Promise is not cancellation of an ExtendScript invocation.
  private pendingEval: { readonly completion: Promise<void> } | undefined;
  constructor(private readonly bridge: EvalScriptBridge, options: CEPAdapterOptions = {}) {
    this.timeoutMs = options.timeoutMs ?? 5000;
    this.onAttempt = options.onAttempt;
  }
  async readSnapshot(): Promise<CompositionSnapshot> {
    return this.enqueue(async () => parseSnapshotResponse(await this.readWithRecovery("fstrLineHost.readSnapshot()", "snapshot")));
  }
  /** NotificationDelivery owns the deadline and must retain its in-flight guard
   * until the actual host callback, including after a UI-facing read timeout. */
  async readNotificationSnapshot(): Promise<CompositionSnapshot> {
    try { return await this.readSnapshot(); }
    catch (error) {
      await this.pendingEval?.completion;
      throw error;
    }
  }
  async readDiagnostics(): Promise<HostDiagnostics> {
    return this.enqueue(async () => parseDiagnostics(await this.readWithRecovery("fstrLineHost.diagnostics()", "diagnostics")));
  }
  async execute(command: TimelineCommand): Promise<HostOperationResult> {
    return this.enqueue(async () => {
      if (this.writeOutcomeUncertain) throw new Error("UNKNOWN_COMMAND_OUTCOME: further writes disabled; inspect native AE and restart the host/bridge.");
      const payload = serializeCommandForEval(command);
      let raw: string;
      try { raw = await this.tracedEval(`fstrLineHost.executeCommand(${payload})`, "command", 1); }
      catch (error) { this.writeOutcomeUncertain = true; throw error; }
      try {
        const result = parseOperationResponse(raw);
        if (result.operationId !== command.operationId) throw new Error("Host operation identity mismatch");
        return result;
      } catch (error) {
        // A failed transport/invalid reply does NOT prove that AE did not apply the edit.
        if (!(error instanceof HostResponseError) || error.hostCode === "ROLLBACK_FAILED" || error.hostCode === "RECOVERY_REQUIRED") {
          this.writeOutcomeUncertain = true;
        }
        throw error;
      }
    });
  }
  private async readWithRecovery(script: string, operation: "snapshot" | "diagnostics"): Promise<string> {
    // Bounded startup workaround; never retry mutations, timeouts, or host errors.
    for (let attempt = 1; attempt <= 3; attempt += 1) {
      const raw = await this.tracedEval(script, operation, attempt);
      if (raw !== "") return raw;
      if (attempt < 3) await new Promise<void>((resolve) => setTimeout(resolve, attempt * 500));
    }
    throw new Error(`AE returned an empty response after 3 ${operation} attempts. Use Refresh to retry.`);
  }
  private async tracedEval(script: string, operation: BridgeAttempt["operation"], attempt: number): Promise<string> {
    const start = Date.now();
    let outcome: BridgeAttempt["outcome"] = "transport-error";
    try { const raw = await this.eval(script); outcome = raw === "" ? "empty" : "response"; return raw; }
    finally { try { this.onAttempt?.({ operation, attempt, elapsedMs: Date.now() - start, outcome }); } catch { /* observer only */ } }
  }
  private enqueue<T>(operation: () => Promise<T>): Promise<T> {
    const guarded = () => {
      if (this.pendingEval !== undefined) {
        throw new Error("HOST_CALL_PENDING: previous AE call has not returned; wait for its callback or recover the host session. Reload is not proof of cancellation.");
      }
      return operation();
    };
    const result = this.operationTail.then(guarded, guarded);
    this.operationTail = result.then(() => undefined, () => undefined);
    return result;
  }
  private eval(script: string): Promise<string> {
    return new Promise((resolve, reject) => {
      let settled = false;
      let completed!: () => void;
      const token = { completion: new Promise<void>((resolveCompletion) => { completed = resolveCompletion; }) };
      this.pendingEval = token;
      const timer = setTimeout(() => {
        if (!settled) { settled = true; reject(new Error(`CEP evalScript timed out after ${this.timeoutMs}ms`)); }
      }, this.timeoutMs);
      try {
        this.bridge.evalScript(script, (result) => {
          // Late completion releases only its own invocation. It must neither
          // resolve the expired read nor unlock a newer invocation twice.
          if (this.pendingEval === token) this.pendingEval = undefined;
          completed();
          if (settled) return;
          settled = true; clearTimeout(timer); resolve(result);
        });
      } catch (error) {
        // A synchronous bridge exception does not establish whether dispatch
        // happened. Keep the guard until a callback or real host recovery.
        if (!settled) { settled = true; clearTimeout(timer); reject(error); }
      }
    });
  }
}

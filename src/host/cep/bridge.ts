import type { TimelineCommand } from "../../core/types.js";
import { parseOperationResponse, parseSnapshotResponse, serializeCommandForEval } from "../protocol.js";
import type { HostAdapter, HostOperationResult } from "../host-adapter.js";
import type { CompositionSnapshot } from "../../core/types.js";
import { parseDiagnostics, type HostDiagnostics } from "../diagnostics.js";

export interface EvalScriptBridge {
  evalScript(script: string, callback: (result: string) => void): void;
}

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

  constructor(
    private readonly bridge: EvalScriptBridge,
    options: CEPAdapterOptions = {},
  ) {
    this.timeoutMs = options.timeoutMs ?? 5000;
    this.onAttempt = options.onAttempt;
  }

  async readSnapshot(): Promise<CompositionSnapshot> {
    return this.enqueue(async () => {
      const raw = await this.readWithRecovery("fstrLineHost.readSnapshot()", "snapshot");
      return parseSnapshotResponse(raw);
    });
  }

  async readDiagnostics(): Promise<HostDiagnostics> {
    return this.enqueue(async () => parseDiagnostics(await this.readWithRecovery("fstrLineHost.diagnostics()", "diagnostics")));
  }

  async execute(command: TimelineCommand): Promise<HostOperationResult> {
    return this.enqueue(async () => {
      const payload = serializeCommandForEval(command);
      const raw = await this.tracedEval(`fstrLineHost.executeCommand(${payload})`, "command", 1);
      return parseOperationResponse(raw);
    });
  }

  private async readWithRecovery(script: string, operation: "snapshot" | "diagnostics"): Promise<string> {
    // Observed AE startup empty reply recovers on manual Refresh. Root cause is unknown.
    // Retry only completed empty reads, never commands, timeouts or host error envelopes.
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
    try {
      const raw = await this.eval(script);
      outcome = raw === "" ? "empty" : "response";
      return raw;
    } finally {
      // Diagnostics must not change operation semantics, even if the view fails.
      try { this.onAttempt?.({ operation, attempt, elapsedMs: Date.now() - start, outcome }); } catch { /* observer only */ }
    }
  }

  private enqueue<T>(operation: () => Promise<T>): Promise<T> {
    const result = this.operationTail.then(operation, operation);
    this.operationTail = result.then(() => undefined, () => undefined);
    return result;
  }

  private eval(script: string): Promise<string> {
    return new Promise((resolve, reject) => {
      let settled = false;
      const timer = setTimeout(() => {
        if (!settled) {
          settled = true;
          reject(new Error(`CEP evalScript timed out after ${this.timeoutMs}ms`));
        }
      }, this.timeoutMs);

      try {
        this.bridge.evalScript(script, (result) => {
          if (settled) {
            return;
          }
          settled = true;
          clearTimeout(timer);
          resolve(result);
        });
      } catch (error) {
        if (!settled) {
          settled = true;
          clearTimeout(timer);
          reject(error);
        }
      }
    });
  }
}

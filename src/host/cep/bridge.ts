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
}

export class CEPAdapter implements HostAdapter {
  private readonly timeoutMs: number;
  private operationTail: Promise<void> = Promise.resolve();

  constructor(
    private readonly bridge: EvalScriptBridge,
    options: CEPAdapterOptions = {},
  ) {
    this.timeoutMs = options.timeoutMs ?? 5000;
  }

  async readSnapshot(): Promise<CompositionSnapshot> {
    return this.enqueue(async () => {
      const raw = await this.eval("fstrLineHost.readSnapshot()");
      return parseSnapshotResponse(raw);
    });
  }

  async readDiagnostics(): Promise<HostDiagnostics> {
    return this.enqueue(async () => parseDiagnostics(await this.eval("fstrLineHost.diagnostics()")));
  }

  async execute(command: TimelineCommand): Promise<HostOperationResult> {
    return this.enqueue(async () => {
      const payload = serializeCommandForEval(command);
      const raw = await this.eval(`fstrLineHost.executeCommand(${payload})`);
      return parseOperationResponse(raw);
    });
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

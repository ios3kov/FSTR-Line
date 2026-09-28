import type { CompositionSnapshot, TimelineCommand } from "../core/types.js";

export interface HostOperationResult {
  readonly operationId: string;
  readonly changed: boolean;
  readonly snapshot: CompositionSnapshot;
}

export interface HostAdapter {
  readSnapshot(): Promise<CompositionSnapshot>;
  execute(command: TimelineCommand): Promise<HostOperationResult>;
}

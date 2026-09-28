import { parseResponse } from "./protocol.js";

export interface BuildIdentity {
  readonly buildId: string;
  readonly gitCommit: string;
  readonly dirty: boolean;
  readonly version: string;
}

export interface HostDiagnostics {
  readonly build: BuildIdentity;
  readonly aeVersion: string;
}

export function parseDiagnostics(raw: string): HostDiagnostics {
  const value = parseResponse<HostDiagnostics>(raw);
  const build = value?.build;
  if (!build || typeof build.buildId !== "string" || !build.buildId ||
      typeof build.gitCommit !== "string" || !/^[a-f0-9]{40}$/.test(build.gitCommit) ||
      typeof build.dirty !== "boolean" || typeof build.version !== "string" || !build.version ||
      typeof value.aeVersion !== "string" || !value.aeVersion) {
    throw new Error("Malformed host diagnostics");
  }
  return value;
}

export function matchingBuilds(a: BuildIdentity, b: BuildIdentity): boolean {
  return a.buildId === b.buildId && a.gitCommit === b.gitCommit &&
    a.dirty === b.dirty && a.version === b.version;
}

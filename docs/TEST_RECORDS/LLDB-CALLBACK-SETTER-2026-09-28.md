# LLDB callback setter return semantics — 2026-09-28

At f4669d7 the macOS runtime smoke successfully attached to the owned fixture and resolved one expected breakpoint location, then the controller failed because it treated the return of SBBreakpoint.SetScriptCallbackFunction as a boolean success indicator. In this LLDB Python binding the setter returns None on success. Earlier real_lldb_control already used the same method without a boolean check and observed 3/3 callback hits.

The controller now calls SetScriptCallbackFunction without interpreting its return. This does not weaken acceptance: the runtime smoke still requires at least one actual candidate-hit in trace.jsonl, correct PID/module UUID, semantic non-overclaim, normal observer completion and clean detach. If the callback is not installed, the smoke still fails on zero hits.

No AE behavior, breakpoint regex, module identity, target state access or security setting is changed. Full rerun required.

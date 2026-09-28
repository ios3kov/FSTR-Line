# Command probe runtime — 2026-09-28

## Run identity

- Run: `runtime-20260928T184627Z`
- Build ID: `20260928T184359Z-cf383a8-72414`
- Target: After Effects `25.6x101` (`25.6.0.101`), macOS arm64
- Probe: `FSTRCommandProbe.plugin`, installed in the AE MediaCore test location
- Initial project state: `numItems=0`, `dirty=false`
- Log: `.artifacts/command-probe/runtime-20260928T184627Z/events.jsonl`

## Registration result

PASS. AE loaded the corrected probe and emitted:

```json
{"buildId":"20260928T184359Z-cf383a8-72414","sequence":1,"kind":"loaded","command":0,"requestedPriority":1,"priority":0,"alreadyHandled":0}
```

The previous `5027:47 Plugin ID is invalid` run is invalid and is excluded from
the result because its entry-point ABI was wrong. The corrected build uses the
five-argument `AEGP_PluginInitFunc` signature and includes a compile-time ABI
assertion.

The callback reported `priority=0`, although registration requested
`AEGP_HP_BeforeAE` (`1`). The probe's event record is therefore evidence of the
actual value passed by AE, not evidence that the callback runs after a change.
The SDK header says the command-hook priority is currently always BeforeAE;
this discrepancy requires follow-up before interpreting timing.

## Script-originated mutation scenario

The following was executed through ExtendScript in the same AE process:

1. create a composition;
2. add a solid layer;
3. modify start time, in point and out point;
4. change the enabled switch and layer selection;
5. set composition time;
6. close the undo group.

Result: **no command callback was appended** after the operation. The only log
record remained the initial `loaded` record. This is a negative observation for
the command hook as a detector of this script-originated mutation scenario.
It does not yet establish whether the absence is caused by script execution,
command-hook semantics, or the probe's registration context.

## Coverage status

| Scenario | Result |
|---|---|
| Probe loaded | PASS |
| ExtendScript composition/layer mutation | No callback observed |
| Native layer drag/trim | NOT RUN |
| Native add/delete/reorder | NOT RUN |
| Native switches and selection | NOT RUN |
| Composition activation/project change | NOT RUN |
| Playhead/scrub/playback | NOT RUN |
| Native Undo/Redo | NOT RUN |
| Other-plugin mutation | NOT RUN |

Conclusion: `AEGP_Command_ALL` is not proven to be a complete source. The first
runtime observation is negative for the tested ExtendScript scenario. SYNC-001
remains blocked; no production synchronization change is accepted from this
probe.

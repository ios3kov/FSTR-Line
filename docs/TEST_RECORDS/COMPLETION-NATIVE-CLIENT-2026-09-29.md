# Native completion subscriber and deferred work — 2026-09-29

Baseline `fbba0f908b4619807852af7e427a2750ef372b82`. Read-only static
inspection of installed AE 25.6.0.101 arm64. No process attach, native call,
installation or project change. Goal: identify an actual registration client,
its context acquisition, callback behavior and exported-symbol availability.

Verified on-disk SHA-256:

- BEE.dylib: `817b9de9c6d57b5d6988b634842090e1528fe817a5685c8d1ff358553c6660ca`.
- AfterFXLib: `ce3aa2f16fe5449a77379a6b622e1a221596e511b86f7708dd3e2f7a3cced01a`.

## Observed native path

Addresses are unslid and apply only to these files.

| Site | Static observation |
| --- | --- |
| AfterFXLib SamuraiUpdateParamsUI, `0x885d9c`–`0x885dcc` | Obtains an AV layer from PF_InData, its CLayer/parent comp, parent project, then BEE_Project::GetUndoContext |
| `0x885dd4`–`0x885dd8` | Tests GetExecutingAnything; inactive path branches to direct queue posting |
| `0x885e40` | Active path calls GetUndoCommandCompletedSignal |
| `0x885e98` | Calls Signal<void(BEE_UndoContext*), true>::Connect with a std::__1::function; x8 supplies indirect return storage |
| `0x885ea4` | Moves returned Connection into a heap-held ScopedConnection captured by the callback |
| Callback `0x89c290`, normal path `0x89c2d8` | Posts a captured-ID function through BEE_WorkQueue_PostGenericFunction |
| Callback `0x89c308` | Disconnects after queue posting on the normal path |
| Inactive path `0x885f0c` | Posts the same kind of work without waiting on completion |

The callback body has an exception-unwind path at `0x89c320`–`0x89c350`
which does not execute the normal-path Disconnect call. The observed pattern
therefore is not proof of exactly-once cleanup under arbitrary queue failure.

The full Connect specialization at AfterFXLib `0x8869e0` takes callback
ownership, registers a connection link under a recursive mutex, and constructs
a Connection from weak link ownership at `0x886b74`. `nm` lists this function
as local text (`t`); `nm -gU` does not list it. No definition of this exact
specialization was found in BEE. This does not prove absence in every AE module,
but this native call site is not an exported registrar usable by ordinary
symbol lookup in these two modules.

BEE_WorkQueue_PostGenericFunction at `0x7913dc` reads the global queue pointer;
when null it returns at `0x7913f0` without posting. Otherwise it tail-calls
BEE_ThreadedRenderUpdateQueue::PostGenericFunction at `0x780e88`. That body
copies/binds the function, calls AddFunctionToQueue at `0x780f50`, and conditionally
invokes a stored callback. Queue execution thread, ordering, queue lifecycle and
completion acknowledgement are not established by these bodies.

The bound execution target is Render_GenericFunction at BEE `0x781024`.
Its complete body calls BEE_Globals::GetProjectClone at `0x781040`, constructs
BEE_ProjectSetContext around that returned pointer at `0x781050`, passes the
same pointer to the queued function at `0x78106c`, then destroys the context
guard on normal and unwind paths. GetProjectClone itself is a two-instruction
load of the globals object's `+0x18` member. Thus this path selects the global
clone accessor at execution time; it does not pass a captured original project
pointer from registration. Clone freshness, association with the UI project,
and permission to call public AEGP APIs in this context remain unverified.

## Interpretation and decision

An actual native client uses completion to trigger deferred work. Its callback
does not directly perform a project snapshot read. This narrows a viable
research direction, but does not establish that completion itself is a safe
post-commit barrier for FSTR. The native client obtains context through an
effect-specific internal object chain; it does not provide a public AEGP bridge
from a project handle to a lifetime-safe BEE_UndoContext.

Do not implement an address-based call to the local Connect specialization or
copy its object layout into a shipping plugin from this evidence. Required
unknowns remain context acquisition/lifetime, compatible callback and return
ABI, queue acknowledgement/recovery, callback quiescence/module unload, and
coverage beyond Undo activity. Licensing/maintenance acceptance remains open.

The queued path must not be treated as a proven main-thread AEGP snapshot
dispatcher. Next bounded work: establish queue execution ordering/thread and
clone association, and determine whether an exported registration/context path exists. A future
disposable harness needs those contracts before invoking a private callback.
SYNC-001 shipping source and delivery remain BLOCKED/NOT RUN.

## Reproduction and verification

Use `xcrun llvm-objdump --macho --arch=arm64 --disassemble --dis-symname`
with the installed module and these exact symbols:

AfterFXLib:

```text
__Z21SamuraiUpdateParamsUIP9PF_InDataP10PF_OutDataPP11PF_ParamDef
__ZNSt3__110__function6__funcIZ21SamuraiUpdateParamsUIP9PF_InDataP10PF_OutDataPP11PF_ParamDefE3$_0NS_9allocatorIS9_EEFvP15BEE_UndoContextEEclEOSD_
__ZN7dvacore9messaging6SignalIFvP15BEE_UndoContextELb1EE7ConnectENSt3__18functionIS4_EE
```

BEE:

```text
__Z33BEE_WorkQueue_PostGenericFunctionRKN5boost8functionIFvR11BEE_ProjectEEE
__ZN29BEE_ThreadedRenderUpdateQueue19PostGenericFunctionERKN5boost8functionIFvR11BEE_ProjectEEE
__ZN29BEE_ThreadedRenderUpdateQueue22Render_GenericFunctionERKN5boost8functionIFvR11BEE_ProjectEEE
__ZN11BEE_Globals15GetProjectCloneEv
```

The first full caller output exceeded the display limit; conclusions use the
explicitly reread `0x885d98`–`0x885f10` registration/branch region and complete
callback/Connect/queue bodies. Whole-caller completeness is not claimed.
Compared all-symbol and exported-defined-symbol inventories with successful
tool exits. Documentation review and `git diff --check` apply. Build/runtime
regression N/A for this documentation-only record under DEVELOPMENT_RULES §9;
no new application artifact or runtime acceptance is asserted.

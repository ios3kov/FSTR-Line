#!/usr/bin/env python3
"""Read-only queue/context evidence collector. Never calls or loads Adobe code."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import plistlib
import re
import selectors
import signal
import subprocess
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
# Exact names from COMPLETION-NATIVE-CLIENT-2026-09-29.md, not guessed ABIs.
REQUIRED = {
    "BEE": (
        "__Z33BEE_WorkQueue_PostGenericFunctionRKN5boost8functionIFvR11BEE_ProjectEEE",
        "__ZN29BEE_ThreadedRenderUpdateQueue19PostGenericFunctionERKN5boost8functionIFvR11BEE_ProjectEEE",
        "__ZN29BEE_ThreadedRenderUpdateQueue22Render_GenericFunctionERKN5boost8functionIFvR11BEE_ProjectEEE",
        "__ZN11BEE_Globals15GetProjectCloneEv",
    ),
    "AfterFXLib": (
        "__Z21SamuraiUpdateParamsUIP9PF_InDataP10PF_OutDataPP11PF_ParamDef",
        "__ZN7dvacore9messaging6SignalIFvP15BEE_UndoContextELb1EE7ConnectENSt3__18functionIS4_EE",
        "__ZNSt3__110__function6__funcIZ21SamuraiUpdateParamsUIP9PF_InDataP10PF_OutDataPP11PF_ParamDefE3$_0NS_9allocatorIS9_EEFvP15BEE_UndoContextEEclEOSD_",
    ),
}
LEADS = re.compile(
    r"BEE_ThreadedRenderUpdateQueue.*(?:GenericFunction|AddFunctionToQueue|"
    r"Deserialize|Serialize|Process|Run|Execute|Wait|Flush|Cancel|Clear)|"
    r"BEE_Globals.*(?:Project|Thread)|BEE_Project.*(?:GetUndoContext|Clone)|"
    r"BEE_WorkQueue.*(?:RegisterListener|DeregisterListener)|"
    r"SignalIFvP15BEE_UndoContext.*Connect"
)
# Exact call operands and switch layout from the retained qk6xsvhj report.
# The profile never invokes these functions and never accepts arbitrary VM reads.
CONTEXT_REQUIRED = {
    "BEE": (
        "__Z16BEE_QueryProjectPP11BEE_Project",
        "__Z26BEE_GetCurrentConstProjectv",
        "__ZN21BEE_ProjectSetContextC1EP11BEE_Project",
        "__ZN21BEE_ProjectSetContextD1Ev",
        "__ZN29BEE_ThreadedRenderUpdateQueue18AddFunctionToQueueERKN5boost8functionIFvvEEEP15BEE_UndoContextsPKcS9_PKNSt3__112basic_stringIhNSA_11char_traitsIhEEN7dvacore9allocator12STLAllocatorIhEEEENS_11CommandTypeE",
    ),
    "AfterFXLib": (),  # identity/inventory checked, old callback bodies not repeated
}
CONTEXT_LEADS = re.compile(
    r"^__Z(?:16BEE_QueryProject|26BEE_GetCurrentConstProject)|"
    r"^__ZN21BEE_ProjectSetContext|"
    r"^__ZN29BEE_ThreadedRenderUpdateQueue(?:C[12]|D[012])|"
    r"^__Z[0-9]+BEE_WorkQueue_[A-Za-z_]*(?:Listener|Notify|Dispatch|Emit|Process|Change)"
)
CONTEXT_TABLE = {"moduleSha256": "817b9de9c6d57b5d6988b634842090e1528fe817a5685c8d1ff358553c6660ca",
                 "vmAddress": 0xe8c4d4, "byteCount": 4, "dispatchBase": 0x777c8c,
                 "functionAddress": 0x777bfc}


MAX_BINARY = 2 * 1024**3
MAX_NM = 64 * 1024**2
MAX_BODY = 2 * 1024**2
MAX_LEADS = 256
MAX_SELECTED = 12


class Blocked(ValueError):
    """A missing prerequisite; never evidence that a host mechanism is absent."""


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fingerprint(path: Path) -> str:
    with path.open("rb") as source:
        if not 0 < os.fstat(source.fileno()).st_size <= MAX_BINARY:
            raise Blocked("BINARY_SIZE")
        h = hashlib.sha256()
        total = 0
        for chunk in iter(lambda: source.read(1024**2), b""):
            total += len(chunk)
            if total > MAX_BINARY:
                raise Blocked("BINARY_SIZE")
            h.update(chunk)
        return h.hexdigest()


def run_tool(args: list[str], *, timeout: float = 60, max_bytes: int = MAX_BODY) -> dict:
    """Bound bytes while the child runs, not after capture_output has allocated them."""
    if timeout <= 0 or max_bytes < 1:
        raise ValueError("positive tool bounds required")
    data = bytearray()
    reason = None
    code = None
    try:
        with subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              start_new_session=True) as proc:
            try:
                deadline = time.monotonic() + timeout
                with selectors.DefaultSelector() as ready:
                    ready.register(proc.stdout, selectors.EVENT_READ)
                    while ready.get_map():
                        left = deadline - time.monotonic()
                        if left <= 0:
                            reason = "TIMEOUT"
                            break
                        if not ready.select(left):
                            reason = "TIMEOUT"
                            break
                        chunk = os.read(proc.stdout.fileno(), min(65536, max_bytes + 1 - len(data)))
                        if not chunk:
                            ready.unregister(proc.stdout)
                            break
                        data.extend(chunk)
                        if len(data) > max_bytes:
                            reason = "OUTPUT_LIMIT"
                            break
                if reason is None:
                    try:
                        code = proc.wait(timeout=max(0.001, deadline - time.monotonic()))
                    except subprocess.TimeoutExpired:
                        reason = "TIMEOUT"
            finally:
                # Only the new process group created above, never an AE/user PID.
                if reason is not None or proc.poll() is None:
                    try:
                        os.killpg(proc.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                code = proc.wait(timeout=5)
    except (OSError, subprocess.SubprocessError):
        reason = "TOOL_UNAVAILABLE"
    raw = bytes(data[:max_bytes])
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("utf-8", "replace")
        reason = reason or "INVALID_UTF8"
    return {"exitCode": code, "complete": reason is None and code == 0,
            "reason": reason or (None if code == 0 else "TOOL_FAILED"),
            "bytes": len(raw), "sha256": digest(raw), "text": text}


def arm64_uuid(text: str) -> str:
    matches = re.findall(r"^UUID:\s*([0-9a-fA-F-]{36})\s+\(arm64\)(?:\s|$)", text, re.M)
    if len(matches) != 1:
        raise Blocked("ARM64_UUID_MISSING_OR_AMBIGUOUS")
    import uuid
    return str(uuid.UUID(matches[0]))


def text_symbol_table(text: str) -> dict[str, set[int]]:
    """Preserve every distinct address; local names need not be globally unique.

    This is still a complete, strict parse of the bounded tool output. Nothing
    here selects an address, establishes an ABI or permits a private call.
    """
    result = {}
    for line in text.splitlines():
        if not line.strip() or line.rstrip().endswith(":"):
            continue
        row = re.fullmatch(r"\s*([0-9a-fA-F]+)\s+([A-Za-z?])\s+(.+?)\s*", line)
        if row is None:
            raise Blocked("UNRECOGNIZED_NM_OUTPUT")
        address, kind, symbol = row.groups()
        if kind not in ("t", "T"):
            continue
        result.setdefault(symbol, set()).add(int(address, 16))
    return result


def text_symbols(text: str) -> dict[str, int]:
    """Strict unique-address view for existing isolated tooling controls."""
    table = text_symbol_table(text)
    if any(len(addresses) != 1 for addresses in table.values()):
        raise Blocked("DUPLICATE_TEXT_SYMBOL")
    return {name: next(iter(addresses)) for name, addresses in table.items()}


def address_evidence(addresses: set[int]) -> dict:
    """Bound report samples, without discarding addresses used for validation."""
    return {"distinctAddressCount": len(addresses),
            "addresses": [hex(a) for a in sorted(addresses)[:4]],
            "addressesTruncated": len(addresses) > 4}


def ambiguity_evidence(defined: dict[str, set[int]], exported: dict[str, set[int]]) -> dict:
    names = sorted(name for name, addresses in defined.items() if len(addresses) > 1)
    return {"definedNameCount": len(names),
            "exportedNameCount": sum(len(a) > 1 for a in exported.values()),
            "samplesTruncated": len(names) > 12,
            "samples": [{"symbol": name[:2048], "symbolTruncated": len(name) > 2048,
                         **address_evidence(defined[name])} for name in names[:12]]}


def inspect_body(text: str, symbol: str, address: int) -> dict:
    """Positive target/body check, NOT proof of full CFG or runtime semantics."""
    lines = text.splitlines()
    labels = [i for i, line in enumerate(lines) if line.strip() == symbol + ":"]
    if len(labels) != 1:
        raise Blocked("REQUESTED_BODY_MISSING_OR_AMBIGUOUS")
    instructions = []
    for line in lines[labels[0] + 1:]:
        row = re.match(r"^\s*([0-9a-fA-F]{1,16}):?\s+(.+)$", line)
        if row:
            instructions.append((int(row[1], 16), row[2]))
        elif line.strip():
            raise Blocked("UNEXPECTED_BODY_OUTPUT")
    if not instructions or instructions[0][0] != address:
        raise Blocked("REQUESTED_BODY_ADDRESS_MISMATCH")
    if any(a != address + 4 * i for i, (a, _) in enumerate(instructions)):
        raise Blocked("NONCONTIGUOUS_ARM64_BODY")
    if any("<unknown>" in instruction for _, instruction in instructions):
        raise Blocked("UNDECODED_INSTRUCTION")
    return {"instructionCount": len(instructions),
            "branchSites": [{"address": hex(a), "instruction": instruction}
                            for a, instruction in instructions
                            if re.match(r"(?:bl|blr|b|br)\s", instruction)]}


def module_path(app: Path, relative: str) -> Path:
    part = Path(relative)
    if part.is_absolute() or ".." in part.parts:
        raise Blocked("UNSAFE_MODULE_PATH")
    path = (app / part).resolve(strict=True)
    if not path.is_relative_to(app) or not path.is_file():
        raise Blocked("UNSAFE_MODULE_PATH")
    return path


def requested_symbols(values: list[str] | tuple[str, ...]) -> dict[str, list[str]]:
    """Only exact, scope-limited names; never offsets, shell text or extra modules."""
    if not isinstance(values, (list, tuple)):
        raise Blocked("INVALID_SYMBOL_SELECTION")
    if len(values) > MAX_SELECTED:
        raise Blocked("SYMBOL_SELECTION_LIMIT")
    requested = {key: list(names) for key, names in REQUIRED.items()}
    seen = set()
    for value in values:
        if not isinstance(value, str) or len(value) > 2048:
            raise Blocked("INVALID_SYMBOL_SELECTION")
        module, separator, symbol = value.partition(":")
        if not separator or module not in REQUIRED or not re.fullmatch(r"_[A-Za-z0-9_.$]+", symbol):
            raise Blocked("INVALID_SYMBOL_SELECTION")
        if symbol not in REQUIRED[module] and not LEADS.search(symbol):
            raise Blocked("SYMBOL_OUTSIDE_RESEARCH_SCOPE")
        if value in seen:
            raise Blocked("DUPLICATE_SYMBOL_SELECTION")
        seen.add(value)
        if symbol not in requested[module]:
            requested[module].append(symbol)
    return requested


def collect(app: Path, policy: dict, runner=run_tool, *, inspect_symbols=(),
            context_followup=False, read_range=None) -> dict:
    """Collect roots and selected fresh inventory leads. No private code invocation."""
    report = {"schemaVersion": 1, "kind": "queue-context-static",
              "collectionStatus": "BLOCKED", "SYNC-001": "NOT RUN",
              "privateInvocationAllowed": False, "modules": {}, "commands": [],
              "claims": {key: "UNPROVEN" for key in (
                  "queueThread", "queueOrder", "cloneAssociation", "contextAcquisition",
                  "registrationABI", "callbackQuiescence", "postCommit", "coverage")}}
    def call(args, limit=MAX_BODY):
        row = runner(args, timeout=60, max_bytes=limit)
        report["commands"].append({"args": args, **{k: v for k, v in row.items() if k != "text"}})
        if row.get("complete") is not True or row.get("exitCode") != 0:
            raise Blocked(row.get("reason") or "INCOMPLETE_TOOL_RESULT")
        return row["text"]
    try:
        if type(context_followup) is not bool:
            raise Blocked("INVALID_CONTEXT_PROFILE")
        if context_followup:
            if inspect_symbols:
                raise Blocked("CONTEXT_PROFILE_DISALLOWS_EXTRA_SYMBOLS")
            if not callable(read_range):
                raise Blocked("CONTEXT_READER_REQUIRED")
            if policy["modules"]["BEE"]["sha256"] != CONTEXT_TABLE["moduleSha256"]:
                raise Blocked("CONTEXT_PROFILE_BUILD_MISMATCH")
            requested = {key: list(names) for key, names in CONTEXT_REQUIRED.items()}
            leads = CONTEXT_LEADS
        else:
            requested = requested_symbols(inspect_symbols)
            leads = LEADS
        report["profile"] = "context-followup" if context_followup else "queue-roots"
        report["requestedSymbols"] = requested
        report["expectedBodyCount"] = sum(len(names) for names in requested.values())
        app = app.expanduser().resolve(strict=True)
        info_path = module_path(app, "Contents/Info.plist")
        if info_path.stat().st_size > 1024**2:
            raise Blocked("PLIST_SIZE")
        metadata = plistlib.loads(info_path.read_bytes())
        for field, key in (("CFBundleIdentifier", "aeBundleId"),
                           ("CFBundleShortVersionString", "aeShortVersion"),
                           ("CFBundleVersion", "aeBundleVersion")):
            if metadata.get(field) != policy[key]:
                raise Blocked("AE_BUILD_MISMATCH")
        report["aeBuild"] = policy["aeBundleVersion"]
        paths = {}
        # Refuse every identity mismatch BEFORE nm/disassembly, for all modules.
        for key in REQUIRED:
            spec = policy["modules"][key]
            path = module_path(app, spec["relativePath"])
            actual = fingerprint(path)
            if actual != spec["sha256"]:
                raise Blocked("MODULE_HASH_MISMATCH:" + key)
            found_uuid = arm64_uuid(call(["xcrun", "dwarfdump", "--uuid", str(path)]))
            if found_uuid != spec["uuid"].lower():
                raise Blocked("MODULE_UUID_MISMATCH:" + key)
            paths[key] = path
            report["modules"][key] = {"sha256": actual, "arm64UUID": found_uuid,
                                      "relativePath": spec["relativePath"], "bodies": {}}
        report["toolVersion"] = call(["xcrun", "llvm-objdump", "--version"])
        addresses = {}
        # Every module and requested name must pass before ANY disassembly.
        # An old report, CLI name or nm visibility is not permission to call code.
        for key, path in paths.items():
            defined = text_symbol_table(call(["xcrun", "nm", "-arch", "arm64", "-U", str(path)], MAX_NM))
            exported = text_symbol_table(call(["xcrun", "nm", "-arch", "arm64", "-gU", str(path)], MAX_NM))
            report["modules"][key]["nmAmbiguities"] = ambiguity_evidence(defined, exported)
            if not defined or not exported or any(not a.issubset(defined.get(n, set()))
                                                 for n, a in exported.items()):
                raise Blocked("INCONSISTENT_SYMBOL_TABLES:" + key)
            names = sorted(set(requested[key]) | {n for n in defined if leads.search(n)})
            if len(names) > MAX_LEADS:
                raise Blocked("CANDIDATE_LIMIT:" + key)
            report["modules"][key]["inventory"] = [
                {"symbol": n,
                 "address": hex(next(iter(defined[n]))) if n in defined and len(defined[n]) == 1 else None,
                 **address_evidence(defined.get(n, set())),
                 "visibility": "defined-external-nm" if n in exported else
                 "defined-only-in-full-nm" if n in defined else "not-found-in-scanned-module"}
                for n in names]
            for symbol in requested[key]:
                if symbol not in defined:
                    reason = "REQUIRED_SYMBOL_MISSING" if context_followup or symbol in REQUIRED[key] else "SELECTED_SYMBOL_MISSING"
                    raise Blocked(reason + ":" + key + ":" + symbol)
                if len(defined[symbol]) != 1:
                    report["ambiguousTarget"] = {"module": key, "symbol": symbol,
                                                 **address_evidence(defined[symbol])}
                    raise Blocked("AMBIGUOUS_REQUESTED_TEXT_SYMBOL:" + key + ":" + symbol)
            addresses[key] = {symbol: next(iter(defined[symbol])) for symbol in requested[key]}
        for key, path in paths.items():
            for symbol in requested[key]:
                body = call(["xcrun", "llvm-objdump", "--macho", "--arch=arm64",
                             "--disassemble", "--no-show-raw-insn", "--dis-symname", symbol, str(path)])
                facts = inspect_body(body, symbol, addresses[key][symbol])
                report["modules"][key]["bodies"][symbol] = {**facts, "text": body}
        if context_followup:
            table = CONTEXT_TABLE
            anchor = CONTEXT_REQUIRED["BEE"][-1]
            if addresses["BEE"][anchor] != table["functionAddress"]:
                raise Blocked("CONTEXT_ANCHOR_ADDRESS_MISMATCH")
            try:
                row = read_range(paths["BEE"], report["modules"]["BEE"]["sha256"],
                                 report["modules"]["BEE"]["arm64UUID"],
                                 table["vmAddress"], table["byteCount"])
            except ValueError as error:
                raise Blocked("CONTEXT_RANGE:" + str(error)) from error
            raw = bytes.fromhex(row["hex"])
            if (len(raw) != table["byteCount"] or row["byteCount"] != len(raw) or row["sha256"] != digest(raw) or
                    row["vmAddress"] != hex(table["vmAddress"]) or
                    row["moduleSha256"] != table["moduleSha256"] or
                    row["arm64UUID"] != report["modules"]["BEE"]["arm64UUID"]):
                raise Blocked("CONTEXT_RANGE_EVIDENCE_MISMATCH")
            targets = [table["dispatchBase"] + value * 4 for value in raw]
            end = addresses["BEE"][anchor] + 4 * report["modules"]["BEE"]["bodies"][anchor]["instructionCount"]
            if any(not addresses["BEE"][anchor] <= target < end for target in targets):
                raise Blocked("CONTEXT_DISPATCH_TARGET_OUTSIDE_BODY")
            report["commandTypeTable"] = {**row, "dispatchBase": hex(table["dispatchBase"]),
                "targets": [{"commandType": i, "unslidTarget": hex(target)}
                            for i, target in enumerate(targets)],
                "interpretation": "static unsigned-byte scaled branch table; not runtime delivery evidence"}
        # Detect persistent replacement of a module during collection.
        for key, path in paths.items():
            if module_path(app, policy["modules"][key]["relativePath"]) != path or \
                    fingerprint(path) != report["modules"][key]["sha256"]:
                raise Blocked("MODULE_CHANGED_DURING_COLLECTION:" + key)
        if not all(set(report["modules"][k]["bodies"]) == set(v) for k, v in requested.items()):
            raise Blocked("INCOMPLETE_REQUESTED_BODY_SET")
        report["collectionStatus"] = "PASS"
    except (Blocked, OSError, ValueError, KeyError, TypeError) as error:
        report["reason"] = str(error) if isinstance(error, Blocked) else type(error).__name__
    # Tool paths can contain a user's name; no project data is read at any time.
    def redact(value):
        if isinstance(value, str):
            return value.replace(str(app), "<AE_APP>").replace(str(Path.home()), "<HOME>")
        if isinstance(value, list):
            return [redact(item) for item in value]
        if isinstance(value, dict):
            return {key: redact(item) for key, item in value.items()}
        return value
    return redact(report)


def save_report(report: dict, output: Path) -> Path:
    output = output.expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    owned = Path(tempfile.mkdtemp(prefix="FSTR-AE-Queue-", dir=output))
    report = {**report, "runId": owned.name, "collectorSha256": fingerprint(Path(__file__)),
              "capturedAtUnix": time.time()}
    payload = (json.dumps(report, indent=2, sort_keys=True) + "\n").encode("utf-8")
    with (owned / "report.json").open("xb") as dest:
        dest.write(payload)
    (owned / "SHA256.txt").write_text(digest(payload) + "  report.json\n", encoding="ascii")
    return owned / "report.json"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--inspect-symbol", action="append", default=[], metavar="MODULE:SYMBOL",
                        help="exact name from the queue/context inventory; repeat at most 12 times")
    args = parser.parse_args(argv)
    if platform.system() != "Darwin":
        report = {"collectionStatus": "BLOCKED", "reason": "MACOS_REQUIRED",
                  "SYNC-001": "NOT RUN", "privateInvocationAllowed": False}
    else:
        try:
            policy_bytes = (ROOT / "deep_targets.json").read_bytes()
            report = collect(args.app, json.loads(policy_bytes), inspect_symbols=args.inspect_symbol)
            report["policySha256"] = digest(policy_bytes)
        except (OSError, ValueError) as error:
            report = {"collectionStatus": "BLOCKED", "reason": type(error).__name__,
                      "SYNC-001": "NOT RUN", "privateInvocationAllowed": False}
    path = save_report(report, args.output)
    print(report["collectionStatus"] + ": " + str(path))
    return 0 if report["collectionStatus"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())

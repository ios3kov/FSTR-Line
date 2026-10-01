#!/usr/bin/env python3
"""Read-only Mach-O identity and bounded static leads. Never executes or patches AE."""
from __future__ import annotations

import argparse
import hashlib
import json
import mmap
import os
from pathlib import Path
import re
import stat
import struct
import sys
import uuid
from datetime import datetime, timezone

TERMS = re.compile(rb"notifi|observer|dispatch|timeline|playhead|selection|undo|redo|project|layer|change", re.I)
THIN = {bytes.fromhex("cffaedfe"): ("<", True), bytes.fromhex("cefaedfe"): ("<", False),
        bytes.fromhex("feedfacf"): (">", True), bytes.fromhex("feedface"): (">", False)}
FAT = {bytes.fromhex("cafebabe"): (">", False), bytes.fromhex("bebafeca"): ("<", False),
       bytes.fromhex("cafebabf"): (">", True), bytes.fromhex("bfbafeca"): ("<", True)}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def parse_macho(data, max_leads: int = 200, max_symbols: int = 200000) -> list[dict]:
    """Offsets are file offsets; symbol n_value is an unslid VM value, not callable proof."""
    require(1 <= max_leads <= 10000 and 1 <= max_symbols <= 1000000, "Invalid bounds")
    total = len(data)
    require(total >= 4, "Truncated magic")

    def thin(base: int, size: int) -> dict:
        require(size >= 28 and base >= 0 and base + size <= total, "Truncated Mach-O slice")
        kind = THIN.get(bytes(data[base:base + 4]))
        require(kind is not None, "Unsupported Mach-O slice")
        endian, is64 = kind
        header_size = 32 if is64 else 28
        require(size >= header_size, "Truncated header")
        _, cpu, subtype, filetype, ncmds, command_bytes, flags = struct.unpack_from(endian + "7I", data, base)
        require(ncmds <= 65536 and header_size + command_bytes <= size, "Invalid load-command bounds")
        cursor = base + header_size
        end = cursor + command_bytes
        uuids, symtables = [], []
        for _ in range(ncmds):
            require(cursor + 8 <= end, "Truncated load command")
            cmd, length = struct.unpack_from(endian + "2I", data, cursor)
            require(length >= 8 and length % 4 == 0 and cursor + length <= end, "Invalid load-command length")
            if cmd == 0x1B:
                require(length == 24, "Invalid UUID command")
                uuids.append(str(uuid.UUID(bytes=bytes(data[cursor + 8:cursor + 24]))))
            elif cmd == 0x2:
                require(length == 24, "Invalid symbol-table command")
                symtables.append(struct.unpack_from(endian + "4I", data, cursor + 8))
            cursor += length
        require(cursor == end and len(uuids) <= 1 and len(symtables) <= 1, "Inconsistent load commands")
        symbols = []
        declared = examined = 0
        limited = False
        for symoff, count, stroff, strsize in symtables:
            entry_size = 16 if is64 else 12
            require(symoff + count * entry_size <= size and stroff + strsize <= size, "Symbol table outside slice")
            declared += count
            for index in range(min(count, max_symbols)):
                entry = base + symoff + index * entry_size
                name_index, ntype, section, desc, value = struct.unpack_from(endian + ("IBBHQ" if is64 else "IBBHI"), data, entry)
                examined += 1
                require(name_index < strsize or (name_index == 0 and strsize == 0), "Invalid symbol string index")
                if name_index == 0 or ntype & 0xE0:
                    continue
                start = base + stroff + name_index
                stop = min(base + stroff + strsize, start + 1024)
                zero = data.find(b"\0", start, stop)
                if zero < 0:
                    limited = True
                    continue
                raw = bytes(data[start:zero])
                if TERMS.search(raw):
                    if len(symbols) == max_leads:
                        limited = True
                        break
                    symbols.append({"name": raw.decode("utf-8", "replace"), "tableIndex": index,
                                    "unslidValue": hex(value), "type": ntype, "section": section,
                                    "defined": (ntype & 0x0E) != 0})
            limited |= examined < declared
        return {"fileOffset": base, "size": size, "cpuType": cpu, "cpuSubtype": subtype,
                "is64Bit": is64, "endian": endian, "fileType": filetype, "flags": flags,
                "uuid": uuids[0] if uuids else None, "matchingSymbols": symbols,
                "symbolsDeclared": declared, "symbolsExamined": examined, "symbolsLimited": limited}

    magic = bytes(data[:4])
    if magic in THIN:
        return [thin(0, total)]
    require(magic in FAT, "Not a supported Mach-O/fat binary")
    require(total >= 8, "Truncated fat header")
    endian, fat64 = FAT[magic]
    count = struct.unpack_from(endian + "I", data, 4)[0]
    require(0 < count <= 64, "Invalid fat architecture count")
    width = 32 if fat64 else 20
    table_end = 8 + count * width
    require(table_end <= total, "Truncated fat architecture table")
    slices, intervals = [], []
    for index in range(count):
        entry = struct.unpack_from(endian + ("IIQQII" if fat64 else "IIIII"), data, 8 + index * width)
        cpu, subtype, offset, size, alignment = entry[:5]
        require(alignment <= 31 and offset >= table_end and size > 0 and offset + size <= total, "Invalid fat slice range")
        require(offset % (1 << alignment) == 0, "Unaligned fat slice")
        require(all(offset + size <= a or offset >= b for a, b in intervals), "Overlapping fat slices")
        item = thin(offset, size)
        require(item["cpuType"] == cpu and item["cpuSubtype"] == subtype, "Fat/slice architecture mismatch")
        intervals.append((offset, offset + size))
        slices.append(item)
    return slices



def read_macho_range(path: Path, expected_sha: str, expected_uuid: str,
                     address: int, length: int) -> dict:
    """Read 1..64 bytes from one file-backed arm64 section, never process memory.

    Reuses the existing thin/fat parser. Addresses are unslid VM values, not
    file offsets. Only a hash/UUID-matching linked little-endian arm64 image
    is accepted. This returns evidence bytes, not a callable ABI or permission.
    """
    require(type(address) is int and type(length) is int and
            0 <= address < 2**64 and 1 <= length <= 64 and
            address + length <= 2**64, "Invalid VM read bounds")
    require(isinstance(expected_sha, str) and
            re.fullmatch(r"[0-9a-f]{64}", expected_sha) is not None, "Invalid expected hash")
    wanted_uuid = str(uuid.UUID(expected_uuid))
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(fd, "rb") as source:
        before = os.fstat(source.fileno())
        require(stat.S_ISREG(before.st_mode) and 4 <= before.st_size <= 2 * 1024**3,
                "Unsupported file type/size")
        with mmap.mmap(source.fileno(), 0, access=mmap.ACCESS_READ) as data:
            require(hashlib.sha256(data).hexdigest() == expected_sha, "Range module hash mismatch")
            slices = parse_macho(data, max_leads=1, max_symbols=1)
            selected = [s for s in slices if s["cpuType"] == 0x0100000c]
            require(len(selected) == 1, "Missing or ambiguous arm64 slice")
            image = selected[0]
            require(image["is64Bit"] and image["endian"] == "<" and
                    image["cpuSubtype"] & 0xffffff == 0 and
                    image["fileType"] in (2, 6, 8) and image["uuid"] == wanted_uuid,
                    "Range architecture/type/UUID mismatch")
            base, size = image["fileOffset"], image["size"]
            ncmds = struct.unpack_from("<I", data, base + 16)[0]
            cursor = base + 32
            matches = []
            for _ in range(ncmds):
                cmd, cmdsize = struct.unpack_from("<II", data, cursor)
                require(cmdsize % 8 == 0, "Unaligned 64-bit load command")
                if cmd == 0x19:  # LC_SEGMENT_64; format from Apple's loader.h
                    require(cmdsize >= 72, "Truncated segment command")
                    fields = struct.unpack_from("<II16sQQQQiiII", data, cursor)
                    segname, vmaddr, vmsize, fileoff, filesize = fields[2:7]
                    nsects = fields[9]
                    require(cmdsize == 72 + 80 * nsects and
                            vmaddr + vmsize <= 2**64 and filesize <= vmsize and
                            fileoff + filesize <= size, "Invalid segment bounds")
                    for index in range(nsects):
                        sec = struct.unpack_from("<16s16sQQIIIIIIII", data, cursor + 72 + 80 * index)
                        name, owner, start, count, offset = sec[:5]
                        kind = sec[8] & 0xff
                        require(owner == segname and vmaddr <= start and
                                start + count <= vmaddr + vmsize, "Invalid section VM range")
                        backed = kind not in (1, 0xc, 0x12)  # zero-fill section types
                        if backed:
                            require(fileoff <= offset and offset + count <= fileoff + filesize and
                                    offset == fileoff + start - vmaddr, "Invalid section file mapping")
                        if start <= address and address + length <= start + count:
                            require(backed, "Requested range is zero-fill")
                            matches.append((base + offset + address - start, name, owner))
                cursor += cmdsize
            require(len(matches) == 1, "Missing or ambiguous file-backed VM range")
            offset, section, segment = matches[0]
            raw = bytes(data[offset:offset + length])
            require(len(raw) == length, "Truncated VM range")
            require(hashlib.sha256(data).hexdigest() == expected_sha, "Range module changed")
            after = os.fstat(source.fileno())
            require((before.st_size, before.st_mtime_ns, before.st_ctime_ns) ==
                    (after.st_size, after.st_mtime_ns, after.st_ctime_ns), "Range input changed")
    return {"vmAddress": hex(address), "byteCount": length,
            "fileOffset": offset, "sliceOffset": base, "arm64UUID": wanted_uuid,
            "moduleSha256": expected_sha, "hex": raw.hex(),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "segment": segment.rstrip(b"\0").decode("ascii"),
            "section": section.rstrip(b"\0").decode("ascii")}


def inspect_file(path: Path, max_scan: int = 256 * 1024 * 1024, max_leads: int = 200) -> dict:
    require(max_scan > 0 and 1 <= max_leads <= 10000, "Invalid scan limits")
    path = path.absolute()
    require(not path.is_symlink(), "Symlink input is not accepted")
    if not path.exists():
        raise FileNotFoundError("Input binary unavailable")
    require(path.is_file(), "An exact regular binary file is required, not an app directory")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and 4 <= before.st_size <= 2 * 1024**3, "Unsupported file type/size")
        with mmap.mmap(fd, 0, access=mmap.ACCESS_READ) as data:
            digest = hashlib.sha256(data).hexdigest()
            slices = parse_macho(data, max_leads=max_leads)
            scan_end = min(len(data), max_scan)
            leads = []
            output_limited = False
            for match in TERMS.finditer(data, 0, scan_end):
                if len(leads) >= max_leads:
                    output_limited = True
                    break
                a, b = match.start(), match.end()
                while a > max(0, match.start() - 96) and 32 <= data[a - 1] <= 126:
                    a -= 1
                while b < min(scan_end, match.end() + 160) and 32 <= data[b] <= 126:
                    b += 1
                leads.append({"fileOffset": match.start(), "context": bytes(data[a:b]).decode("ascii", "replace")})
            after = os.fstat(fd)
            require((before.st_size, before.st_mtime_ns, before.st_ctime_ns) ==
                    (after.st_size, after.st_mtime_ns, after.st_ctime_ns), "Input changed during inspection")
    finally:
        os.close(fd)
    return {"schemaVersion": 1, "tool": "fstr-static-inspector-1", "inputName": path.name,
            "sha256": digest, "bytes": before.st_size, "slices": slices,
            "stringLeads": leads, "stringScanBytes": scan_end,
            "stringScanLimited": scan_end < before.st_size or output_limited,
            "staticInspection": "PASS", "notificationSource": "NOT RUN", "SYNC-001": "NOT RUN",
            "limitations": ["Static names are leads, not evidence of events or callable functions.",
                            "No disassembly, cross-references, runtime attach or coverage test was performed.",
                            "No-match/limited output is not proof that a notification path is absent.",
                            "The complete application module set must be inspected separately."]}


def write_report(report: dict, root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex
    directory = root / run_id
    directory.mkdir(mode=0o700)
    result = directory / "identity.json"
    record = dict(report, testRunId=run_id, toolSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    with result.open("x", encoding="utf-8") as stream:
        json.dump(record, stream, indent=2, ensure_ascii=True)
        stream.write("\n")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", type=Path)
    parser.add_argument("--output", type=Path, required=True, help="Owned research output directory")
    parser.add_argument("--ae-build", required=True, help="Operator-provided build label; not independently verified")
    parser.add_argument("--max-scan-mib", type=int, default=256)
    parser.add_argument("--max-leads", type=int, default=200)
    args = parser.parse_args()
    try:
        require(1 <= args.max_scan_mib <= 2048, "Scan limit must be 1..2048 MiB")
        report = inspect_file(args.binary, args.max_scan_mib * 1024**2, args.max_leads)
        report["claimedAEBuild"] = args.ae_build
        report["claimedAEBuildVerified"] = False
        print(write_report(report, args.output))
        return 0
    except (OSError, ValueError) as error:
        print(json.dumps({"status": "BLOCKED" if isinstance(error, OSError) else "FAIL",
                          "error": str(error), "SYNC-001": "NOT RUN"}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

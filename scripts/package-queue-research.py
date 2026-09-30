#!/usr/bin/env python3
"""Package only committed queue diagnostic sources; no Adobe binaries included."""
from __future__ import annotations

import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAMES = ("Queue-AE.command", "queue_kit.py", "queue_static.py", "deep_targets.json", "QUEUE-README.txt")


def build(root: Path = ROOT) -> dict:
    def git(*args: str) -> bytes:
        return subprocess.check_output(["git", "-C", str(root), *args], timeout=30)
    if git("status", "--porcelain", "--untracked-files=normal").strip():
        raise ValueError("DIRTY_SOURCE")
    commit = git("rev-parse", "HEAD").decode().strip()
    payload = {}
    for name in NAMES:
        path = "research/ae-notifications/" + name
        entry = git("ls-tree", commit, "--", path).decode()
        if not entry.startswith(("100644 blob ", "100755 blob ")):
            raise ValueError("MISSING_OR_NONREGULAR_SOURCE:" + name)
        payload[name] = git("show", commit + ":" + path)
    manifest = {"schemaVersion": 1, "sourceCommit": commit, "sourceState": "clean",
                "buildId": "fstr-queue-" + commit[:12],
                "files": {name: hashlib.sha256(data).hexdigest() for name, data in payload.items()}}
    payload["build-manifest.json"] = (json.dumps(manifest, indent=2) + "\n").encode()
    out = root / "dist/queue-research" / commit
    out.mkdir(parents=True, exist_ok=False)
    archive = out / "FSTR-AE-Queue.zip"
    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_STORED) as dest:
        for name, data in payload.items():
            entry = zipfile.ZipInfo("FSTR-AE-Queue/" + name, (1980, 1, 1, 0, 0, 0))
            entry.create_system = 3
            entry.external_attr = (0o100755 if name.endswith(".command") else 0o100644) << 16
            dest.writestr(entry, data)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    (out / "SHA256.txt").write_text(digest + "  " + archive.name + "\n", encoding="ascii")
    if git("rev-parse", "HEAD").decode().strip() != commit or git("status", "--porcelain").strip():
        raise ValueError("SOURCE_CHANGED_DURING_BUILD")
    return {"archive": str(archive), "sha256": digest, "sourceCommit": commit}


if __name__ == "__main__":
    print(json.dumps(build()))

#!/bin/bash
set -euo pipefail
HERE="$(cd -- "$(dirname -- "$0")" && pwd)"
if [ "$(uname -s)" != Darwin ]; then
  echo 'BLOCKED: macOS required.' >&2; exit 2
fi
for PY in "$(command -v python3 || true)" /opt/homebrew/bin/python3 /usr/local/bin/python3 /usr/bin/python3; do
  if [ -x "$PY" ] && "$PY" -I -B -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)' 2>/dev/null; then
    exec "$PY" -I -B "$HERE/context_probe.py"
  fi
done
echo 'BLOCKED: Python 3.10+ required.' >&2
exit 2

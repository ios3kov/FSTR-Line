#!/bin/bash
set -euo pipefail
HERE="$(cd -- "$(dirname -- "$0")" && pwd)"
for PY in "$(command -v python3 || true)" /opt/homebrew/bin/python3 /usr/local/bin/python3 /usr/bin/python3; do
  if [ -x "$PY" ] && "$PY" -I -B -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)' 2>/dev/null; then
    exec "$PY" -I -B "$HERE/queue_kit.py" "$@"
  fi
done
echo 'BLOCKED: Python 3.10+ required. No application inspected or changed.' >&2
exit 2

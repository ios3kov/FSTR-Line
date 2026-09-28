#!/bin/bash
set -euo pipefail
HERE="$(cd -- "$(dirname -- "$0")" && pwd)"
for PY in "$(command -v python3 || true)" /opt/homebrew/bin/python3 /usr/local/bin/python3 /usr/bin/python3; do
  if [ -x "$PY" ] && "$PY" -I -B -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)' 2>/dev/null; then
    APP="$(/usr/bin/osascript -e 'POSIX path of (choose file with prompt "Select the same After Effects 25.6 application (.app)" of type {"com.apple.application-bundle"})')" || exit 2
    exec "$PY" -I -B "$HERE/focused_static.py" --app "$APP"
  fi
done
echo 'BLOCKED: Python 3.10+ is required.' >&2
exit 2

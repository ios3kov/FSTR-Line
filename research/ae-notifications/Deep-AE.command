#!/bin/bash
set -euo pipefail
HERE="$(cd -- "$(dirname -- "$0")" && pwd)"
if [ "$(uname -s)" != Darwin ]; then
  echo 'BLOCKED: macOS required.' >&2; exit 2
fi
for PY in "$(command -v python3 || true)" /opt/homebrew/bin/python3 /usr/local/bin/python3 /usr/bin/python3; do
  if [ -x "$PY" ] && "$PY" -I -B -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)' 2>/dev/null; then
    APP=$(/usr/bin/osascript <<'APPLESCRIPT'
try
  set chosenApp to choose application as alias with prompt "Select the exact Adobe After Effects 2025 app used for FSTR research"
  return POSIX path of chosenApp
on error number -128
  return ""
end try
APPLESCRIPT
)
    if [ -z "$APP" ]; then echo 'BLOCKED: application selection cancelled.' >&2; exit 2; fi
    exec "$PY" -I -B "$HERE/deep_static.py" --app "$APP"
  fi
done
echo 'BLOCKED: Python 3.10+ required.' >&2
exit 2

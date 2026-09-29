#!/bin/bash
set -euo pipefail
HERE="$(cd -- "$(dirname -- "$0")" && pwd)"
exec python3 -I -B "$HERE/plugin_origin_tool.py" uninstall

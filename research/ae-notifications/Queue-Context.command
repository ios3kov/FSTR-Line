#!/bin/bash
# Offline context/table follow-up. No install, attach, host call or project read.
set -euo pipefail
HERE="$(cd -- "$(dirname -- "$0")" && pwd)"
exec /bin/bash "$HERE/Queue-AE.command" --context-followup "$@"

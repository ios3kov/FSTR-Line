#!/bin/bash
# Exact implementation-body follow-up to 2mniyqyl. Offline, no host calls.
set -euo pipefail
HERE="$(cd -- "$(dirname -- "$0")" && pwd)"
exec /bin/bash "$HERE/Queue-AE.command" --context-details "$@"

#!/bin/bash
# Exact-symbol follow-up to report FSTR-AE-Queue-t5rmrf54. Offline only.
set -euo pipefail
if [ "$#" -gt 2 ] || { [ "$#" -eq 2 ] && [ "$2" != --verify-only ]; }; then
  echo 'Usage: Queue-Inspect-Observed.command [existing-kit-directory [--verify-only]]' >&2
  exit 2
fi
KIT="${1:-$HOME/Desktop/AAE/04_FSTR-Line/FSTR-AE-Queue}"
if [ ! -d "$KIT" ]; then
  echo 'BLOCKED: existing FSTR-AE-Queue directory not found. No application inspected.' >&2
  exit 2
fi
cd -- "$KIT"
# Refuse another/modified kit BEFORE executing its launcher or Python code.
if ! shasum -a 256 -c <<'FSTR_HASHES'
3e6dbd7a95e4099259e8522d12d44c852e25c4d412a96a933530c016c79b2d93  Queue-AE.command
d31417c856d622a48a064357ca39c1eb0b251cd2b64b754bbf25523ff9dfb84f  queue_kit.py
3dafe1c99a4a7aebf9f235e6f6c8341e60c6e2a3d0b85aa46dfea0f6122403bb  queue_static.py
1e748db1d0c565f02e23133f265b3d5768445dddabbddcf40c23114c5dee96f5  deep_targets.json
017853a47d0bddcaf5b87ccbac358fae6fb207b1c39fe24840164ec52a42e3c8  QUEUE-README.txt
53d1177b74ea98e45fe5d12c574fc2a70ec230a277910dc52867fd047f650258  build-manifest.json
FSTR_HASHES
then
  echo 'BLOCKED: expected unchanged eef15f5 diagnostic kit. No application inspected.' >&2
  exit 2
fi
if [ "$#" -eq 2 ]; then set -- --verify-only; else set --; fi
# Names are copied from the verified report inventory, not guessed prototypes.
# The existing collector retains its seven roots and all identity/limit guards.
exec /bin/bash ./Queue-AE.command "$@" \
  --inspect-symbol 'BEE:__ZN29BEE_ThreadedRenderUpdateQueue18AddFunctionToQueueERKN5boost8functionIFvvEEEP15BEE_UndoContextsPKcS9_PKNSt3__112basic_stringIhNSA_11char_traitsIhEEN7dvacore9allocator12STLAllocatorIhEEEENS_11CommandTypeE' \
  --inspect-symbol 'BEE:__ZN29BEE_ThreadedRenderUpdateQueue23ProcessFromRenderThreadEy' \
  --inspect-symbol 'BEE:__ZN29BEE_ThreadedRenderUpdateQueue29Render_DeserializeFullProjectERKNSt3__112basic_stringIhNS0_11char_traitsIhEEN7dvacore9allocator12STLAllocatorIhEEEEiRKNS4_7utility4GuidE' \
  --inspect-symbol 'BEE:__ZN11BEE_Globals12ProjectBirthEv' \
  --inspect-symbol 'BEE:__ZN11BEE_Globals12ProjectDeathEv' \
  --inspect-symbol 'BEE:__ZN11BEE_Globals10GetProjectEv' \
  --inspect-symbol 'BEE:__ZN11BEE_Globals14GetProjectFauxEv' \
  --inspect-symbol 'BEE:__ZN11BEE_Globals13IsProjectOpenEv' \
  --inspect-symbol 'BEE:__ZN11BEE_Globals18IsProjectCloneOpenEv' \
  --inspect-symbol 'BEE:__ZN11BEE_Project14GetUndoContextEv' \
  --inspect-symbol 'BEE:__Z30BEE_WorkQueue_RegisterListenerRKN5boost8functionIFv14ItemChangeTypeNS_10shared_ptrI18BEE_WorkQueue_ItemEEEEE' \
  --inspect-symbol 'BEE:__Z32BEE_WorkQueue_DeregisterListenerRKN7dvacore7utility4GuidE'

#!/usr/bin/env bash
# usage: scripts/remote_status.sh EXP [run-id]   (no run-id: list runs)
source "$(dirname "$0")/_k8s.sh"
EXP="${1:?experiment id}"; RUN_ID="${2:-}"
POD=$(running_pods | head -1)
[ -n "$POD" ] || { echo "no Running pod under prefix $PREFIX" >&2; exit 1; }
if [ -z "$RUN_ID" ]; then
  k exec "$POD" -- bash -lc "ls -1 '$REMOTE_OUTPUT_ROOT/$EXP' 2>/dev/null || echo '(no runs)'"
  exit 0
fi
RUN_DIR="$REMOTE_OUTPUT_ROOT/$EXP/$RUN_ID"
k exec "$POD" -- bash -lc "
  cd '$RUN_DIR' 2>/dev/null || { echo 'run dir missing'; exit 1; }
  test -f done.txt && echo \"DONE exit=\$(cat done.txt)\" || echo RUNNING
  test -f launcher.pid && echo \"pid=\$(cat launcher.pid)\"
  test -f receipt.json && python3 -c 'import json;r=json.load(open(\"receipt.json\"));print(\"receipt status:\",r[\"status\"])'
  echo '--- run.log (tail) ---'; test -f run.log && tail -20 run.log
"

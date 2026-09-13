#!/usr/bin/env bash
# Detached launch of a registered experiment on an idle reservation pod.
# usage: scripts/remote_run.sh A-0 [run-id]
source "$(dirname "$0")/_k8s.sh"
EXP="${1:?experiment id}"
RUN_ID="${2:-$(date -u +%Y%m%d-%H%M%S)-remote}"

# 1. local gate: manifest validates and the tree is pushed
uv run python scripts/validate_experiment.py "$EXP"
if [ -n "$(git status --porcelain)" ]; then
  echo "local tree is dirty; commit and push before a remote run" >&2; exit 1
fi
LOCAL_HEAD=$(git rev-parse HEAD)
if ! git branch -r --contains "$LOCAL_HEAD" | grep -q .; then
  echo "HEAD $LOCAL_HEAD is not on any remote; push first" >&2; exit 1
fi

# 2. resolve an idle pod (never hardcode a suffix)
POD=$(idle_pod)
if [ -z "$POD" ]; then echo "no idle pod under prefix $PREFIX; stop and report" >&2; exit 1; fi
echo "pod=$POD run_id=$RUN_ID"

# 3. sync: remote checkout follows the pushed commit
k exec "$POD" -- bash -lc "
  set -e
  test -d '$REMOTE_CHECKOUT/.git' || { echo 'REMOTE_CHECKOUT missing: clone it once by hand' >&2; exit 2; }
  cd '$REMOTE_CHECKOUT'
  git status --short
  git fetch origin && git pull --ff-only
  test \"\$(git rev-parse HEAD)\" = '$LOCAL_HEAD' || { echo 'remote HEAD differs from local HEAD after pull' >&2; exit 3; }
"

# 4. detached launch; receipt and log live under the run dir
RUN_DIR="$REMOTE_OUTPUT_ROOT/$EXP/$RUN_ID"
k exec "$POD" -- bash -lc "
  set -e
  cd '$REMOTE_CHECKOUT'
  mkdir -p '$RUN_DIR'
  nohup bash -lc '
    set -a; [ -f .env ] && source .env; set +a
    export OUTPUT_ROOT=\"$REMOTE_OUTPUT_ROOT\"
    uv sync --locked >> \"$RUN_DIR/run.log\" 2>&1
    uv run python scripts/train.py --exp \"$EXP\" --run-id \"$RUN_ID\" >> \"$RUN_DIR/run.log\" 2>&1
    echo \$? > \"$RUN_DIR/done.txt\"
  ' </dev/null >/dev/null 2>&1 &
  echo \$! > '$RUN_DIR/launcher.pid'
  disown
  echo launched pid=\$(cat '$RUN_DIR/launcher.pid')
"
echo "poll with: make remote-status EXP=$EXP RUN=$RUN_ID"

#!/usr/bin/env bash
# Copy receipt.json, run.log, and tracked expected_artifacts of one run into
# experiments/<S>/<id-slug>/receipts/<run-id>/ for commit.
# usage: scripts/fetch_receipt.sh A-0 RUN_ID
source "$(dirname "$0")/_k8s.sh"
EXP="${1:?experiment id}"; RUN_ID="${2:?run id}"
POD=$(running_pods | head -1)
[ -n "$POD" ] || { echo "no Running pod under prefix $PREFIX" >&2; exit 1; }
RUN_DIR="$REMOTE_OUTPUT_ROOT/$EXP/$RUN_ID"

EXP_DIR=$(uv run python -c "from myproject import registry; print(registry.load('.', '$EXP').dir)")
FILES=$(uv run python -c "from myproject import registry; e=registry.load('.', '$EXP'); print(' '.join(a['path'] for a in e.manifest.get('expected_artifacts', []) if a.get('track')))")
MAX_MB=$(uv run python -c "from myproject import registry; print(registry.load('.', '$EXP').manifest.get('storage', {}).get('max_tracked_mb', 5))")
DEST="$EXP_DIR/receipts/$RUN_ID"
mkdir -p "$DEST"

# size every tracked file on the pod; fetch the small ones, list the large ones in REMOTE.md
SIZES=$(k exec "$POD" -- bash -lc "cd '$RUN_DIR' && for f in $FILES run.log; do [ -e \"\$f\" ] && du -sm \"\$f\" | awk '{print \$1, \$2}'; done")
SMALL=""; { echo "# Files left on the server"; echo; echo "Run dir: \`$RUN_DIR\` on pod prefix \`$PREFIX\`"; echo; echo "| file | size (MB) | server path |"; echo "|---|---|---|"; } > "$DEST/REMOTE.md"
LARGE=0
while read -r mb f; do
  [ -z "$f" ] && continue
  if [ "$mb" -le "$MAX_MB" ]; then SMALL="$SMALL $f"; else echo "| $f | $mb | $RUN_DIR/$f |" >> "$DEST/REMOTE.md"; LARGE=1; fi
done <<< "$SIZES"
[ "$LARGE" = 1 ] || rm -f "$DEST/REMOTE.md"
k exec "$POD" -- bash -lc "cd '$RUN_DIR' && tar -cf - $SMALL" | tar -xf - -C "$DEST"
echo "fetched into $DEST:"; ls -la "$DEST"
[ "$LARGE" = 1 ] && echo "large files stayed on the server; see $DEST/REMOTE.md"
echo "open receipt.json and the tracked files before writing RESULT.md (meta-rule 4)"

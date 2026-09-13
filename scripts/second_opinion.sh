#!/usr/bin/env bash
# Ask the *other* agent for an independent reading of a report's data and
# observations, and write it verbatim to reports/<slug>/REVIEW.md.
# usage: AGENT_NAME=claude scripts/second_opinion.sh <slug>
# Mechanism follows the cross-agent-review skill: Claude asks Codex via
# `codex exec`, Codex asks Claude via `claude -p`. Model ids come from
# CODEX_MODEL / CLAUDE_MODEL in the environment.
set -euo pipefail
SLUG="${1:?report slug}"
ME="${AGENT_NAME:?set AGENT_NAME to claude or codex (the agent asking)}"
DIR="reports/$SLUG"
test -f "$DIR/report.toml" || { echo "no $DIR/report.toml" >&2; exit 1; }
LOG="${TMPDIR:-/tmp}/second_opinion_$SLUG.log"

PROMPT=$(cat <<EOF
You are giving an independent second opinion on an experiment summary.
Read these files yourself: $DIR/report.toml, $DIR/data/*.json, $DIR/index.html
(only the section id="observations"; ignore any interpretation), and the
RESULT.md of each member experiment listed in report.toml.

Write, in plain language a reader without project context can follow:
1. Your own interpretation of what the data show and what it might mean.
2. Where you would disagree with, or add caution to, the observations as written.
3. The single cheapest next experiment that would change the conclusion.
Do not invent numbers; cite data file names. Keep it under 400 words.
Start your answer with the line "Agent: <your name>" and then "Date: $(date -u +%F)".
EOF
)

case "$ME" in
  claude)
    OTHER=codex
    printf '%s\n' "$PROMPT" | timeout 1800 codex exec -c model="${CODEX_MODEL:?set CODEX_MODEL}" \
      --sandbox read-only - </dev/null > "$LOG" 2>&1 || true
    ;;
  codex)
    OTHER=claude
    timeout 1800 claude -p --model "${CLAUDE_MODEL:?set CLAUDE_MODEL}" --no-session-persistence \
      "$PROMPT" > "$LOG" 2>&1 || true
    ;;
  *) echo "AGENT_NAME must be claude or codex" >&2; exit 1 ;;
esac

if ! grep -qi '^Agent:' "$LOG"; then
  echo "no opinion received from $OTHER; see $LOG" >&2; exit 1
fi
{ sed -n '/^[Aa]gent:/,$p' "$LOG"; } > "$DIR/REVIEW.md"
echo "wrote $DIR/REVIEW.md (from $OTHER). Paste it verbatim into the second-opinion section, then write interpretation."

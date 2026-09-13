#!/usr/bin/env bash
# One-time initialisation of a repo created from this template.
# usage: scripts/init_repo.sh <package_name> [repo_name]
# Normally invoked by new-research-repo; safe to run by hand after `gh repo create --template`.
set -euo pipefail
PKG="${1:?python package name, e.g. myproj}"
REPO="${2:-$PKG}"
cd "$(dirname "$0")/.."
[[ "$PKG" =~ ^[a-z_][a-z0-9_]*$ ]] || { echo "package name must be a valid identifier" >&2; exit 1; }

DEFAULTS="${RESEARCH_REPO_DEFAULTS:-$HOME/.config/research-repo/defaults.env}"
[ -f "$DEFAULTS" ] && { set -a; source "$DEFAULTS"; set +a; }

sedi() { if sed --version >/dev/null 2>&1; then sed -i "$@"; else sed -i '' "$@"; fi; }

# 1. package rename
if [ "$PKG" != "myproject" ]; then
  mv src/myproject "src/$PKG"
  grep -rl --exclude-dir=.git --exclude-dir=.venv --exclude-dir=outputs 'myproject' . \
    | while read -r f; do sedi -e "s/myproject/$PKG/g" "$f"; done
fi
sedi -e "s#repos/$PKG#repos/$REPO#; s#outputs/$PKG#outputs/$REPO#" .env.example

# 2. .env from owner defaults (never commits; .env is gitignored)
if [ ! -f .env ]; then
  cp .env.example .env
  for k in KCFG NS PREFIX REMOTE_ROOT; do
    v="${!k:-}"
    [ -n "$v" ] && sedi -e "s#^$k=.*#$k=$v#" .env
  done
fi
[ -e outputs ] || mkdir -p outputs
mkdir -p "/tmp/$USER"

# 3. lock, sync, test, validate
rm -f uv.lock
set -a; source .env; set +a
uv lock --quiet && uv sync --extra dev --quiet
uv run pytest -q
uv run python scripts/validate_experiment.py
uv run python scripts/experiment_log.py >/dev/null
echo "initialised package '$PKG' for repo '$REPO'"

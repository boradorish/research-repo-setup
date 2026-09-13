#!/usr/bin/env bash
# Environment and repo readiness check. Run first in any new session.
# Prints OK / WARN / FAIL lines; exits 1 if anything FAILs.
cd "$(dirname "$0")/.."
[ -f .env ] && { set -a; source .env; set +a; }
rc=0
ok()   { printf 'OK    %s\n' "$*"; }
warn() { printf 'WARN  %s\n' "$*"; }
fail() { printf 'FAIL  %s\n' "$*"; rc=1; }
have() { command -v "$1" >/dev/null 2>&1; }
tmo() { if have timeout; then timeout "$@"; elif have gtimeout; then gtimeout "$@"; else shift; "$@"; fi; }

echo "== tools"
for t in uv git gh kubectl; do have "$t" && ok "$t" || fail "$t not on PATH"; done
for t in codex claude; do have "$t" && ok "$t" || warn "$t not on PATH (second opinions / delegation unavailable)"; done
{ have latexmk || have tectonic; } && ok "LaTeX compiler" || warn "no latexmk/tectonic (paper pages cannot be checked locally)"

echo "== repo"
[ -f .env ] && ok ".env present" || fail ".env missing (cp .env.example .env)"
[ -f uv.lock ] && ok "uv.lock present" || fail "uv.lock missing (uv lock)"
if [ -f .env ]; then
  uv lock --check >/dev/null 2>&1 && ok "uv.lock matches pyproject" || warn "uv.lock out of date (uv lock)"
fi
[ -d .venv ] && ok ".venv present" || warn ".venv missing (make sync)"
[ -d outputs ] && ok "outputs/ present" || warn "outputs/ missing (mkdir outputs or symlink to storage)"
if grep -q '<Project name>' README.md 2>/dev/null; then fail "README.md still has the template title"; else ok "README titled"; fi
if grep -q '<One' README.md experiments/A/PREMISE.md 2>/dev/null; then warn "research question placeholder still present in README.md / PREMISE.md"; else ok "research question stated"; fi
tmpl_pkg="my""project"   # split so init_repo's rename does not rewrite this check
if [ -d "src/$tmpl_pkg" ] && [ "$(basename "$PWD")" != "research-repo-setup" ]; then warn "package still named $tmpl_pkg (scripts/init_repo.sh <pkg>)"; fi
uv run python scripts/validate_experiment.py >/dev/null 2>&1 && ok "all manifests validate" || fail "a manifest fails validation (make validate)"
uv run python scripts/experiment_log.py --check >/dev/null 2>&1 && ok "experiments/LOG.md current" || warn "experiments/LOG.md stale (make log)"
git rev-parse --is-inside-work-tree >/dev/null 2>&1 && ok "git repository" || fail "not a git repository"
git remote get-url origin >/dev/null 2>&1 && ok "origin: $(git remote get-url origin)" || warn "no origin remote"

echo "== compute"
[ -n "${PREFIX:-}" ] && ok "PREFIX=$PREFIX" || fail "PREFIX empty in .env (reservation prefix, e.g. prod-rsv-<owner>)"
[ -f "${KCFG:-$HOME/.kube/config}" ] && ok "kubeconfig ${KCFG:-$HOME/.kube/config}" || fail "kubeconfig not found"
if have kubectl && [ -f "${KCFG:-$HOME/.kube/config}" ]; then
  if tmo 15 kubectl --kubeconfig "${KCFG:-$HOME/.kube/config}" -n "${NS:-p-production}" get pods --no-headers >/dev/null 2>&1; then
    n=$(kubectl --kubeconfig "${KCFG:-$HOME/.kube/config}" -n "${NS:-p-production}" get pods --no-headers 2>/dev/null | awk -v p="^${PREFIX:-__none__}" '$1 ~ p && $3=="Running"' | wc -l | tr -d ' ')
    ok "cluster reachable (ns ${NS:-p-production}); $n Running pod(s) under PREFIX"
  else
    warn "cluster not reachable now (VPN? kubeconfig context?)"
  fi
fi
[ -n "${REMOTE_ROOT:-}" ] && ok "REMOTE_ROOT=$REMOTE_ROOT" || warn "REMOTE_ROOT empty"

echo "== credentials (presence only)"
[ -n "${HF_TOKEN:-}" ] && ok "HF_TOKEN set" || warn "HF_TOKEN not set (make hf-push unavailable)"
[ -n "${OVERLEAF_GIT_TOKEN:-${OVERLEAF_API:-}}" ] && ok "Overleaf git token set" || warn "OVERLEAF_GIT_TOKEN not set (overleaf sync/push unavailable)"
[ -n "${CODEX_MODEL:-}" ] && ok "CODEX_MODEL=$CODEX_MODEL" || warn "CODEX_MODEL not set (needed for second opinions from Claude)"
[ -n "${CLAUDE_MODEL:-}" ] && ok "CLAUDE_MODEL=$CLAUDE_MODEL" || warn "CLAUDE_MODEL not set (needed for second opinions from Codex)"

echo "== paper"
url=$(uv run python -c "from $(ls src | head -1) import overleaf; print(overleaf.load_policy('.').project_url)" 2>/dev/null || true)
[ -n "$url" ] && ok "overleaf project linked" || warn "overleaf project_url empty (agents will ask: Overleaf 프로젝트 링크 줘!)"

exit $rc

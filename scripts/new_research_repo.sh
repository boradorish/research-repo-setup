#!/usr/bin/env bash
# Create a new research repository from the research-repo-setup template.
#
#   new-research-repo <name> [--question "<one sentence>"] [--pkg <package>]
#                     [--dir <parent>] [--public] [--no-github] [--template <dir-or-url>]
#
# Reads owner defaults from ~/.config/research-repo/defaults.env (GITHUB_OWNER,
# REPOS_DIR, TEMPLATE_DIR/TEMPLATE_URL, PREFIX, REMOTE_ROOT, ...). The new repo
# gets a fresh git history, its own .env, the template-only files removed, a
# first commit, and a private GitHub repository with `origin` pushed.
set -euo pipefail

DEFAULTS="${RESEARCH_REPO_DEFAULTS:-$HOME/.config/research-repo/defaults.env}"
[ -f "$DEFAULTS" ] && { set -a; source "$DEFAULTS"; set +a; }

NAME=""; PKG=""; PARENT="${REPOS_DIR:-$HOME}"; VISIBILITY="--private"; GITHUB=1
TEMPLATE="${TEMPLATE_DIR:-$HOME/research-repo-setup}"; QUESTION=""
while [ $# -gt 0 ]; do
  case "$1" in
    --pkg) PKG="$2"; shift 2 ;;
    --dir) PARENT="$2"; shift 2 ;;
    --public) VISIBILITY="--public"; shift ;;
    --no-github) GITHUB=0; shift ;;
    --template) TEMPLATE="$2"; shift 2 ;;
    --question) QUESTION="$2"; shift 2 ;;
    -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
    -*) echo "unknown option $1" >&2; exit 2 ;;
    *) NAME="$1"; shift ;;
  esac
done
[ -n "$NAME" ] || { echo "usage: new-research-repo <name> [--question '...']" >&2; exit 2; }
[[ "$NAME" =~ ^[A-Za-z0-9._-]+$ ]] || { echo "repo name may contain letters, digits, . _ -" >&2; exit 2; }
if [ -z "$PKG" ]; then
  PKG=$(printf '%s' "$NAME" | tr 'A-Z-' 'a-z_' | sed 's/[^a-z0-9_]//g; s/^[0-9]*//')
  [ -n "$PKG" ] || PKG="project"
fi
DEST="$PARENT/$NAME"
[ -e "$DEST" ] && { echo "$DEST already exists" >&2; exit 1; }

# 1. materialise the template without its history or local state
mkdir -p "$PARENT"
if [ -d "$TEMPLATE" ]; then
  rsync -a --exclude '.git' --exclude '.venv' --exclude 'outputs' --exclude '.env' \
        --exclude '.pytest_cache' --exclude '.ruff_cache' --exclude '__pycache__' \
        --exclude 'paper/overleaf' --exclude 'experiments/*/*/receipts/*' \
        "$TEMPLATE/" "$DEST/"
else
  git clone --depth 1 --quiet "${TEMPLATE:-${TEMPLATE_URL:?set TEMPLATE_DIR or TEMPLATE_URL}}" "$DEST"
  rm -rf "$DEST/.git"
fi
cd "$DEST"

# 2. template-only content goes away
rm -f scripts/new_research_repo.sh
python3 - "$NAME" "$QUESTION" <<'PY'
import re, sys
from pathlib import Path
name, question = sys.argv[1], sys.argv[2]
r = Path("README.md"); s = r.read_text()
s = s.replace("# <Project name>", f"# {name}")
s = re.sub(r"> Template state\..*?\n(> .*\n)*", "> Agents: read `AI_GUIDELINE.md` first, then run `make doctor`.\n", s, count=1)
s = re.sub(r"## Creating a research repo from this template\n.*?(?=\n## )", "", s, count=1, flags=re.S)
if question:
    s = s.replace("<One affirmative sentence naming the phenomenon and the estimand.>", question)
r.write_text(s)
if question:
    p = Path("experiments/A/PREMISE.md"); t = p.read_text()
    t = re.sub(r"<One sentence naming the estimand.*?>", question, t, count=1, flags=re.S)
    p.write_text(t)
t = Path("TODO.md"); s = t.read_text()
s = s.replace("- [ ] Run `scripts/init_repo.sh <package> <repo-name>` and fill `.env`.\n", "")
if question:
    s = s.replace("- [ ] Rewrite `README.md` and `experiments/A/PREMISE.md` with the research question.\n",
                  "- [ ] Sharpen the research question in `README.md` and `experiments/A/PREMISE.md` (estimand, construction).\n")
t.write_text(s)
m = Path("Makefile"); s = m.read_text()
s = re.sub(r"\ninstall-cli:.*?(?=\n\S|\Z)", "", s, count=1, flags=re.S).replace(".PHONY: doctor install-cli", ".PHONY: doctor")
m.write_text(s)
w = Path("WORKLOG.md"); s = w.read_text()
import datetime as dt
s = s.replace("- 2026-09-13 Scaffold created from research-repo-setup template.",
              f"- {dt.date.today().isoformat()} {name} created from research-repo-setup template.")
w.write_text(s)
PY

# 3. rename the package, write .env from defaults, lock, test, validate
bash scripts/init_repo.sh "$PKG" "$NAME"
rm -f scripts/init_repo.sh

# 4. fresh history and GitHub
git init -b main --quiet
git add -A
git commit --quiet -m "Repo: initialize $NAME from research-repo-setup template

Package: $PKG
Template: $TEMPLATE
Research question: ${QUESTION:-<not yet stated>}"
if [ "$GITHUB" = 1 ]; then
  OWNER="${GITHUB_OWNER:-$(gh api user --jq .login)}"
  gh repo create "$OWNER/$NAME" $VISIBILITY --source . --remote origin --push
fi

echo
echo "created $DEST"
[ "$GITHUB" = 1 ] && echo "github: https://github.com/${OWNER}/${NAME}"
echo "next: cd $DEST && make doctor"

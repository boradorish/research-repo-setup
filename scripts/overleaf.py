"""Overleaf CLI: status | sync | gate | push | set-level LEVEL. Policy in paper/OVERLEAF.md."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from myproject import overleaf

REPO_ROOT = Path(__file__).resolve().parents[1]


def skill_script() -> Path:
    d = Path(os.environ.get("OVERLEAF_GIT_SKILL_DIR", Path.home() / ".claude/skills/overleaf-git"))
    s = d / "scripts" / "overleaf_git_sync.sh"
    if not s.is_file():
        sys.exit(f"overleaf-git skill script not found at {s}; install SNU-PI/snupi-skills")
    return s


def main(argv: list[str]) -> int:
    cmd = argv[0] if argv else "status"
    policy = overleaf.load_policy(REPO_ROOT)
    clone = REPO_ROOT / policy.clone_dir

    if cmd == "set-level":
        if len(argv) < 2:
            sys.exit("usage: overleaf.py set-level <read|bronze|silver|gold>")
        old, new = overleaf.set_level(REPO_ROOT, argv[1])
        print(f"overleaf level {old} -> {new}")
        print(overleaf.describe(overleaf.load_policy(REPO_ROOT)))
        return 0

    if cmd == "status":
        print(overleaf.describe(policy))
        if clone.is_dir():
            subprocess.run(["git", "-C", str(clone), "status", "--short", "--branch"], check=False)
        else:
            print(f"clone: absent ({clone})")
        return 0

    try:
        overleaf.require_link(policy)
    except overleaf.PolicyError as e:
        print(str(e))
        return 2

    if cmd == "sync":
        return subprocess.call([str(skill_script()), policy.project_url, str(clone)])

    if cmd == "gate":
        if not clone.is_dir():
            sys.exit(f"no clone at {clone}; run make overleaf-sync")
        changes = overleaf.working_tree_changes(clone)
        violations = overleaf.gate(policy, changes, overleaf.bib_keys(clone, changes))
        if not changes:
            print("no local changes")
        for c in changes:
            cls = overleaf.classify(policy, c.path)
            print(f"  {cls:9s} {c.path}  (+{len(c.added)} -{len(c.removed)})")
        if violations:
            print("VIOLATIONS:")
            for x in violations:
                print("  - " + x)
            return 1
        print("gate: OK under level", policy.level)
        return 0

    if cmd == "push":
        if os.environ.get("CONFIRM") != "yes":
            sys.exit(
                "push needs the owner's explicit word for this change set; rerun with CONFIRM=yes"
            )
        rc = main(["gate"])
        if rc != 0:
            return rc
        dirty = subprocess.run(
            ["git", "-C", str(clone), "status", "--porcelain"], capture_output=True, text=True
        ).stdout.strip()
        if dirty:
            sys.exit("commit inside the clone first ([claude] ...); the skill refuses a dirty tree")
        subprocess.run(
            ["git", "-C", str(clone), "log", "--oneline", "@{upstream}..HEAD"], check=False
        )
        return subprocess.call([str(skill_script()), "--push", policy.project_url, str(clone)])

    sys.exit(f"unknown command {cmd}")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

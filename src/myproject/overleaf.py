"""Overleaf policy: load the level, classify paths, and gate a working-tree diff.

Rules are stated in paper/OVERLEAF.md; this module makes them fail in code.
"""

from __future__ import annotations

import fnmatch
import re
import subprocess
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

LEVELS = ("read", "bronze", "silver", "gold", "platinum")
ASK_FOR_LINK = "Overleaf 프로젝트 링크 줘!"
CITE_RE = re.compile(r"\\cite[a-zA-Z*]*(?:\[[^\]]*\])*\{([^}]*)\}")
BIBKEY_RE = re.compile(r"^@\w+\s*\{\s*([^,\s]+)\s*,", re.M)


class PolicyError(ValueError):
    pass


@dataclass
class Policy:
    project_url: str
    level: str
    clone_dir: str
    agent_dir: str
    figure_globs: list[str]
    appendix_globs: list[str]
    protected_globs: list[str]
    front_matter_globs: list[str] = field(default_factory=list)
    macros: list[str] = field(default_factory=lambda: ["CLAUDE", "CODEX", "GEMINI", "AGENT"])

    @property
    def rank(self) -> int:
        return LEVELS.index(self.level)


def policy_path(repo_root: str | Path) -> Path:
    return Path(repo_root) / "paper" / "overleaf.toml"


def load_policy(repo_root: str | Path) -> Policy:
    with open(policy_path(repo_root), "rb") as f:
        d = tomllib.load(f)
    level = d.get("level", "read")
    if level not in LEVELS:
        raise PolicyError(f"level {level!r} must be one of {LEVELS}")
    return Policy(
        project_url=d.get("project_url", ""),
        level=level,
        clone_dir=d.get("clone_dir", "paper/overleaf"),
        agent_dir=d.get("agent_dir", "agent"),
        figure_globs=list(d.get("figure_globs", [])),
        appendix_globs=list(d.get("appendix_globs", [])),
        protected_globs=list(d.get("protected_globs", [])),
        front_matter_globs=list(d.get("front_matter_globs", [])),
        macros=list(d.get("macros", ["CLAUDE", "CODEX", "GEMINI", "AGENT"])),
    )


def require_link(policy: Policy) -> None:
    if not policy.project_url.strip():
        raise PolicyError(ASK_FOR_LINK)


def set_level(repo_root: str | Path, level: str, who: str = "owner") -> tuple[str, str]:
    """Rewrite `level` in place (keeps comments) and append a WORKLOG line."""
    if level not in LEVELS:
        raise PolicyError(f"level {level!r} must be one of {LEVELS}")
    p = policy_path(repo_root)
    text = p.read_text()
    m = re.search(r'^level\s*=\s*"(\w+)"', text, re.M)
    old = m.group(1) if m else "read"
    text = re.sub(r'^level\s*=\s*"\w+"', f'level = "{level}"', text, count=1, flags=re.M)
    p.write_text(text)
    import datetime as dt

    line = f"- {dt.date.today().isoformat()} Overleaf level {old} -> {level} ({who}).\n"
    with open(Path(repo_root) / "WORKLOG.md", "a") as f:
        f.write(line)
    return old, level


def _match(path: str, globs: list[str]) -> bool:
    return any(fnmatch.fnmatch(path, g) or fnmatch.fnmatch(Path(path).name, g) for g in globs)


def classify(policy: Policy, path: str) -> str:
    """protected | front_matter | agent | figure | appendix | bib | body | other"""
    if _match(path, policy.protected_globs):
        return "protected"
    if _match(path, policy.front_matter_globs):
        return "front_matter"
    if path == policy.agent_dir or path.startswith(policy.agent_dir.rstrip("/") + "/"):
        return "agent"
    if _match(path, policy.appendix_globs):
        return "appendix"
    if _match(path, policy.figure_globs):
        return "figure"
    if path.endswith(".bib"):
        return "bib"
    if path.endswith(".tex"):
        return "body"
    return "other"


MIN_RANK = {
    "protected": 99,
    "front_matter": 4,
    "agent": 1,
    "figure": 2,
    "appendix": 2,
    "bib": 2,
    "body": 3,
    "other": 3,
}


@dataclass
class Change:
    path: str
    added: list[str]
    removed: list[str]
    is_new: bool = False


def working_tree_changes(clone: Path) -> list[Change]:
    """Staged + unstaged changes against HEAD, plus untracked files."""

    def git(*a: str) -> str:
        return subprocess.check_output(["git", "-C", str(clone), *a], text=True)

    changes: dict[str, Change] = {}
    diff = git("diff", "HEAD", "--no-color", "--unified=0", "--no-ext-diff")
    cur: Change | None = None
    for ln in diff.splitlines():
        if ln.startswith("+++ b/"):
            cur = changes.setdefault(ln[6:], Change(ln[6:], [], []))
        elif ln.startswith("--- /dev/null") and cur is None:
            pass
        elif cur and ln.startswith("+") and not ln.startswith("+++"):
            cur.added.append(ln[1:])
        elif cur and ln.startswith("-") and not ln.startswith("---"):
            cur.removed.append(ln[1:])
    for ln in git("ls-files", "--others", "--exclude-standard").splitlines():
        p = clone / ln
        if p.is_file():
            try:
                lines = p.read_text(errors="replace").splitlines()
            except OSError:
                lines = []
            changes[ln] = Change(ln, lines, [], is_new=True)
    return list(changes.values())


def bib_keys(clone: Path, changes: list[Change]) -> set[str]:
    keys: set[str] = set()
    for p in clone.rglob("*.bib"):
        keys |= set(BIBKEY_RE.findall(p.read_text(errors="replace")))
    for c in changes:
        if c.path.endswith(".bib"):
            keys |= set(BIBKEY_RE.findall("\n".join(c.added)))
    return keys


def gate(policy: Policy, changes: list[Change], known_bib_keys: set[str]) -> list[str]:
    """Return violations. Empty list means the change set is within policy."""
    v: list[str] = []
    macro_re = re.compile(r"\\(" + "|".join(map(re.escape, policy.macros)) + r")(DEL)?\{")
    del_re = re.compile(r"\\(" + "|".join(map(re.escape, policy.macros)) + r")DEL\{")

    if policy.rank == 0 and changes:
        v.append("level=read permits no changes; " + ", ".join(c.path for c in changes))
        return v

    for c in changes:
        cls = classify(policy, c.path)
        if cls == "protected":
            v.append(f"{c.path}: protected at every level")
            continue
        if policy.rank < MIN_RANK[cls]:
            v.append(
                f"{c.path}: class {cls} needs level {LEVELS[MIN_RANK[cls]]}, have {policy.level}"
            )
            continue
        if cls == "bib" and c.removed:
            v.append(f"{c.path}: .bib entries may be added, never removed or rewritten")
        if c.path.endswith(".tex"):
            added_text = "\n".join(c.added)
            substantive = [ln for ln in c.added if ln.strip() and not ln.lstrip().startswith("%")]
            if substantive and cls != "agent" and not macro_re.search(added_text):
                v.append(f"{c.path}: inserted text carries no agent macro (\\CLAUDE{{...}} etc.)")
            if c.removed and cls != "agent" and not del_re.search(added_text):
                v.append(f"{c.path}: lines removed without a matching ...DEL{{}} macro")
            for m in CITE_RE.finditer(added_text):
                for key in (k.strip() for k in m.group(1).split(",")):
                    if key and key not in known_bib_keys:
                        v.append(f"{c.path}: \\cite{{{key}}} has no entry in any .bib")
    return v


def describe(policy: Policy) -> str:
    rows = [
        f"level: {policy.level}",
        f"project_url: {policy.project_url or '(empty) ' + ASK_FOR_LINK}",
        f"clone_dir: {policy.clone_dir}",
        "may write:",
    ]
    if policy.rank >= 1:
        rows.append(f"  - {policy.agent_dir}/ (not \\input by the paper)")
    if policy.rank >= 2:
        rows.append(f"  - appendix: {policy.appendix_globs}")
        rows.append(f"  - figures/tables: {policy.figure_globs}; .bib additions")
    if policy.rank >= 3:
        rows.append("  - body sections (claim-tier results only)")
    if policy.rank >= 4:
        rows.append(f"  - front matter and structure: {policy.front_matter_globs}")
    if policy.rank == 0:
        rows.append("  - nothing (sync and read only)")
    rows.append(f"never: {policy.protected_globs}")
    return "\n".join(rows)

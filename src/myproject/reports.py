"""Report (summary artifact) contract. Rules: reports/README.md."""

from __future__ import annotations

import json
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from myproject import registry

AGENTS = ("claude", "codex", "gemini")
STATUSES = ("draft", "published")
REQUIRED_SECTIONS = ("observations", "interpretation", "second-opinion", "provenance")
REPORTS_DIR = "reports"


class ReportError(ValueError):
    pass


@dataclass(frozen=True)
class Report:
    slug: str
    dir: Path
    meta: dict[str, Any]


def list_slugs(repo_root: str | Path) -> list[str]:
    root = Path(repo_root) / REPORTS_DIR
    return sorted(
        p.name
        for p in root.iterdir()
        if p.is_dir() and not p.name.startswith("_") and (p / "report.toml").is_file()
    )


def load(repo_root: str | Path, slug: str) -> Report:
    d = Path(repo_root) / REPORTS_DIR / slug
    mp = d / "report.toml"
    if not mp.is_file():
        raise ReportError(f"no report.toml in {d}")
    with open(mp, "rb") as f:
        meta = tomllib.load(f)
    rep = Report(slug=slug, dir=d, meta=meta)
    validate(rep, repo_root)
    return rep


def _section_text(html: str, sec_id: str) -> str:
    m = re.search(
        rf'<(section|footer)[^>]*id="{re.escape(sec_id)}"[^>]*>(.*?)</\1>', html, re.S | re.I
    )
    if not m:
        return ""
    body = re.sub(r"<!--.*?-->", "", m.group(2), flags=re.S)
    body = re.sub(r'<p class="tag">.*?</p>', "", body, flags=re.S)
    return re.sub(r"<[^>]+>", "", body).strip()


def review_agent(review_path: Path) -> str:
    if not review_path.is_file():
        return ""
    m = re.search(r"^Agent:\s*(\w+)", review_path.read_text(), re.M | re.I)
    return m.group(1).lower() if m else ""


def validate(rep: Report, repo_root: str | Path) -> None:
    m, d = rep.meta, rep.dir
    errors: list[str] = []

    if m.get("slug") != rep.slug:
        errors.append(f"slug {m.get('slug')!r} does not match directory {rep.slug!r}")
    if registry.ID_RE.match(rep.slug or ""):
        errors.append("slug names a flow, not an experiment id")
    if not str(m.get("flow", "")).strip():
        errors.append("flow is required: one sentence naming the question this flow answers")
    exps = m.get("experiments") or []
    if not exps:
        errors.append("experiments must list at least one member")
    for e in exps:
        try:
            registry.load(repo_root, e)
        except registry.ManifestError as ex:
            errors.append(f"member {e}: {ex}")
    author = str(m.get("author_agent", "")).lower()
    if author not in AGENTS:
        errors.append(f"author_agent must be one of {AGENTS}")
    if m.get("status") not in STATUSES:
        errors.append(f"status must be one of {STATUSES}")
    if m.get("status") == "published" and not str(m.get("artifact_url", "")).strip():
        errors.append("published reports carry artifact_url")

    html_path = d / "index.html"
    if not html_path.is_file():
        errors.append("index.html is missing")
        html = ""
    else:
        html = html_path.read_text()
        for sec in REQUIRED_SECTIONS:
            if not re.search(rf'id="{re.escape(sec)}"', html):
                errors.append(f'index.html lacks a section with id="{sec}"')

    interp = _section_text(html, "interpretation")
    if interp:
        rev = review_agent(d / "REVIEW.md")
        if not rev:
            errors.append("interpretation exists but REVIEW.md with an 'Agent:' line is missing")
        elif rev == author:
            errors.append(f"REVIEW.md must come from an agent other than the author ({author})")
        if not _section_text(html, "second-opinion"):
            errors.append("interpretation exists but the second-opinion section is empty")

    data_dir = d / "data"
    files = sorted(data_dir.glob("*.json")) if data_dir.is_dir() else []
    if m.get("status") == "published" and not files:
        errors.append("published reports carry at least one data/*.json with provenance")
    for f in files:
        try:
            obj = json.loads(f.read_text())
        except json.JSONDecodeError as ex:
            errors.append(f"{f.name}: invalid JSON ({ex})")
            continue
        src = obj.get("source") if isinstance(obj, dict) else None
        if not src:
            errors.append(f"{f.name}: needs a 'source' receipt path")
        elif not (Path(repo_root) / src).exists():
            errors.append(f"{f.name}: source {src} does not exist")
        if isinstance(obj, dict) and obj.get("exp_id") not in exps:
            errors.append(f"{f.name}: exp_id must be one of the member experiments")

    if errors:
        raise ReportError(f"report {rep.slug}: " + "; ".join(errors))

"""Experiment manifest schema and validator. Raises on any contract violation.

Id scheme: ``<SERIES>-<N>`` such as ``A-1``. The series letter names a research
premise (one ``experiments/<SERIES>/PREMISE.md``); the number counts experiments
under that premise. ``N = 0`` is reserved for smoke / infrastructure runs. A new
premise opens a new letter. Directory: ``experiments/<SERIES>/<SERIES>-<N>[-slug]/``.
"""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

STATUSES = ("draft", "registered", "running", "complete", "stopped", "failed")
TIERS = ("smoke", "exploratory", "claim")
VERDICTS = ("pending", "success", "failure", "inconclusive")
RELATION_KINDS = ("extends", "controls", "contradicts", "reproduces", "motivates")
EXPERIMENTS_DIR = "experiments"
ID_RE = re.compile(r"^(?P<series>[A-Z])-(?P<n>\d+)$")


class ManifestError(ValueError):
    pass


@dataclass(frozen=True)
class Experiment:
    id: str
    dir: Path
    manifest_path: Path
    manifest: dict[str, Any]

    @property
    def series(self) -> str:
        return self.id.split("-")[0]

    @property
    def number(self) -> int:
        return int(self.id.split("-")[1])

    @property
    def status(self) -> str:
        return self.manifest["status"]

    @property
    def evidence(self) -> str:
        return self.manifest["evidence"]

    @property
    def verdict(self) -> str:
        return self.manifest.get("verdict", "pending")

    @property
    def summary(self) -> str:
        return self.manifest.get("summary", "")

    @property
    def relations(self) -> list[dict[str, str]]:
        return list(self.manifest.get("relations", []))


def parse_id(exp_id: str) -> tuple[str, int]:
    m = ID_RE.match(exp_id)
    if not m:
        raise ManifestError(f"id {exp_id!r} must look like A-1 (series letter, dash, number)")
    return m["series"], int(m["n"])


def experiment_dir(repo_root: str | Path, exp_id: str) -> Path:
    series, _ = parse_id(exp_id)
    sdir = Path(repo_root) / EXPERIMENTS_DIR / series
    if not sdir.is_dir():
        raise ManifestError(f"no series directory {sdir}")
    hits = [
        p
        for p in sdir.iterdir()
        if p.is_dir() and (p.name == exp_id or p.name.startswith(exp_id + "-"))
    ]
    if not hits:
        raise ManifestError(f"no experiment directory for {exp_id} under {sdir}")
    if len(hits) > 1:
        raise ManifestError(f"ambiguous directories for {exp_id}: {[h.name for h in hits]}")
    return hits[0]


def list_ids(repo_root: str | Path) -> list[str]:
    root = Path(repo_root) / EXPERIMENTS_DIR
    ids: list[tuple[str, int]] = []
    for sdir in sorted(p for p in root.iterdir() if p.is_dir() and re.fullmatch(r"[A-Z]", p.name)):
        for d in sdir.iterdir():
            if d.is_dir() and (d / "experiment.toml").is_file():
                m = re.match(r"^([A-Z])-(\d+)", d.name)
                if m:
                    ids.append((m[1], int(m[2])))
    return [f"{s}-{n}" for s, n in sorted(ids)]


def load(repo_root: str | Path, exp_id: str) -> Experiment:
    d = experiment_dir(repo_root, exp_id)
    mp = d / "experiment.toml"
    if not mp.is_file():
        raise ManifestError(f"missing manifest {mp}")
    with open(mp, "rb") as f:
        manifest = tomllib.load(f)
    exp = Experiment(id=exp_id, dir=d, manifest_path=mp, manifest=manifest)
    validate(exp, repo_root)
    return exp


def validate(exp: Experiment, repo_root: str | Path) -> None:
    m = exp.manifest
    root = Path(repo_root)
    errors: list[str] = []

    def need(field: str, why: str = "") -> None:
        v = m.get(field)
        if v in (None, "", [], {}):
            errors.append(f"{field} is required{(' (' + why + ')') if why else ''}")

    for f in ("id", "title", "status", "evidence", "question", "task", "config", "seeds"):
        need(f)
    if m.get("id") != exp.id:
        errors.append(f"id {m.get('id')!r} does not match directory {exp.dir.name!r}")
    try:
        series, n = parse_id(str(m.get("id", "")))
    except ManifestError as e:
        errors.append(str(e))
        series, n = "", -1
    if series and not (root / EXPERIMENTS_DIR / series / "PREMISE.md").is_file():
        errors.append(
            f"series {series} needs experiments/{series}/PREMISE.md stating its research question"
        )
    if n == 0 and m.get("evidence") != "smoke":
        errors.append("number 0 is reserved for smoke / infrastructure runs")
    if m.get("status") not in STATUSES:
        errors.append(f"status must be one of {STATUSES}")
    if m.get("evidence") not in TIERS:
        errors.append(f"evidence must be one of {TIERS}")
    verdict = m.get("verdict", "pending")
    if verdict not in VERDICTS:
        errors.append(f"verdict must be one of {VERDICTS}")
    if verdict != "pending":
        need("summary", "a verdict needs a one-line interpretation")
        if m.get("status") not in ("complete", "stopped", "failed"):
            errors.append("a verdict other than pending requires a terminal status")

    status, tier = m.get("status"), m.get("evidence")
    if status != "draft":
        need("entrypoint", "non-draft manifests must declare an entrypoint")
    if tier != "smoke":
        need("comparison_axes", "non-smoke manifests must name comparison axes")
        need("hypothesis", "non-smoke manifests state what is expected")
    if tier == "claim":
        need("decision_rule", "claim tier needs a prospective decision rule")
        need("outcome_branches", "claim tier needs affirmative outcome branches")
        if status != "draft":
            need("reviewed_by", "claim tier needs one cross-family review before launch")

    # Reproducibility: data, GPU, and environment are fixed before the run (non-smoke).
    if tier != "smoke":
        inputs = m.get("inputs") or []
        real = [i for i in inputs if i.get("name") and i.get("identity")]
        if not real:
            errors.append(
                "inputs must list every dataset/checkpoint with the identity it already carries"
            )
        for i in inputs:
            if i.get("kind") not in ("dataset", "checkpoint", "artifact"):
                errors.append(f"input {i.get('name')!r}: kind must be dataset|checkpoint|artifact")
        comp = m.get("compute") or {}
        if not comp.get("gpu_type"):
            errors.append("compute.gpu_type is required (numerics depend on it)")
        env = m.get("environment") or {}
        for k in ("python", "determinism"):
            if not env.get(k):
                errors.append(f"environment.{k} is required")

    seeds = m.get("seeds")
    if seeds is not None and (
        not isinstance(seeds, list) or not all(isinstance(s, int) for s in seeds)
    ):
        errors.append("seeds must be a literal list of integers")

    for r in m.get("relations", []):
        to, kind = r.get("to", ""), r.get("kind", "")
        if not ID_RE.match(to):
            errors.append(f"relation target {to!r} is not an experiment id")
        if kind not in RELATION_KINDS:
            errors.append(f"relation kind {kind!r} must be one of {RELATION_KINDS}")
        if to == exp.id:
            errors.append("an experiment cannot relate to itself")

    arts = m.get("expected_artifacts") or []
    if not any(a.get("path") == "receipt.json" for a in arts):
        errors.append("expected_artifacts must include receipt.json")

    cfg = root / str(m.get("config", ""))
    if m.get("config") and not cfg.is_file():
        errors.append(f"config {cfg} does not exist")

    task = m.get("task")
    if task and not (root / "src" / "myproject" / "tasks" / f"{task}.py").is_file():
        errors.append(f"task module src/myproject/tasks/{task}.py does not exist")

    if errors:
        raise ManifestError(f"{exp.id}: " + "; ".join(errors))


def assert_runnable(exp: Experiment, reproduce: bool) -> None:
    if reproduce:
        if exp.status != "complete":
            raise ManifestError(f"{exp.id}: --reproduce requires status=complete, got {exp.status}")
        return
    if exp.status != "registered":
        raise ManifestError(
            f"{exp.id}: normal execution accepts only status=registered, got {exp.status}"
        )

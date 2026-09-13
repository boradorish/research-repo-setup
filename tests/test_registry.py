import tomllib
from pathlib import Path

import pytest

from myproject import registry

REPO = Path(__file__).resolve().parents[1]


def test_smoke_manifest_validates():
    exp = registry.load(REPO, "A-0")
    assert exp.status == "registered"
    assert exp.evidence == "smoke"
    assert exp.series == "A" and exp.number == 0


def test_list_ids_sorted_by_series_then_number():
    assert registry.list_ids(REPO)[0] == "A-0"


def test_bad_id_shapes_rejected():
    for bad in ("EXP-001", "a-1", "A1", "AB-1", "A-x"):
        with pytest.raises(registry.ManifestError):
            registry.parse_id(bad)


def test_template_is_not_runnable_as_is():
    d = REPO / "experiments" / "_template"
    with open(d / "experiment.toml", "rb") as f:
        manifest = tomllib.load(f)
    exp = registry.Experiment(
        id="A-1", dir=d, manifest_path=d / "experiment.toml", manifest=manifest
    )
    with pytest.raises(registry.ManifestError):
        registry.validate(exp, REPO)


MIN = """
id = "{id}"
title = "t"
status = "{status}"
evidence = "{tier}"
question = "q"
hypothesis = "h"
task = "smoke"
entrypoint = "scripts/train.py"
config = "configs/base.toml"
seeds = [0, 1]
comparison_axes = ["seed"]
{extra}
[[inputs]]
name = "toy"
kind = "dataset"
identity = "synthetic:seed-derived"
[environment]
python = "3.12"
determinism = "seeded"
[compute]
gpus = 1
gpu_type = "any"
[[expected_artifacts]]
path = "receipt.json"
track = true
"""


def _repo(tmp_path: Path, exp_id: str, body: str, premise: bool = True) -> Path:
    (tmp_path / "configs").mkdir()
    (tmp_path / "configs" / "base.toml").write_text("[train]\nsteps=1\n")
    (tmp_path / "src" / "myproject" / "tasks").mkdir(parents=True)
    (tmp_path / "src" / "myproject" / "tasks" / "smoke.py").write_text("")
    series = exp_id.split("-")[0]
    d = tmp_path / "experiments" / series / f"{exp_id}-slug"
    d.mkdir(parents=True)
    if premise:
        (d.parent / "PREMISE.md").write_text("# Series\n\nq\n")
    (d / "experiment.toml").write_text(body)
    return tmp_path


def test_series_needs_premise(tmp_path):
    root = _repo(
        tmp_path,
        "B-1",
        MIN.format(id="B-1", status="draft", tier="exploratory", extra=""),
        premise=False,
    )
    with pytest.raises(registry.ManifestError, match="PREMISE.md"):
        registry.load(root, "B-1")


def test_number_zero_reserved_for_smoke(tmp_path):
    root = _repo(
        tmp_path, "B-0", MIN.format(id="B-0", status="draft", tier="exploratory", extra="")
    )
    with pytest.raises(registry.ManifestError, match="reserved"):
        registry.load(root, "B-0")


def test_claim_requires_decision_rule(tmp_path):
    root = _repo(tmp_path, "A-1", MIN.format(id="A-1", status="registered", tier="claim", extra=""))
    with pytest.raises(registry.ManifestError, match="decision_rule"):
        registry.load(root, "A-1")


def test_exploratory_requires_comparison_axes(tmp_path):
    body = MIN.format(id="A-2", status="draft", tier="exploratory", extra="").replace(
        'comparison_axes = ["seed"]', "comparison_axes = []"
    )
    root = _repo(tmp_path, "A-2", body)
    with pytest.raises(registry.ManifestError, match="comparison_axes"):
        registry.load(root, "A-2")


def test_verdict_requires_summary_and_terminal_status(tmp_path):
    body = MIN.format(
        id="A-3", status="registered", tier="exploratory", extra='verdict = "success"\n'
    )
    root = _repo(tmp_path, "A-3", body)
    with pytest.raises(registry.ManifestError, match="summary"):
        registry.load(root, "A-3")


def test_relation_kind_and_target_checked(tmp_path):
    extra = '[[relations]]\nto = "A-3"\nkind = "vibes"\n'
    root = _repo(
        tmp_path, "A-4", MIN.format(id="A-4", status="draft", tier="exploratory", extra=extra)
    )
    with pytest.raises(registry.ManifestError, match="kind"):
        registry.load(root, "A-4")


def test_only_registered_is_runnable(tmp_path):
    root = _repo(
        tmp_path, "A-5", MIN.format(id="A-5", status="draft", tier="exploratory", extra="")
    )
    exp = registry.load(root, "A-5")
    with pytest.raises(registry.ManifestError, match="registered"):
        registry.assert_runnable(exp, reproduce=False)
    with pytest.raises(registry.ManifestError, match="complete"):
        registry.assert_runnable(exp, reproduce=True)


def test_non_smoke_requires_data_gpu_and_environment(tmp_path):
    body = MIN.format(id="A-6", status="draft", tier="exploratory", extra="")
    body = body.replace('identity = "synthetic:seed-derived"', 'identity = ""')
    body = body.replace('gpu_type = "any"', 'gpu_type = ""')
    body = body.replace('determinism = "seeded"', 'determinism = ""')
    root = _repo(tmp_path, "A-6", body)
    with pytest.raises(registry.ManifestError) as ei:
        registry.load(root, "A-6")
    msg = str(ei.value)
    assert "inputs" in msg and "gpu_type" in msg and "determinism" in msg

import json
import shutil
from pathlib import Path

import pytest

from myproject import reports

REPO = Path(__file__).resolve().parents[1]
TEMPLATE_HTML = (REPO / "reports" / "_template" / "index.html").read_text()


def _mk(tmp_path: Path, slug: str, meta: str, html: str = TEMPLATE_HTML, review: str | None = None):
    # minimal repo with the real A-0 experiment copied in
    for sub in ("experiments/A/A-0-smoke", "configs", "src/myproject/tasks"):
        (tmp_path / sub).mkdir(parents=True, exist_ok=True)
    shutil.copy(
        REPO / "experiments/A/A-0-smoke/experiment.toml", tmp_path / "experiments/A/A-0-smoke"
    )
    shutil.copy(REPO / "experiments/A/PREMISE.md", tmp_path / "experiments/A")
    shutil.copy(REPO / "configs/base.toml", tmp_path / "configs")
    (tmp_path / "src/myproject/tasks/smoke.py").write_text("")
    d = tmp_path / "reports" / slug
    d.mkdir(parents=True)
    (d / "report.toml").write_text(meta)
    (d / "index.html").write_text(html)
    if review is not None:
        (d / "REVIEW.md").write_text(review)
    return tmp_path


META = (
    'slug = "{slug}"\nflow = "{flow}"\nexperiments = ["A-0"]\nauthor_agent = "claude"\n'
    'status = "{status}"\nartifact_url = "{url}"\n'
)


def test_template_skeleton_passes_as_draft(tmp_path):
    root = _mk(
        tmp_path, "smoke-flow", META.format(slug="smoke-flow", flow="q", status="draft", url="")
    )
    reports.load(root, "smoke-flow")


def test_slug_must_not_be_an_experiment_id(tmp_path):
    root = _mk(tmp_path, "A-0", META.format(slug="A-0", flow="q", status="draft", url=""))
    with pytest.raises(reports.ReportError, match="flow, not an experiment"):
        reports.load(root, "A-0")


def test_flow_required(tmp_path):
    root = _mk(tmp_path, "x", META.format(slug="x", flow="", status="draft", url=""))
    with pytest.raises(reports.ReportError, match="flow is required"):
        reports.load(root, "x")


def test_interpretation_requires_other_agent_review(tmp_path):
    html = TEMPLATE_HTML.replace(
        '<p class="tag">interpretation, written after the second opinion below</p>',
        '<p class="tag">interpretation, written after the second opinion below</p>'
        "<p>Width helps.</p>",
    )
    meta = META.format(slug="x", flow="q", status="draft", url="")
    root = _mk(tmp_path, "x", meta, html)
    with pytest.raises(reports.ReportError, match="REVIEW.md"):
        reports.load(root, "x")
    root2 = _mk(tmp_path / "b", "x", meta, html, review="Agent: claude\nDate: 2026-09-13\n...")
    with pytest.raises(reports.ReportError, match="other than the author"):
        reports.load(root2, "x")
    html_ok = html.replace(
        '<p class="tag">verbatim from REVIEW.md — agent: ___, date: ___</p>',
        '<p class="tag">verbatim</p><p>Agent: codex. I agree with caution.</p>',
    )
    root3 = _mk(tmp_path / "c", "x", meta, html_ok, review="Agent: codex\nDate: 2026-09-13\n...")
    reports.load(root3, "x")


def test_published_needs_url_and_sourced_data(tmp_path):
    meta = META.format(slug="x", flow="q", status="published", url="")
    root = _mk(tmp_path, "x", meta)
    with pytest.raises(reports.ReportError, match="artifact_url"):
        reports.load(root, "x")
    meta = META.format(slug="x", flow="q", status="published", url="https://claude.ai/x")
    root = _mk(tmp_path / "b", "x", meta)
    with pytest.raises(reports.ReportError, match="data/"):
        reports.load(root, "x")
    d = root / "reports" / "x" / "data"
    d.mkdir()
    (d / "loss.json").write_text(
        json.dumps({"exp_id": "A-0", "source": "experiments/nope.json", "y": [1]})
    )
    with pytest.raises(reports.ReportError, match="does not exist"):
        reports.load(root, "x")
    (d / "loss.json").write_text(
        json.dumps({"exp_id": "A-0", "source": "experiments/A/A-0-smoke/experiment.toml", "y": [1]})
    )
    reports.load(root, "x")

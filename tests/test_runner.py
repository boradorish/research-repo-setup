import json
from pathlib import Path

import pytest

from myproject import runner

REPO = Path(__file__).resolve().parents[1]


def test_smoke_run_leaves_receipt_and_artifacts(tmp_path, monkeypatch):
    monkeypatch.setenv("OUTPUT_ROOT", str(tmp_path))
    run_dir = runner.run(REPO, "A-0", run_id="t1")
    receipt = json.loads((run_dir / "receipt.json").read_text())
    assert receipt["status"] == "complete"
    assert receipt["resolved_config"]["train"]["steps"] == 3  # override applied
    assert (run_dir / "smoke.json").is_file()
    assert (run_dir / "experiment.toml").is_file()


def test_run_id_never_overwrites(tmp_path, monkeypatch):
    monkeypatch.setenv("OUTPUT_ROOT", str(tmp_path))
    runner.run(REPO, "A-0", run_id="dup")
    with pytest.raises(FileExistsError):
        runner.run(REPO, "A-0", run_id="dup")


def test_failed_task_still_writes_receipt(tmp_path, monkeypatch):
    monkeypatch.setenv("OUTPUT_ROOT", str(tmp_path))
    import myproject.tasks.smoke as smoke

    def boom(*a, **k):
        raise RuntimeError("boom")

    monkeypatch.setattr(smoke, "run", boom)
    with pytest.raises(RuntimeError):
        runner.run(REPO, "A-0", run_id="fail")
    receipt = json.loads((tmp_path / "A-0" / "fail" / "receipt.json").read_text())
    assert receipt["status"] == "failed"
    assert receipt["error"]["message"] == "boom"

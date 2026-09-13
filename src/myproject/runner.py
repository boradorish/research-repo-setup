"""Create the run directory, write the receipt before and after, dispatch the task."""

from __future__ import annotations

import datetime as dt
import importlib
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import traceback
from pathlib import Path
from typing import Any

from myproject import config, registry


def new_run_id(now: dt.datetime | None = None) -> str:
    now = now or dt.datetime.now(dt.UTC)
    return now.strftime("%Y%m%d-%H%M%S") + f"-{os.getpid()}"


def git_identity(repo_root: Path) -> dict[str, Any]:
    def run(*args: str) -> str:
        try:
            return subprocess.check_output(
                ["git", *args], cwd=repo_root, text=True, stderr=subprocess.DEVNULL
            ).strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return ""

    return {"git_commit": run("rev-parse", "HEAD"), "git_dirty": bool(run("status", "--porcelain"))}


def hardware_identity() -> dict[str, Any]:
    """What actually ran: GPU names, driver, torch/cuda. Recorded, not trusted over the manifest."""
    info: dict[str, Any] = {"gpus": [], "driver": None, "torch": None, "cuda": None}
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=name,driver_version", "--format=csv,noheader"],
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=20,
        )
        rows = [r.split(", ") for r in out.strip().splitlines() if r.strip()]
        info["gpus"] = [r[0] for r in rows]
        info["driver"] = rows[0][1] if rows and len(rows[0]) > 1 else None
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        pass
    try:
        import torch  # type: ignore[import-not-found]

        info["torch"] = torch.__version__
        info["cuda"] = torch.version.cuda
    except ImportError:
        pass
    return info


def output_root(repo_root: Path) -> Path:
    return Path(os.environ.get("OUTPUT_ROOT") or repo_root / "outputs")


def write_receipt(run_dir: Path, receipt: dict[str, Any]) -> None:
    tmp = run_dir / "receipt.json.tmp"
    tmp.write_text(json.dumps(receipt, indent=2, sort_keys=True, default=str))
    tmp.replace(run_dir / "receipt.json")


def run(
    repo_root: str | Path,
    exp_id: str,
    reproduce: str | None = None,
    run_id: str | None = None,
) -> Path:
    repo_root = Path(repo_root).resolve()
    exp = registry.load(repo_root, exp_id)
    registry.assert_runnable(exp, reproduce=bool(reproduce))

    run_id = run_id or new_run_id()
    run_dir = output_root(repo_root) / exp_id / run_id
    run_dir.parent.mkdir(parents=True, exist_ok=True)
    run_dir.mkdir(exist_ok=False)  # a run id never overwrites a previous run

    # The manifest that governs this run is copied unchanged into the run directory.
    shutil.copy2(exp.manifest_path, run_dir / "experiment.toml")
    resolved = config.resolve(exp.manifest, repo_root)

    receipt: dict[str, Any] = {
        "exp_id": exp_id,
        "run_id": run_id,
        "status": "running",
        "reproduce_of": reproduce,
        "started_at": dt.datetime.now(dt.UTC).isoformat(),
        "ended_at": None,
        "host": socket.gethostname(),
        "python": platform.python_version(),
        "cwd": str(repo_root),
        "run_dir": str(run_dir),
        **git_identity(repo_root),
        "hardware": hardware_identity(),
        "env": {
            k: os.environ.get(k) for k in ("REMOTE_ROOT", "OUTPUT_ROOT", "UV_PROJECT_ENVIRONMENT")
        },
        "manifest": exp.manifest,
        "resolved_config": resolved,
        "result": None,
        "error": None,
    }
    write_receipt(run_dir, receipt)

    try:
        task = importlib.import_module(f"myproject.tasks.{exp.manifest['task']}")
        receipt["result"] = task.run(resolved, run_dir, exp.manifest)
        receipt["status"] = "complete"
    except BaseException as e:  # noqa: BLE001 - a failed run must still leave a receipt
        receipt["status"] = "failed"
        receipt["error"] = {
            "type": type(e).__name__,
            "message": str(e),
            "trace": traceback.format_exc(),
        }
        raise
    finally:
        receipt["ended_at"] = dt.datetime.now(dt.UTC).isoformat()
        write_receipt(run_dir, receipt)
        print(f"receipt: {run_dir / 'receipt.json'} status={receipt['status']}", file=sys.stderr)
    return run_dir

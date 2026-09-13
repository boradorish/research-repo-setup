"""Pipeline smoke task: records the environment and exercises the run-dir contract.

Records whether the remote root is a persistent mount, whether GPUs are visible, and
runs a trivial deterministic loop over the registered seeds.
"""

from __future__ import annotations

import json
import os
import random
import shutil
import subprocess
from pathlib import Path
from typing import Any


def _sh(cmd: list[str]) -> str:
    try:
        return subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT, timeout=30).strip()
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
        return f"<unavailable: {type(e).__name__}>"


def mount_info(path: str | None) -> dict[str, Any]:
    if not path:
        return {"path": None, "exists": False}
    p = Path(path)
    info: dict[str, Any] = {
        "path": path,
        "exists": p.exists(),
        "writable": os.access(path, os.W_OK),
    }
    if p.exists() and shutil.which("df"):
        info["df"] = _sh(["df", "-hP", str(p)])
        if shutil.which("findmnt"):
            info["findmnt"] = _sh(["findmnt", "-T", str(p), "-o", "SOURCE,FSTYPE,TARGET", "-n"])
    return info


def gpu_info() -> dict[str, Any]:
    out: dict[str, Any] = {
        "nvidia_smi": _sh(
            [
                "nvidia-smi",
                "--query-gpu=index,name,memory.used,memory.total",
                "--format=csv,noheader",
            ]
        )
    }
    try:
        import torch  # type: ignore[import-not-found]

        out["torch"] = torch.__version__
        out["cuda_available"] = torch.cuda.is_available()
        out["device_count"] = torch.cuda.device_count()
    except ImportError:
        out["torch"] = None
    return out


def run(cfg: dict[str, Any], run_dir: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    per_seed = {}
    for seed in manifest["seeds"]:
        rng = random.Random(seed)  # per-stream seed derived purely from the registered seed
        total = 0.0
        for _ in range(int(cfg["train"]["steps"])):
            total += rng.random()
        per_seed[str(seed)] = {"steps": cfg["train"]["steps"], "sum": total}

    report = {
        "remote_root": mount_info(os.environ.get("REMOTE_ROOT")),
        "output_root": mount_info(os.environ.get("OUTPUT_ROOT")),
        "gpu": gpu_info(),
        "per_seed": per_seed,
        "config_width": cfg["model"]["width"],
    }
    (run_dir / "smoke.json").write_text(json.dumps(report, indent=2))
    return {"seeds": list(per_seed), "steps": cfg["train"]["steps"]}

"""Upload a run's model/data artifacts to the Hugging Face Hub and stamp the receipt.

usage: uv run python scripts/hf_push.py --exp A-1 --run <run-id> [--paths ckpt/ data/]
Requires the `hf` extra and HF_TOKEN in the environment. The manifest's
[storage].hf_repo names the target repo; the receipt gains `hf = {repo, revision}`.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from myproject import registry, runner

REPO_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--exp", required=True)
    ap.add_argument("--run", required=True)
    ap.add_argument("--paths", nargs="*", default=None, help="run-dir relative paths; default all")
    ap.add_argument("--repo-type", default="model", choices=["model", "dataset"])
    a = ap.parse_args()

    exp = registry.load(REPO_ROOT, a.exp)
    hf_repo = exp.manifest.get("storage", {}).get("hf_repo", "")
    if not hf_repo:
        raise SystemExit(f"{a.exp}: set [storage].hf_repo in the manifest first")
    if not os.environ.get("HF_TOKEN"):
        raise SystemExit("HF_TOKEN is not set in the environment")
    try:
        from huggingface_hub import HfApi  # type: ignore[import-not-found]
    except ImportError as e:
        raise SystemExit("install the hf extra: uv sync --extra hf") from e

    run_dir = runner.output_root(REPO_ROOT) / a.exp / a.run
    receipt_path = run_dir / "receipt.json"
    if not receipt_path.is_file():
        raise SystemExit(f"no receipt at {receipt_path}")

    api = HfApi()
    api.create_repo(hf_repo, repo_type=a.repo_type, exist_ok=True)
    info = api.upload_folder(
        folder_path=str(run_dir),
        path_in_repo=f"{a.exp}/{a.run}",
        repo_id=hf_repo,
        repo_type=a.repo_type,
        allow_patterns=a.paths,
        commit_message=f"{a.exp} {a.run}",
    )
    receipt = json.loads(receipt_path.read_text())
    receipt["hf"] = {"repo": hf_repo, "type": a.repo_type, "revision": getattr(info, "oid", None)}
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True, default=str))
    print(f"uploaded {run_dir} -> {hf_repo}:{a.exp}/{a.run}; receipt stamped")


if __name__ == "__main__":
    main()

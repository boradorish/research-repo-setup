"""The one training entry point. Parses arguments and calls into the package."""

from __future__ import annotations

import argparse
from pathlib import Path

from myproject import runner

REPO_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    ap = argparse.ArgumentParser(description="Run a registered experiment.")
    ap.add_argument("--exp", required=True, help="experiment id, e.g. A-0")
    ap.add_argument("--run-id", default=None, help="override the generated run id")
    ap.add_argument(
        "--reproduce",
        default=None,
        metavar="RUN_ID",
        help="re-run a complete manifest unchanged; names the source run id",
    )
    args = ap.parse_args()
    run_dir = runner.run(REPO_ROOT, args.exp, reproduce=args.reproduce, run_id=args.run_id)
    print(run_dir)


if __name__ == "__main__":
    main()

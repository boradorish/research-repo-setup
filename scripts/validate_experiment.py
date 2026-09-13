"""Validate one manifest (or all). Exit code 1 on any contract violation."""

from __future__ import annotations

import sys
from pathlib import Path

from myproject import registry

REPO_ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str]) -> int:
    ids = argv or registry.list_ids(REPO_ROOT)
    rc = 0
    for exp_id in ids:
        try:
            exp = registry.load(REPO_ROOT, exp_id)
            print(
                f"OK   {exp_id}  status={exp.status} evidence={exp.evidence} verdict={exp.verdict}"
            )
        except registry.ManifestError as e:
            print(f"FAIL {e}")
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

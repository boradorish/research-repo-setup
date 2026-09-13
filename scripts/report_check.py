"""Validate one report (or all) against reports/README.md. Exit 1 on violation."""

from __future__ import annotations

import sys
from pathlib import Path

from myproject import reports

REPO_ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str]) -> int:
    slugs = argv or reports.list_slugs(REPO_ROOT)
    if not slugs:
        print("no reports yet")
        return 0
    rc = 0
    for slug in slugs:
        try:
            r = reports.load(REPO_ROOT, slug)
            print(f"OK   {slug}  status={r.meta['status']} experiments={r.meta['experiments']}")
        except reports.ReportError as e:
            print(f"FAIL {e}")
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

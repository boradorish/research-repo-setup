"""Regenerate experiments/LOG.md. With --check, exit 1 if the committed file is stale."""

from __future__ import annotations

import sys
from pathlib import Path

from myproject import explog

REPO_ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str]) -> int:
    target = REPO_ROOT / "experiments" / "LOG.md"
    fresh = explog.build(REPO_ROOT)
    if "--check" in argv:
        if not target.is_file() or target.read_text() != fresh:
            print("experiments/LOG.md is stale; run `make log`", file=sys.stderr)
            return 1
        print("experiments/LOG.md is current")
        return 0
    target.write_text(fresh)
    print(target)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

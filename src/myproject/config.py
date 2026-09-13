"""Load the base config and apply manifest deltas. Nothing else may mutate config."""

from __future__ import annotations

import copy
import tomllib
from pathlib import Path
from typing import Any


def load_base(path: str | Path) -> dict[str, Any]:
    with open(path, "rb") as f:
        return tomllib.load(f)


def apply_overrides(base: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    """Apply dotted-key deltas. Every key must already exist in base; new keys raise.

    This is what keeps configs/base.toml authoritative: a delta can change a value
    but cannot introduce a parameter the base does not declare.
    """
    cfg = copy.deepcopy(base)
    for dotted, value in _flatten(overrides).items():
        node = cfg
        parts = dotted.split(".")
        for p in parts[:-1]:
            if p not in node or not isinstance(node[p], dict):
                raise KeyError(f"override {dotted!r}: section {p!r} not in base config")
            node = node[p]
        leaf = parts[-1]
        if leaf not in node:
            raise KeyError(f"override {dotted!r}: key not declared in base config")
        node[leaf] = value
    return cfg


def _flatten(d: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in d.items():
        key = f"{prefix}{k}"
        if isinstance(v, dict):
            out.update(_flatten(v, key + "."))
        else:
            out[key] = v
    return out


def resolve(manifest: dict[str, Any], repo_root: str | Path) -> dict[str, Any]:
    base = load_base(Path(repo_root) / manifest["config"])
    return apply_overrides(base, manifest.get("overrides", {}))

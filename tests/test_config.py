import pytest

from myproject import config

BASE = {"model": {"width": 64}, "train": {"steps": 100, "lr": 1e-3}}


def test_override_existing_key():
    cfg = config.apply_overrides(BASE, {"train.steps": 3})
    assert cfg["train"]["steps"] == 3
    assert BASE["train"]["steps"] == 100  # base untouched


def test_nested_table_form():
    cfg = config.apply_overrides(BASE, {"train": {"lr": 0.5}})
    assert cfg["train"]["lr"] == 0.5


def test_undeclared_key_raises():
    with pytest.raises(KeyError):
        config.apply_overrides(BASE, {"train.momentum": 0.9})

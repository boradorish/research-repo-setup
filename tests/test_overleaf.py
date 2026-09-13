from pathlib import Path

import pytest

from myproject import overleaf

REPO = Path(__file__).resolve().parents[1]


def _policy(level: str) -> overleaf.Policy:
    p = overleaf.load_policy(REPO)
    p.level = level
    return p


def test_repo_policy_loads_and_defaults_to_read():
    p = overleaf.load_policy(REPO)
    assert p.level == "read"
    with pytest.raises(overleaf.PolicyError, match="링크"):
        overleaf.require_link(p)


def test_classify():
    p = _policy("gold")
    assert overleaf.classify(p, "author.tex") == "protected"
    assert overleaf.classify(p, "abstract.tex") == "front_matter"
    assert overleaf.classify(p, "agent/draft.tex") == "agent"
    assert overleaf.classify(p, "sections/appendix_b.tex") == "appendix"
    assert overleaf.classify(p, "figures/fig1.pdf") == "figure"
    assert overleaf.classify(p, "refs.bib") == "bib"
    assert overleaf.classify(p, "sections/intro.tex") == "body"


def test_read_blocks_everything():
    ch = [overleaf.Change("agent/x.tex", ["hi"], [])]
    assert overleaf.gate(_policy("read"), ch, set())


def test_bronze_allows_agent_dir_only():
    ok = [overleaf.Change("agent/x.tex", ["plain draft"], [])]
    assert overleaf.gate(_policy("bronze"), ok, set()) == []
    bad = [overleaf.Change("sections/appendix.tex", ["\\CLAUDE{x}"], [])]
    assert any("needs level silver" in v for v in overleaf.gate(_policy("bronze"), bad, set()))


def test_silver_appendix_needs_macro_and_real_cite():
    p = _policy("silver")
    no_macro = [overleaf.Change("sections/appendix.tex", ["We observe X."], [])]
    assert any("agent macro" in v for v in overleaf.gate(p, no_macro, set()))
    fake_cite = [overleaf.Change("sections/appendix.tex", ["\\CLAUDE{See \\cite{ghost2024}.}"], [])]
    assert any("ghost2024" in v for v in overleaf.gate(p, fake_cite, {"real2023"}))
    good = [overleaf.Change("sections/appendix.tex", ["\\CLAUDE{See \\cite{real2023}.}"], [])]
    assert overleaf.gate(p, good, {"real2023"}) == []
    body = [overleaf.Change("sections/intro.tex", ["\\CLAUDE{x}"], [])]
    assert any("needs level gold" in v for v in overleaf.gate(p, body, set()))


def test_gold_body_deletion_needs_del_macro_and_protected_stays():
    p = _policy("gold")
    silent = [overleaf.Change("sections/intro.tex", ["\\CLAUDE{new}"], ["old human sentence"])]
    assert any("DEL" in v for v in overleaf.gate(p, silent, set()))
    tracked = [
        overleaf.Change("sections/intro.tex", ["\\CLAUDEDEL{old}\\CLAUDE{new}"], ["old"]),
    ]
    assert overleaf.gate(p, tracked, set()) == []
    assert any(
        "protected" in v
        for v in overleaf.gate(p, [overleaf.Change("author.tex", ["\\CLAUDE{x}"], [])], set())
    )
    assert any(
        "needs level platinum" in v
        for v in overleaf.gate(p, [overleaf.Change("abstract.tex", ["\\CLAUDE{x}"], [])], set())
    )


def test_platinum_unlocks_front_matter_but_not_authors():
    p = _policy("platinum")
    assert overleaf.gate(p, [overleaf.Change("abstract.tex", ["\\CLAUDE{x}"], [])], set()) == []
    assert overleaf.gate(p, [overleaf.Change("main.tex", ["\\CLAUDE{x}"], [])], set()) == []
    assert any(
        "protected" in v
        for v in overleaf.gate(p, [overleaf.Change("author.tex", ["\\CLAUDE{x}"], [])], set())
    )


def test_bib_additions_only():
    p = _policy("silver")
    assert any(
        "never removed" in v
        for v in overleaf.gate(p, [overleaf.Change("refs.bib", [], ["@article{a,"])], set())
    )


def test_set_level_rewrites_and_logs(tmp_path):
    (tmp_path / "paper").mkdir()
    (tmp_path / "paper" / "overleaf.toml").write_text(
        '# c\nlevel = "read"   # note\nproject_url = ""\n'
    )
    (tmp_path / "WORKLOG.md").write_text("# W\n")
    old, new = overleaf.set_level(tmp_path, "gold")
    assert (old, new) == ("read", "gold")
    text = (tmp_path / "paper" / "overleaf.toml").read_text()
    assert 'level = "gold"   # note' in text and "# c" in text
    assert "read -> gold" in (tmp_path / "WORKLOG.md").read_text()
    with pytest.raises(overleaf.PolicyError):
        overleaf.set_level(tmp_path, "diamond")

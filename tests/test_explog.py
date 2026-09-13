from pathlib import Path

from myproject import explog

REPO = Path(__file__).resolve().parents[1]


def test_log_lists_smoke_and_emits_mermaid():
    text = explog.build(REPO)
    assert "## Series A" in text
    assert "[A-0](./A/A-0-smoke/)" in text
    assert "```mermaid" in text and "graph LR" in text
    assert 'A_0["A-0<br/>' in text

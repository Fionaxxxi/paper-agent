from types import SimpleNamespace

from tools.arxiv_tool import _is_withdrawn


def test_arxiv_withdrawn_records_are_rejected_before_ranking():
    withdrawn = SimpleNamespace(title="This paper has been withdrawn", summary="Withdrawn by the authors")
    active = SimpleNamespace(title="ReAct: Synergizing Reasoning and Acting", summary="We study agent reasoning.")
    assert _is_withdrawn(withdrawn) is True
    assert _is_withdrawn(active) is False

import pytest

from memory.llm_wiki import MarkdownWikiStore, publish_agent_result


def _verified_state(**overrides):
    state = {
        "trace_id": "trace-1",
        "conversation_id": "conversation-1",
        "query": "比较 ReAct 与 Reflexion",
        "task_type": "compare",
        "answer": "ReAct 结合推理与行动；Reflexion 使用语言反馈改进后续尝试。",
        "documents": [
            {
                "title": "ReAct",
                "source": "arxiv",
                "entry_id": "2210.03629",
                "pdf_url": "https://arxiv.org/abs/2210.03629",
            }
        ],
        "answer_verification": {
            "passed": True,
            "score": 1.0,
            "failure_types": [],
        },
        "answer_reflection_count": 0,
        "paper_metadata": {},
    }
    state.update(overrides)
    return state


def test_verified_research_note_writes_markdown_evidence_and_index(tmp_path):
    result = publish_agent_result(
        _verified_state(), root=tmp_path, enabled=True, allowed_task_types={"compare"}
    )

    note = (tmp_path / "notes" / "trace-1.md").read_text(encoding="utf-8")
    index = (tmp_path / "README.md").read_text(encoding="utf-8")

    assert result.published is True
    assert "## 研究结论" in note
    assert "**ReAct**" in note
    assert "2210.03629" in note
    assert "Verifier：`通过`" in note
    assert "notes/trace-1.md" in index


@pytest.mark.parametrize(
    ("state_update", "enabled", "reason"),
    [
        ({}, False, "auto_publish_disabled"),
        ({"task_type": "qa"}, True, "task_type_not_allowed"),
        ({"answer_verification": {"passed": False}}, True, "answer_not_verified"),
        ({"documents": []}, True, "no_traceable_evidence"),
        (
            {"paper_metadata": {"answer_mode": "insufficient_evidence"}},
            True,
            "insufficient_evidence",
        ),
    ],
)
def test_wiki_publish_gate_rejects_untrusted_or_disabled_results(
    tmp_path, state_update, enabled, reason
):
    result = publish_agent_result(
        _verified_state(**state_update),
        root=tmp_path,
        enabled=enabled,
        allowed_task_types={"compare"},
    )

    assert result.published is False
    assert result.reason == reason
    assert not (tmp_path / "notes").exists()


def test_republishing_same_trace_is_idempotent_in_index(tmp_path):
    store = MarkdownWikiStore(tmp_path)
    store.publish(_verified_state(answer="第一版结论"))
    store.publish(_verified_state(answer="修订后的结论"))

    note = store.read_note("trace-1")
    index = (tmp_path / "README.md").read_text(encoding="utf-8")

    assert "修订后的结论" in note
    assert "第一版结论" not in note
    assert index.count("notes/trace-1.md") == 1


def test_wiki_reader_sanitizes_note_identifier(tmp_path):
    store = MarkdownWikiStore(tmp_path)
    store.publish(_verified_state())

    assert store.read_note("../../trace-1") is None
    assert store.read_note("trace-1") is not None

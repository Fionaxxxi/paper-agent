import nodes.generate as generate_module
from nodes.metrics import metrics_node


def test_low_quality_stop_returns_evidence_safe_answer_without_llm(monkeypatch):
    monkeypatch.setattr(
        generate_module,
        "get_llm",
        lambda: (_ for _ in ()).throw(AssertionError("LLM must not be called")),
    )
    result = generate_module.generate_node({
        "query": "GraphRAG research",
        "documents": [{"title": "Weak candidate"}],
        "retrieval_outcome": "stopped_low_quality",
        "retrieval_stop_reason": "retry_budget_exhausted",
        "retrieval_replan": {"reason": "第二轮相关性仍然不足"},
        "paper_metadata": {},
    })

    assert "证据不足" in result["answer"]
    assert "Weak candidate" in result["answer"]
    assert result["paper_metadata"]["answer_mode"] == "insufficient_evidence"
    assert result["paper_metadata"]["generation_skipped"] is True
    assert "llm_call_count" not in result


def test_accepted_retrieval_keeps_normal_generation_path(monkeypatch):
    calls = []
    monkeypatch.setattr(generate_module, "attach_skill_context", lambda state: state)
    monkeypatch.setattr(
        generate_module,
        "get_skill",
        lambda state: type("Skill", (), {"need_llm": False, "run": lambda self, current: calls.append("skill") or {"answer": "normal"}})(),
    )

    result = generate_module.generate_node({"documents": [{"title": "Good"}], "retrieval_outcome": "accepted"})

    assert result["answer"] == "normal"
    assert calls == ["skill"]


def test_metrics_records_recovery_budget_and_generation_mode():
    result = metrics_node({
        "documents": [{"title": "Weak"}],
        "retry_count": 1,
        "retrieval_outcome": "stopped_low_quality",
        "retrieval_stop_reason": "retry_budget_exhausted",
        "paper_metadata": {"answer_mode": "insufficient_evidence", "generation_skipped": True},
        "node_timings": {},
    })
    metrics = result["paper_metadata"]["metrics"]

    assert metrics["retrieval_recovered"] is False
    assert metrics["retrieval_budget_exhausted"] is True
    assert metrics["answer_mode"] == "insufficient_evidence"
    assert metrics["generation_skipped"] is True

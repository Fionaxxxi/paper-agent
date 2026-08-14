import nodes.generate as generate_module

from nodes.research_coverage import research_coverage_node
from research.coverage import evaluate_evidence_coverage
from research.writer import build_writer_prompt


def store_with_claims(*claims):
    return {
        "enabled": True,
        "evidence": [{
            "evidence_id": "E-123456789abc", "title": "ReAct",
            "source": "arxiv", "locator": "doi:10.1/react",
            "snippet": "reasoning and acting", "task_ids": ["T1"],
        }],
        "claim_evidence_inputs": list(claims),
    }


def test_coverage_gate_passes_only_fully_supported_claims():
    """作用：所有依赖任务都有证据时允许Research Writer生成报告。"""
    result = evaluate_evidence_coverage(store_with_claims({
        "task_id": "T3", "claim": "综合比较", "evidence_ids": ["E-123456789abc"],
        "missing_dependency_task_ids": [], "coverage_ready": True,
    }))
    assert result["status"] == "passed"
    assert result["coverage_pct"] == 100.0
    assert result["writer_allowed"] is True


def test_coverage_gate_reports_partial_missing_dependencies():
    """作用：部分综合声明缺证据时保留缺失任务，供Writer显式降级。"""
    result = evaluate_evidence_coverage(store_with_claims(
        {"task_id": "T3", "claim": "方法", "coverage_ready": True},
        {"task_id": "T4", "claim": "趋势", "coverage_ready": False,
         "missing_dependency_task_ids": ["T2"]},
    ))
    assert result["status"] == "partial"
    assert result["coverage_pct"] == 50.0
    assert result["uncovered_claims"][0]["missing_dependency_task_ids"] == ["T2"]


def test_coverage_gate_blocks_when_no_claim_has_evidence():
    """作用：核心综合声明全部无证据时禁止调用Research Writer。"""
    result = evaluate_evidence_coverage(store_with_claims({
        "task_id": "T3", "claim": "研究结论", "coverage_ready": False,
        "missing_dependency_task_ids": ["T1", "T2"],
    }))
    assert result["status"] == "blocked"
    assert result["writer_allowed"] is False


def test_non_research_coverage_keeps_fast_path_available():
    """作用：未启用Evidence Store的普通任务不会被Coverage Gate阻断。"""
    result = research_coverage_node({"evidence_store": {"enabled": False}})
    assert result["research_coverage"]["status"] == "not_applicable"
    assert result["research_coverage"]["writer_allowed"] is True


def test_writer_prompt_contains_only_stable_evidence_contract():
    """作用：Writer收到稳定证据ID、定位符和未覆盖声明约束。"""
    prompt = build_writer_prompt("基础提示", {
        "evidence_store": store_with_claims(),
        "research_coverage": {"status": "partial", "coverage_pct": 50,
                              "uncovered_claims": [{"claim": "趋势"}]},
    })
    assert "E-123456789abc" in prompt
    assert "doi:10.1/react" in prompt
    assert "不得创造引用" in prompt
    assert "趋势" in prompt


def test_blocked_writer_skips_llm_and_returns_safe_answer(monkeypatch):
    """作用：覆盖率为零时零LLM返回明确的证据不足报告。"""
    monkeypatch.setattr(
        generate_module, "get_llm",
        lambda: (_ for _ in ()).throw(AssertionError("不应调用LLM")),
    )
    result = generate_module.generate_node({
        "task_level": "L3", "documents": [{"title": "候选"}],
        "research_analysis": {"primary_skill": "literature_review"},
        "research_coverage": {
            "enabled": True, "writer_allowed": False, "status": "blocked",
            "uncovered_claims": [{"claim": "趋势", "missing_dependency_task_ids": ["T2"]}],
        },
    })
    assert "研究报告生成已降级" in result["answer"]
    assert result["paper_metadata"]["generation_skipped"] is True
    assert result["paper_metadata"]["answer_mode"] == "research_coverage_blocked"

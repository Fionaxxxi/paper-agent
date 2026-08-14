import json

from eval_harness.llm_online_eval import (
    evaluate_case,
    load_dataset,
    materialize_cases,
    merge_case_results,
    regrade_report,
)


def test_online_dataset_is_frozen_unique_and_covers_three_levels():
    """作用：防止正式在线集被意外清空、重复编号或只覆盖复杂任务。"""
    dataset = load_dataset(__import__("pathlib").Path("eval_harness/datasets/llm_online_v1.json"))
    levels = {case.get("expected", {}).get("task_level") or case.get("task_level") for case in dataset["cases"]}
    assert dataset["frozen"] is True
    assert len(dataset["cases"]) == 7
    assert levels == {"L1", "L2", "L3"}


def test_core_online_dataset_has_30_stratified_cases_and_valid_fixtures():
    """作用：正式核心集必须达到30题并覆盖分析、规划和四类科研生成。"""
    dataset = load_dataset(__import__("pathlib").Path("eval_harness/datasets/llm_core_v1.json"))
    cases = materialize_cases(dataset)
    assert len(cases) == 30
    assert {case["category"] for case in cases} == {
        "research_analysis", "query_planning", "generation"
    }
    assert sum(case["category"] == "research_analysis" for case in cases) == 18
    assert sum(case["category"] == "query_planning" for case in cases) == 4
    assert sum(case["category"] == "generation" for case in cases) == 8
    generation_cases = [case for case in cases if case["category"] == "generation"]
    assert all(case.get("documents") for case in generation_cases)


def test_analysis_evaluator_reports_each_failed_check(monkeypatch):
    """作用：证明报告不会用总体文本长度掩盖错误等级、Skill 或调用预算。"""
    monkeypatch.setattr(
        "eval_harness.llm_online_eval.research_analyze_node",
        lambda state: {"task_level": "L2", "research_analysis": {"primary_skill": "qa"},
                       "research_plan_validation": {"valid": False}, "llm_call_count": 2,
                       "llm_failed_call_count": 1, "token_usage": 10},
    )
    case = {
        "id": "x", "category": "research_analysis", "description": "d", "query": "q",
        "expected": {"task_level": "L3", "primary_skill": "literature_review", "plan_valid": True,
                     "llm_calls_min": 1, "llm_calls_max": 1},
    }
    result = evaluate_case(case)
    assert result["passed"] is False
    assert set(result["checks"].values()) == {False}


def test_generation_evaluator_checks_route_structure_evidence_and_cost(monkeypatch):
    """作用：证明在线生成必须同时满足路由、内容、证据身份与调用次数。"""
    monkeypatch.setattr(
        "eval_harness.llm_online_eval.generate_node",
        lambda state: {"answer": "研究现状、研究空白与 ReAct 证据。" * 20,
                       "paper_metadata": {"skill_used": "literature_review"},
                       "llm_call_count": 1, "llm_failed_call_count": 0, "token_usage": 100},
    )
    case = {
        "id": "x", "category": "generation", "description": "d", "query": "q",
        "task_type": "recommend", "task_level": "L3", "primary_skill": "literature_review",
        "expected_skill": "literature_review", "min_answer_chars": 100,
        "required_any": [["研究现状"], ["研究空白"]], "required_titles": ["ReAct"],
        "documents": [{"title": "ReAct", "content": "e"}],
    }
    result = evaluate_case(case)
    assert result["passed"] is True
    assert all(result["checks"].values())


def test_report_only_regrades_existing_generation_without_calling_llm():
    """作用：修正判分规则后复用已付费原始输出，不重复调用模型。"""
    dataset = load_dataset(__import__("pathlib").Path("eval_harness/datasets/llm_online_v1.json"))
    case = next(c for c in dataset["cases"] if c["id"] == "generation_paper_critique")
    response = "claimed_contributions strengths weaknesses evidence_quality reproducibility_risks Reflexion " * 80
    report = {"summary": {}, "cases": [{
        "id": case["id"], "category": "generation", "passed": False,
        "response": response,
        "actual": {"skill_used": "paper_critique", "llm_calls": 1, "failed_calls": 0, "tokens": 100},
    }]}
    regraded = regrade_report(report, dataset)
    assert regraded["cases"][0]["passed"] is True
    assert regraded["summary"]["pass_rate_pct"] == 100.0


def test_provider_failure_is_not_reported_as_capability_failure(monkeypatch):
    """作用：模型服务调用失败必须与 Agent 输出质量失败分开统计。"""
    monkeypatch.setattr(
        "eval_harness.llm_online_eval.research_analyze_node",
        lambda state: {
            "task_level": "L3",
            "research_analysis": {"primary_skill": "literature_review"},
            "research_plan_validation": {"valid": True},
            "llm_call_count": 1,
            "llm_failed_call_count": 1,
            "token_usage": 0,
            "llm_usage": [{"success": False, "error_type": "RateLimitError"}],
        },
    )
    case = {
        "id": "provider", "category": "research_analysis",
        "description": "d", "query": "q",
        "expected": {
            "task_level": "L3", "primary_skill": "literature_review",
            "plan_valid": True, "llm_calls_min": 1, "llm_calls_max": 1,
        },
    }
    result = evaluate_case(case)
    assert result["failure_kind"] == "provider"
    assert result["actual"]["llm_error_types"] == ["RateLimitError"]


def test_provider_retry_does_not_overwrite_existing_capability_result():
    """作用：Provider重试失败只追加历史，不覆盖已有正式能力结论。"""
    baseline = [{"id": "c1", "passed": False, "failure_kind": "capability"}]
    retry = [{"id": "c1", "passed": False, "failure_kind": "provider"}]
    merged = merge_case_results(baseline, retry)
    assert merged[0]["failure_kind"] == "capability"
    assert merged[0]["attempts"][0]["failure_kind"] == "provider"

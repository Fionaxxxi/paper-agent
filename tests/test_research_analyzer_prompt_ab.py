from eval_harness.research_analyzer_prompt_ab import (
    DEFAULT_DATASET,
    compare,
    grade,
    load_dataset,
    offline_contract,
)
from research.analyzer import build_analyzer_prompt
from research.contracts import ResearchAnalysis


def test_few_shot_prompt_contains_boundary_examples_and_keeps_new_query_last():
    prompt = build_analyzer_prompt("新的复杂请求", "few_shot")

    assert "代表论文只是证据要求" in prompt
    assert "单主题方向分析" in prompt
    assert "2023年以来" in prompt
    assert prompt.rstrip().endswith("用户请求：新的复杂请求")


def test_zero_shot_prompt_has_no_examples_and_unknown_variant_is_rejected():
    prompt = build_analyzer_prompt("测试", "zero_shot")

    assert "示例1" not in prompt
    try:
        build_analyzer_prompt("测试", "unknown")
    except ValueError as error:
        assert "zero_shot、schema_guard 或 few_shot" in str(error)
    else:
        raise AssertionError("未知 Prompt variant 必须被拒绝")


def test_schema_guard_is_minimal_and_only_adds_json_type_constraints():
    zero = build_analyzer_prompt("测试", "zero_shot")
    guarded = build_analyzer_prompt("测试", "schema_guard")
    few = build_analyzer_prompt("测试", "few_shot")
    assert "source_requirements" in guarded
    assert "必须是 JSON 数组" in guarded
    assert "示例1" not in guarded
    assert len(zero) < len(guarded) < len(few)


def test_analyzer_prompt_ab_dataset_is_frozen_and_has_six_l3_boundaries():
    dataset = load_dataset(DEFAULT_DATASET)

    assert dataset["version"] == "1.0.0"
    assert len(dataset["cases"]) == 6
    assert all(case["expected_level"] == "L3" for case in dataset["cases"])


def test_analyzer_ab_grader_checks_objectives_dimensions_and_source_requirement():
    case = load_dataset(DEFAULT_DATASET)["cases"][0]
    analysis = ResearchAnalysis(
        intent="deep_research", task_level="L3", topic="Agent反思",
        objectives=["分析2023年以来趋势", "检索代表论文", "识别研究空白"],
        evaluation_dimensions=["反馈来源"], primary_skill="literature_review",
        requires_multiple_sources=True, requires_report=True,
        confidence=0.9, reason="多目标",
    )

    result = grade(case, analysis)

    assert result["passed"] is True
    assert result["missing_objective_terms"] == []


def test_ab_promotion_requires_quality_gain_and_bounded_token_cost():
    zero = {"pass_rate_pct": 66.67, "parse_rate_pct": 100.0,
            "token_usage": 1000, "average_latency_seconds": 1.0}
    good_few = {"pass_rate_pct": 83.33, "parse_rate_pct": 100.0,
                "token_usage": 3000, "average_latency_seconds": 1.2}
    expensive_few = {**good_few, "token_usage": 4000}
    low_absolute_few = {**good_few, "pass_rate_pct": 33.33}

    assert compare(zero, good_few)["decision"] == "promote"
    assert compare(zero, expensive_few)["decision"] == "keep_zero_shot"
    assert compare(zero, low_absolute_few)["decision"] == "keep_zero_shot"
    assert offline_contract(load_dataset(DEFAULT_DATASET))["summary"]["llm_call_count"] == 0

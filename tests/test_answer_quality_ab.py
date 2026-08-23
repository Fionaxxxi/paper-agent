from pathlib import Path

from eval_harness.answer_quality_ab import (
    grade_answer,
    load_dataset,
    regrade,
    rerun_paper_agent_case,
    write_report,
)


DATASET = Path("eval_harness/datasets/answer_quality_ab_v1.json")


def test_answer_quality_dataset_is_frozen_and_representative():
    """作用：保证正式回答质量集包含15至20题，且覆盖比较、总结、综合和证据不足。"""
    data = load_dataset(DATASET)
    assert len(data["cases"]) == 16
    assert {case["category"] for case in data["cases"]} == {
        "method_comparison", "paper_summary", "research_synthesis", "insufficient_evidence"
    }


def test_grader_rewards_grounded_dimensions_and_safe_insufficiency():
    """作用：答案覆盖维度、关键事实就近引用正确证据并披露不足时应得到满分。"""
    case = load_dataset(DATASET)["cases"][0]
    answer = (
        "Agent Loop：ReAct交替进行推理和行动 [E-react-loop]；Reflexion使用语言反馈 [E-reflexion]。\n"
        "记忆方式：Reflexion把语言反馈写入情景记忆 [E-reflexion]。\n"
        "适用边界：当前材料没有统一实验，性能胜负证据不足。"
    )
    result = grade_answer(case, answer)
    assert result["metrics"]["dimension_coverage_pct"] == 100
    assert result["metrics"]["claim_evidence_support_pct"] == 100
    assert result["metrics"]["insufficiency_disclosed"] is True


def test_grader_detects_missing_citations_and_forbidden_claims():
    """作用：只复述事实但没有Evidence引用，或写入人工禁止的无依据结论，不能冒充高质量回答。"""
    case = load_dataset(DATASET)["cases"][0]
    answer = "ReAct结合推理和行动。Reflexion使用语言反馈和情景记忆。Reflexion在所有任务上优于ReAct。"
    result = grade_answer(case, answer)
    assert result["passed"] is False
    assert result["metrics"]["claim_evidence_support_pct"] == 0
    assert result["metrics"]["forbidden_claim_count"] == 1


def test_report_can_be_regraded_without_new_llm_calls(tmp_path):
    """作用：评分规则调整后复用已付费原始回答，不重复消耗Token。"""
    data = load_dataset(DATASET)
    rows = []
    usage = {"llm_call_count": 1, "failed_llm_call_count": 0, "token_usage": 10, "duration_seconds": 1.0}
    for case in data["cases"]:
        answer = "证据不足。"
        graded = grade_answer(case, answer)
        rows.append({"id": case["id"], "category": case["category"], "query": case["query"],
                     "baseline": {"answer": answer, "usage": usage, **graded},
                     "paper_agent": {"answer": answer, "usage": usage, "validators": {}, **graded}})
    report = {"cases": rows, "baseline": {}, "paper_agent": {}, "comparison": {}}
    result = regrade(data, report)
    assert result["mode"] == "online_real_llm_ab_regraded"
    json_path, csv_path = write_report(result, tmp_path)
    assert json_path.exists() and csv_path.exists()
    assert "claim_evidence_support_pct" in csv_path.read_text(encoding="utf-8-sig")


def test_targeted_candidate_rerun_preserves_other_paid_answers(monkeypatch):
    """作用：供应商失败时只替换指定PaperAgent答案，其他已付费答案保持不变。"""
    data = load_dataset(DATASET)
    usage = {"llm_call_count": 1, "failed_llm_call_count": 0, "token_usage": 10, "duration_seconds": 1.0}
    rows = []
    for case in data["cases"]:
        graded = grade_answer(case, "证据不足。")
        item = {"answer": "证据不足。", "usage": usage, **graded}
        rows.append({"id": case["id"], "category": case["category"], "query": case["query"],
                     "baseline": dict(item), "paper_agent": {**item, "validators": {}}})
    monkeypatch.setattr(
        "eval_harness.answer_quality_ab._run_paper_agent",
        lambda case: ("replacement", usage, {}),
    )
    result = rerun_paper_agent_case(data, {"cases": rows}, data["cases"][0]["id"])
    assert result["cases"][0]["paper_agent"]["answer"] == "replacement"
    assert result["cases"][1]["paper_agent"]["answer"] == "证据不足。"
    assert result["cases"][0]["baseline"]["answer"] == "证据不足。"

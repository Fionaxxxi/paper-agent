from pathlib import Path

from eval_harness.research_report_eval import grade_report, load_dataset, merge_results, regrade_existing, run, write_report


DATASET = Path("eval_harness/datasets/research_report_v1.json")


def test_report_dataset_is_frozen_small_and_manually_grounded():
    """作用：首版保持4个代表案例，每项声明都有人工允许证据集合。"""
    dataset = load_dataset(DATASET)
    assert len(dataset["cases"]) == 4
    assert {case["skill"] for case in dataset["cases"]} == {"literature_review", "paper_critique"}
    assert all(claim["allowed_evidence_ids"] for case in dataset["cases"] for claim in case["claims"])


def test_grader_detects_hallucinated_citation_and_uncovered_claim():
    """作用：引用不存在或声明附近没有正确证据时不能通过。"""
    case = load_dataset(DATASET)["cases"][0]
    answer = "## 研究范围\nAgent。\n\n## 方法比较\n推理和行动、反馈与记忆存在差异 [E-fake0000000]。\n\n## 研究空白\n未知。\n\n## 证据索引\n[E-fake0000000]"
    result = grade_report(case, answer)
    assert result["passed"] is False
    assert result["metrics"]["hallucinated_citation_count"] == 1
    assert result["metrics"]["claim_coverage_pct"] < 100


def test_reference_reports_validate_harness_without_llm():
    """作用：人工参考报告用于验证评测器本身，不冒充模型成绩。"""
    report = run(load_dataset(DATASET), online=False)
    assert report["mode"] == "reference_harness_validation"
    assert report["summary"]["passed_count"] == 4
    assert report["summary"]["llm_call_count"] == 0
    assert report["summary"]["hallucinated_citation_count"] == 0
    assert all(row["citation_validation"]["enabled"] for row in report["cases"])


def test_report_writer_outputs_json_and_flat_csv(tmp_path):
    """作用：一键评测生成机器可读JSON和可直接用Excel查看的CSV表格。"""
    report = run(load_dataset(DATASET), online=False)
    json_path, csv_path = write_report(report, tmp_path)
    assert json_path.exists() and csv_path.exists()
    csv_text = csv_path.read_text(encoding="utf-8-sig")
    assert "claim_coverage_pct" in csv_text
    assert "review_agent_loop" in csv_text


def test_section_aliases_are_accepted_but_citations_must_be_sentence_local():
    """作用：接受合法中英文章节别名，但禁止跨bullet借用引用。"""
    case = load_dataset(DATASET)["cases"][0]
    answer = "## Scope\n范围。\n## Method Comparison\n推理和行动 [E-react0000001]\n反馈和记忆 [E-reflexion001]\n综合比较存在差异。\n## Research Gaps\n不足。\n## Evidence Index\n[E-react0000001] [E-reflexion001]"
    result = grade_report(case, answer)
    assert result["metrics"]["structure_completeness_pct"] == 100
    assert result["metrics"]["claim_coverage_pct"] < 100


def test_existing_paid_answers_can_be_regraded_without_llm():
    """作用：判分规则修复后复用原始报告，不重复产生模型费用。"""
    dataset = load_dataset(DATASET)
    original = run(dataset, online=False)
    regraded = regrade_existing(dataset, original)
    assert regraded["mode"] == "online_llm_regraded"
    assert regraded["summary"]["llm_call_count"] == 0


def test_targeted_rerun_merges_without_replacing_untouched_cases():
    """作用：Provider失败后只重跑指定题，成功题原文与Token保持不变。"""
    dataset = load_dataset(DATASET)
    existing = run(dataset, online=False)
    rerun = run(dataset, online=False, case_ids={"critique_react"})
    rerun["cases"][0]["answer"] = "replacement"
    merged = merge_results(existing, rerun)
    by_id = {row["id"]: row for row in merged["cases"]}
    assert by_id["critique_react"]["answer"] == "replacement"
    assert by_id["review_agent_loop"]["answer"] == existing["cases"][0]["answer"]
    assert merged["summary"]["case_count"] == 4

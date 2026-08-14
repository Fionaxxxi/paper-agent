from eval_harness.citation_repair_ab import run_ab
from eval_harness.research_report_eval import load_dataset, run
from nodes.research_citation_repair import research_citation_repair_node
from research.citation_repair import repair_uncited_synthesis
from validators.research_citation_validator import validate_research_citations


def base_state(line: str):
    return {
        "task_level": "L3",
        "answer": f"论文事实 [E-react]\n{line}\n## 证据索引\n[E-react] ReAct\n[E-reflexion] Reflexion",
        "research_coverage": {"enabled": True},
        "research_analysis": {"primary_skill": "literature_review"},
        "evidence_store": {"evidence": [
            {"evidence_id": "E-react", "title": "ReAct"},
            {"evidence_id": "E-reflexion", "title": "Reflexion"},
        ]},
    }


def test_unique_title_matches_repair_uncited_synthesis_without_llm():
    """作用：综合判断明确提到两篇论文时安全补全对应Evidence ID。"""
    state = base_state("综合判断：ReAct与Reflexion采用不同循环机制")
    state["citation_validation"] = validate_research_citations(state).model_dump(mode="python")
    result = repair_uncited_synthesis(state)
    assert result["status"] == "repaired"
    assert "[E-react] [E-reflexion]" in result["answer"]
    assert result["validation_after"]["passed"] is True


def test_no_title_match_is_left_for_bounded_reflection():
    """作用：无法唯一定位证据的综合判断保持原文，不猜测引用。"""
    state = base_state("综合判断：两种方法采用不同循环机制")
    state["citation_validation"] = validate_research_citations(state).model_dump(mode="python")
    result = repair_uncited_synthesis(state)
    assert result["status"] == "no_unique_match"
    assert result["repaired_line_count"] == 0


def test_other_citation_failures_disable_deterministic_repair():
    """作用：存在虚构ID等其他错误时不能只补一条引用后宣称修复。"""
    state = base_state("综合判断：ReAct与Reflexion不同 [E-fake]")
    state["citation_validation"] = validate_research_citations(state).model_dump(mode="python")
    result = repair_uncited_synthesis(state)
    assert result["status"] == "not_repairable"


def test_repair_node_updates_answer_and_validation_together():
    """作用：LangGraph节点原子更新修复答案、修复记录和Validator结果。"""
    state = base_state("综合判断：ReAct与Reflexion不同")
    state["citation_validation"] = validate_research_citations(state).model_dump(mode="python")
    update = research_citation_repair_node(state)
    assert update["citation_repair"]["status"] == "repaired"
    assert update["citation_validation"]["passed"] is True


def test_existing_online_style_report_can_run_zero_token_ab():
    """作用：复用已有报告比较修复前后，不产生模型Token。"""
    dataset = load_dataset(__import__("pathlib").Path("eval_harness/datasets/research_report_v1.json"))
    report = run(dataset, online=False)
    result = run_ab(dataset, report)
    assert result["summary"]["case_count"] == 4
    assert result["summary"]["token_usage_delta"] == 0

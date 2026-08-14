from nodes.research_citation_validate import research_citation_validate_node
from skills.paper_critique_skill import PaperCritiqueSkill
from validators.answer_quality_validator import verify_answer
from validators.research_citation_validator import validate_research_citations


def state(answer: str, skill: str = "literature_review"):
    return {
        "task_level": "L3", "answer": answer,
        "research_coverage": {"enabled": True},
        "research_analysis": {"primary_skill": skill},
        "evidence_store": {"evidence": [{"evidence_id": "E-valid000001"}]},
        "documents": [{"title": "ReAct"}], "task_type": "recommend",
    }


def test_valid_grounded_report_passes_citation_validator():
    """作用：稳定引用、相邻综合证据和证据索引齐全时通过。"""
    result = validate_research_citations(state(
        "## 方法比较\n论文事实 [E-valid000001]\n综合判断：存在差异 [E-valid000001]\n## 证据索引\n[E-valid000001] ReAct"
    ))
    assert result.passed is True
    assert result.failure_types == []


def test_unknown_evidence_id_is_rejected():
    """作用：Writer虚构Evidence ID时记录明确失败类型。"""
    result = validate_research_citations(state(
        "事实 [E-fake0000000]\n## 证据索引\n[E-fake0000000]"
    ))
    assert "invalid_evidence_id" in result.failure_types
    assert result.invalid_evidence_ids == ["E-fake0000000"]


def test_uncited_synthesis_is_not_allowed_to_borrow_other_line_citation():
    """作用：综合判断必须在同一行引用证据，不能借用上一条引用。"""
    result = validate_research_citations(state(
        "论文事实 [E-valid000001]\n综合判断：二者存在差异\n## 证据索引\n[E-valid000001]"
    ))
    assert "uncited_synthesis_claim" in result.failure_types


def test_paper_critique_material_gap_is_not_paper_defect():
    """作用：批判报告把材料缺失写成论文本身缺陷时阻断。"""
    result = validate_research_citations(state(
        "该贡献目前仅停留在理论构想，无法通过严格审查 [E-valid000001]\n## 证据索引\n[E-valid000001]",
        skill="paper_critique",
    ))
    assert "critique_evidence_overreach" in result.failure_types


def test_non_l3_answer_keeps_validator_not_applicable():
    """作用：普通回答不承担Research Citation Validator成本与约束。"""
    result = research_citation_validate_node({"task_level": "L1", "answer": "普通回答"})
    assert result["citation_validation"]["status"] == "not_applicable"
    assert result["citation_validation"]["passed"] is True


def test_citation_failure_enters_answer_verification_without_reflection():
    """作用：引用失败降低最终验证结果，但当前阶段不额外调用Reflection。"""
    checked = research_citation_validate_node(state(
        "ReAct 方法说明 [E-fake0000000]\n## 证据索引\n[E-fake0000000]"
    ))
    result = verify_answer({**state("ReAct 方法与方向说明足够完整。"), **checked})
    assert result.passed is False
    assert "invalid_evidence_id" in result.failure_types
    assert result.should_reflect is False


def test_paper_critique_prompt_distinguishes_material_from_paper_limitations():
    """作用：生成前明确禁止把输入片段缺失推断成论文缺陷。"""
    prompt = PaperCritiqueSkill().build_prompt({"query": "批判论文", "documents_text": "证据"})
    assert "不等于“论文本身没有做这项工作”" in prompt
    assert "材料局限" in prompt

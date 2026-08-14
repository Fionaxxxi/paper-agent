"""科研型结构化 Skill 的契约与路由测试。

每个用例同时说明能力意义，后续新增科研 Skill 时应在本文件补充对应契约、
路由边界和 Prompt 证据约束测试。
"""

import pytest
from pydantic import ValidationError

from research.contracts import LiteratureReviewOutput, PaperCritiqueOutput
from skills.literature_review_skill import LiteratureReviewSkill
from skills.paper_critique_skill import PaperCritiqueSkill
from skills.qa_skill import QASkill
from skills.router import get_skill


def test_structured_outputs_reject_missing_required_research_content():
    """代表结果：契约能阻止空综述或没有论文贡献的批判结果进入后续节点。"""
    with pytest.raises(ValidationError):
        LiteratureReviewOutput(topic="Agent", scope="", research_landscape=[])
    with pytest.raises(ValidationError):
        PaperCritiqueOutput(paper_title="ReAct", claimed_contributions=[])


def test_l3_primary_skill_routes_to_literature_review():
    """代表结果：通过 Policy Gate 的 L3 计划会实际选择综述 Skill。"""
    skill = get_skill({
        "task_level": "L3",
        "task_type": "recommend",
        "research_analysis": {"primary_skill": "literature_review"},
    })
    assert isinstance(skill, LiteratureReviewSkill)


def test_unknown_or_non_l3_research_skill_cannot_override_fast_path():
    """代表结果：未知 Skill 和普通 L1 问答不能借研究字段越过确定性路由。"""
    unknown = get_skill({
        "task_level": "L3", "task_type": "qa",
        "research_analysis": {"primary_skill": "unknown"},
    })
    simple = get_skill({
        "task_level": "L1", "task_type": "qa",
        "research_analysis": {"primary_skill": "literature_review"},
    })
    assert isinstance(unknown, QASkill)
    assert isinstance(simple, QASkill)


def test_research_prompts_expose_contract_and_evidence_guardrails():
    """代表结果：两个 Skill 都要求可定位证据并明确禁止无证据猜测。"""
    state = {
        "query": "调研 Agent 架构",
        "research_brief": {"topic": "Agent 架构"},
        "skill_context": {"documents_text": "ReAct | chunk-1 | https://example.test"},
    }
    review_prompt = LiteratureReviewSkill().build_prompt(state)
    critique_prompt = PaperCritiqueSkill().build_prompt(state)
    assert "research_landscape" in review_prompt
    assert "Chunk ID" in review_prompt and "不得" in review_prompt
    assert "reproducibility_risks" in critique_prompt
    assert "证据不足" in critique_prompt and "不得猜测" in critique_prompt

from agent.state import AgentState
from skills.base import BaseSkill
from skills.paper_summary_skill import PaperSummarySkill
from skills.paper_compare_skill import PaperCompareSkill
from skills.research_direction_skill import ResearchDirectionSkill
from skills.citation_skill import CitationSkill
from skills.qa_skill import QASkill
from skills.pdf_reading_skill import PDFReadingSkill
from skills.pdf_multimodal_skills import (
    FigureUnderstandingSkill,
    FormulaExplanationSkill,
    TableAnalysisSkill,
)
from skills.literature_review_skill import LiteratureReviewSkill
from skills.paper_critique_skill import PaperCritiqueSkill


RESEARCH_SKILLS = {
    "literature_review": LiteratureReviewSkill,
    "paper_critique": PaperCritiqueSkill,
}


PDF_SKILL_RULES = (
    (FormulaExplanationSkill, ("公式", "方程", "损失函数", "目标函数", "符号", "变量", "equation", "formula", "loss function")),
    (TableAnalysisSkill, ("表格", "图表", "实验结果", "指标", "消融", "数值", "table", "ablation", "benchmark result")),
    (FigureUnderstandingSkill, ("架构图", "流程图", "示意图", "模型图", "图中", "figure", "diagram", "pipeline")),
)


def get_pdf_skill(query: str) -> BaseSkill:
    normalized = (query or "").lower()
    for skill_class, keywords in PDF_SKILL_RULES:
        if any(keyword in normalized for keyword in keywords):
            return skill_class()
    return PDFReadingSkill()


def get_skill(state: AgentState) -> BaseSkill:
    """
    根据 Reason Node 识别出的 task_type 选择对应 Skill。
    """

    task_type = state.get("task_type", "qa")
    research_analysis = state.get("research_analysis", {})
    primary_skill = research_analysis.get("primary_skill", "")

    # Research Analyzer 已通过白名单 Policy Gate。只有 L3 研究任务可以
    # 覆盖普通 task_type 路由，避免简单问答被意外升级成昂贵的综述生成。
    if state.get("task_level") == "L3" and primary_skill in RESEARCH_SKILLS:
        return RESEARCH_SKILLS[primary_skill]()

    if task_type == "pdf_reading":
        return get_pdf_skill(state.get("query", ""))

    if task_type == "summarize":
        return PaperSummarySkill()

    if task_type == "compare":
        return PaperCompareSkill()

    if task_type == "recommend":
        return ResearchDirectionSkill()

    if task_type == "citation":
        return CitationSkill()

    return QASkill()

from agent.state import AgentState
from skills.base import BaseSkill
from skills.paper_summary_skill import PaperSummarySkill
from skills.paper_compare_skill import PaperCompareSkill
from skills.research_direction_skill import ResearchDirectionSkill
from skills.citation_skill import CitationSkill
from skills.qa_skill import QASkill


def get_skill(state: AgentState) -> BaseSkill:
    """
    根据 Reason Node 识别出的 task_type 选择对应 Skill。
    """

    task_type = state.get("task_type", "qa")

    if task_type == "summarize":
        return PaperSummarySkill()

    if task_type == "compare":
        return PaperCompareSkill()

    if task_type == "recommend":
        return ResearchDirectionSkill()

    if task_type == "citation":
        return CitationSkill()

    return QASkill()
from typing import Literal
from pydantic import BaseModel, Field


class ResearchAnalysis(BaseModel):
    intent: str
    task_level: Literal["L1", "L2", "L3"]
    topic: str
    objectives: list[str] = Field(min_length=1, max_length=6)
    evaluation_dimensions: list[str] = Field(default_factory=list, max_length=8)
    source_requirements: list[str] = Field(default_factory=lambda: ["academic_papers"])
    primary_skill: str = "qa"
    secondary_skills: list[str] = Field(default_factory=list)
    requires_retrieval: bool = True
    requires_multiple_sources: bool = False
    requires_report: bool = False
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str
    analysis_source: Literal["rule", "llm", "rule_fallback"] = "rule"


class ResearchBrief(BaseModel):
    objective: str
    topic: str
    task_level: Literal["L1", "L2", "L3"]
    research_questions: list[str] = Field(min_length=1, max_length=6)
    evaluation_dimensions: list[str] = Field(default_factory=list, max_length=8)
    allowed_sources: list[str] = Field(min_length=1)
    output_format: str = "chinese_markdown"
    citation_required: bool = True
    max_tasks: int = Field(default=5, ge=1, le=5)
    max_parallel_tasks: int = Field(default=2, ge=1, le=2)
    max_replan: int = Field(default=1, ge=0, le=1)
    max_report_reflection: int = Field(default=1, ge=0, le=1)


class ResearchTask(BaseModel):
    task_id: str
    objective: str
    query: str
    source: str
    depends_on: list[str] = Field(default_factory=list)
    expected_evidence: str


class ResearchPlan(BaseModel):
    objective: str
    tasks: list[ResearchTask] = Field(min_length=1, max_length=5)
    max_parallel_tasks: int = Field(default=2, ge=1, le=2)


class PlanValidation(BaseModel):
    valid: bool
    errors: list[str] = Field(default_factory=list)


class EvidenceReference(BaseModel):
    """研究结论引用的最小可追溯证据。"""

    title: str = Field(min_length=1)
    source: str = Field(min_length=1)
    locator: str = Field(min_length=1, description="URL、DOI、页码或 Chunk ID")


class LiteratureReviewOutput(BaseModel):
    """LiteratureReviewSkill 的目标输出契约。"""

    topic: str = Field(min_length=1)
    scope: str = Field(min_length=1)
    research_landscape: list[str] = Field(min_length=1, max_length=8)
    method_comparison: list[str] = Field(default_factory=list, max_length=8)
    research_gaps: list[str] = Field(default_factory=list, max_length=6)
    future_directions: list[str] = Field(default_factory=list, max_length=6)
    evidence: list[EvidenceReference] = Field(default_factory=list, max_length=20)
    limitations: list[str] = Field(default_factory=list, max_length=6)


class PaperCritiqueOutput(BaseModel):
    """PaperCritiqueSkill 的目标输出契约。"""

    paper_title: str = Field(min_length=1)
    claimed_contributions: list[str] = Field(min_length=1, max_length=8)
    strengths: list[str] = Field(default_factory=list, max_length=8)
    weaknesses: list[str] = Field(default_factory=list, max_length=8)
    evidence_quality: list[str] = Field(default_factory=list, max_length=6)
    reproducibility_risks: list[str] = Field(default_factory=list, max_length=6)
    follow_up_questions: list[str] = Field(default_factory=list, max_length=6)
    evidence: list[EvidenceReference] = Field(default_factory=list, max_length=12)

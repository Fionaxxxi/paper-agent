from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class AgentHandoff(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Literal["planner", "executor", "reviewer"]
    status: Literal["completed", "partial", "blocked"]
    input_refs: list[str] = Field(default_factory=list, max_length=12)
    output_summary: dict[str, Any] = Field(default_factory=dict)
    failure_reason: str = ""


class MultiAgentTrace(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool
    status: Literal["not_applicable", "completed", "partial", "blocked"]
    orchestration_mode: Literal["bounded_role_pipeline"] = "bounded_role_pipeline"
    max_review_loops: int = Field(default=0, ge=0, le=1)
    actual_review_loops: int = Field(default=0, ge=0, le=1)
    additional_llm_calls: int = Field(default=0, ge=0)
    handoffs: list[AgentHandoff] = Field(default_factory=list, max_length=3)

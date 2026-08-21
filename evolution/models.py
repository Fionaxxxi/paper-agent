from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class FailureRecord(BaseModel):
    case_id: str
    trace_id: str = ""
    module: str
    failure_type: str
    severity: Literal["low", "medium", "high", "critical"] = "medium"
    query: str = ""
    source: str = "eval"
    evidence: dict[str, Any] = Field(default_factory=dict)


class FailureDataset(BaseModel):
    dataset_version: str = "failure-dataset-v1"
    source_files: list[str] = Field(default_factory=list)
    records: list[FailureRecord] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)


class StrategyCandidate(BaseModel):
    candidate_id: str
    target_module: str
    change_type: Literal["prompt", "few_shot", "policy", "retrieval", "routing"]
    config_patch: dict[str, Any]
    rationale: str
    evidence_case_ids: list[str]
    risk_level: Literal["low", "medium", "high"] = "medium"
    requires_human_approval: bool = True
    auto_apply: bool = False


class Scorecard(BaseModel):
    version: str
    case_ids: list[str]
    pass_rate_pct: float
    critical_pass_rate_pct: float = 100.0
    safety_pass_rate_pct: float = 100.0
    provider_failure_count: int = 0
    average_tokens: float = 0.0
    p95_latency_seconds: float = 0.0
    per_case_passed: dict[str, bool] = Field(default_factory=dict)


class PromotionDecision(BaseModel):
    status: Literal["eligible_for_human_approval", "rejected", "manual_review"]
    gate_passed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    deltas: dict[str, float] = Field(default_factory=dict)
    regressed_case_ids: list[str] = Field(default_factory=list)
    requires_human_approval: bool = True
    auto_applied: bool = False

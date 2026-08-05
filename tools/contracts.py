"""Stable data contracts shared by native and future MCP tools."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ToolRiskLevel(str, Enum):
    READ_ONLY = "read_only"
    WRITE = "write"
    HIGH_RISK = "high_risk"


class ToolErrorCode(str, Enum):
    TOOL_NOT_FOUND = "TOOL_NOT_FOUND"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    INVALID_INPUT = "INVALID_INPUT"
    TIMEOUT = "TIMEOUT"
    EXECUTION_ERROR = "EXECUTION_ERROR"
    INVALID_OUTPUT = "INVALID_OUTPUT"


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 1
    retryable_error_codes: tuple[str, ...] = (
        ToolErrorCode.TIMEOUT.value,
        ToolErrorCode.EXECUTION_ERROR.value,
    )

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")


@dataclass(frozen=True)
class ToolSpec:
    name: str
    version: str
    description: str
    input_model: type[BaseModel]
    output_model: type[BaseModel]
    provider: str
    capabilities: tuple[str, ...] = field(default_factory=tuple)
    risk_level: ToolRiskLevel = ToolRiskLevel.READ_ONLY
    timeout_seconds: float = 30.0
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    cache_policy: str = "external"

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("tool name must not be empty")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than 0")


class ToolResult(BaseModel):
    success: bool
    tool_name: str
    tool_version: str = ""
    source: str = ""
    data: Any = None
    error_code: str = ""
    error_message: str = ""
    latency_seconds: float = Field(default=0.0, ge=0.0)
    attempt_count: int = Field(default=0, ge=0)
    cache_hit: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

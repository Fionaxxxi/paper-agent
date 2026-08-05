"""Authorization policy applied before every tool invocation."""

from __future__ import annotations

from dataclasses import dataclass, field

from tools.contracts import ToolRiskLevel, ToolSpec


@dataclass(frozen=True)
class ToolPolicy:
    allowed_risk_levels: frozenset[ToolRiskLevel] = field(
        default_factory=lambda: frozenset({ToolRiskLevel.READ_ONLY})
    )

    def authorize(self, spec: ToolSpec) -> tuple[bool, str]:
        if spec.risk_level in self.allowed_risk_levels:
            return True, ""
        return False, f"tool risk level is not allowed: {spec.risk_level.value}"

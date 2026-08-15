from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictPDFContract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PDFEvidenceScope(StrictPDFContract):
    pages: list[int] = Field(min_length=1, max_length=3)
    evidence_mode: Literal["text_only", "ocr_visual"]
    uncertainties: list[str] = Field(default_factory=list, max_length=8)


class FigureUnderstandingOutput(StrictPDFContract):
    target_found: bool = True
    summary: str = Field(min_length=1)
    components: list[str] = Field(default_factory=list, max_length=12)
    relationships: list[str] = Field(default_factory=list, max_length=12)
    evidence_scope: PDFEvidenceScope

    @model_validator(mode="after")
    def validate_target_evidence(self):
        if self.target_found and not self.components:
            raise ValueError("target_found=true 时必须提供至少一个图中组件")
        if not self.target_found and not self.evidence_scope.uncertainties:
            raise ValueError("未发现目标图时必须说明识别限制")
        return self


class TableMetric(StrictPDFContract):
    name: str = Field(min_length=1)
    direction: Literal["higher_better", "lower_better", "unknown"] = "unknown"


class TableAnalysisOutput(StrictPDFContract):
    table_purpose: str = Field(min_length=1)
    metrics: list[TableMetric] = Field(default_factory=list, max_length=12)
    comparisons: list[str] = Field(default_factory=list, max_length=12)
    conclusions: list[str] = Field(default_factory=list, max_length=8)
    evidence_scope: PDFEvidenceScope


class FormulaSymbol(StrictPDFContract):
    symbol: str = Field(min_length=1)
    meaning: str = Field(min_length=1)


class FormulaExplanationOutput(StrictPDFContract):
    formula: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    symbols: list[FormulaSymbol] = Field(default_factory=list, max_length=20)
    computation: list[str] = Field(default_factory=list, max_length=12)
    evidence_scope: PDFEvidenceScope

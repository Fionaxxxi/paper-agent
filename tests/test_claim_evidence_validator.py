import pytest

from nodes.claim_evidence_validate import claim_evidence_validate_node
from validators.answer_quality_validator import verify_answer
from validators.claim_evidence_validator import validate_claim_evidence


def _state(answer: str, evidence: list[dict] | None = None):
    return {
        "task_level": "L3",
        "task_type": "recommend",
        "answer": answer,
        "research_coverage": {"enabled": True},
        "evidence_store": {
            "enabled": True,
            "evidence": evidence or [
                {"evidence_id": "E-react", "title": "ReAct", "snippet": "ReAct interleaves reasoning and acting."},
                {"evidence_id": "E-reflexion", "title": "Reflexion", "snippet": "Reflexion uses verbal feedback and episodic memory."},
            ],
        },
        "documents": [{"title": "ReAct"}],
    }


def test_claim_evidence_validator_reports_supported_and_partial_claims():
    result = validate_claim_evidence(_state(
        "ReAct 将推理与行动交替执行 [E-react]\n"
        "ReAct 将推理与行动交替执行 [E-react] [E-reflexion]\n"
        "## 证据索引\n[E-react] ReAct\n[E-reflexion] Reflexion"
    ))

    assert [claim.status for claim in result.claims] == ["supported", "partial"]
    assert result.passed is True
    assert result.status == "partial"
    assert result.support_rate_pct == 50.0


@pytest.mark.parametrize(
    ("snippet", "expected_status", "expected_failure"),
    [
        ("Unrelated database benchmark.", "insufficient", "claim_evidence_insufficient"),
        ("ReAct evidence does not support this claim.", "contradicted", "claim_evidence_contradicted"),
    ],
)
def test_claim_evidence_validator_blocks_insufficient_or_contradicted_claims(
    snippet, expected_status, expected_failure
):
    result = validate_claim_evidence(_state(
        "ReAct 能稳定提升所有研究任务 [E-react]\n## 证据索引\n[E-react] ReAct",
        [{"evidence_id": "E-react", "title": "Evidence", "snippet": snippet}],
    ))

    assert result.claims[0].status == expected_status
    assert result.passed is False
    assert expected_failure in result.failure_types


def test_claim_evidence_node_exposes_metrics_without_extra_llm():
    result = claim_evidence_validate_node(_state(
        "ReAct 将推理与行动交替执行 [E-react]\n## 证据索引\n[E-react] ReAct"
    ))

    assert result["claim_evidence_validation"]["passed"] is True
    assert result["paper_metadata"]["claim_evidence_support_rate_pct"] == 100.0


def test_claim_evidence_failure_blocks_answer_without_reflection():
    state = _state("ReAct 能解决所有任务 [E-react]。这是一个完整的研究方向判断。")
    checked = claim_evidence_validate_node({
        **state,
        "evidence_store": {"enabled": True, "evidence": [
            {"evidence_id": "E-react", "title": "Other Evidence", "snippet": "Unrelated database benchmark."}
        ]},
    })
    result = verify_answer({**state, **checked})

    assert result.passed is False
    assert "claim_evidence_insufficient" in result.failure_types
    assert result.should_reflect is False

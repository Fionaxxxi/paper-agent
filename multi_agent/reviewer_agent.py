from multi_agent.contracts import AgentHandoff


def build_reviewer_handoff(state: dict) -> AgentHandoff:
    answer = state.get("answer_verification", {})
    citation = state.get("citation_validation", {})
    citation_passed = not citation.get("enabled") or citation.get("passed", False)
    passed = bool(answer.get("passed")) and citation_passed
    failures = list(answer.get("failure_types", []))
    return AgentHandoff(
        role="reviewer",
        status="completed" if passed else "blocked",
        input_refs=["answer", "evidence_store", "citation_validation"],
        output_summary={
            "answer_passed": bool(answer.get("passed")),
            "citation_passed": citation_passed,
            "citation_repair_status": state.get("citation_repair", {}).get("status", "not_applicable"),
            "failure_types": failures,
        },
        failure_reason="" if passed else ",".join(failures) or "review_failed",
    )

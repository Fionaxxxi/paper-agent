from agent.state import AgentState
from core.config import settings
from core.llm_usage import TrackedLLMError, build_llm_usage_update
from research.analyzer import (
    analyze_with_llm,
    enforce_analysis_policy,
    rule_analyze,
    should_use_llm,
)
from research.planning import build_research_brief, build_research_plan, validate_research_plan


def research_analyze_node(state: AgentState) -> AgentState:
    rule_analysis = rule_analyze(state.get("query", ""))
    analysis = rule_analysis
    usage_update = {}
    if settings.RESEARCH_ANALYSIS_WITH_LLM and should_use_llm(analysis):
        try:
            candidate, usage = analyze_with_llm(state.get("query", ""))
            analysis = enforce_analysis_policy(rule_analysis, candidate)
            usage_update = build_llm_usage_update(state, usage)
        except TrackedLLMError as error:
            usage_update = build_llm_usage_update(state, error.usage_record)
            analysis = analysis.model_copy(update={"analysis_source": "rule_fallback"})
        except Exception:
            analysis = analysis.model_copy(update={"analysis_source": "rule_fallback"})
    brief = build_research_brief(analysis)
    plan = build_research_plan(brief)
    validation = validate_research_plan(
        plan,
        allowed_sources={*brief.allowed_sources, "evidence_store"},
    )
    return {
        **usage_update,
        "research_analysis": analysis.model_dump(mode="python"),
        "research_brief": brief.model_dump(mode="python"),
        "research_plan": plan.model_dump(mode="python"),
        "research_plan_validation": validation.model_dump(mode="python"),
        "task_level": analysis.task_level,
        "paper_metadata": {
            **state.get("paper_metadata", {}), "task_level": analysis.task_level,
            "research_intent": analysis.intent,
            "research_analysis_source": analysis.analysis_source,
            "research_plan_valid": validation.valid,
        },
    }

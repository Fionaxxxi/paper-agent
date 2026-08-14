from research.analyzer import analyze_with_llm, enforce_analysis_policy, rule_analyze
from research.contracts import ResearchAnalysis
from research.contracts import ResearchPlan, ResearchTask
from research.planning import build_research_brief, build_research_plan, validate_research_plan
import nodes.research_analyze as analyze_node_module


def test_rule_analyzer_separates_simple_comparison_and_deep_research():
    cases = [
        ("检索有关 RAG 的论文", "L1"),
        ("找一下 ReAct 论文", "L1"),
        ("RAG 是什么？", "L1"),
        ("总结这篇 Agent 论文", "L1"),
        ("比较 ReAct 和 Reflexion", "L2"),
        ("Agent Memory 的未来趋势是什么", "L2"),
        ("有哪些有价值的工具型 Agent 方向", "L2"),
        ("对比 GraphRAG 和普通 RAG", "L2"),
        ("调研 Agent 架构的前景、价值和代表论文", "L3"),
        ("比较 Agent Loop 的趋势与研究空白", "L3"),
        ("系统调研 Agent Memory 的代表论文和未来方向", "L3"),
        ("写一份 Agent 架构综述并分析研究空白", "L3"),
    ]
    predictions = [rule_analyze(query).task_level for query, _ in cases]
    expected = [level for _, level in cases]

    assert predictions == expected
    simple_false_l3 = sum(
        prediction == "L3"
        for prediction, (_, level) in zip(predictions, cases)
        if level == "L1"
    )
    assert simple_false_l3 == 0


def test_representative_papers_alone_remains_a_simple_search():
    """“代表论文”是证据要求，不应单独把一次检索升级为方向研究。"""
    result = rule_analyze("检索有关 RAG 的代表论文")
    assert result.task_level == "L1"
    assert result.primary_skill == "qa"


def test_l3_rule_fallback_preserves_time_trend_and_gap_constraints():
    """结构化模型不可用时，时间范围、趋势和研究空白仍进入目标。"""
    result = rule_analyze("调研2023年以来Agent反思机制的趋势、代表论文和研究空白")
    objective_text = " ".join(result.objectives)
    assert result.task_level == "L3"
    assert "2023年以来" in objective_text
    assert "趋势" in objective_text
    assert "代表论文" in objective_text
    assert "研究空白" in objective_text


def test_llm_analysis_accepts_thinking_text_and_fenced_json(monkeypatch):
    """兼容模型在严格 JSON 外附带 thinking 标签和 Markdown 代码块。"""
    payload = {
        "intent": "deep_research", "task_level": "L3", "topic": "Agent",
        "objectives": ["梳理方向"], "evaluation_dimensions": ["价值"],
        "source_requirements": ["academic_papers"],
        "primary_skill": "literature_review", "secondary_skills": [],
        "requires_retrieval": True, "requires_multiple_sources": True,
        "requires_report": True, "confidence": 0.9, "reason": "复杂任务",
    }

    class FakeResponse:
        content = "<think>internal</think>说明文字\n```json\n" + __import__("json").dumps(payload) + "\n```"
        usage_metadata = {"input_tokens": 10, "output_tokens": 20, "total_tokens": 30}
        response_metadata = {}

    class FakeLLM:
        def invoke(self, prompt):
            return FakeResponse()

    monkeypatch.setattr("research.analyzer.ChatOpenAI", lambda **kwargs: FakeLLM())
    analysis, usage = analyze_with_llm("复杂研究任务")
    assert analysis.task_level == "L3"
    assert analysis.primary_skill == "literature_review"
    assert usage["total_tokens"] == 30

    deep = rule_analyze("调研有价值和前景的 Agent 架构方向、代表论文与研究空白")
    assert deep.task_level == "L3"
    assert deep.primary_skill == "literature_review"
    assert "未来潜力" in deep.evaluation_dimensions


def test_simple_request_does_not_call_llm(monkeypatch):
    monkeypatch.setattr(
        analyze_node_module,
        "analyze_with_llm",
        lambda _: (_ for _ in ()).throw(AssertionError("simple request must not call LLM")),
    )
    result = analyze_node_module.research_analyze_node({"query": "检索 RAG 论文"})
    assert result["task_level"] == "L1"
    assert result["research_analysis"]["analysis_source"] == "rule"
    assert result.get("llm_call_count", 0) == 0


def test_complex_request_uses_structured_llm_analysis_and_builds_valid_plan(monkeypatch):
    analysis = rule_analyze("调研有价值和前景的 Agent 架构方向、代表论文与研究空白").model_copy(
        update={"analysis_source": "llm", "confidence": 0.93}
    )
    usage = {"node_name": "research_analyze", "model_name": "fake", "success": True,
             "input_tokens": 20, "output_tokens": 10, "total_tokens": 30,
             "token_usage_available": True, "latency_seconds": 0.01, "error_type": ""}
    monkeypatch.setattr(analyze_node_module, "analyze_with_llm", lambda _: (analysis, usage))

    result = analyze_node_module.research_analyze_node({"query": analysis.topic, "llm_usage": []})

    assert result["research_analysis"]["analysis_source"] == "llm"
    assert result["research_plan_validation"]["valid"] is True
    assert len(result["research_plan"]["tasks"]) == 5
    assert result["token_usage"] == 30


def test_llm_analysis_failure_falls_back_to_bounded_rule_plan(monkeypatch):
    monkeypatch.setattr(
        analyze_node_module, "analyze_with_llm", lambda _: (_ for _ in ()).throw(ValueError("bad json"))
    )
    result = analyze_node_module.research_analyze_node(
        {"query": "调研有价值和前景的 Agent 架构方向、代表论文与研究空白"}
    )
    assert result["research_analysis"]["analysis_source"] == "rule_fallback"
    assert result["research_plan_validation"]["valid"] is True


def test_plan_validator_rejects_cycles_unknown_sources_and_dependencies():
    plan = ResearchPlan(
        objective="invalid",
        tasks=[
            ResearchTask(task_id="T1", objective="A", query="a", source="unknown",
                         depends_on=["T2"], expected_evidence="e"),
            ResearchTask(task_id="T2", objective="B", query="b", source="arxiv",
                         depends_on=["T1", "T9"], expected_evidence="e"),
        ],
    )
    result = validate_research_plan(plan)
    assert result.valid is False
    assert "cyclic_dependencies" in result.errors
    assert any(error.startswith("source_not_allowed") for error in result.errors)
    assert any(error.startswith("unknown_dependency") for error in result.errors)


def test_brief_and_plan_respect_task_and_parallel_budgets():
    analysis = rule_analyze("调研有价值和前景的 Agent 架构方向、代表论文与研究空白")
    brief = build_research_brief(analysis)
    plan = build_research_plan(brief)
    assert brief.max_tasks == 5
    assert brief.max_parallel_tasks == 2
    assert len(plan.tasks) <= 5
    assert plan.max_parallel_tasks == 2


def test_policy_gate_prevents_llm_downgrade_and_unknown_skills():
    rule = rule_analyze("调研有价值和前景的 Agent 架构方向、代表论文与研究空白")
    candidate = ResearchAnalysis(
        intent="chat",
        task_level="L1",
        topic="Agent 架构",
        objectives=["随便回答"],
        primary_skill="unregistered_skill",
        secondary_skills=["paper_compare", "unsafe_skill"],
        requires_retrieval=False,
        requires_report=False,
        confidence=0.9,
        reason="fake",
        analysis_source="llm",
    )

    result = enforce_analysis_policy(rule, candidate)

    assert result.task_level == "L3"
    assert result.primary_skill == "literature_review"
    assert result.secondary_skills == ["paper_compare"]
    assert result.requires_retrieval is True
    assert result.requires_report is True


def test_plan_validator_applies_current_brief_source_allowlist():
    plan = ResearchPlan(
        objective="source policy",
        tasks=[
            ResearchTask(
                task_id="T1",
                objective="search local",
                query="agent",
                source="local_rag",
                expected_evidence="evidence",
            )
        ],
    )

    result = validate_research_plan(plan, allowed_sources={"arxiv"})

    assert result.valid is False
    assert result.errors == ["source_not_allowed:T1:local_rag"]

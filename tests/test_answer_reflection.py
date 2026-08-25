from types import SimpleNamespace

import agent.graph as graph_module
import nodes.answer_reflect as reflect_module
import nodes.answer_verify as verify_node_module
from nodes.answer_verify import answer_verify_node, route_after_answer_verify
from nodes.metrics import metrics_node
from validators.answer_quality_validator import verify_answer


def test_verifier_accepts_a_grounded_structured_answer():
    result = verify_answer(
        {
            "task_type": "compare",
            "documents": [{"title": "ReAct"}, {"title": "Reflexion"}],
            "answer": (
                "ReAct 与 Reflexion 的对比显示，两者都面向语言智能体。"
                "核心差异在于 ReAct 交替执行推理与行动，而 Reflexion 使用语言反馈改进后续尝试。"
            ),
        }
    )

    assert result.passed is True
    assert result.score == 1.0
    assert result.should_reflect is False


def test_verifier_only_requests_reflection_when_repair_evidence_exists():
    repairable = verify_answer(
        {"answer": "太短", "documents": [{"title": "ReAct", "content": "evidence"}]}
    )
    unsupported = verify_answer({"answer": "太短", "documents": []})

    assert repairable.should_reflect is True
    assert "answer_too_short" in repairable.failure_types
    assert unsupported.should_reflect is False
    assert unsupported.stop_reason == "no_repair_context"


def test_insufficient_evidence_answer_does_not_enter_reflection():
    result = verify_answer(
        {
            "answer": "证据不足，已停止。",
            "documents": [{"title": "Weak"}],
            "paper_metadata": {"answer_mode": "insufficient_evidence"},
        }
    )

    assert result.passed is True
    assert result.stop_reason == "insufficient_evidence_already_disclosed"


def test_reflection_feature_flag_keeps_verification_but_disables_repair(monkeypatch):
    monkeypatch.setattr(
        verify_node_module.settings, "ANSWER_REFLECTION_ENABLED", False
    )
    state = {
        "answer_verification": {"passed": False, "should_reflect": True},
        "answer_reflection_count": 0,
    }

    assert route_after_answer_verify(state) == "finish"


def test_reflection_uses_one_tracked_llm_call_and_keeps_evidence_in_prompt(monkeypatch):
    class FakeLLM:
        def invoke(self, prompt):
            assert "ReAct" in prompt
            return SimpleNamespace(
                content="根据 ReAct 论文，模型通过交替生成推理轨迹和行动来完成任务。",
                usage_metadata={"input_tokens": 20, "output_tokens": 10, "total_tokens": 30},
                response_metadata={},
            )

    monkeypatch.setattr(reflect_module, "get_llm", lambda: FakeLLM())
    result = reflect_module.answer_reflect_node(
        {
            "query": "ReAct 做了什么？",
            "answer": "太短",
            "documents": [{"title": "ReAct", "content": "Reasoning and acting."}],
            "answer_verification": {
                "failure_types": ["answer_too_short"],
                "issues": ["答案过短"],
            },
            "llm_usage": [],
        }
    )

    assert result["answer_reflection_count"] == 1
    assert result["answer_reflection"]["status"] == "completed"
    assert result["llm_call_count"] == 1
    assert result["token_usage"] == 30


def test_reflection_does_not_replace_answer_when_model_hits_output_limit(monkeypatch):
    original = "## 完整分析\n" + ("GraphRAG 证据充分的完整流程说明。" * 40)

    class TruncatedLLM:
        def invoke(self, prompt):
            return SimpleNamespace(
                content="### 针对 Figure 1 的解释\n\n1. 输入：Source Documents；\n2. 最终",
                usage_metadata={"input_tokens": 100, "output_tokens": 50, "total_tokens": 150},
                response_metadata={"finish_reason": "length"},
            )

    monkeypatch.setattr(reflect_module, "get_llm", lambda: TruncatedLLM())
    result = reflect_module.answer_reflect_node({
        "query": "解释这篇论文的架构图",
        "answer": original,
        "documents": [{"title": "GraphRAG", "content": "evidence"}],
        "answer_verification": {"failure_types": ["missing_evidence_reference"], "issues": ["补充引用"]},
        "llm_usage": [],
    })

    assert result["answer"] == original
    assert result["answer_reflection"]["status"] == "rejected_incomplete"
    assert result["answer_reflection"]["rejection_reason"] == "finish_reason_length"


def test_reflection_rejects_materially_shorter_rewrite_without_finish_reason(monkeypatch):
    original = "完整论文分析。" * 80

    class ShortLLM:
        def invoke(self, prompt):
            return SimpleNamespace(
                content="1. 输入：Source Documents；\n2. 最终",
                usage_metadata={},
                response_metadata={},
            )

    monkeypatch.setattr(reflect_module, "get_llm", lambda: ShortLLM())
    result = reflect_module.answer_reflect_node({
        "query": "解释架构图",
        "answer": original,
        "documents": [{"title": "GraphRAG", "content": "evidence"}],
        "answer_verification": {"failure_types": ["answer_too_short"], "issues": []},
        "llm_usage": [],
    })

    assert result["answer"] == original
    assert result["answer_reflection"]["rejection_reason"] == "materially_shorter_than_original"


def test_second_verification_restores_initial_answer_when_score_does_not_improve():
    initial = answer_verify_node(
        {"answer": "初始答案", "documents": [{"title": "ReAct"}]}
    )
    second = answer_verify_node(
        {
            "answer": "同样很短",
            "answer_before_reflection": "初始答案",
            "documents": [{"title": "ReAct"}],
            "answer_reflection_count": 1,
            "answer_initial_score": initial["answer_initial_score"],
            "answer_initial_verification": initial["answer_initial_verification"],
        }
    )

    assert second["answer"] == "初始答案"
    assert second["answer_reflection_restored"] is True
    assert second["answer_stop_reason"] == "reflection_no_improvement"
    assert route_after_answer_verify({**second, "answer_reflection_count": 1}) == "finish"


def test_graph_runs_answer_reflection_at_most_once(monkeypatch):
    calls = []

    def node(name, update):
        def run(state):
            calls.append(name)
            return update(state) if callable(update) else update
        return run

    monkeypatch.setattr(graph_module, "query_rewrite_node", node("rewrite", {"rewritten_query": "q"}))
    monkeypatch.setattr(graph_module, "query_plan_node", node("plan", {"sub_queries": ["q"]}))
    monkeypatch.setattr(graph_module, "retrieve_node", node("retrieve", {"documents": [{"title": "ReAct"}]}))
    monkeypatch.setattr(graph_module, "evaluate_node", node("evaluate", {"retrieval_score": 1.0}))
    monkeypatch.setattr(graph_module, "reason_node", node("reason", {"task_type": "qa"}))
    monkeypatch.setattr(graph_module, "generate_node", node("generate", {"answer": "短答案"}))
    monkeypatch.setattr(
        graph_module,
        "answer_verify_node",
        node(
            "verify",
            lambda state: {
                "answer_verification": {
                    "passed": state.get("answer_reflection_count", 0) == 1,
                    "should_reflect": state.get("answer_reflection_count", 0) == 0,
                }
            },
        ),
    )
    monkeypatch.setattr(
        graph_module,
        "answer_reflect_node",
        node("reflect", {"answer": "修复后的完整答案", "answer_reflection_count": 1}),
    )
    monkeypatch.setattr(graph_module, "metrics_node", node("metrics", {}))

    result = graph_module.build_graph().invoke({"query": "研究 ReAct", "retry_count": 0})

    assert calls.count("reflect") == 1
    assert calls[-3:] == ["reflect", "verify", "metrics"]
    assert result["answer"] == "修复后的完整答案"


def test_metrics_records_answer_loop_quality_and_stop_outcome():
    result = metrics_node(
        {
            "answer_verification": {
                "passed": False,
                "score": 0.8,
                "failure_types": ["missing_evidence_reference"],
            },
            "answer_reflection_count": 1,
            "answer_reflection": {"status": "completed"},
            "answer_reflection_restored": True,
            "answer_stop_reason": "reflection_no_improvement",
            "paper_metadata": {},
            "node_timings": {},
        }
    )
    metrics = result["paper_metadata"]["metrics"]

    assert metrics["answer_verification_score"] == 0.8
    assert metrics["answer_reflection_count"] == 1
    assert metrics["answer_reflection_restored"] is True
    assert metrics["answer_stop_reason"] == "reflection_no_improvement"

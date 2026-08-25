from types import SimpleNamespace

import nodes.evaluate as evaluate_module
import nodes.generate as generate_module
import nodes.reason as reason_module


class FakeLLM:
    def __init__(self, content, input_tokens=10, output_tokens=2):
        self.call_count = 0
        self.response = SimpleNamespace(
            content=content,
            usage_metadata={
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
            },
            response_metadata={},
        )

    def invoke(self, prompt):
        self.call_count += 1
        return self.response


class FakeSkill:
    name = "qa"
    need_llm = True

    def build_prompt(self, state):
        return "answer the research question"


def test_reason_node_records_llm_usage(monkeypatch):
    monkeypatch.setattr(reason_module.settings, "REASON_WITH_LLM", True)
    monkeypatch.setattr(
        reason_module,
        "get_llm",
        lambda: FakeLLM("compare", input_tokens=12, output_tokens=1),
    )

    result = reason_module.reason_node({"query": "ambiguous request"})

    assert result["task_type"] == "compare"
    assert result["llm_call_count"] == 1
    assert result["token_usage"] == 13
    assert result["llm_usage"][0]["node_name"] == "reason"


def test_evaluate_node_records_usage_only_when_llm_is_enabled(monkeypatch):
    monkeypatch.setattr(evaluate_module.settings, "EVALUATE_WITH_LLM", True)
    monkeypatch.setattr(
        evaluate_module,
        "get_llm",
        lambda: FakeLLM("0.8", input_tokens=30, output_tokens=1),
    )

    result = evaluate_module.evaluate_node(
        {
            "query": "RAG",
            "documents": [{"title": "RAG", "content": "retrieval"}],
        }
    )

    assert result["retrieval_score"] == 0.8
    assert result["llm_call_count"] == 1
    assert result["token_usage"] == 31
    assert result["llm_usage"][0]["node_name"] == "evaluate"


def test_generate_node_records_usage(monkeypatch):
    monkeypatch.setattr(
        generate_module,
        "attach_skill_context",
        lambda state: state,
    )
    monkeypatch.setattr(
        generate_module,
        "get_skill",
        lambda state: FakeSkill(),
    )
    monkeypatch.setattr(
        generate_module,
        "get_llm",
        lambda: FakeLLM("grounded answer", input_tokens=100, output_tokens=20),
    )

    result = generate_module.generate_node(
        {
            "query": "What is RAG?",
            "task_type": "qa",
            "documents": [{"title": "RAG paper"}],
            "paper_metadata": {},
        }
    )

    assert result["answer"] == "grounded answer"
    assert result["llm_call_count"] == 1
    assert result["token_usage"] == 120
    assert result["llm_usage"][0]["node_name"] == "generate"


def test_generate_removes_only_dangling_outline_marker_from_long_answer(monkeypatch):
    monkeypatch.setattr(generate_module, "attach_skill_context", lambda state: state)
    monkeypatch.setattr(generate_module, "get_skill", lambda state: FakeSkill())
    long_answer = "\n\n".join(
        [f"## {index}. 分析\n" + ("这是具有证据支持的完整分析内容。" * 8) for index in range(1, 7)]
    ) + "\n\n7"
    monkeypatch.setattr(generate_module, "get_llm", lambda: FakeLLM(long_answer))

    result = generate_module.generate_node({
        "query": "比较两种 Agent 架构",
        "task_type": "compare",
        "documents": [{"title": "Agent paper"}],
        "paper_metadata": {},
    })

    assert not result["answer"].endswith("7")
    assert result["paper_metadata"]["answer_tail_cleanup"] == {
        "status": "repaired",
        "repaired": True,
        "removed_tail": "7",
        "reason": "dangling_outline_marker",
    }


def test_answer_tail_cleanup_preserves_numeric_short_answer():
    answer, metadata = generate_module.clean_generated_answer_tail("7")

    assert answer == "7"
    assert metadata["status"] == "unchanged"


def test_generate_collects_memory_metadata_in_same_llm_call(monkeypatch):
    monkeypatch.setattr(generate_module, "attach_skill_context", lambda state: state)
    monkeypatch.setattr(generate_module, "get_skill", lambda state: FakeSkill())
    llm = FakeLLM(
        '可验证的综合结论。<MEMORY_METADATA>{"worth_storing":true,'
        '"memory_type":"research_finding","value_score":0.9,'
        '"stability":"stable","time_sensitive":false,"topic":"RAG"}'
        '</MEMORY_METADATA>'
    )
    monkeypatch.setattr(generate_module, "get_llm", lambda: llm)

    result = generate_module.generate_node({
        "query": "比较两种RAG方案",
        "task_type": "compare",
        "task_level": "L2",
        "documents": [{"title": "RAG paper"}],
        "paper_metadata": {},
    })

    assert llm.call_count == 1
    assert result["answer"] == "可验证的综合结论。"
    assert result["memory_metadata"]["status"] == "valid"
    assert result["memory_metadata"]["source_answer_hash"]


def test_rule_based_evaluate_does_not_create_an_llm_call(monkeypatch):
    monkeypatch.setattr(evaluate_module.settings, "EVALUATE_WITH_LLM", False)

    result = evaluate_module.evaluate_node(
        {
            "query": "RAG",
            "documents": [{"title": "RAG", "content": "retrieval"}],
        }
    )

    assert "llm_call_count" not in result
    assert result["retrieval_score"] > 0

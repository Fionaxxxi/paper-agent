import pytest

from nodes.intent_router import classify_input_intent, intent_router_node, normalize_message


@pytest.mark.parametrize("query", ["hi", "Hello!", " 你好。 ", "您好"])
def test_classifies_exact_greetings_without_an_llm(query):
    assert classify_input_intent({"query": query}) == "greeting"


@pytest.mark.parametrize("query", ["thanks", "Thank you!", "谢谢", "感谢！"])
def test_classifies_thanks_without_an_llm(query):
    assert classify_input_intent({"query": query}) == "thanks"


@pytest.mark.parametrize("query", ["who are you?", "你是谁？", "你能做什么"])
def test_classifies_identity_questions_without_an_llm(query):
    assert classify_input_intent({"query": query}) == "identity"


@pytest.mark.parametrize(
    "state",
    [
        {"query": "hi, find recent RAG papers"},
        {"query": "你好，请比较 RAG 和 GraphRAG"},
        {"query": "hi", "pdf_path": "paper.pdf"},
    ],
)
def test_does_not_short_circuit_research_or_pdf_requests(state):
    assert classify_input_intent(state) == "research"


def test_normalize_message_only_removes_superficial_variations():
    assert normalize_message("  HELLO！！ ") == "hello"


def test_smalltalk_result_is_local_and_preserves_existing_state_metadata():
    result = intent_router_node(
        {
            "query": "hi",
            "tools_used": [],
            "token_usage": 0,
            "paper_metadata": {"conversation_id": "conversation-1"},
        }
    )

    assert result["task_type"] == "smalltalk"
    assert result["answer"].startswith("你好")
    assert result["documents"] == []
    assert result["tools_used"] == []
    assert result["token_usage"] == 0
    assert result["paper_metadata"]["conversation_id"] == "conversation-1"
    assert result["paper_metadata"]["short_circuited"] is True

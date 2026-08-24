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
    "query",
    [
        "你好，先简单介绍一下你能做什么。",
        "您好，可以介绍一下你的主要能力吗？",
        "请说明一下你可以帮我做什么",
    ],
)
def test_classifies_greeting_plus_capability_request_as_local_identity(query):
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


def test_local_capability_response_clears_previous_research_execution_state():
    result = intent_router_node({
        "query": "你好，先简单介绍一下你能做什么。",
        "documents": [{"title": "stale"}], "tools_used": ["arxiv_retriever"],
        "retry_count": 1, "retry_query": "stale survey", "retrieval_score": 0.5,
        "llm_call_count": 1, "token_usage": 419,
        "evidence_store": {"enabled": True, "evidence_count": 7},
        "paper_metadata": {"skill_used": "qa", "retrieval_source": "arxiv"},
    })
    assert result["input_intent"] == "identity"
    assert result["documents"] == [] and result["tools_used"] == []
    assert result["retry_count"] == 0 and result["retry_query"] == ""
    assert result["llm_call_count"] == 0 and result["token_usage"] == 0
    assert result["evidence_store"]["evidence_count"] == 0
    assert result["paper_metadata"]["skill_used"] == "local_response"
    assert result["paper_metadata"]["retrieval_source"] == "local"

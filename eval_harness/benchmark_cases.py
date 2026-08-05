from typing import Any, Dict, List


INTENT_CASES: List[Dict[str, Any]] = [
    {"id": "greeting_en", "query": "hi", "expected_intent": "greeting"},
    {"id": "greeting_zh", "query": "你好", "expected_intent": "greeting"},
    {"id": "thanks_en", "query": "thank you", "expected_intent": "thanks"},
    {"id": "thanks_zh", "query": "谢谢", "expected_intent": "thanks"},
    {"id": "identity_en", "query": "who are you?", "expected_intent": "identity"},
    {"id": "identity_zh", "query": "你能做什么", "expected_intent": "identity"},
    {
        "id": "research_en",
        "query": "compare RAG and GraphRAG",
        "expected_intent": "research",
    },
    {
        "id": "research_zh",
        "query": "比较 RAG 和 GraphRAG",
        "expected_intent": "research",
    },
    {
        "id": "compound_greeting",
        "query": "你好，请比较 RAG 和 GraphRAG",
        "expected_intent": "research",
    },
    {
        "id": "pdf_overrides_greeting",
        "query": "hi",
        "pdf_path": "paper.pdf",
        "expected_intent": "research",
    },
]


QUERY_PLAN_CASES: List[Dict[str, Any]] = [
    {
        "id": "simple_definition",
        "query": "什么是 RAG",
        "rewritten_query": "retrieval augmented generation",
        "task_type": "qa",
        "expected_multi_query": False,
    },
    {
        "id": "simple_fact",
        "query": "BERT 是哪一年发布的",
        "rewritten_query": "BERT publication year",
        "task_type": "qa",
        "expected_multi_query": False,
    },
    {
        "id": "comparison",
        "query": "比较 RAG 和 GraphRAG",
        "rewritten_query": "RAG GraphRAG comparison",
        "task_type": "compare",
        "expected_multi_query": True,
    },
    {
        "id": "summary",
        "query": "总结 Agentic RAG 的主要方法",
        "rewritten_query": "Agentic RAG",
        "task_type": "summarize",
        "expected_multi_query": True,
    },
    {
        "id": "recommendation",
        "query": "推荐几个多模态 RAG 研究方向",
        "rewritten_query": "multimodal RAG",
        "task_type": "recommend",
        "expected_multi_query": True,
    },
    {
        "id": "citation",
        "query": "给出 GraphRAG 的代表论文",
        "rewritten_query": "GraphRAG",
        "task_type": "citation",
        "expected_multi_query": True,
    },
]


RESULT_MERGER_CASES: List[Dict[str, Any]] = [
    {
        "id": "entry_id_duplicates",
        "document_groups": [
            [
                {"entry_id": "1", "title": "Paper A"},
                {"entry_id": "2", "title": "Paper B"},
            ],
            [
                {"entry_id": "1", "title": "Paper A duplicate"},
                {"entry_id": "3", "title": "Paper C"},
            ],
        ],
        "expected_unique_count": 3,
        "max_documents": 8,
    },
    {
        "id": "title_duplicates",
        "document_groups": [
            [{"title": "Retrieval Augmented Generation"}],
            [
                {"title": " retrieval augmented generation "},
                {"title": "GraphRAG"},
            ],
        ],
        "expected_unique_count": 2,
        "max_documents": 8,
    },
    {
        "id": "already_unique",
        "document_groups": [
            [{"entry_id": "1"}, {"entry_id": "2"}],
            [{"entry_id": "3"}, {"entry_id": "4"}],
        ],
        "expected_unique_count": 4,
        "max_documents": 8,
    },
]


RETRY_CASES: List[Dict[str, Any]] = [
    {
        "id": "low_score_first_attempt",
        "retrieval_score": 0.4,
        "retry_count": 0,
        "expected_route": "retry",
    },
    {
        "id": "threshold_score",
        "retrieval_score": 0.7,
        "retry_count": 0,
        "expected_route": "generate",
    },
    {
        "id": "high_score",
        "retrieval_score": 0.9,
        "retry_count": 0,
        "expected_route": "generate",
    },
    {
        "id": "low_score_after_retry",
        "retrieval_score": 0.3,
        "retry_count": 1,
        "expected_route": "generate",
    },
]


TOOL_EXECUTION_CASES: List[Dict[str, Any]] = [
    {
        "id": "valid_success",
        "arguments": {"value": 2},
        "behavior": "success",
        "max_attempts": 1,
        "expected": {
            "success": True,
            "error_code": "",
            "attempt_count": 1,
        },
    },
    {
        "id": "write_tool_blocked",
        "arguments": {"value": 2},
        "behavior": "success",
        "risk_level": "write",
        "max_attempts": 1,
        "expected": {
            "success": False,
            "error_code": "PERMISSION_DENIED",
            "attempt_count": 0,
        },
    },
    {
        "id": "invalid_input_blocked",
        "arguments": {"value": 0},
        "behavior": "success",
        "max_attempts": 1,
        "expected": {
            "success": False,
            "error_code": "INVALID_INPUT",
            "attempt_count": 0,
        },
    },
    {
        "id": "execution_error_structured",
        "arguments": {"value": 2},
        "behavior": "execution_error",
        "max_attempts": 1,
        "expected": {
            "success": False,
            "error_code": "EXECUTION_ERROR",
            "attempt_count": 1,
        },
    },
    {
        "id": "temporary_failure_recovered",
        "arguments": {"value": 2},
        "behavior": "fail_once",
        "max_attempts": 2,
        "expected": {
            "success": True,
            "error_code": "",
            "attempt_count": 2,
        },
    },
    {
        "id": "invalid_output_blocked",
        "arguments": {"value": 2},
        "behavior": "invalid_output",
        "max_attempts": 1,
        "expected": {
            "success": False,
            "error_code": "INVALID_OUTPUT",
            "attempt_count": 1,
        },
    },
]


LLM_USAGE_CASES: List[Dict[str, Any]] = [
    {
        "id": "reason_and_generate_success",
        "records": [
            {
                "node_name": "reason",
                "model_name": "benchmark-model",
                "success": True,
                "input_tokens": 20,
                "output_tokens": 5,
                "total_tokens": 25,
                "token_usage_available": True,
                "latency_seconds": 0.1,
                "error_type": "",
            },
            {
                "node_name": "generate",
                "model_name": "benchmark-model",
                "success": True,
                "input_tokens": 100,
                "output_tokens": 40,
                "total_tokens": 140,
                "token_usage_available": True,
                "latency_seconds": 0.4,
                "error_type": "",
            },
        ],
        "expected": {
            "llm_call_count": 2,
            "llm_failed_call_count": 0,
            "input_token_usage": 120,
            "output_token_usage": 45,
            "token_usage": 165,
        },
    },
    {
        "id": "failed_generate_call",
        "records": [
            {
                "node_name": "generate",
                "model_name": "benchmark-model",
                "success": False,
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "token_usage_available": False,
                "latency_seconds": 0.25,
                "error_type": "TimeoutError",
            },
        ],
        "expected": {
            "llm_call_count": 1,
            "llm_failed_call_count": 1,
            "input_token_usage": 0,
            "output_token_usage": 0,
            "token_usage": 0,
        },
    },
]


LLM_USAGE_CASES: List[Dict[str, Any]] = [
    {
        "id": "reason_and_generate_success",
        "records": [
            {
                "node_name": "reason",
                "model_name": "benchmark-model",
                "success": True,
                "input_tokens": 20,
                "output_tokens": 5,
                "total_tokens": 25,
                "token_usage_available": True,
                "latency_seconds": 0.1,
                "error_type": "",
            },
            {
                "node_name": "generate",
                "model_name": "benchmark-model",
                "success": True,
                "input_tokens": 100,
                "output_tokens": 40,
                "total_tokens": 140,
                "token_usage_available": True,
                "latency_seconds": 0.4,
                "error_type": "",
            },
        ],
        "expected": {
            "llm_call_count": 2,
            "llm_failed_call_count": 0,
            "input_token_usage": 120,
            "output_token_usage": 45,
            "token_usage": 165,
        },
    },
    {
        "id": "failed_generate_call",
        "records": [
            {
                "node_name": "generate",
                "model_name": "benchmark-model",
                "success": False,
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "token_usage_available": False,
                "latency_seconds": 0.25,
                "error_type": "TimeoutError",
            },
        ],
        "expected": {
            "llm_call_count": 1,
            "llm_failed_call_count": 1,
            "input_token_usage": 0,
            "output_token_usage": 0,
            "token_usage": 0,
        },
    },
]

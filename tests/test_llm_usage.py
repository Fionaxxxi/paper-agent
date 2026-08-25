from types import SimpleNamespace

import pytest

from core.llm_usage import (
    TrackedLLMError,
    build_llm_usage_update,
    extract_token_usage,
    invoke_llm_with_usage,
)
from nodes.metrics import build_llm_usage_by_node, metrics_node


class SuccessfulLLM:
    def __init__(self, response):
        self.response = response

    def invoke(self, prompt):
        return self.response


class FailingLLM:
    def invoke(self, prompt):
        raise TimeoutError("model timed out")


def test_extracts_langchain_usage_metadata():
    response = SimpleNamespace(
        usage_metadata={
            "input_tokens": 120,
            "output_tokens": 30,
            "total_tokens": 150,
        },
        response_metadata={},
    )

    assert extract_token_usage(response) == {
        "input_tokens": 120,
        "output_tokens": 30,
        "total_tokens": 150,
        "token_usage_available": True,
    }


def test_extracts_openai_compatible_response_metadata():
    response = SimpleNamespace(
        usage_metadata=None,
        response_metadata={
            "token_usage": {
                "prompt_tokens": 80,
                "completion_tokens": 20,
                "total_tokens": 100,
            }
        },
    )

    assert extract_token_usage(response) == {
        "input_tokens": 80,
        "output_tokens": 20,
        "total_tokens": 100,
        "token_usage_available": True,
    }


def test_missing_usage_is_explicit_instead_of_estimated():
    response = SimpleNamespace(
        usage_metadata=None,
        response_metadata={},
    )

    assert extract_token_usage(response) == {
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "token_usage_available": False,
    }


def test_successful_invocation_records_model_node_tokens_and_latency():
    response = SimpleNamespace(
        content="answer",
        usage_metadata={
            "input_tokens": 10,
            "output_tokens": 5,
            "total_tokens": 15,
        },
        response_metadata={"finish_reason": "length"},
    )

    actual_response, record = invoke_llm_with_usage(
        llm=SuccessfulLLM(response),
        prompt="test prompt",
        node_name="generate",
        model_name="test-model",
    )

    assert actual_response is response
    assert record["node_name"] == "generate"
    assert record["model_name"] == "test-model"
    assert record["success"] is True
    assert record["total_tokens"] == 15
    assert record["finish_reason"] == "length"
    assert record["latency_seconds"] >= 0


def test_failed_invocation_preserves_call_and_latency_record():
    with pytest.raises(TrackedLLMError) as exc_info:
        invoke_llm_with_usage(
            llm=FailingLLM(),
            prompt="test prompt",
            node_name="reason",
            model_name="test-model",
        )

    record = exc_info.value.usage_record
    assert isinstance(exc_info.value.original_error, TimeoutError)
    assert record["success"] is False
    assert record["error_type"] == "TimeoutError"
    assert record["total_tokens"] == 0
    assert record["latency_seconds"] >= 0


def test_multiple_node_records_are_aggregated_without_double_counting():
    reason_record = {
        "node_name": "reason",
        "success": True,
        "input_tokens": 20,
        "output_tokens": 5,
        "total_tokens": 25,
        "latency_seconds": 0.1,
    }
    generate_record = {
        "node_name": "generate",
        "success": True,
        "input_tokens": 100,
        "output_tokens": 40,
        "total_tokens": 140,
        "latency_seconds": 0.4,
    }

    first_update = build_llm_usage_update({}, reason_record)
    second_update = build_llm_usage_update(first_update, generate_record)

    assert second_update["llm_call_count"] == 2
    assert second_update["llm_failed_call_count"] == 0
    assert second_update["input_token_usage"] == 120
    assert second_update["output_token_usage"] == 45
    assert second_update["token_usage"] == 165


def test_metrics_groups_usage_by_node_and_reports_totals():
    records = [
        {
            "node_name": "reason",
            "success": True,
            "input_tokens": 20,
            "output_tokens": 5,
            "total_tokens": 25,
            "latency_seconds": 0.1,
            "token_usage_available": True,
        },
        {
            "node_name": "generate",
            "success": False,
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "latency_seconds": 0.4,
            "token_usage_available": False,
        },
    ]
    grouped = build_llm_usage_by_node(records)

    assert grouped["reason"]["total_tokens"] == 25
    assert grouped["generate"]["failed_call_count"] == 1

    result = metrics_node(
        {
            "llm_usage": records,
            "llm_call_count": 2,
            "llm_failed_call_count": 1,
            "input_token_usage": 20,
            "output_token_usage": 5,
            "token_usage": 25,
            "node_timings": {},
            "paper_metadata": {},
        }
    )
    metrics = result["paper_metadata"]["metrics"]

    assert metrics["llm_call_count"] == 2
    assert metrics["llm_failed_call_count"] == 1
    assert metrics["token_usage"] == 25
    assert metrics["llm_usage_unavailable_count"] == 1
    assert metrics["llm_latency_seconds"] == 0.5

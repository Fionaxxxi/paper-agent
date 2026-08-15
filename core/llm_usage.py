import time
from typing import Any, Dict, Tuple

from agent.state import AgentState


def _as_non_negative_int(value: Any) -> int:
    try:
        return max(int(value or 0), 0)
    except (TypeError, ValueError):
        return 0


def extract_token_usage(response: Any) -> Dict[str, Any]:
    """
    Extract token usage from common LangChain AIMessage metadata shapes.
    """

    usage_metadata = getattr(response, "usage_metadata", None) or {}
    response_metadata = getattr(response, "response_metadata", None) or {}
    token_usage = response_metadata.get("token_usage", {}) or {}

    input_tokens = _as_non_negative_int(
        usage_metadata.get(
            "input_tokens",
            token_usage.get("prompt_tokens", 0),
        )
    )
    output_tokens = _as_non_negative_int(
        usage_metadata.get(
            "output_tokens",
            token_usage.get("completion_tokens", 0),
        )
    )
    total_tokens = _as_non_negative_int(
        usage_metadata.get(
            "total_tokens",
            token_usage.get("total_tokens", input_tokens + output_tokens),
        )
    )
    if total_tokens == 0 and (input_tokens or output_tokens):
        total_tokens = input_tokens + output_tokens

    usage_available = bool(usage_metadata or token_usage)

    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "token_usage_available": usage_available,
    }


class TrackedLLMError(Exception):
    def __init__(
        self,
        original_error: Exception,
        usage_record: Dict[str, Any],
    ) -> None:
        super().__init__(str(original_error))
        self.original_error = original_error
        self.usage_record = usage_record


def invoke_llm_with_usage(
    llm: Any,
    prompt: Any,
    node_name: str,
    model_name: str,
    prompt_version: str = "",
) -> Tuple[Any, Dict[str, Any]]:
    """
    Invoke an LLM and return a normalized per-call usage record.

    Failed calls raise TrackedLLMError so callers can preserve their existing
    fallback behavior while still recording call count and latency.
    """

    started_at = time.perf_counter()

    try:
        response = llm.invoke(prompt)
    except Exception as error:
        latency_seconds = round(time.perf_counter() - started_at, 4)
        record = {
            "node_name": node_name,
            "model_name": model_name,
            "success": False,
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "token_usage_available": False,
            "latency_seconds": latency_seconds,
            "error_type": type(error).__name__,
            "prompt_version": prompt_version,
        }
        raise TrackedLLMError(error, record) from error

    latency_seconds = round(time.perf_counter() - started_at, 4)
    usage = extract_token_usage(response)
    record = {
        "node_name": node_name,
        "model_name": model_name,
        "success": True,
        **usage,
        "latency_seconds": latency_seconds,
        "error_type": "",
        "prompt_version": prompt_version,
    }
    return response, record


def build_llm_usage_update(
    state: AgentState,
    usage_record: Dict[str, Any],
) -> AgentState:
    records = [
        *state.get("llm_usage", []),
        usage_record,
    ]

    return {
        "llm_usage": records,
        "llm_call_count": len(records),
        "llm_failed_call_count": sum(
            1 for record in records if not record.get("success", False)
        ),
        "input_token_usage": sum(
            _as_non_negative_int(record.get("input_tokens", 0))
            for record in records
        ),
        "output_token_usage": sum(
            _as_non_negative_int(record.get("output_tokens", 0))
            for record in records
        ),
        "token_usage": sum(
            _as_non_negative_int(record.get("total_tokens", 0))
            for record in records
        ),
    }

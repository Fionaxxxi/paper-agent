"""Validated, observable and bounded execution for registered tools."""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from typing import Any

from pydantic import ValidationError

from tools.base import Tool
from tools.contracts import ToolErrorCode, ToolRateLimitError, ToolResult
from tools.policy import ToolPolicy
from tools.registry import ToolRegistry


class ToolExecutor:
    def __init__(
        self,
        registry: ToolRegistry,
        policy: ToolPolicy | None = None,
    ) -> None:
        self.registry = registry
        self.policy = policy or ToolPolicy()

    def execute(self, tool_name: str, arguments: dict[str, Any]) -> ToolResult:
        started_at = time.perf_counter()
        tool = self.registry.get(tool_name)
        if tool is None:
            return ToolResult(
                success=False,
                tool_name=tool_name,
                error_code=ToolErrorCode.TOOL_NOT_FOUND.value,
                error_message=f"tool is not registered: {tool_name}",
                latency_seconds=self._elapsed(started_at),
            )

        spec = tool.spec
        allowed, denial_reason = self.policy.authorize(spec)
        if not allowed:
            return ToolResult(
                success=False,
                tool_name=spec.name,
                tool_version=spec.version,
                source=spec.provider,
                error_code=ToolErrorCode.PERMISSION_DENIED.value,
                error_message=denial_reason,
                latency_seconds=self._elapsed(started_at),
                metadata=self._metadata(tool),
            )

        try:
            validated_input = spec.input_model.model_validate(arguments)
        except ValidationError as error:
            return ToolResult(
                success=False,
                tool_name=spec.name,
                tool_version=spec.version,
                source=spec.provider,
                error_code=ToolErrorCode.INVALID_INPUT.value,
                error_message=str(error),
                latency_seconds=self._elapsed(started_at),
                metadata=self._metadata(tool),
            )

        last_error_code = ""
        last_error_message = ""
        max_attempts = spec.retry_policy.max_attempts

        for attempt in range(1, max_attempts + 1):
            try:
                raw_output = self._invoke_with_timeout(
                    tool,
                    validated_input,
                    spec.timeout_seconds,
                )
                try:
                    output = spec.output_model.model_validate(raw_output)
                except ValidationError as error:
                    return ToolResult(
                        success=False,
                        tool_name=spec.name,
                        tool_version=spec.version,
                        source=spec.provider,
                        error_code=ToolErrorCode.INVALID_OUTPUT.value,
                        error_message=str(error),
                        latency_seconds=self._elapsed(started_at),
                        attempt_count=attempt,
                        metadata=self._metadata(tool),
                    )

                return ToolResult(
                    success=True,
                    tool_name=spec.name,
                    tool_version=spec.version,
                    source=spec.provider,
                    data=output.model_dump(mode="python"),
                    latency_seconds=self._elapsed(started_at),
                    attempt_count=attempt,
                    metadata=self._metadata(tool),
                )

            except FutureTimeoutError:
                last_error_code = ToolErrorCode.TIMEOUT.value
                last_error_message = (
                    f"tool execution exceeded {spec.timeout_seconds} seconds"
                )
            except ToolRateLimitError as error:
                last_error_code = ToolErrorCode.RATE_LIMITED.value
                last_error_message = str(error)
            except Exception as error:
                last_error_code = ToolErrorCode.EXECUTION_ERROR.value
                last_error_message = f"{type(error).__name__}: {error}"

            if (
                attempt >= max_attempts
                or last_error_code not in spec.retry_policy.retryable_error_codes
            ):
                return ToolResult(
                    success=False,
                    tool_name=spec.name,
                    tool_version=spec.version,
                    source=spec.provider,
                    error_code=last_error_code,
                    error_message=last_error_message,
                    latency_seconds=self._elapsed(started_at),
                    attempt_count=attempt,
                    metadata=self._metadata(tool),
                )

        raise RuntimeError("unreachable tool execution state")

    @staticmethod
    def _invoke_with_timeout(tool: Tool, validated_input, timeout_seconds: float):
        pool = ThreadPoolExecutor(max_workers=1)
        future = pool.submit(tool.invoke, validated_input)
        timed_out = False
        try:
            return future.result(timeout=timeout_seconds)
        except FutureTimeoutError:
            timed_out = True
            future.cancel()
            raise
        finally:
            pool.shutdown(wait=not timed_out, cancel_futures=timed_out)

    @staticmethod
    def _elapsed(started_at: float) -> float:
        return round(max(0.0, time.perf_counter() - started_at), 6)

    @staticmethod
    def _metadata(tool: Tool) -> dict[str, Any]:
        spec = tool.spec
        metadata = {
            "capabilities": list(spec.capabilities),
            "risk_level": spec.risk_level.value,
            "cache_policy": spec.cache_policy,
        }
        audit_metadata = getattr(tool, "audit_metadata", None)
        if isinstance(audit_metadata, dict):
            metadata.update(audit_metadata)
        return metadata

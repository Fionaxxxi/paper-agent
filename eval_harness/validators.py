from typing import Any, Dict, List, Tuple

from validators.answer_validator import (
    validate_answer_contains,
    validate_answer_contains_any,
    validate_answer_not_empty,
)
from validators.citation_validator import validate_citation_output
from validators.pdf_grounding_validator import validate_pdf_reading_output
from validators.retrieval_validator import (
    validate_cache_consistency,
    validate_retrieval_basic,
)


def get_paper_metadata(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get paper_metadata from PaperAgent result.
    """

    return result.get("paper_metadata", {})


def get_skill_used(result: Dict[str, Any]) -> str:
    """
    Get skill_used from paper_metadata.
    """

    paper_metadata = get_paper_metadata(result)
    return paper_metadata.get("skill_used", "")


def merge_errors(
    all_errors: List[str],
    passed: bool,
    errors: List[str],
) -> None:
    """
    Merge validator errors into the total error list.
    """

    if not passed:
        all_errors.extend(errors)


def validate_result(
    result: Dict[str, Any],
    expected: Dict[str, Any],
) -> Tuple[bool, List[str]]:
    """
    Validate PaperAgentService.chat() result according to expected rules.

    This function belongs to eval_harness, so it reads the expected fields
    defined in eval_harness/cases.py and delegates actual validation logic
    to the formal validators package.
    """

    errors: List[str] = []

    # 1. 通用 answer 非空检查
    passed, validator_errors = validate_answer_not_empty(result)
    merge_errors(errors, passed, validator_errors)

    # 2. 校验 task_type
    expected_task_type = expected.get("task_type")
    if expected_task_type:
        actual_task_type = result.get("task_type")

        if actual_task_type != expected_task_type:
            errors.append(
                f"task_type expected={expected_task_type}, actual={actual_task_type}"
            )

    # 3. 校验 skill_used
    expected_skill = expected.get("skill_used")
    if expected_skill:
        actual_skill = get_skill_used(result)

        if actual_skill != expected_skill:
            errors.append(
                f"skill_used expected={expected_skill}, actual={actual_skill}"
            )

    # 4. 校验 answer 必须包含所有关键词
    answer_contains = expected.get("answer_contains", [])
    if answer_contains:
        passed, validator_errors = validate_answer_contains(
            result=result,
            keywords=answer_contains,
        )
        merge_errors(errors, passed, validator_errors)

    # 5. 校验 answer 包含任意一个关键词
    answer_contains_any = expected.get("answer_contains_any", [])
    if answer_contains_any:
        passed, validator_errors = validate_answer_contains_any(
            result=result,
            keywords=answer_contains_any,
        )
        merge_errors(errors, passed, validator_errors)

    # 6. 校验 history_count
    history_count_gt = expected.get("history_count_gt")
    if history_count_gt is not None:
        paper_metadata = get_paper_metadata(result)
        actual_history_count = paper_metadata.get("history_count", 0)

        if actual_history_count <= history_count_gt:
            errors.append(
                f"history_count expected > {history_count_gt}, actual={actual_history_count}"
            )

    # 7. 校验 pdf_page_count
    pdf_page_count_gt = expected.get("pdf_page_count_gt")
    if pdf_page_count_gt is not None:
        actual_pdf_page_count = result.get("pdf_page_count", 0)

        if actual_pdf_page_count <= pdf_page_count_gt:
            errors.append(
                f"pdf_page_count expected > {pdf_page_count_gt}, actual={actual_pdf_page_count}"
            )

        paper_metadata = get_paper_metadata(result)
        pdf_error = paper_metadata.get("pdf_error", "")

        if pdf_error:
            errors.append(f"pdf_error is not empty: {pdf_error}")

    # 8. 校验 Agentic RAG / Query Planning 指标
    expected_agentic_rag_enabled = expected.get("agentic_rag_enabled")
    if expected_agentic_rag_enabled is not None:
        paper_metadata = get_paper_metadata(result)
        metrics = paper_metadata.get("metrics", {})

        actual_agentic_rag_enabled = metrics.get(
            "agentic_rag_enabled",
            paper_metadata.get("agentic_rag_enabled", False),
        )

        if actual_agentic_rag_enabled != expected_agentic_rag_enabled:
            errors.append(
                f"agentic_rag_enabled expected={expected_agentic_rag_enabled}, "
                f"actual={actual_agentic_rag_enabled}"
            )

    expected_query_plan_enabled = expected.get("query_plan_enabled")
    if expected_query_plan_enabled is not None:
        paper_metadata = get_paper_metadata(result)
        metrics = paper_metadata.get("metrics", {})

        actual_query_plan_enabled = metrics.get(
            "query_plan_enabled",
            paper_metadata.get("query_plan_enabled", False),
        )

        if actual_query_plan_enabled != expected_query_plan_enabled:
            errors.append(
                f"query_plan_enabled expected={expected_query_plan_enabled}, "
                f"actual={actual_query_plan_enabled}"
            )

    sub_query_count_gt = expected.get("sub_query_count_gt")
    if sub_query_count_gt is not None:
        paper_metadata = get_paper_metadata(result)
        metrics = paper_metadata.get("metrics", {})

        actual_sub_query_count = metrics.get(
            "sub_query_count",
            paper_metadata.get("sub_query_count", 0),
        )

        if actual_sub_query_count <= sub_query_count_gt:
            errors.append(
                f"sub_query_count expected > {sub_query_count_gt}, "
                f"actual={actual_sub_query_count}"
            )

    expected_retrieval_source = expected.get("retrieval_source")
    if expected_retrieval_source:
        paper_metadata = get_paper_metadata(result)
        metrics = paper_metadata.get("metrics", {})

        actual_retrieval_source = metrics.get(
            "retrieval_source",
            paper_metadata.get("retrieval_source", ""),
        )

        if actual_retrieval_source != expected_retrieval_source:
            errors.append(
                f"retrieval_source expected={expected_retrieval_source}, "
                f"actual={actual_retrieval_source}"
            )

    merged_document_count_gt = expected.get("merged_document_count_gt")
    if merged_document_count_gt is not None:
        paper_metadata = get_paper_metadata(result)
        metrics = paper_metadata.get("metrics", {})

        actual_merged_document_count = metrics.get(
            "merged_document_count",
            paper_metadata.get("merged_document_count", 0),
        )

        if actual_merged_document_count <= merged_document_count_gt:
            errors.append(
                f"merged_document_count expected > {merged_document_count_gt}, "
                f"actual={actual_merged_document_count}"
            )

    # 9. 针对 citation 任务调用 Citation Verifier
    if expected_task_type == "citation":
        passed, validator_errors = validate_citation_output(result)
        merge_errors(errors, passed, validator_errors)

    # 10. 针对 PDF 任务调用 PDF Verifier
    if expected_task_type == "pdf_reading":
        passed, validator_errors = validate_pdf_reading_output(result)
        merge_errors(errors, passed, validator_errors)

    # 11. 普通非 PDF 任务调用 Retrieval Verifier
    if expected_task_type != "pdf_reading":
        passed, validator_errors = validate_retrieval_basic(result)
        merge_errors(errors, passed, validator_errors)

        passed, validator_errors = validate_cache_consistency(result)
        merge_errors(errors, passed, validator_errors)

    return len(errors) == 0, errors


def validate_cache_hit(
    first_result: Dict[str, Any],
    second_result: Dict[str, Any],
) -> Tuple[bool, List[str]]:
    """
    Validate whether the second run of the same query hits cache.

    Supports:
    - single-query retrieval cache
    - Agentic RAG multi-query cache
    """

    errors: List[str] = []

    second_metadata = get_paper_metadata(second_result)
    metrics = second_metadata.get("metrics", {})

    cache_hit = metrics.get(
        "cache_hit",
        second_metadata.get("cache_hit", False),
    )

    retrieval_source = metrics.get(
        "retrieval_source",
        second_metadata.get("retrieval_source", ""),
    )

    cache_hit_count = metrics.get(
        "cache_hit_count",
        second_metadata.get("cache_hit_count", 0),
    )

    retrieval_sources = metrics.get(
        "retrieval_sources",
        second_metadata.get("retrieval_sources", []),
    )

    # Agentic RAG multi-query mode:
    # The overall retrieval_source is multi_query, while cache usage is
    # represented by cache_hit_count and retrieval_sources.
    if retrieval_source == "multi_query":
        if cache_hit_count <= 0 and "cache" not in retrieval_sources:
            errors.append(
                "second run expected cache usage in multi_query mode, "
                f"cache_hit_count={cache_hit_count}, "
                f"retrieval_sources={retrieval_sources}"
            )

        return len(errors) == 0, errors

    # Legacy single-query mode:
    # The second run should directly hit cache.
    if cache_hit is not True:
        errors.append(f"second run cache_hit expected=True, actual={cache_hit}")

    if retrieval_source != "cache":
        errors.append(
            f"second run retrieval_source expected=cache, actual={retrieval_source}"
        )

    passed, validator_errors = validate_cache_consistency(second_result)
    merge_errors(errors, passed, validator_errors)

    return len(errors) == 0, errors
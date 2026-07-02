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

    # 8. 针对 citation 任务调用 Citation Verifier
    if expected_task_type == "citation":
        passed, validator_errors = validate_citation_output(result)
        merge_errors(errors, passed, validator_errors)

    # 9. 针对 PDF 任务调用 PDF Verifier
    if expected_task_type == "pdf_reading":
        passed, validator_errors = validate_pdf_reading_output(result)
        merge_errors(errors, passed, validator_errors)

    # 10. 普通非 PDF 任务调用 Retrieval Verifier
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
    """

    errors: List[str] = []

    second_metadata = get_paper_metadata(second_result)
    cache_hit = second_metadata.get("cache_hit", False)
    retrieval_source = second_metadata.get("retrieval_source", "")

    if cache_hit is not True:
        errors.append(f"second run cache_hit expected=True, actual={cache_hit}")

    if retrieval_source != "cache":
        errors.append(
            f"second run retrieval_source expected=cache, actual={retrieval_source}"
        )

    passed, validator_errors = validate_cache_consistency(second_result)
    merge_errors(errors, passed, validator_errors)

    return len(errors) == 0, errors
from typing import Any, Dict, List, Tuple


def get_paper_metadata(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get paper_metadata from PaperAgent result.
    """

    return result.get("paper_metadata", {})


def get_metrics(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get metrics from paper_metadata.

    Some fields such as retrieval_count, retrieval_score, tools_used
    are stored inside paper_metadata["metrics"].
    """

    metadata = get_paper_metadata(result)
    return metadata.get("metrics", {})


def get_metric_value(
    result: Dict[str, Any],
    key: str,
    default: Any = None,
) -> Any:
    """
    Read a value from metrics first, then fall back to paper_metadata.

    This makes the validator compatible with both structures:
    - paper_metadata["metrics"][key]
    - paper_metadata[key]
    """

    metadata = get_paper_metadata(result)
    metrics = get_metrics(result)

    if key in metrics:
        return metrics.get(key, default)

    return metadata.get(key, default)


def validate_retrieval_basic(result: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate whether a normal retrieval-based task has valid retrieval metadata.

    PDF tasks do not require retrieval_count > 0 because PDFReadingSkill
    should skip Retrieve / Evaluate / Retry.
    """

    errors: List[str] = []

    is_pdf_task = get_metric_value(result, "is_pdf_task", False)
    retrieval_count = get_metric_value(result, "retrieval_count", 0)
    retrieval_score = get_metric_value(result, "retrieval_score", 0.0)
    retrieval_source = get_metric_value(result, "retrieval_source", "")
    tools_used = get_metric_value(result, "tools_used", [])

    if is_pdf_task:
        return True, []

    if retrieval_count <= 0:
        errors.append(f"retrieval_count expected > 0, actual={retrieval_count}")

    if retrieval_score < 0:
        errors.append(f"retrieval_score expected >= 0, actual={retrieval_score}")

    if not retrieval_source:
        errors.append("retrieval_source is empty")

    if not tools_used:
        errors.append("tools_used is empty")

    return len(errors) == 0, errors


def validate_cache_consistency(result: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate whether cache_hit and retrieval_source are consistent.
    """

    errors: List[str] = []

    cache_hit = get_metric_value(result, "cache_hit", False)
    retrieval_source = get_metric_value(result, "retrieval_source", "")

    if cache_hit and retrieval_source != "cache":
        errors.append(
            f"cache_hit=True but retrieval_source is {retrieval_source}, expected=cache"
        )

    if retrieval_source == "cache" and cache_hit is not True:
        errors.append("retrieval_source=cache but cache_hit is not True")

    return len(errors) == 0, errors
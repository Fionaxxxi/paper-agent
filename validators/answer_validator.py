from typing import Any, Dict, List, Tuple


def validate_answer_not_empty(result: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    验证 answer 是否为空。
    """

    errors: List[str] = []
    answer = result.get("answer", "")

    if not answer or not answer.strip():
        errors.append("answer is empty")

    return len(errors) == 0, errors


def validate_answer_contains(
    result: Dict[str, Any],
    keywords: List[str],
) -> Tuple[bool, List[str]]:
    """
    验证 answer 是否包含所有指定关键词。
    """

    errors: List[str] = []
    answer = result.get("answer", "")

    for keyword in keywords:
        if keyword not in answer:
            errors.append(f"answer does not contain keyword: {keyword}")

    return len(errors) == 0, errors


def validate_answer_contains_any(
    result: Dict[str, Any],
    keywords: List[str],
) -> Tuple[bool, List[str]]:
    """
    验证 answer 是否包含任意一个指定关键词。
    """

    errors: List[str] = []
    answer = result.get("answer", "")

    if keywords and not any(keyword in answer for keyword in keywords):
        errors.append(f"answer does not contain any keyword from: {keywords}")

    return len(errors) == 0, errors
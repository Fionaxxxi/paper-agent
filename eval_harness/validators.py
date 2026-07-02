from typing import Any, Dict, List, Tuple


def get_skill_used(result: Dict[str, Any]) -> str:
    paper_metadata = result.get("paper_metadata", {})
    return paper_metadata.get("skill_used", "")


def get_metrics(result: Dict[str, Any]) -> Dict[str, Any]:
    paper_metadata = result.get("paper_metadata", {})
    return paper_metadata.get("metrics", {})


def validate_result(
    result: Dict[str, Any],
    expected: Dict[str, Any],
) -> Tuple[bool, List[str]]:
    """
    根据 expected 规则验证 PaperAgentService.chat() 返回结果。

    支持的校验项：
    - task_type: 校验任务类型
    - skill_used: 校验实际使用的 Skill
    - answer_contains: 要求 answer 同时包含所有关键词
    - answer_contains_any: 要求 answer 包含任意一个关键词
    - history_count_gt: 要求 history_count 大于某个值
    - pdf_page_count_gt: 要求 pdf_page_count 大于某个值
    """

    errors = []

    # 1. 校验 task_type
    expected_task_type = expected.get("task_type")
    if expected_task_type:
        actual_task_type = result.get("task_type")

        if actual_task_type != expected_task_type:
            errors.append(
                f"task_type expected={expected_task_type}, actual={actual_task_type}"
            )

    # 2. 校验 skill_used
    expected_skill = expected.get("skill_used")
    if expected_skill:
        actual_skill = get_skill_used(result)

        if actual_skill != expected_skill:
            errors.append(
                f"skill_used expected={expected_skill}, actual={actual_skill}"
            )

    # 3. 校验 answer 必须包含所有关键词
    answer = result.get("answer", "")
    answer_contains = expected.get("answer_contains", [])

    for keyword in answer_contains:
        if keyword not in answer:
            errors.append(f"answer does not contain keyword: {keyword}")

    # 4. 校验 answer 包含任意一个关键词即可
    answer_contains_any = expected.get("answer_contains_any", [])

    if answer_contains_any:
        if not any(keyword in answer for keyword in answer_contains_any):
            errors.append(
                f"answer does not contain any keyword from: {answer_contains_any}"
            )

    # 5. 校验 history_count
    history_count_gt = expected.get("history_count_gt")
    if history_count_gt is not None:
        paper_metadata = result.get("paper_metadata", {})
        actual_history_count = paper_metadata.get("history_count", 0)

        if actual_history_count <= history_count_gt:
            errors.append(
                f"history_count expected > {history_count_gt}, actual={actual_history_count}"
            )

    # 6. 校验 pdf_page_count
    pdf_page_count_gt = expected.get("pdf_page_count_gt")
    if pdf_page_count_gt is not None:
        actual_pdf_page_count = result.get("pdf_page_count", 0)

        if actual_pdf_page_count <= pdf_page_count_gt:
            errors.append(
                f"pdf_page_count expected > {pdf_page_count_gt}, actual={actual_pdf_page_count}"
            )

        paper_metadata = result.get("paper_metadata", {})
        pdf_error = paper_metadata.get("pdf_error", "")

        if pdf_error:
            errors.append(f"pdf_error is not empty: {pdf_error}")

    return len(errors) == 0, errors


def validate_cache_hit(
    first_result: Dict[str, Any],
    second_result: Dict[str, Any],
) -> Tuple[bool, List[str]]:
    """
    校验第二次相同请求是否命中缓存。
    """

    errors = []

    second_metadata = second_result.get("paper_metadata", {})
    cache_hit = second_metadata.get("cache_hit", False)
    retrieval_source = second_metadata.get("retrieval_source", "")

    if cache_hit is not True:
        errors.append(f"second run cache_hit expected=True, actual={cache_hit}")

    if retrieval_source != "cache":
        errors.append(
            f"second run retrieval_source expected=cache, actual={retrieval_source}"
        )

    return len(errors) == 0, errors
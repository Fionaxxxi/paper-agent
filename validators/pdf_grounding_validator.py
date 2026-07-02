from typing import Any, Dict, List, Tuple


def get_paper_metadata(result: Dict[str, Any]) -> Dict[str, Any]:
    return result.get("paper_metadata", {})


def validate_pdf_reading_output(result: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    验证 PDFReadingSkill 输出是否基本合格。
    """

    errors: List[str] = []

    task_type = result.get("task_type")
    pdf_page_count = result.get("pdf_page_count", 0)
    answer = result.get("answer", "")

    metadata = get_paper_metadata(result)
    skill_used = metadata.get("skill_used", "")
    pdf_error = metadata.get("pdf_error", "")

    if task_type != "pdf_reading":
        errors.append(f"task_type expected=pdf_reading, actual={task_type}")

    if skill_used != "pdf_reading":
        errors.append(f"skill_used expected=pdf_reading, actual={skill_used}")

    if pdf_page_count <= 0:
        errors.append(f"pdf_page_count expected > 0, actual={pdf_page_count}")

    if pdf_error:
        errors.append(f"pdf_error is not empty: {pdf_error}")

    if not answer.strip():
        errors.append("pdf reading answer is empty")

    return len(errors) == 0, errors
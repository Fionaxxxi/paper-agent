from typing import Any, Dict, List, Tuple


def get_paper_metadata(result: Dict[str, Any]) -> Dict[str, Any]:
    return result.get("paper_metadata", {})


def validate_citation_output(result: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    验证 CitationSkill 输出是否基本合格。
    """

    errors: List[str] = []

    task_type = result.get("task_type")
    metadata = get_paper_metadata(result)
    skill_used = metadata.get("skill_used", "")
    citation_format = metadata.get("citation_format", "")
    answer = result.get("answer", "")

    if task_type != "citation":
        errors.append(f"task_type expected=citation, actual={task_type}")

    if skill_used != "citation":
        errors.append(f"skill_used expected=citation, actual={skill_used}")

    if citation_format == "bibtex":
        if "@article" not in answer and "@inproceedings" not in answer:
            errors.append("BibTeX output should contain @article or @inproceedings")

    if not answer.strip():
        errors.append("citation answer is empty")

    return len(errors) == 0, errors

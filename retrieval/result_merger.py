from typing import Any, Dict, List


def normalize_text(value: Any) -> str:
    """
    Normalize text for stable comparison.
    """

    if value is None:
        return ""

    return str(value).strip().lower()


def build_document_key(document: Dict[str, Any]) -> str:
    """
    Build a stable deduplication key for a document.

    Priority:
    1. entry_id
    2. pdf_url
    3. title
    """

    entry_id = normalize_text(document.get("entry_id"))
    if entry_id:
        return f"entry_id:{entry_id}"

    pdf_url = normalize_text(document.get("pdf_url"))
    if pdf_url:
        return f"pdf_url:{pdf_url}"

    title = normalize_text(document.get("title"))
    if title:
        return f"title:{title}"

    return ""


def merge_documents(
    document_groups: List[List[Dict[str, Any]]],
    max_documents: int = 8,
) -> List[Dict[str, Any]]:
    """
    Merge multiple document lists and remove duplicates.

    The order is preserved:
    - earlier sub-query results have higher priority
    - earlier documents inside each group have higher priority
    """

    merged_documents: List[Dict[str, Any]] = []
    seen_keys = set()

    for documents in document_groups:
        for document in documents:
            key = build_document_key(document)

            if key and key in seen_keys:
                continue

            if key:
                seen_keys.add(key)

            merged_documents.append(document)

            if len(merged_documents) >= max_documents:
                return merged_documents

    return merged_documents


def merge_documents_with_stats(
    document_groups: List[List[Dict[str, Any]]],
    max_documents: int = 8,
) -> Dict[str, Any]:
    """
    Merge documents and return both merged results and statistics.
    """

    raw_count = sum(len(group) for group in document_groups)

    merged_documents = merge_documents(
        document_groups=document_groups,
        max_documents=max_documents,
    )

    return {
        "documents": merged_documents,
        "raw_document_count": raw_count,
        "merged_document_count": len(merged_documents),
        "deduplicated_count": max(raw_count - len(merged_documents), 0),
    }
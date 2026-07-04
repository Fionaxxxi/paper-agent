from typing import Any, Dict, List


def safe_join_authors(authors: Any) -> str:
    """
    Convert authors into a readable string.
    """

    if not authors:
        return ""

    if isinstance(authors, list):
        return ", ".join(str(author) for author in authors)

    return str(authors)


def truncate_text(text: Any, limit: int) -> str:
    """
    Truncate long text to a fixed character limit.
    """

    if text is None:
        return ""

    text = str(text).strip()

    if limit <= 0:
        return ""

    if len(text) <= limit:
        return text

    return text[:limit].rstrip() + "...[truncated]"


def get_document_content(document: Dict[str, Any]) -> str:
    """
    Get the most useful content field from a document.

    Different retrievers may use different field names:
    - content
    - summary
    - abstract
    """

    return (
        document.get("content")
        or document.get("summary")
        or document.get("abstract")
        or ""
    )


def format_single_document(
    document: Dict[str, Any],
    index: int,
    content_limit: int,
) -> str:
    """
    Format one paper document for prompt context.
    """

    title = document.get("title", "")
    authors = safe_join_authors(document.get("authors", ""))
    year = document.get("year", "")
    source = document.get("source", "")
    pdf_url = document.get("pdf_url", "")
    entry_id = document.get("entry_id", "")

    content = truncate_text(
        get_document_content(document),
        content_limit,
    )

    parts = [
        f"[Paper {index}]",
        f"Title: {title}",
    ]

    if authors:
        parts.append(f"Authors: {authors}")

    if year:
        parts.append(f"Year: {year}")

    if source:
        parts.append(f"Source: {source}")

    if pdf_url:
        parts.append(f"PDF URL: {pdf_url}")

    if entry_id:
        parts.append(f"Entry ID: {entry_id}")

    if content:
        parts.append("Content:")
        parts.append(content)

    return "\n".join(parts)


def format_documents_for_prompt(
    documents: List[Dict[str, Any]],
    max_documents: int = 5,
    content_limit: int = 800,
) -> str:
    """
    Format retrieved documents into prompt-friendly text.
    """

    if not documents:
        return ""

    selected_documents = documents[:max_documents]

    formatted_documents = []

    for index, document in enumerate(selected_documents, start=1):
        formatted_documents.append(
            format_single_document(
                document=document,
                index=index,
                content_limit=content_limit,
            )
        )

    return "\n\n".join(formatted_documents)
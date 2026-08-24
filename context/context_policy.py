from typing import Any, Dict


DEFAULT_CONTEXT_POLICY: Dict[str, Any] = {
    "use_history": True,
    "use_documents": True,
    "use_pdf": False,
    "use_metadata": True,
    "max_documents": 5,
    "document_content_limit": 800,
    "max_pdf_chars": 0,
}


CONTEXT_POLICIES: Dict[str, Dict[str, Any]] = {
    "qa": {
        "use_history": True,
        "use_documents": True,
        "use_pdf": False,
        "use_metadata": True,
        "max_documents": 5,
        "document_content_limit": 800,
        "max_pdf_chars": 0,
    },
    "summarize": {
        "use_history": True,
        "use_documents": True,
        "use_pdf": False,
        "use_metadata": True,
        "max_documents": 5,
        "document_content_limit": 1000,
        "max_pdf_chars": 0,
    },
    "compare": {
        "use_history": True,
        "use_documents": True,
        "use_pdf": False,
        "use_metadata": True,
        "max_documents": 8,
        "document_content_limit": 1600,
        "max_pdf_chars": 0,
    },
    "recommend": {
        "use_history": True,
        "use_documents": True,
        "use_pdf": False,
        "use_metadata": True,
        "max_documents": 8,
        "document_content_limit": 1600,
        "max_pdf_chars": 0,
    },
    "citation": {
        "use_history": False,
        "use_documents": True,
        "use_pdf": False,
        "use_metadata": True,
        "max_documents": 5,
        "document_content_limit": 200,
        "max_pdf_chars": 0,
    },
    "pdf_reading": {
        "use_history": True,
        "use_documents": False,
        "use_pdf": True,
        "use_metadata": True,
        "max_documents": 0,
        "document_content_limit": 0,
        "max_pdf_chars": 12000,
    },
}


def get_context_policy(task_type: str) -> Dict[str, Any]:
    """
    Get context policy by task_type.

    If task_type is unknown, return the default context policy.
    """

    if not task_type:
        return DEFAULT_CONTEXT_POLICY

    return CONTEXT_POLICIES.get(task_type, DEFAULT_CONTEXT_POLICY)

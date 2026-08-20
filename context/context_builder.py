from typing import Any, Dict

from context.context_policy import get_context_policy
from context.document_formatter import format_documents_for_prompt, truncate_text
from prompts.contracts import wrap_untrusted_evidence


def get_state_value(state: Dict[str, Any], key: str, default: Any = "") -> Any:
    """
    Safely get a value from AgentState.
    """

    value = state.get(key, default)

    if value is None:
        return default

    return value


def build_metadata_context(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build metadata context for skills.

    This keeps important runtime information available without mixing it
    directly into the prompt text.
    """

    return {
        "trace_id": get_state_value(state, "trace_id", ""),
        "conversation_id": get_state_value(state, "conversation_id", ""),
        "task_type": get_state_value(state, "task_type", ""),
        "retrieval_score": get_state_value(state, "retrieval_score", 0.0),
        "tools_used": get_state_value(state, "tools_used", []),
        "pdf_path": get_state_value(state, "pdf_path", ""),
        "pdf_page_count": get_state_value(state, "pdf_page_count", 0),
        "pdf_selected_pages": get_state_value(state, "pdf_selected_pages", []),
        "pdf_vision_status": get_state_value(state, "pdf_vision_status", "not_requested"),
        "paper_metadata": get_state_value(state, "paper_metadata", {}),
    }


def build_skill_context(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build a unified context object for downstream Skills.

    The context is controlled by task-specific context policies.
    """

    task_type = get_state_value(state, "task_type", "qa")
    policy = get_context_policy(task_type)

    query = get_state_value(state, "query", "")
    rewritten_query = get_state_value(state, "rewritten_query", "")
    history_text = get_state_value(state, "history_text", "")
    long_term_memory_context = get_state_value(state, "long_term_memory_context", "")
    documents = get_state_value(state, "documents", [])
    pdf_text = get_state_value(state, "pdf_text", "")

    if not policy.get("use_history", True):
        history_text = ""
        long_term_memory_context = ""
    elif long_term_memory_context:
        history_text = f"{history_text}\n\n【按需召回的长期研究记忆】\n{long_term_memory_context}".strip()

    if policy.get("use_documents", True):
        documents_text = format_documents_for_prompt(
            documents=documents,
            max_documents=policy.get("max_documents", 5),
            content_limit=policy.get("document_content_limit", 800),
        )
        documents_text = wrap_untrusted_evidence(documents_text)
    else:
        documents_text = ""

    if policy.get("use_pdf", False):
        pdf_text = truncate_text(
            pdf_text,
            policy.get("max_pdf_chars", 12000),
        )
    else:
        pdf_text = ""

    metadata = (
        build_metadata_context(state)
        if policy.get("use_metadata", True)
        else {}
    )

    return {
        "query": query,
        "rewritten_query": rewritten_query,
        "task_type": task_type,
        "history_text": history_text,
        "long_term_memory_context": long_term_memory_context,
        "documents_text": documents_text,
        "pdf_text": pdf_text,
        "metadata": metadata,
        "policy": policy,
    }


def attach_skill_context(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Attach skill_context to AgentState.

    This function is useful inside Generate Node because it keeps the
    original state structure while adding a normalized context object.
    """

    skill_context = build_skill_context(state)

    return {
        **state,
        "skill_context": skill_context,
    }

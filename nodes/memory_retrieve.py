from agent.state import AgentState
from core.config import settings
from memory.long_term_memory import LongTermMemoryStore, memory_need_detection
from prompts.contracts import wrap_untrusted_evidence


def memory_retrieve_node(state: AgentState) -> AgentState:
    decision = memory_need_detection(state)
    memories = []
    owner_id = state.get("user_id") or state.get("conversation_id", "")
    if decision["needed"] and settings.LONG_TERM_MEMORY_ENABLED and owner_id:
        memories = LongTermMemoryStore(settings.LONG_TERM_MEMORY_DB_PATH).search(
            owner_id, state.get("query", ""), settings.LONG_TERM_MEMORY_TOP_K
        )
    context = ""
    if memories:
        rows = [
            f"[{item['memory_id']}] {item['topic']}（稳定性：{item['stability']}）：{item['content'][:800]}"
            for item in memories
        ]
        raw_context = "\n".join(rows)[: settings.LONG_TERM_MEMORY_CONTEXT_MAX_CHARS]
        context = wrap_untrusted_evidence(raw_context, "经过验证的长期研究记忆")
    status = (
        "disabled" if not settings.LONG_TERM_MEMORY_ENABLED
        else "owner_missing" if decision["needed"] and not owner_id
        else "retrieved" if memories
        else "no_match" if decision["needed"]
        else "not_needed"
    )
    retrieval = {
        **decision,
        "status": status,
        "retrieved_count": len(memories),
        "memory_ids": [item["memory_id"] for item in memories],
        "context_chars": len(context),
        "additional_llm_calls": 0,
    }
    return {
        "memory_retrieval": retrieval,
        "retrieved_memories": memories,
        "long_term_memory_context": context,
        "paper_metadata": {**state.get("paper_metadata", {}), "memory_retrieval": retrieval},
    }

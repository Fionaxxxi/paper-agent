from agent.state import AgentState
from core.config import settings
from memory.long_term_memory import LongTermMemoryStore, TIME_SENSITIVE_SIGNALS, evaluate_memory_write


def memory_write_gate_node(state: AgentState) -> AgentState:
    if not settings.LONG_TERM_MEMORY_ENABLED:
        result = {"allowed": False, "reason": "feature_disabled", "action": "skip", "memory_id": ""}
        return {
            "memory_write_gate": result,
            "paper_metadata": {**state.get("paper_metadata", {}), "memory_write_gate": result},
        }
    gate = evaluate_memory_write(state, settings.LONG_TERM_MEMORY_VALUE_THRESHOLD)
    result = {**gate, "action": "skip", "memory_id": ""}
    if gate["allowed"]:
        metadata = dict(state.get("memory_metadata", {}))
        time_sensitive = bool(metadata.get("time_sensitive")) or any(
            signal in state.get("query", "") for signal in TIME_SENSITIVE_SIGNALS
        )
        stability = "snapshot" if time_sensitive else metadata.get("stability", "unknown")
        evidence_ids = [
            item.get("evidence_id") for item in state.get("evidence_store", {}).get("evidence", [])
            if item.get("evidence_id")
        ]
        stored = LongTermMemoryStore(settings.LONG_TERM_MEMORY_DB_PATH).write(
            owner_id=state.get("user_id") or state.get("conversation_id", ""), topic=metadata.get("topic") or state.get("query", "")[:160],
            memory_type=metadata.get("memory_type", "research_finding"), content=state.get("answer", ""),
            value_score=float(metadata.get("value_score", 0)), stability=stability,
            time_sensitive=time_sensitive, evidence_ids=evidence_ids,
            trace_id=state.get("trace_id", ""), snapshot_days=settings.LONG_TERM_MEMORY_SNAPSHOT_DAYS,
        )
        result = {**gate, **stored, "time_sensitive": time_sensitive, "stability": stability}
    return {
        "memory_write_gate": result,
        "paper_metadata": {**state.get("paper_metadata", {}), "memory_write_gate": result},
    }

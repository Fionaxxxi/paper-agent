import time
from typing import Any, Dict, List

from agent.graph import build_graph
from core.logger import logger
from core.trace import generate_trace_id
from memory.conversation_memory import (
    format_memory_context,
    get_memory_store,
    load_memory_context,
    save_message,
    update_research_memory,
)
from memory.llm_wiki import publish_agent_result
from memory.graph_checkpointer import get_default_graph_checkpointer
from document_loader.pdf_loader import load_pdf_text
from core.config import settings


class PaperAgentService:
    """
    PaperAgent 服务层。

    作用：
    1. 封装 LangGraph 调用
    2. 生成 trace_id
    3. 初始化 AgentState
    4. 整理 API 响应数据
    """

    def __init__(self, checkpointer=None):
        if checkpointer is None:
            checkpointer = get_default_graph_checkpointer(
                settings.LANGGRAPH_CHECKPOINT_DB_PATH,
                enabled=settings.LANGGRAPH_CHECKPOINT_ENABLED,
            )
        self.graph = build_graph(checkpointer=checkpointer)

    def chat(
            self,
            query: str,
            conversation_id: str | None = None,
            pdf_path: str | None = None,
    ) -> Dict[str, Any]:
        trace_id = generate_trace_id()
        start_time = time.perf_counter()

        if not conversation_id:
            conversation_id = trace_id

        memory_context = load_memory_context(conversation_id)
        pending_clarification = (
            get_memory_store().load_checkpoint(
                conversation_id, "pending_clarification"
            ) or {}
        )
        history = memory_context.recent_messages
        history_text = format_memory_context(memory_context)

        logger.info(
            "trace_id=%s | conversation_id=%s | api received query=%s",
            trace_id,
            conversation_id,
            query,
        )

        pdf_text = ""
        pdf_page_count = 0
        pdf_error = ""

        if pdf_path:
            pdf_result = load_pdf_text(
                pdf_path=pdf_path,
                max_chars=settings.PDF_MAX_CHARS,
            )
            pdf_text = pdf_result.get("text", "")
            pdf_page_count = pdf_result.get("page_count", 0)
            pdf_error = pdf_result.get("error", "")

        initial_state = {
            "trace_id": trace_id,
            "conversation_id": conversation_id,
            "history": history,
            "history_text": history_text,

            "query": query,
            "input_intent": "",
            "documents": [],
            "retrieval_score": 0.0,
            "retrieval_outcome": "",
            "retrieval_stop_reason": "",
            "answer": "",
            "pdf_path": pdf_path or "",
            "pdf_text": pdf_text,
            "pdf_page_count": pdf_page_count,
            "pdf_error": pdf_error,

            "retry_count": 0,
            "retry_query": "",
            "retrieval_replan": {},
            "tools_used": [],
            "token_usage": 0,
            "input_token_usage": 0,
            "output_token_usage": 0,
            "llm_call_count": 0,
            "llm_failed_call_count": 0,
            "llm_usage": [],
            "answer_reflection_count": 0,
            "answer_verification": {},
            "answer_initial_score": 0.0,
            "answer_initial_verification": {},
            "answer_reflection": {},
            "answer_before_reflection": "",
            "answer_reflection_restored": False,
            "answer_stop_reason": "",
            "error_message": None,
            "is_valid": True,
            "rewritten_query": "",
            "task_type": "",
            "sub_queries": [],
            "query_plan_enabled": False,
            "query_plan_reason": "",
            "query_complexity": "",
            "complexity_reason": "",
            "task_level": "",
            "research_analysis": {},
            "research_brief": {},
            "research_plan": {},
            "research_plan_validation": {},
            "clarification_required": False,
            "clarification_question": "",
            "clarification_candidates": [],
            "pending_clarification": pending_clarification,
            "original_query": "",
            "resolved_query": "",
            "resolved_referent": "",
            "research_schedule": {},
            "evidence_store": {},
            "repository_evidence": [],
            "repository_enrichment": {},
            "research_coverage": {},
            "citation_validation": {},
            "citation_repair": {},
            "node_timings": {},
            "paper_metadata": {
                "conversation_id": conversation_id,
                "history_count": len(history),
                "memory_total_message_count": memory_context.total_message_count,
                "memory_compressed_message_count": memory_context.compressed_message_count,
                "memory_active_topics": memory_context.active_topics,
                "memory_active_papers": memory_context.active_papers,
                "langgraph_checkpoint_enabled": settings.LANGGRAPH_CHECKPOINT_ENABLED,
                "langgraph_thread_id": conversation_id,
                "pdf_path": pdf_path,
                "pdf_page_count": pdf_page_count,
                "pdf_error": pdf_error,
            },
        }

        checkpoint_config = {"configurable": {"thread_id": conversation_id}}
        result = self.graph.invoke(initial_state, config=checkpoint_config)
        get_memory_store().save_checkpoint(
            conversation_id,
            "pending_clarification",
            result.get("pending_clarification", {}),
        )

        total_time = round(time.perf_counter() - start_time, 2)

        node_timings = {
            **result.get("node_timings", {}),
            "total": total_time,
        }

        papers = self.format_papers(result.get("documents", []))
        answer = result.get("answer", "")

        save_message(conversation_id, "user", query)
        save_message(conversation_id, "assistant", answer)
        if not result.get("clarification_required"):
            update_research_memory(
                conversation_id,
                query=result.get("query", query),
                documents=result.get("documents", []),
            )
        wiki_result = publish_agent_result(
            result,
            root=settings.LLM_WIKI_DIR,
            enabled=settings.LLM_WIKI_AUTO_PUBLISH_ENABLED,
            allowed_task_types={
                item.strip()
                for item in settings.LLM_WIKI_ALLOWED_TASK_TYPES.split(",")
                if item.strip()
            },
        )

        logger.info(
            "trace_id=%s | conversation_id=%s | api workflow finished | total_time=%ss",
            trace_id,
            conversation_id,
            total_time,
        )

        return {
            "answer": answer,
            "task_type": result.get("task_type", "qa"),
            "retrieval_score": result.get("retrieval_score", 0.0),
            "tools_used": result.get("tools_used", []),
            "papers": papers,
            "paper_metadata": {
                **result.get("paper_metadata", {}),
                "conversation_id": conversation_id,
                "history_count": len(history),
                "memory_total_message_count": memory_context.total_message_count,
                "memory_compressed_message_count": memory_context.compressed_message_count,
                "memory_active_topics": memory_context.active_topics,
                "memory_active_papers": memory_context.active_papers,
                "llm_wiki": wiki_result.as_dict(),
                "langgraph_checkpoint_enabled": settings.LANGGRAPH_CHECKPOINT_ENABLED,
                "langgraph_thread_id": conversation_id,
                "research_analysis": result.get("research_analysis", {}),
                "research_brief": result.get("research_brief", {}),
                "research_plan": result.get("research_plan", {}),
                "research_plan_validation": result.get(
                    "research_plan_validation", {}
                ),
                "clarification_required": result.get("clarification_required", False),
                "clarification_question": result.get("clarification_question", ""),
                "clarification_candidates": result.get("clarification_candidates", []),
                "resolved_referent": result.get("resolved_referent", ""),
                "resolved_query": result.get("resolved_query", ""),
                "research_schedule": result.get("research_schedule", {}),
                "evidence_store": result.get("evidence_store", {}),
                "repository_enrichment": result.get("repository_enrichment", {}),
                "research_coverage": result.get("research_coverage", {}),
                "citation_validation": result.get("citation_validation", {}),
                "citation_repair": result.get("citation_repair", {}),
                "pdf_path": pdf_path,
                "pdf_page_count": result.get("pdf_page_count", pdf_page_count),
                "pdf_error": result.get("pdf_error", pdf_error),
                "llm_call_count": result.get("llm_call_count", 0),
                "llm_failed_call_count": result.get("llm_failed_call_count", 0),
                "input_token_usage": result.get("input_token_usage", 0),
                "output_token_usage": result.get("output_token_usage", 0),
                "token_usage": result.get("token_usage", 0),
            },
            "node_timings": node_timings,
            "trace_id": trace_id,
            "conversation_id": conversation_id,
            "pdf_path": pdf_path,
            "pdf_page_count": result.get("pdf_page_count", pdf_page_count),
        }

    def format_papers(self, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        API 响应中的论文内容不返回完整摘要，只保留前 300 字。
        避免接口响应过大，也方便前端展示。
        """

        formatted_papers = []

        for paper in papers:
            content = paper.get("content", "")

            if content and len(content) > 300:
                content = content[:300] + "...[内容已截断]"

            formatted_papers.append(
                {
                    "title": paper.get("title"),
                    "authors": paper.get("authors", []),
                    "year": paper.get("year"),
                    "content": content,
                    "pdf_url": paper.get("pdf_url"),
                    "entry_id": paper.get("entry_id"),
                    "source": paper.get("source"),
                    "document_id": paper.get("document_id"),
                    "chunk_id": paper.get("chunk_id"),
                    "page": paper.get("page"),
                    "retrieval_score": paper.get("retrieval_score"),
                }
            )

        return formatted_papers


paper_agent_service = PaperAgentService()

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
from memory.graph_checkpointer import delete_thread_checkpoints
from memory.long_term_memory import LongTermMemoryStore
from document_loader.pdf_loader import load_pdf_pages, load_pdf_text
from document_loader.pdf_page_selector import select_visual_pages
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
            user_id: str | None = None,
            pdf_path: str | None = None,
            pdf_pages: list[int] | None = None,
            retrieval_scope: str = "auto",
            selected_document: dict[str, Any] | None = None,
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
        pdf_selected_pages = list(pdf_pages or [])
        pdf_page_images: list[str] = []
        pdf_vision_status = "not_requested"
        pdf_page_selection = {"enabled": False, "selected_pages": [], "reason": "not_requested"}

        if pdf_path:
            if not pdf_selected_pages:
                pdf_page_selection = select_visual_pages(
                    pdf_path, query, max_pages=settings.PDF_MAX_SELECTED_PAGES
                )
                pdf_selected_pages = pdf_page_selection.get("selected_pages", [])
            pdf_result = (
                load_pdf_pages(
                    pdf_path=pdf_path,
                    pages=pdf_selected_pages,
                    max_chars=settings.PDF_MAX_CHARS,
                    max_pages=settings.PDF_MAX_SELECTED_PAGES,
                    image_cache_dir=settings.PDF_PAGE_IMAGE_CACHE_DIR,
                )
                if pdf_selected_pages
                else load_pdf_text(pdf_path=pdf_path, max_chars=settings.PDF_MAX_CHARS)
            )
            pdf_text = pdf_result.get("text", "")
            pdf_page_count = pdf_result.get("page_count", 0)
            pdf_error = pdf_result.get("error", "")
            pdf_selected_pages = pdf_result.get("selected_pages", pdf_selected_pages)
            pdf_page_images = pdf_result.get("image_paths", [])
            if pdf_selected_pages:
                pdf_vision_status = (
                    "ready" if pdf_page_images and settings.PDF_VISION_ENABLED
                    else "rendered_text_only" if pdf_page_images
                    else "renderer_unavailable_text_only"
                )

        selected_document = selected_document or {}
        active_papers = list(memory_context.active_papers)
        if selected_document.get("title") and selected_document["title"] not in active_papers:
            active_papers.insert(0, selected_document["title"])

        initial_state = {
            "trace_id": trace_id,
            "conversation_id": conversation_id,
            "user_id": user_id or "",
            "history": history,
            "history_text": history_text,

            "query": query,
            "input_intent": "",
            "documents": [],
            "retrieval_score": 0.0,
            "retrieval_outcome": "",
            "retrieval_stop_reason": "",
            "retrieval_evaluation": {},
            "retrieval_strategy": {},
            "retrieval_scope": retrieval_scope,
            "answer": "",
            "pdf_path": pdf_path or "",
            "pdf_text": pdf_text,
            "pdf_page_count": pdf_page_count,
            "pdf_error": pdf_error,
            "pdf_selected_pages": pdf_selected_pages,
            "pdf_page_images": pdf_page_images,
            "pdf_vision_status": pdf_vision_status,
            "pdf_page_selection": pdf_page_selection,

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
            "claim_evidence_validation": {},
            "citation_repair": {},
            "pdf_grounding_validation": {},
            "multi_agent_trace": {},
            "memory_metadata": {},
            "memory_write_gate": {},
            "memory_retrieval": {},
            "retrieved_memories": [],
            "long_term_memory_context": "",
            "node_timings": {},
            "paper_metadata": {
                "conversation_id": conversation_id,
                "user_id": user_id or "",
                "history_count": len(history),
                "memory_total_message_count": memory_context.total_message_count,
                "memory_compressed_message_count": memory_context.compressed_message_count,
                "memory_active_topics": memory_context.active_topics,
                "memory_active_papers": active_papers,
                "selected_document_id": selected_document.get("document_id", ""),
                "selected_document_title": selected_document.get("title", ""),
                "selected_document_source": "personal_library" if selected_document else "",
                "langgraph_checkpoint_enabled": settings.LANGGRAPH_CHECKPOINT_ENABLED,
                "langgraph_thread_id": conversation_id,
                "pdf_path": pdf_path,
                "pdf_page_count": pdf_page_count,
                "pdf_error": pdf_error,
                "pdf_selected_pages": pdf_selected_pages,
                "pdf_vision_status": pdf_vision_status,
                "pdf_page_selection": pdf_page_selection,
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
                "user_id": user_id or "",
                "history_count": len(history),
                "memory_total_message_count": memory_context.total_message_count,
                "memory_compressed_message_count": memory_context.compressed_message_count,
                "memory_active_topics": memory_context.active_topics,
                "memory_active_papers": active_papers,
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
                "claim_evidence_validation": result.get("claim_evidence_validation", {}),
                "citation_repair": result.get("citation_repair", {}),
                "pdf_grounding_validation": result.get("pdf_grounding_validation", {}),
                "multi_agent_trace": result.get("multi_agent_trace", {}),
                "memory_metadata": result.get("memory_metadata", {}),
                "memory_write_gate": result.get("memory_write_gate", {}),
                "memory_retrieval": result.get("memory_retrieval", {}),
                "pdf_path": None if selected_document else pdf_path,
                "pdf_page_count": result.get("pdf_page_count", pdf_page_count),
                "pdf_error": result.get("pdf_error", pdf_error),
                "pdf_selected_pages": result.get("pdf_selected_pages", pdf_selected_pages),
                "pdf_vision_status": result.get("pdf_vision_status", pdf_vision_status),
                "pdf_page_selection": result.get("pdf_page_selection", pdf_page_selection),
                "llm_call_count": result.get("llm_call_count", 0),
                "llm_failed_call_count": result.get("llm_failed_call_count", 0),
                "input_token_usage": result.get("input_token_usage", 0),
                "output_token_usage": result.get("output_token_usage", 0),
                "token_usage": result.get("token_usage", 0),
            },
            "node_timings": node_timings,
            "trace_id": trace_id,
            "conversation_id": conversation_id,
            "pdf_path": None if selected_document else pdf_path,
            "pdf_page_count": result.get("pdf_page_count", pdf_page_count),
            "pdf_selected_pages": result.get("pdf_selected_pages", pdf_selected_pages),
            "pdf_vision_status": result.get("pdf_vision_status", pdf_vision_status),
        }

    def format_papers(self, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        API 响应中的论文内容不返回完整摘要，只保留前 300 字。
        避免接口响应过大，也方便前端展示。
        """

        formatted_papers = []

        for paper in papers:
            content = paper.get("content", "")
            doi = str(paper.get("doi") or "").strip()
            entry_id = str(paper.get("entry_id") or "").strip()
            web_url = str(paper.get("landing_page_url") or "").strip()
            if not web_url and doi:
                normalized_doi = doi.removeprefix("doi:").removeprefix("https://doi.org/").removeprefix("http://doi.org/")
                web_url = f"https://doi.org/{normalized_doi}"
            if not web_url and entry_id.startswith(("http://", "https://")):
                web_url = entry_id
            if not web_url and paper.get("source") == "arxiv" and entry_id:
                web_url = f"https://arxiv.org/abs/{entry_id}"

            if content and len(content) > 300:
                content = content[:300] + "...[内容已截断]"

            formatted_papers.append(
                {
                    "title": paper.get("title"),
                    "authors": paper.get("authors", []),
                    "year": paper.get("year"),
                    "content": content,
                    "pdf_url": paper.get("pdf_url"),
                    "web_url": web_url,
                    "landing_page_url": paper.get("landing_page_url"),
                    "doi": doi,
                    "entry_id": paper.get("entry_id"),
                    "source": paper.get("source"),
                    "document_id": paper.get("document_id"),
                    "chunk_id": paper.get("chunk_id"),
                    "page": paper.get("page"),
                    "retrieval_score": paper.get("retrieval_score"),
                }
            )

        return formatted_papers

    def list_long_term_memories(self, owner_id: str, *, include_inactive: bool = False) -> Dict[str, Any]:
        store = LongTermMemoryStore(settings.LONG_TERM_MEMORY_DB_PATH)
        store.expire_snapshots()
        return {
            "owner_id": owner_id,
            "memories": store.list_memories(owner_id, include_inactive=include_inactive),
            "statistics": store.statistics(owner_id),
        }

    def list_memory_conflicts(self, owner_id: str) -> Dict[str, Any]:
        store = LongTermMemoryStore(settings.LONG_TERM_MEMORY_DB_PATH)
        return {"owner_id": owner_id, "conflicts": store.list_conflicts(owner_id)}

    def delete_long_term_memory(self, owner_id: str, memory_id: str) -> bool:
        return LongTermMemoryStore(settings.LONG_TERM_MEMORY_DB_PATH).delete_memory(owner_id, memory_id)

    def delete_owner_memory(self, owner_id: str) -> Dict[str, int]:
        """隐私删除：同时清除会话、派生长期记忆和当前进程的工作流检查点。"""
        get_memory_store().delete_conversation(owner_id)
        long_term_count = LongTermMemoryStore(settings.LONG_TERM_MEMORY_DB_PATH).delete_owner(owner_id)
        checkpoint_count = delete_thread_checkpoints(owner_id)
        return {"long_term_deleted": long_term_count, "checkpoint_rows_deleted": checkpoint_count}

    def expire_long_term_snapshots(self) -> int:
        return LongTermMemoryStore(settings.LONG_TERM_MEMORY_DB_PATH).expire_snapshots()


paper_agent_service = PaperAgentService()

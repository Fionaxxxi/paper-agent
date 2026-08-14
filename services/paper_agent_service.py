import time
from typing import Any, Dict, List

from agent.graph import build_graph
from core.logger import logger
from core.trace import generate_trace_id
from memory.conversation_memory import (
    format_memory_context,
    load_memory_context,
    save_message,
    update_research_memory,
)
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

    def __init__(self):
        self.graph = build_graph()

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
            "pdf_path": pdf_path or "",
            "pdf_text": pdf_text,
            "pdf_page_count": pdf_page_count,
            "pdf_error": pdf_error,

            "retry_count": 0,
            "tools_used": [],
            "token_usage": 0,
            "input_token_usage": 0,
            "output_token_usage": 0,
            "llm_call_count": 0,
            "llm_failed_call_count": 0,
            "llm_usage": [],
            "answer_reflection_count": 0,
            "node_timings": {},
            "paper_metadata": {
                "conversation_id": conversation_id,
                "history_count": len(history),
                "memory_total_message_count": memory_context.total_message_count,
                "memory_compressed_message_count": memory_context.compressed_message_count,
                "memory_active_topics": memory_context.active_topics,
                "memory_active_papers": memory_context.active_papers,
                "pdf_path": pdf_path,
                "pdf_page_count": pdf_page_count,
                "pdf_error": pdf_error,
            },
        }

        result = self.graph.invoke(initial_state)

        total_time = round(time.perf_counter() - start_time, 2)

        node_timings = {
            **result.get("node_timings", {}),
            "total": total_time,
        }

        papers = self.format_papers(result.get("documents", []))
        answer = result.get("answer", "")

        save_message(conversation_id, "user", query)
        save_message(conversation_id, "assistant", answer)
        update_research_memory(
            conversation_id,
            query=query,
            documents=result.get("documents", []),
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

import time
from typing import Any, Dict

from agent.graph import build_graph
from core.logger import logger
from core.trace import generate_trace_id


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

    def chat(self, query: str) -> Dict[str, Any]:
        trace_id = generate_trace_id()
        start_time = time.perf_counter()

        logger.info("trace_id=%s | api received query=%s", trace_id, query)

        initial_state = {
            "trace_id": trace_id,
            "query": query,
            "retry_count": 0,
            "tools_used": [],
            "token_usage": 0,
            "node_timings": {},
            "paper_metadata": {},
        }

        result = self.graph.invoke(initial_state)

        total_time = round(time.perf_counter() - start_time, 2)

        node_timings = {
            **result.get("node_timings", {}),
            "total": total_time,
        }

        logger.info(
            "trace_id=%s | api workflow finished | total_time=%ss",
            trace_id,
            total_time,
        )

        return {
            "answer": result.get("answer", ""),
            "task_type": result.get("task_type", "qa"),
            "retrieval_score": result.get("retrieval_score", 0.0),
            "tools_used": result.get("tools_used", []),
            "papers": result.get("documents", []),
            "paper_metadata": result.get("paper_metadata", {}),
            "node_timings": node_timings,
            "trace_id": trace_id,
        }


paper_agent_service = PaperAgentService()
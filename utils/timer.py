import time
from typing import Callable

from agent.state import AgentState
from core.logger import logger


def timed_node(node_name: str, node_func: Callable[[AgentState], AgentState]):
    """
    给 LangGraph 节点添加耗时统计。
    每个节点执行完成后立即打印耗时，并写入日志。
    """

    def wrapper(state: AgentState) -> AgentState:
        trace_id = state.get("trace_id", "unknown")

        print(f"\n[Node Start] {node_name}")
        logger.info("trace_id=%s | node=%s | status=start", trace_id, node_name)

        start_time = time.perf_counter()

        try:
            result = node_func(state)

            elapsed = round(time.perf_counter() - start_time, 2)

            print(f"[Node Done] {node_name}: {elapsed}s")
            logger.info(
                "trace_id=%s | node=%s | status=success | latency=%ss",
                trace_id,
                node_name,
                elapsed,
            )

            if node_name == "query_rewrite":
                print(f"  rewritten_query: {result.get('rewritten_query')}")

            elif node_name == "retrieve":
                documents = result.get("documents", [])
                print(f"  documents_count: {len(documents)}")
                if documents:
                    print(f"  first_paper: {documents[0].get('title')}")

            elif node_name == "evaluate":
                print(f"  retrieval_score: {result.get('retrieval_score')}")

            elif node_name == "reason":
                print(f"  task_type: {result.get('task_type')}")

            elif node_name == "generate":
                answer = result.get("answer", "")
                print(f"  answer_length: {len(answer)}")

            old_timings = state.get("node_timings", {})

            return {
                **result,
                "node_timings": {
                    **old_timings,
                    node_name: elapsed,
                },
            }

        except Exception as e:
            elapsed = round(time.perf_counter() - start_time, 2)

            print(f"[Node Failed] {node_name}: {elapsed}s")
            print(f"  error_type: {type(e).__name__}")
            print(f"  error_message: {e}")

            logger.exception(
                "trace_id=%s | node=%s | status=failed | latency=%ss | error=%s",
                trace_id,
                node_name,
                elapsed,
                e,
            )

            raise

    return wrapper
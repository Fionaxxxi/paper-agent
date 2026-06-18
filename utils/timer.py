import time
from typing import Callable

from agent.state import AgentState


def timed_node(node_name: str, node_func: Callable[[AgentState], AgentState]):
    """
    给 LangGraph 节点添加耗时统计。
    每个节点执行完成后，立即打印该节点耗时。
    """

    def wrapper(state: AgentState) -> AgentState:
        print(f"\n[Node Start] {node_name}")

        start_time = time.perf_counter()

        result = node_func(state)

        elapsed = round(time.perf_counter() - start_time, 2)

        print(f"[Node Done] {node_name}: {elapsed}s")

        old_timings = state.get("node_timings", {})

        return {
            **result,
            "node_timings": {
                **old_timings,
                node_name: elapsed,
            },
        }

    return wrapper
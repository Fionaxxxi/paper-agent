import time

from agent.graph import build_graph
from core.trace import generate_trace_id
from core.logger import logger


def main():
    graph = build_graph()

    print("=== PaperAgent ===")
    print("输入 exit 退出程序")

    logger.info("PaperAgent command line app started")

    while True:
        query = input("\n请输入论文问题：").strip()

        if query.lower() in ["exit", "quit", "q"]:
            print("已退出 PaperAgent。")
            logger.info("PaperAgent command line app exited")
            break

        if not query:
            print("问题不能为空。")
            continue

        trace_id = generate_trace_id()
        start_time = time.perf_counter()

        logger.info("trace_id=%s | received query=%s", trace_id, query)

        result = graph.invoke(
            {
                "trace_id": trace_id,
                "query": query,
                "retry_count": 0,
                "tools_used": [],
                "token_usage": 0,
                "node_timings": {},
                "paper_metadata": {},
            }
        )

        total_time = round(time.perf_counter() - start_time, 2)

        print("\n" + "=" * 50)
        print(result.get("answer", "没有生成答案"))
        print("=" * 50)

        print(f"\n[Total Runtime] {total_time}s")
        print(f"[Trace ID] {trace_id}")

        logger.info(
            "trace_id=%s | workflow finished | total_time=%ss",
            trace_id,
            total_time,
        )


if __name__ == "__main__":
    main()
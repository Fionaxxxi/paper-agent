from agent.graph import build_graph


def main():
    graph = build_graph()

    print("=== PaperAgent ===")
    print("输入 exit 退出程序")

    while True:
        query = input("\n请输入论文问题：").strip()

        if query.lower() in ["exit", "quit", "q"]:
            print("已退出 PaperAgent。")
            break

        if not query:
            print("问题不能为空。")
            continue

        result = graph.invoke(
            {
                "query": query,
                "retry_count": 0,
                "tools_used": [],
                "token_usage": 0,
            }
        )

        print("\n" + "=" * 50)
        print(result.get("answer", "没有生成答案"))
        print("=" * 50)


if __name__ == "__main__":
    main()
from agent.graph import build_graph
from memory.graph_checkpointer import create_sqlite_checkpointer


def test_official_sqlite_checkpointer_persists_state_across_graph_instances(tmp_path):
    path = tmp_path / "checkpoints.db"
    config = {"configurable": {"thread_id": "conversation-1"}}
    first_saver = create_sqlite_checkpointer(path)
    first_graph = build_graph(checkpointer=first_saver)

    result = first_graph.invoke({"query": "hi", "retry_count": 0}, config=config)
    assert result["input_intent"] == "greeting"
    first_saver.conn.close()

    second_saver = create_sqlite_checkpointer(path)
    second_graph = build_graph(checkpointer=second_saver)
    snapshot = second_graph.get_state(config)

    assert snapshot.values["query"] == "hi"
    assert snapshot.values["answer"].startswith("你好")
    assert snapshot.next == ()
    second_saver.conn.close()


def test_sqlite_checkpointer_isolates_threads_and_supports_deletion(tmp_path):
    saver = create_sqlite_checkpointer(tmp_path / "checkpoints.db")
    graph = build_graph(checkpointer=saver)
    first = {"configurable": {"thread_id": "c1"}}
    second = {"configurable": {"thread_id": "c2"}}

    graph.invoke({"query": "hi", "retry_count": 0}, config=first)
    graph.invoke({"query": "谢谢", "retry_count": 0}, config=second)

    assert graph.get_state(first).values["input_intent"] == "greeting"
    assert graph.get_state(second).values["input_intent"] == "thanks"

    saver.delete_thread("c1")
    assert saver.get_tuple(first) is None
    assert saver.get_tuple(second) is not None
    saver.conn.close()


def test_checkpointer_can_be_disabled_without_creating_a_database(tmp_path):
    path = tmp_path / "disabled.db"

    saver = create_sqlite_checkpointer(path, enabled=False)

    assert saver is None
    assert not path.exists()

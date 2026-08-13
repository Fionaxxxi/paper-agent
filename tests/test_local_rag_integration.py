import nodes.retrieve as retrieve_module


def test_local_rag_mode_enters_main_retrieval_flow(monkeypatch):
    monkeypatch.setattr(retrieve_module.settings,"RETRIEVAL_MODE","local_rag")
    monkeypatch.setattr(retrieve_module.settings,"LOCAL_RAG_MAX_RESULTS",3)
    from local_rag import runtime
    monkeypatch.setattr(runtime,"search_local_papers",lambda query,limit:{"documents":[{"title":"RAG","content":"evidence","source":"local_rag","chunk_id":"c1","page":2}],"decision":{"route":"hybrid","dense_top1":.6,"dense_margin":.02}})

    result=retrieve_module.retrieve_by_query("什么是 RAG",{})

    assert result["retrieval_source"] == "local_rag"
    assert result["documents"][0]["chunk_id"] == "c1"
    assert result["local_rag_decision"]["route"] == "hybrid"
    assert result["tools_used"] == ["local_rag_retriever","local_rag_hybrid"]


def test_retrieve_node_exposes_local_rag_route_in_metadata(monkeypatch):
    monkeypatch.setattr(retrieve_module.settings,"RETRIEVAL_MODE","local_rag")
    monkeypatch.setattr(retrieve_module,"retrieve_by_query",lambda query,state:{"documents":[{"title":"DPR"}],"tools_used":["local_rag_dense"],"retrieval_source":"local_rag","retrieval_mode":"local_rag","cache_hit":True,"local_rag_decision":{"route":"dense"},"ranking_strategy":"confidence_gated_bm25_dense_rrf"})

    result=retrieve_module.retrieve_node({"query":"DPR","task_type":"qa","tools_used":[],"paper_metadata":{}})

    assert result["paper_metadata"]["retrieval_mode"] == "local_rag"
    assert result["paper_metadata"]["local_rag_decision"]["route"] == "dense"
    assert result["paper_metadata"]["ranking_strategy"] == "confidence_gated_bm25_dense_rrf"

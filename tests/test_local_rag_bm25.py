from local_rag.bm25 import BM25Retriever, mixed_tokenize
from local_rag.contracts import TextChunk
from eval_harness.local_rag_benchmark import _metrics


def _chunk(identity, text):
    return TextChunk("d", identity, 1, 1, text, 0, len(text))


def test_mixed_tokenizer_supports_chinese_and_english_queries():
    tokens = mixed_tokenize("GraphRAG 如何进行图检索 44.5%")
    assert {"graphrag", "如", "如何", "图检", "44.5%"} <= set(tokens)


def test_bm25_ranks_matching_chunk_first_and_is_deterministic():
    retriever = BM25Retriever([_chunk("c1", "dense passage retrieval dual encoder"), _chunk("c2", "agent memory reflection")])
    first = retriever.search("dense retrieval", 2)
    second = retriever.search("dense retrieval", 2)
    assert first == second
    assert first[0][0].chunk_id == "c1"
    assert first[0][1] > first[1][1]


def test_bm25_rejects_invalid_configuration_and_limit():
    import pytest
    with pytest.raises(ValueError):
        BM25Retriever([])
    retriever = BM25Retriever([_chunk("c1", "text")])
    with pytest.raises(ValueError):
        retriever.search("text", 0)


def test_local_rag_metrics_use_exact_gold_chunk_rank():
    metrics = _metrics(["noise", "gold", "other"], {"gold"}, [1, 3])
    assert metrics["recall_at_1"] == 0
    assert metrics["recall_at_3"] == 1
    assert metrics["mrr_at_3"] == 0.5
    assert metrics["ndcg_at_3"] == 0.63093


def test_local_rag_metrics_do_not_double_count_duplicate_page_hits():
    metrics = _metrics(["page-1", "page-1", "noise"], {"page-1"}, [3])
    assert metrics["recall_at_3"] == 1
    assert metrics["mrr_at_3"] == 1
    assert metrics["ndcg_at_3"] == 1

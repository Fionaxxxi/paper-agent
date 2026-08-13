import numpy as np
import pytest

from eval_harness.local_rag_dense_eval import warm_up_retriever
from local_rag.contracts import TextChunk
from local_rag.dense import DenseIndexCache, DenseRetriever, _normalize


class FakeEmbedding:
    def embed(self, texts, **_kwargs):
        mapping = {"relevant": [3.0, 0.0], "noise": [0.0, 4.0], "query": [2.0, 0.0]}
        return iter(np.asarray(mapping[text], dtype=np.float32) for text in texts)


def _chunk(identity, text):
    return TextChunk("d", identity, 1, 1, text, 0, len(text))


def test_dense_retriever_normalizes_vectors_and_ranks_by_cosine():
    retriever = DenseRetriever([_chunk("c1", "noise"), _chunk("c2", "relevant")], FakeEmbedding())
    result = retriever.search("query", 2)
    assert result[0][0].chunk_id == "c2"
    assert result[0][1] == 1.0
    assert result[1][1] == 0.0


def test_dense_retriever_rejects_zero_vectors_and_invalid_inputs():
    with pytest.raises(ValueError, match="non-zero"):
        _normalize(np.asarray([[0.0, 0.0]]))
    with pytest.raises(ValueError):
        DenseRetriever([], FakeEmbedding())


def test_dense_index_cache_round_trips_vectors_and_invalidates_changed_corpus(tmp_path):
    chunks = [_chunk("c1", "relevant"), _chunk("c2", "noise")]
    cache = DenseIndexCache(tmp_path)
    fingerprint = cache.fingerprint(chunks, "model-v1", "parser:1", "chunker:1")
    cache.save(fingerprint, np.asarray([[3.0, 0.0], [0.0, 4.0]], dtype=np.float32))

    loaded = cache.load(fingerprint, 2)
    assert loaded is not None
    assert np.allclose(np.linalg.norm(loaded, axis=1), [1.0, 1.0])
    changed = cache.fingerprint([_chunk("c1", "changed")], "model-v1", "parser:1", "chunker:1")
    assert changed != fingerprint
    assert cache.load(changed, 1) is None


def test_dense_retriever_reuses_cached_vectors_without_document_embedding():
    class QueryOnlyEmbedding:
        def embed(self, texts, **_kwargs):
            assert texts == ["query"]
            return iter([np.asarray([1.0, 0.0], dtype=np.float32)])

    retriever = DenseRetriever([_chunk("c1", "relevant")], QueryOnlyEmbedding(), vectors=np.asarray([[5.0, 0.0]]))
    assert retriever.search("query", 1)[0][0].chunk_id == "c1"


def test_dense_warmup_is_fixed_and_excluded_from_formal_timing():
    retriever = DenseRetriever([_chunk("c1", "relevant")], FakeEmbedding(), vectors=np.asarray([[1.0, 0.0]]))
    warmup = warm_up_retriever(retriever, query="query", count=2)
    assert warmup["count"] == 2
    assert len(warmup["latency_ms"]) == 2
    assert warmup["excluded_from_formal_timing"] is True

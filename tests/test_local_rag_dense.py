import numpy as np
import pytest

from local_rag.contracts import TextChunk
from local_rag.dense import DenseRetriever, _normalize


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

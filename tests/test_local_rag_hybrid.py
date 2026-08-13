from local_rag.contracts import TextChunk
from local_rag.hybrid import ReciprocalRankFusionRetriever


def _chunk(identity):
    return TextChunk("d",identity,1,1,identity,0,len(identity))


class FixedRetriever:
    def __init__(self, identities): self.identities=identities
    def search(self, _query, limit): return [(_chunk(identity),100-index) for index,identity in enumerate(self.identities[:limit])]


def test_rrf_rewards_cross_retriever_agreement_without_mixing_raw_scores():
    hybrid=ReciprocalRankFusionRetriever(FixedRetriever(["lexical","shared"]),FixedRetriever(["semantic","shared"]),rrf_k=20,candidate_limit=2)
    results=hybrid.search("query",3)
    assert results[0][0].chunk_id == "shared"
    assert results[0][1] == round(2/22,8)


def test_rrf_is_deterministic_and_rejects_invalid_configuration():
    import pytest
    with pytest.raises(ValueError): ReciprocalRankFusionRetriever(FixedRetriever([]),FixedRetriever([]),rrf_k=0)
    hybrid=ReciprocalRankFusionRetriever(FixedRetriever(["b"]),FixedRetriever(["a"]),rrf_k=60,candidate_limit=1)
    assert [x[0].chunk_id for x in hybrid.search("q",2)] == ["a","b"]

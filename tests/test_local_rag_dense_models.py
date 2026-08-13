import pytest

from eval_harness.local_rag_dense_eval import MODEL_CONFIGS, run


def test_dense_model_matrix_changes_only_declared_embedding_properties(tmp_path):
    mini=MODEL_CONFIGS["sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"]
    mpnet=MODEL_CONFIGS["sentence-transformers/paraphrase-multilingual-mpnet-base-v2"]
    assert mini["dimension"] == 384 and mpnet["dimension"] == 768
    assert mini["config_id"] != mpnet["config_id"]
    assert set(mini) == set(mpnet) == {"config_id", "dimension", "max_tokens", "pooling"}
    with pytest.raises(ValueError, match="unsupported benchmark model"):
        run(tmp_path/"unknown.json", "unknown/model")

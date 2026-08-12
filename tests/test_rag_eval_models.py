import pytest
from pydantic import ValidationError

from eval_harness.rag_eval_models import RAGEvalDataset, RAGExperimentConfig


def _dataset():
    return {
        "dataset_name": "paper qa seed",
        "dataset_version": "0.1.0",
        "description": "seed",
        "corpus_version": "0.1.0",
        "k_values": [1, 3, 5],
        "cases": [{
            "id": "q1", "question": "What is RAG?", "language": "en",
            "category": "definition", "difficulty": "simple",
            "reference_answer": "RAG combines retrieval and generation.",
            "evidence": [{"document_id": "d1", "chunk_id": "c1", "page_start": 1, "page_end": 1, "quote": "retrieval and generation", "source_path": "papers/rag.pdf", "relevance_grade": 3}],
        }],
    }


def test_rag_dataset_accepts_versioned_grounded_case():
    dataset = RAGEvalDataset.model_validate(_dataset())
    assert dataset.corpus_version == "0.1.0"
    assert dataset.cases[0].evidence[0].page_start == 1


def test_rag_dataset_rejects_invalid_pages_and_duplicate_evidence():
    invalid = _dataset()
    invalid["cases"][0]["evidence"][0]["page_end"] = 0
    with pytest.raises(ValidationError):
        RAGEvalDataset.model_validate(invalid)

    duplicate = _dataset()
    duplicate["cases"].append({**duplicate["cases"][0], "id": "q2"})
    with pytest.raises(ValidationError):
        RAGEvalDataset.model_validate(duplicate)


def test_rag_experiment_config_keeps_technology_choices_replaceable():
    dense = RAGExperimentConfig(config_id="dense-v1", retriever_family="dense", parser="pypdf", chunker="recursive", embedding="candidate-a", store="candidate-a")
    graph = RAGExperimentConfig(config_id="graph-v1", retriever_family="graph", parser="pypdf", chunker="semantic", embedding="candidate-b", store="candidate-b", graph_retriever="candidate-graph")
    assert dense.retriever_family != graph.retriever_family
    assert dense.config_id != graph.config_id

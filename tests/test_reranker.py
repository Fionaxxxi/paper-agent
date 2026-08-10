from retrieval.reranker import (
    rerank_documents_with_stats,
    score_document,
    tokenize,
    verify_document_metadata,
)


def document(title, source, entry_id, *, doi="", content="", cited=0):
    return {
        "title": title,
        "source": source,
        "entry_id": entry_id,
        "doi": doi,
        "content": content,
        "cited_by_count": cited,
        "year": 2024,
    }


def test_tokenize_handles_english_stopwords_and_chinese_characters():
    assert tokenize("The Reflexion Agent 与 记忆") == {
        "reflexion",
        "agent",
        "与",
        "记",
        "忆",
    }


def test_metadata_verifier_detects_conflicting_arxiv_ids_and_missing_abstract():
    result = verify_document_metadata(
        document(
            "Conflicting identity",
            "openalex",
            "https://openalex.org/W1",
            doi="10.48550/arxiv.2303.11366",
        )
        | {"pdf_url": "https://arxiv.org/pdf/2201.11903"}
    )

    assert "ARXIV_ID_CONFLICT" in result["metadata_warnings"]
    assert "MISSING_ABSTRACT" in result["metadata_warnings"]
    assert result["metadata_quality_score"] < 0.5


def test_reranker_promotes_query_relevant_openalex_candidate_into_top_k():
    arxiv = [
        document(f"Unrelated reinforcement paper {index}", "arxiv", f"a{index}")
        for index in range(1, 6)
    ]
    relevant = document(
        "Reflexion: Language Agents with Verbal Reinforcement Learning",
        "openalex",
        "W1",
        content="Language agents learn from verbal feedback and episodic memory.",
    )

    result = rerank_documents_with_stats(
        "verbal reinforcement learning reflective memory language agents",
        [arxiv, [relevant]],
        max_documents=5,
    )

    assert result["documents"][0]["title"].startswith("Reflexion")
    assert result["ranking_strategy"] == "deterministic_cross_source_v1"
    assert result["candidate_count_before_top_k"] == 6


def test_reranker_interleaves_equal_relevance_candidates_by_source_rank():
    arxiv = [
        document("Alpha", "arxiv", "a1"),
        document("Beta", "arxiv", "a2"),
    ]
    openalex = [
        document("Gamma", "openalex", "o1"),
        document("Delta", "openalex", "o2"),
    ]

    result = rerank_documents_with_stats("未知主题", [arxiv, openalex], 4)

    assert [paper["entry_id"] for paper in result["documents"]] == [
        "a1",
        "o1",
        "a2",
        "o2",
    ]


def test_cross_source_title_conflict_is_visible_and_penalized():
    arxiv = document(
        "Chain-of-Thought Prompting Elicits Reasoning",
        "arxiv",
        "2201.11903",
        doi="10.48550/arxiv.2201.11903",
    )
    openalex = document(
        "Completely Different Metadata Record",
        "openalex",
        "W1",
        doi="https://doi.org/10.48550/arxiv.2201.11903",
    )

    result = rerank_documents_with_stats("chain of thought reasoning", [[arxiv], [openalex]], 5)
    merged = result["documents"][0]

    assert result["deduplicated_count"] == 1
    assert merged["sources"] == ["arxiv", "openalex"]
    assert "CROSS_SOURCE_TITLE_CONFLICT" in merged["metadata_warnings"]
    assert score_document("chain of thought reasoning", merged)["ranking_score"] < 0.8

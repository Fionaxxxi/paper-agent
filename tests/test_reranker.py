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


def test_authoritative_arxiv_record_repairs_conflicting_secondary_title():
    arxiv = document(
        "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models",
        "arxiv",
        "https://arxiv.org/abs/2201.11903",
        doi="10.48550/arxiv.2201.11903",
    )
    openalex = document(
        "Unrelated and corrupted secondary title",
        "openalex",
        "https://openalex.org/W1",
        doi="https://doi.org/10.48550/arxiv.2201.11903",
    )

    result = rerank_documents_with_stats(
        "chain of thought prompting reasoning",
        [[openalex], [arxiv]],
        5,
        metadata_resolution_enabled=True,
    )
    resolved = result["documents"][0]

    assert resolved["title"] == arxiv["title"]
    assert resolved["metadata_resolution_status"] == "AUTHORITATIVE_REPAIRED"
    assert "REPAIRED_TITLE_FROM_ARXIV" in resolved["metadata_repairs"]
    assert result["metadata_repaired_count"] == 1


def test_unverified_arxiv_identity_with_unrelated_title_is_quarantined():
    poisoned = document(
        "BNAI NO TOKEN and MIND UNITY",
        "openalex",
        "https://openalex.org/W4221143046",
        doi="https://doi.org/10.48550/arxiv.2201.11903",
    )
    safe = document(
        "Reasoning with language models",
        "openalex",
        "https://openalex.org/W2",
        content="Chain of thought reasoning.",
    )

    result = rerank_documents_with_stats(
        "chain of thought prompting elicits reasoning",
        [[poisoned, safe]],
        5,
        metadata_resolution_enabled=True,
    )

    assert [item["entry_id"] for item in result["documents"]] == [safe["entry_id"]]
    assert result["metadata_quarantined_count"] == 1
    assert result["quarantined_documents"][0]["metadata_resolution_action"] == "QUARANTINE"
    assert "UNVERIFIED_ARXIV_ID_TITLE_MISMATCH" in (
        result["quarantined_documents"][0]["metadata_warnings"]
    )


def test_unverified_but_query_supported_arxiv_identity_remains_available():
    plausible = document(
        "Reflexion Language Agents with Verbal Reinforcement Learning",
        "openalex",
        "https://openalex.org/W3",
        doi="https://doi.org/10.48550/arxiv.2303.11366",
    )

    result = rerank_documents_with_stats(
        "reflexion language agents verbal reinforcement learning",
        [[plausible]],
        5,
        metadata_resolution_enabled=True,
    )

    assert result["documents"][0]["metadata_resolution_status"] == "SECONDARY_ACCEPTED"
    assert "UNVERIFIED_ARXIV_IDENTITY" in result["documents"][0]["metadata_warnings"]
    assert result["metadata_quarantined_count"] == 0


def test_canonical_arxiv_evidence_repairs_secondary_claim_without_query_gate():
    secondary = document(
        "Large Language Models are Zero-Shot Reasoners",
        "openalex",
        "https://openalex.org/W1",
        doi="https://doi.org/10.48550/arxiv.2205.11916",
        content="reasoning with language models",
    )
    canonical = document(
        "Large Language Models are Zero-Shot Reasoners",
        "arxiv",
        "https://arxiv.org/abs/2205.11916",
        content="canonical abstract",
    )

    result = rerank_documents_with_stats(
        "a deliberately unrelated user query",
        [[secondary]],
        metadata_resolution_enabled=True,
        authority_by_identity={"arxiv:2205.11916": canonical},
    )

    assert result["ranking_strategy"] == "canonical_authority_verified_v3"
    assert result["metadata_quarantined_count"] == 0
    assert result["documents"][0]["metadata_resolution_status"] == (
        "AUTHORITATIVE_VERIFIED"
    )


def test_canonical_arxiv_evidence_repairs_wrong_secondary_title():
    secondary = document(
        "Unrelated Secondary Title",
        "openalex",
        "https://openalex.org/W2",
        doi="https://doi.org/10.48550/arxiv.2205.11916",
    )
    canonical = document(
        "Large Language Models are Zero-Shot Reasoners",
        "arxiv",
        "https://arxiv.org/abs/2205.11916",
        content="canonical abstract",
    )

    result = rerank_documents_with_stats(
        "zero shot reasoning",
        [[secondary]],
        metadata_resolution_enabled=True,
        authority_by_identity={"arxiv:2205.11916": canonical},
    )

    paper = result["documents"][0]
    assert paper["title"] == canonical["title"]
    assert "REPAIRED_TITLE_FROM_ARXIV" in paper["metadata_repairs"]
    assert result["metadata_quarantined_count"] == 0


def test_canonical_arxiv_not_found_is_explicit_negative_evidence():
    secondary = document(
        "Claimed Paper",
        "openalex",
        "https://openalex.org/W3",
        doi="https://doi.org/10.48550/arxiv.2013.00279",
    )
    not_found = {
        "source": "arxiv_authority",
        "canonical_identity": "arxiv:2013.00279",
        "canonical_lookup_status": "NOT_FOUND",
    }

    result = rerank_documents_with_stats(
        "claimed paper",
        [[secondary]],
        metadata_resolution_enabled=True,
        authority_by_identity={"arxiv:2013.00279": not_found},
    )

    assert result["metadata_quarantined_count"] == 1
    quarantined = result["quarantined_documents"][0]
    assert quarantined["metadata_resolution_status"] == "AUTHORITATIVE_NOT_FOUND"
    assert "ARXIV_ID_NOT_FOUND_IN_NATIVE_SOURCE" in quarantined["metadata_warnings"]


def test_crossref_doi_evidence_repairs_conflicting_secondary_title():
    secondary = document(
        "Wrong Secondary Title",
        "openalex",
        "https://openalex.org/W4",
        doi="https://doi.org/10.1145/example",
    )
    canonical = document(
        "Canonical DOI Publication Title",
        "crossref",
        "https://doi.org/10.1145/example",
        doi="10.1145/example",
    )

    result = rerank_documents_with_stats(
        "canonical publication",
        [[secondary]],
        metadata_resolution_enabled=True,
        authority_by_identity={"doi:10.1145/example": canonical},
    )

    paper = result["documents"][0]
    assert paper["title"] == canonical["title"]
    assert paper["metadata_resolution_status"] == "DOI_AUTHORITATIVE_REPAIRED"
    assert "REPAIRED_TITLE_FROM_CROSSREF" in paper["metadata_repairs"]


def test_crossref_doi_not_found_is_visible_but_does_not_quarantine():
    secondary = document(
        "Plausible Publication",
        "openalex",
        "https://openalex.org/W5",
        doi="10.5281/missing",
    )
    not_found = {
        "source": "crossref",
        "canonical_identity": "doi:10.5281/missing",
        "canonical_lookup_status": "NOT_FOUND",
    }

    result = rerank_documents_with_stats(
        "plausible publication",
        [[secondary]],
        metadata_resolution_enabled=True,
        authority_by_identity={"doi:10.5281/missing": not_found},
    )

    assert result["metadata_quarantined_count"] == 0
    paper = result["documents"][0]
    assert paper["metadata_resolution_status"] == "DOI_AUTHORITY_NOT_FOUND"
    assert "DOI_AUTHORITY_NOT_FOUND" in paper["metadata_warnings"]

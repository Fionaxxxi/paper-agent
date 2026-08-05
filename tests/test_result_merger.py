from retrieval.result_merger import (
    build_document_key,
    merge_documents,
    merge_documents_with_stats,
    normalize_text,
)


def test_normalize_text_handles_none_whitespace_and_case():
    assert normalize_text(None) == ""
    assert normalize_text("  Graph RAG  ") == "graph rag"


def test_build_document_key_uses_stable_priority():
    document = {
        "doi": " https://doi.org/10.1000/Test ",
        "entry_id": " 2401.00001 ",
        "pdf_url": "https://example.com/paper.pdf",
        "title": "Example Paper",
    }

    assert build_document_key(document) == "doi:10.1000/test"
    assert build_document_key(
        {"entry_id": document["entry_id"], "pdf_url": document["pdf_url"]}
    ) == "entry_id:2401.00001"
    assert build_document_key({"pdf_url": document["pdf_url"], "title": document["title"]}) == (
        "pdf_url:https://example.com/paper.pdf"
    )
    assert build_document_key({"title": " Example Paper "}) == "title:example paper"
    assert build_document_key({"content": "anonymous"}) == ""


def test_merge_documents_deduplicates_across_groups_and_preserves_priority():
    first = {"entry_id": "1", "title": "First version"}
    duplicate = {"entry_id": "1", "title": "Later duplicate"}
    second = {"entry_id": "2", "title": "Second paper"}

    assert merge_documents([[first], [duplicate, second]]) == [first, second]


def test_merge_documents_deduplicates_cross_source_records_by_doi():
    arxiv = {
        "doi": "https://doi.org/10.1000/shared",
        "entry_id": "2401.00001",
        "source": "arxiv",
    }
    openalex = {
        "doi": "10.1000/SHARED",
        "entry_id": "https://openalex.org/W1",
        "source": "openalex",
    }

    assert merge_documents([[arxiv], [openalex]]) == [arxiv]


def test_merge_documents_deduplicates_cross_source_title_when_doi_is_missing():
    arxiv = {
        "title": "A Shared Preprint",
        "entry_id": "2401.00001",
        "source": "arxiv",
    }
    openalex = {
        "title": "  A SHARED PREPRINT ",
        "entry_id": "https://openalex.org/W2",
        "source": "openalex",
    }

    assert merge_documents([[arxiv], [openalex]]) == [arxiv]


def test_merge_documents_keeps_documents_without_a_deduplication_key():
    anonymous_a = {"content": "first anonymous result"}
    anonymous_b = {"content": "second anonymous result"}

    assert merge_documents([[anonymous_a, anonymous_b]]) == [anonymous_a, anonymous_b]


def test_merge_documents_honors_max_documents():
    documents = [{"entry_id": str(index)} for index in range(5)]

    assert merge_documents([documents], max_documents=3) == documents[:3]


def test_merge_documents_with_stats_reports_counts():
    groups = [
        [{"entry_id": "1"}, {"entry_id": "2"}],
        [{"entry_id": "1"}, {"entry_id": "3"}],
    ]

    result = merge_documents_with_stats(groups, max_documents=8)

    assert result["documents"] == [
        {"entry_id": "1"},
        {"entry_id": "2"},
        {"entry_id": "3"},
    ]
    assert result["raw_document_count"] == 4
    assert result["merged_document_count"] == 3
    assert result["deduplicated_count"] == 1

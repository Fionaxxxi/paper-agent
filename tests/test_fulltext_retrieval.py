import retrieval.fulltext as fulltext
from context.context_builder import build_skill_context


def _paper():
    return {
        "title": "GraphRAG",
        "entry_id": "2404.16130",
        "content": "abstract only",
        "pdf_url": "https://arxiv.org/pdf/2404.16130",
        "source": "arxiv",
    }


def test_deep_comparison_requires_fulltext_but_simple_lookup_does_not(monkeypatch):
    monkeypatch.setattr(fulltext.settings, "FULLTEXT_RESEARCH_ENABLED", True)
    assert fulltext.needs_fulltext_research({
        "query": "比较 GraphRAG 和 LightRAG 的实验结果与局限",
        "task_type": "compare", "task_level": "L2",
    }) is True
    assert fulltext.needs_fulltext_research({
        "query": "找 GraphRAG 论文", "task_type": "qa", "task_level": "L1",
    }) is False


def test_fulltext_enrichment_keeps_pages_links_and_abstract_fallback(tmp_path, monkeypatch):
    cached = tmp_path / "paper.pdf"
    cached.write_bytes(b"%PDF fake")
    monkeypatch.setattr(fulltext.settings, "FULLTEXT_RESEARCH_ENABLED", True)
    monkeypatch.setattr(fulltext.settings, "FULLTEXT_MAX_PAPERS", 2)
    monkeypatch.setattr(fulltext.settings, "FULLTEXT_CHUNKS_PER_PAPER", 3)
    monkeypatch.setattr(fulltext, "_download_pdf", lambda document: (cached, {"status": "cache_hit"}))
    monkeypatch.setattr(fulltext, "_rank_pdf_chunks", lambda path, document, query, limit: [{
        **document, "content": "full experimental evidence",
        "source": "online_pdf_fulltext", "page": 7,
        "chunk_id": "2404.16130:p7:c1", "content_scope": "fulltext_chunk",
    }])

    documents, metadata = fulltext.enrich_with_fulltext([_paper()], {
        "query": "详细比较实验结果", "task_type": "compare", "task_level": "L2",
    })

    assert metadata["status"] == "enriched" and metadata["chunk_count"] == 1
    assert documents[0]["content_scope"] == "fulltext_chunk"
    assert documents[0]["page"] == 7
    assert documents[0]["pdf_url"] == _paper()["pdf_url"]
    assert documents[-1]["content"] == "abstract only"


def test_compare_context_does_not_truncate_normal_fulltext_chunks():
    content = "x" * 1400
    context = build_skill_context({
        "query": "比较两篇论文", "task_type": "compare",
        "documents": [{"title": "Paper", "content": content, "page": 3}],
    })
    assert content in context["documents_text"]
    assert "[truncated]" not in context["documents_text"]


def test_pdf_download_rejects_non_https_and_untrusted_hosts():
    assert fulltext._safe_pdf_url("http://arxiv.org/pdf/1") is False
    assert fulltext._safe_pdf_url("https://127.0.0.1/paper.pdf") is False
    assert fulltext._safe_pdf_url("https://evil-arxiv.org/paper.pdf") is False
    assert fulltext._safe_pdf_url("https://arxiv.org/pdf/2404.16130") is True


def test_failed_pdf_download_degrades_even_when_windows_cleanup_is_locked(tmp_path, monkeypatch):
    class FailedResponse:
        def __enter__(self):
            raise ConnectionError("network unavailable")
        def __exit__(self, *args):
            return False

    monkeypatch.setattr(fulltext.settings, "FULLTEXT_CACHE_DIR", str(tmp_path))
    monkeypatch.setattr(fulltext.requests, "get", lambda *args, **kwargs: FailedResponse())
    original_unlink = fulltext.Path.unlink
    monkeypatch.setattr(fulltext.Path, "unlink", lambda self, **kwargs: (_ for _ in ()).throw(PermissionError("locked")))
    try:
        path, status = fulltext._download_pdf(_paper())
    finally:
        monkeypatch.setattr(fulltext.Path, "unlink", original_unlink)
    assert path is None
    assert status["status"] == "failed"
    assert "ConnectionError" in status["reason"]

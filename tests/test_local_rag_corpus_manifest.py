import json

import pytest

from scripts.build_local_rag_manifest import build_corpus_manifest


def test_build_corpus_manifest_preserves_declared_identity_and_hash(tmp_path):
    paper = tmp_path / "paper.pdf"
    paper.write_bytes(b"%PDF-test corpus")
    sources = tmp_path / "sources.json"
    sources.write_text(json.dumps({
        "corpus_version": "0.1.0",
        "documents": [{
            "document_id": "paper_1",
            "arxiv_id": "1234.56789",
            "title": "Representative Paper",
            "filename": paper.name,
            "group": "rag",
        }],
    }), encoding="utf-8")

    output = build_corpus_manifest(sources, tmp_path / "manifest.json")
    payload = json.loads(output.read_text(encoding="utf-8"))

    assert payload["corpus_version"] == "0.1.0"
    assert len(payload["documents"]) == 1
    assert payload["documents"][0]["document_id"] == "paper_1"
    assert payload["documents"][0]["arxiv_id"] == "1234.56789"
    assert len(payload["documents"][0]["sha256"]) == 64


def test_build_corpus_manifest_rejects_missing_declared_pdf(tmp_path):
    sources = tmp_path / "sources.json"
    sources.write_text(json.dumps({
        "corpus_version": "0.1.0",
        "documents": [{
            "document_id": "missing",
            "arxiv_id": "0000.00000",
            "title": "Missing Paper",
            "filename": "missing.pdf",
            "group": "rag",
        }],
    }), encoding="utf-8")

    with pytest.raises(FileNotFoundError, match="missing.pdf"):
        build_corpus_manifest(sources, tmp_path / "manifest.json")

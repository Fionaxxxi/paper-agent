from local_rag.chunker import FixedWindowChunker
from local_rag.contracts import ParsedPage
from local_rag.manifest import build_manifest_entry, requires_rebuild, write_manifest


def test_fixed_window_chunker_preserves_page_and_overlap():
    chunks = FixedWindowChunker(chunk_size=10, overlap=2).chunk([ParsedPage("d1", 3, "abcdefghijklmnop")])
    assert [chunk.text for chunk in chunks] == ["abcdefghij", "ijklmnop"]
    assert all(chunk.page_start == chunk.page_end == 3 for chunk in chunks)
    assert chunks[1].char_start == 8


def test_fixed_window_chunker_rejects_invalid_parameters():
    import pytest
    with pytest.raises(ValueError):
        FixedWindowChunker(chunk_size=10, overlap=10)


def test_manifest_rebuilds_only_for_content_or_processing_version_change(tmp_path):
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"version-one")
    first = build_manifest_entry(pdf, "p1", "parser", "1", "chunker", "1")
    same = build_manifest_entry(pdf, "p1", "parser", "1", "chunker", "1")
    changed_chunker = build_manifest_entry(pdf, "p1", "parser", "1", "chunker", "2")
    pdf.write_bytes(b"version-two")
    changed_content = build_manifest_entry(pdf, "p1", "parser", "1", "chunker", "1")

    assert requires_rebuild(first, same) is False
    assert requires_rebuild(first, changed_chunker) is True
    assert requires_rebuild(first, changed_content) is True


def test_manifest_writer_keeps_corpus_version_and_status(tmp_path):
    source = tmp_path / "paper.pdf"
    source.write_bytes(b"pdf")
    entry = build_manifest_entry(source, "p1", "parser", "1", "chunker", "1")
    output = write_manifest([entry], tmp_path / "manifest.json", "0.1.0")
    import json
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["corpus_version"] == "0.1.0"
    assert payload["documents"][0]["processing_status"] == "pending"

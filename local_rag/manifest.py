"""Incremental corpus manifest: raw PDFs are facts, indexes are rebuildable."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_manifest_entry(path: Path, document_id: str, parser_name: str, parser_version: str, chunker_name: str, chunker_version: str) -> dict[str, Any]:
    return {
        "document_id": document_id,
        "source_path": path.as_posix(),
        "sha256": sha256_file(path),
        "file_size_bytes": path.stat().st_size,
        "parser": {"name": parser_name, "version": parser_version},
        "chunker": {"name": chunker_name, "version": chunker_version},
        "processing_status": "pending",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def requires_rebuild(previous: dict[str, Any] | None, current: dict[str, Any]) -> bool:
    if previous is None:
        return True
    keys = ("sha256", "parser", "chunker")
    return any(previous.get(key) != current.get(key) for key in keys)


def write_manifest(entries: list[dict[str, Any]], path: Path, corpus_version: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"corpus_version": corpus_version, "documents": entries}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path

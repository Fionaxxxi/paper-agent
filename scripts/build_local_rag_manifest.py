"""根据受控来源清单为本地 PDF 生成可复现的增量语料清单。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from local_rag.manifest import build_manifest_entry, write_manifest


def build_corpus_manifest(sources_path: Path, output_path: Path) -> Path:
    """校验来源清单中的 PDF，并写入带内容哈希和处理版本的 Manifest。"""
    sources = json.loads(sources_path.read_text(encoding="utf-8"))
    entries = []
    missing = []
    for document in sources["documents"]:
        pdf_path = sources_path.parent / document["filename"]
        if not pdf_path.is_file():
            missing.append(pdf_path.as_posix())
            continue
        entry = build_manifest_entry(
            pdf_path,
            document["document_id"],
            "pypdf_page",
            "1.0",
            "fixed_window",
            "1.0",
        )
        entry.update(
            {
                "arxiv_id": document["arxiv_id"],
                "title": document["title"],
                "group": document["group"],
            }
        )
        entries.append(entry)

    if missing:
        raise FileNotFoundError("缺少来源清单中的 PDF：" + ", ".join(missing))

    return write_manifest(entries, output_path, sources["corpus_version"])


def main() -> None:
    parser = argparse.ArgumentParser(description="生成 PaperAgent 本地 RAG 语料清单")
    parser.add_argument("--sources", type=Path, default=Path("data/papers/corpus_sources.json"))
    parser.add_argument("--output", type=Path, default=Path("data/processed/local_rag/corpus_manifest.json"))
    args = parser.parse_args()

    output = build_corpus_manifest(args.sources, args.output)
    count = len(json.loads(output.read_text(encoding="utf-8"))["documents"])
    print(f"已生成 {output}，共 {count} 篇论文。")


if __name__ == "__main__":
    main()

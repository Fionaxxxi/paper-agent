"""一次性真实 Hybrid 冒烟：ReAct PDF + arXiv + 主模型。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import requests

from core.config import settings
from product.personal_library import PersonalLibraryStore


REACT_PDF_URL = "https://arxiv.org/pdf/2210.03629"
QUERY = "结合我个人论文库中的 ReAct 原论文和在线论文，比较 ReAct 与反思型 Agent 的核心架构设计、证据边界和适用场景。"


def main() -> int:
    parser = argparse.ArgumentParser(description="PaperAgent Personal+Online+LLM 真实冒烟")
    parser.add_argument("--confirm-online", action="store_true", help="确认允许下载 PDF、访问 arXiv 并调用主模型一次")
    parser.add_argument("--output-dir", default="outputs/hybrid_smoke")
    args = parser.parse_args()
    if not args.confirm_online:
        parser.error("真实冒烟会访问网络并消耗模型 Token；确认后添加 --confirm-online")

    root = Path(args.output_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    pdf_path = root / "react_2210.03629.pdf"
    if not pdf_path.exists():
        response = requests.get(REACT_PDF_URL, timeout=60)
        response.raise_for_status()
        pdf_path.write_bytes(response.content)

    settings.PRODUCT_DB_PATH = str(root / "product.db")
    settings.PERSONAL_LIBRARY_FILES_DIR = str(root / "libraries")
    settings.MEMORY_DB_PATH = str(root / "conversation_memory.db")
    settings.LONG_TERM_MEMORY_DB_PATH = str(root / "long_term_memory.db")
    settings.LANGGRAPH_CHECKPOINT_DB_PATH = str(root / "checkpoints.db")

    user_id = "U-hybrid-smoke"
    library = PersonalLibraryStore(settings.PRODUCT_DB_PATH, settings.PERSONAL_LIBRARY_FILES_DIR)
    ingested = library.ingest_pdf(user_id, pdf_path.name, pdf_path.read_bytes(), title="ReAct")

    from services.paper_agent_service import PaperAgentService
    result = PaperAgentService().chat(
        QUERY,
        conversation_id=user_id,
        user_id=user_id,
        retrieval_scope="hybrid",
    )
    metadata = result.get("paper_metadata", {})
    sources = sorted({paper.get("source", "") for paper in result.get("papers", [])})
    summary = {
        "passed": (
            "personal_library" in sources
            and "arxiv" in sources
            and bool(result.get("answer"))
            and metadata.get("llm_call_count", 0) >= 1
        ),
        "query": QUERY,
        "personal_ingest_action": ingested.get("action"),
        "retrieval_source": metadata.get("retrieval_source"),
        "sources": sources,
        "paper_count": len(result.get("papers", [])),
        "llm_call_count": metadata.get("llm_call_count", 0),
        "token_usage": metadata.get("token_usage", 0),
        "answer_verification_passed": metadata.get("metrics", {}).get("answer_verification_passed", False),
        "trace_id": result.get("trace_id", ""),
    }
    (root / "latest_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    (root / "latest_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

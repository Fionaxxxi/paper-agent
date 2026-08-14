"""将通过验证的研究成果发布为可审阅的 Markdown LLM Wiki。"""

from __future__ import annotations

import hashlib
import re
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


_WRITE_LOCK = threading.Lock()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_note_id(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9_-]+", "-", value).strip("-")
    return normalized[:80]


def _fallback_note_id(state: dict[str, Any]) -> str:
    payload = "\n".join(
        (
            str(state.get("conversation_id", "")),
            str(state.get("query", "")),
            str(state.get("answer", "")),
        )
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True)
class WikiPublishResult:
    published: bool
    reason: str
    note_id: str = ""
    path: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "published": self.published,
            "reason": self.reason,
            "note_id": self.note_id,
            "path": self.path,
        }


class MarkdownWikiStore:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.notes_dir = self.root / "notes"

    def publish(self, state: dict[str, Any]) -> WikiPublishResult:
        trace_id = _safe_note_id(str(state.get("trace_id") or ""))
        note_id = trace_id or _fallback_note_id(state)
        note_path = self.notes_dir / f"{note_id}.md"
        content = self._render_note(state, note_id)

        with _WRITE_LOCK:
            self.notes_dir.mkdir(parents=True, exist_ok=True)
            self._atomic_write(note_path, content)
            self._update_index(note_id, state.get("query", ""), note_path)

        return WikiPublishResult(
            published=True,
            reason="published",
            note_id=note_id,
            path=str(note_path),
        )

    def list_notes(self) -> list[Path]:
        if not self.notes_dir.exists():
            return []
        return sorted(self.notes_dir.glob("*.md"))

    def read_note(self, note_id: str) -> str | None:
        safe_id = _safe_note_id(note_id)
        if not safe_id or note_id != safe_id:
            return None
        path = self.notes_dir / f"{safe_id}.md"
        return path.read_text(encoding="utf-8") if path.exists() else None

    @staticmethod
    def _atomic_write(path: Path, content: str) -> None:
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(content, encoding="utf-8")
        temporary.replace(path)

    def _update_index(self, note_id: str, query: str, note_path: Path) -> None:
        index_path = self.root / "README.md"
        link = f"- [{query or note_id}](notes/{note_path.name})"
        if index_path.exists():
            current = index_path.read_text(encoding="utf-8")
        else:
            current = "# PaperAgent LLM Wiki\n\n仅收录通过验证且具有论文证据的研究笔记。\n\n## 研究笔记\n"
        lines = [line for line in current.splitlines() if f"notes/{note_path.name}" not in line]
        lines.append(link)
        self._atomic_write(index_path, "\n".join(lines).rstrip() + "\n")

    @staticmethod
    def _render_note(state: dict[str, Any], note_id: str) -> str:
        verification = state.get("answer_verification", {})
        documents = state.get("documents", [])
        evidence_lines = []
        for index, document in enumerate(documents, start=1):
            identity = document.get("entry_id") or document.get("document_id") or ""
            page = document.get("page")
            location = f"，第 {page} 页" if page else ""
            url = document.get("pdf_url") or document.get("landing_page_url") or ""
            suffix = f"，[链接]({url})" if url else ""
            evidence_lines.append(
                f"{index}. **{document.get('title', '未命名论文')}**"
                f"（来源：{document.get('source', 'unknown')}，标识：{identity or '无'}{location}）{suffix}"
            )
        evidence = "\n".join(evidence_lines) or "无可用证据。"
        failure_types = verification.get("failure_types", [])

        return f"""# {state.get('query') or '未命名研究笔记'}

## 元数据

- Note ID：`{note_id}`
- Conversation ID：`{state.get('conversation_id', '')}`
- Trace ID：`{state.get('trace_id', '')}`
- Task Type：`{state.get('task_type', '')}`
- 创建时间：`{_utc_now()}`
- Verifier：`{'通过' if verification.get('passed') else '未通过'}`
- Verifier Score：`{verification.get('score', 0.0)}`
- Reflection Count：`{state.get('answer_reflection_count', 0)}`
- Failure Types：`{', '.join(failure_types) if failure_types else '无'}`

## 用户研究问题

{state.get('query', '')}

## 研究结论

{state.get('answer', '')}

## 论文证据

{evidence}

## 审计说明

该笔记由 PaperAgent 在最终答案通过 Verifier 且存在可追溯论文证据后发布。它是可人工审阅的研究产物，不代表未经复核的事实自动成为长期策略。
"""


def publish_agent_result(
    state: dict[str, Any],
    *,
    root: str | Path,
    enabled: bool,
    allowed_task_types: set[str],
) -> WikiPublishResult:
    if not enabled:
        return WikiPublishResult(False, "auto_publish_disabled")
    if state.get("task_type") not in allowed_task_types:
        return WikiPublishResult(False, "task_type_not_allowed")
    verification = state.get("answer_verification", {})
    if not verification.get("passed", False):
        return WikiPublishResult(False, "answer_not_verified")
    if not state.get("documents"):
        return WikiPublishResult(False, "no_traceable_evidence")
    if state.get("paper_metadata", {}).get("answer_mode") == "insufficient_evidence":
        return WikiPublishResult(False, "insufficient_evidence")
    return MarkdownWikiStore(root).publish(state)

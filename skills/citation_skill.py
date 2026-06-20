import re
from typing import Dict, Any, List

from agent.state import AgentState
from skills.base import BaseSkill


class CitationSkill(BaseSkill):
    name = "citation"
    description = "论文引用生成 Skill"
    need_llm = False

    def run(self, state: AgentState) -> Dict[str, Any]:
        documents = state.get("documents", [])
        query = state.get("query", "")

        if not documents:
            return {
                "answer": "没有可用于生成引用的论文信息，请先检索相关论文。"
            }

        citation_format = self.detect_format(query)

        if citation_format == "bibtex":
            answer = self.build_bibtex(documents)
        elif citation_format == "ieee":
            answer = self.build_ieee(documents)
        elif citation_format == "apa":
            answer = self.build_apa(documents)
        else:
            answer = self.build_all_formats(documents)

        return {
            "answer": answer,
            "paper_metadata": {
                **state.get("paper_metadata", {}),
                "skill_used": self.name,
                "citation_format": citation_format,
            },
        }

    def detect_format(self, query: str) -> str:
        query_lower = query.lower()

        if "bibtex" in query_lower or "bib" in query_lower:
            return "bibtex"

        if "ieee" in query_lower:
            return "ieee"

        if "apa" in query_lower:
            return "apa"

        return "all"

    def build_bibtex(self, documents: List[dict]) -> str:
        entries = []

        for index, doc in enumerate(documents, start=1):
            title = self.clean_text(doc.get("title", "Untitled"))
            authors = doc.get("authors", [])
            year = doc.get("year") or "unknown"
            url = doc.get("pdf_url") or doc.get("entry_id") or ""

            key = self.build_bibtex_key(authors, year, title, index)
            author_text = " and ".join(authors) if authors else "Unknown Author"

            entry = f"""@article{{{key},
  title={{{title}}},
  author={{{author_text}}},
  year={{{year}}},
  url={{{url}}}
}}"""
            entries.append(entry)

        return "## BibTeX 引用\n\n```bibtex\n" + "\n\n".join(entries) + "\n```"

    def build_apa(self, documents: List[dict]) -> str:
        lines = ["## APA 引用\n"]

        for doc in documents:
            title = self.clean_text(doc.get("title", "Untitled"))
            authors = doc.get("authors", [])
            year = doc.get("year") or "n.d."
            url = doc.get("pdf_url") or doc.get("entry_id") or ""

            author_text = self.format_apa_authors(authors)

            lines.append(f"{author_text} ({year}). {title}. {url}")

        return "\n\n".join(lines)

    def build_ieee(self, documents: List[dict]) -> str:
        lines = ["## IEEE 引用\n"]

        for index, doc in enumerate(documents, start=1):
            title = self.clean_text(doc.get("title", "Untitled"))
            authors = doc.get("authors", [])
            year = doc.get("year") or "n.d."
            url = doc.get("pdf_url") or doc.get("entry_id") or ""

            author_text = ", ".join(authors) if authors else "Unknown Author"

            lines.append(f"[{index}] {author_text}, \"{title},\" {year}. [Online]. Available: {url}")

        return "\n\n".join(lines)

    def build_all_formats(self, documents: List[dict]) -> str:
        return (
            self.build_bibtex(documents)
            + "\n\n---\n\n"
            + self.build_apa(documents)
            + "\n\n---\n\n"
            + self.build_ieee(documents)
        )

    def build_bibtex_key(
        self,
        authors: List[str],
        year: str,
        title: str,
        index: int,
    ) -> str:
        if authors:
            first_author = authors[0].split()[-1].lower()
        else:
            first_author = "paper"

        first_word = "paper"

        for word in re.findall(r"[A-Za-z]+", title):
            if len(word) > 3:
                first_word = word.lower()
                break

        key = f"{first_author}{year}{first_word}{index}"
        return re.sub(r"[^a-zA-Z0-9_]", "", key)

    def format_apa_authors(self, authors: List[str]) -> str:
        if not authors:
            return "Unknown Author"

        if len(authors) == 1:
            return authors[0]

        if len(authors) == 2:
            return f"{authors[0]} & {authors[1]}"

        return ", ".join(authors[:-1]) + f", & {authors[-1]}"

    def clean_text(self, text: str) -> str:
        return " ".join(str(text).split())
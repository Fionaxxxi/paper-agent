"""依赖无关、结果确定的 BM25 全文检索基线。"""

from __future__ import annotations

import math
import re
from collections import Counter

from local_rag.contracts import TextChunk


TOKEN_PATTERN = re.compile(r"[a-z0-9]+(?:[._-][a-z0-9]+)*%?|[\u4e00-\u9fff]+", re.I)


def mixed_tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    for match in TOKEN_PATTERN.findall(text.casefold()):
        if "\u4e00" <= match[0] <= "\u9fff":
            tokens.extend(match)
            tokens.extend(match[index:index + 2] for index in range(len(match) - 1))
        else:
            tokens.append(match)
    return tokens


class BM25Retriever:
    name = "bm25_mixed_char_word"
    version = "1.0"

    def __init__(self, chunks: list[TextChunk], k1: float = 1.5, b: float = 0.75):
        if not chunks or k1 <= 0 or not 0 <= b <= 1:
            raise ValueError("require chunks, k1 > 0 and 0 <= b <= 1")
        self.chunks, self.k1, self.b = chunks, k1, b
        self.term_frequencies = [Counter(mixed_tokenize(chunk.text)) for chunk in chunks]
        self.lengths = [sum(freq.values()) for freq in self.term_frequencies]
        self.average_length = sum(self.lengths) / len(self.lengths)
        document_frequency = Counter(term for freq in self.term_frequencies for term in freq)
        count = len(chunks)
        self.idf = {
            term: math.log(1 + (count - frequency + 0.5) / (frequency + 0.5))
            for term, frequency in document_frequency.items()
        }

    def search(self, query: str, limit: int = 5) -> list[tuple[TextChunk, float]]:
        if limit < 1:
            raise ValueError("limit must be positive")
        query_terms = Counter(mixed_tokenize(query))
        scored = []
        for index, (chunk, frequencies, length) in enumerate(zip(self.chunks, self.term_frequencies, self.lengths)):
            score = 0.0
            for term, query_frequency in query_terms.items():
                frequency = frequencies.get(term, 0)
                if not frequency:
                    continue
                denominator = frequency + self.k1 * (1 - self.b + self.b * length / self.average_length)
                score += self.idf.get(term, 0.0) * frequency * (self.k1 + 1) / denominator * query_frequency
            scored.append((chunk, score, index))
        scored.sort(key=lambda item: (-item[1], item[0].document_id, item[0].chunk_id, item[2]))
        return [(chunk, round(score, 8)) for chunk, score, _ in scored[:limit]]

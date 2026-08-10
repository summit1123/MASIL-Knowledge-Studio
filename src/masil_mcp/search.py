from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter, defaultdict
from typing import Iterable

from .models import KnowledgeDocument, SearchHit


WORD_RE = re.compile(r"[0-9A-Za-z_+.%:/-]+|[가-힣]+")
AUTHORITY_BOOST = {
    "canonical": 1.30,
    "deck": 1.22,
    "evidence": 1.16,
    "supporting": 0.92,
    "historical": 0.58,
}
STATUS_BOOST = {
    "current": 1.08,
    "active": 1.08,
    "as_printed": 1.04,
    "as_printed_needs_context": 1.02,
    "printed_correction_planned": 0.94,
    "candidate_parameter": 0.94,
    "documented_reference": 0.90,
    "pilot_target": 0.90,
    "pilot_hypothesis": 0.88,
    "unresolved": 0.78,
}
QUERY_STOPWORDS = {
    "왜",
    "어떻게",
    "무엇인가요",
    "뭔가요",
    "뭐예요",
    "하나요",
    "되나요",
    "인가요",
    "건가요",
    "나뉘나요",
    "설명해줘",
    "설명해주세요",
    "알려줘",
    "알려주세요",
}


def normalize(text: str) -> str:
    return unicodedata.normalize("NFKC", text).lower().strip()


def words(text: str) -> list[str]:
    text = normalize(text)
    return [
        word
        for word in WORD_RE.findall(text)
        if word not in QUERY_STOPWORDS and not (re.fullmatch(r"[가-힣]", word))
    ]


def word_terms(word: str) -> list[str]:
    terms = [word]
    if re.fullmatch(r"[가-힣]+", word) and len(word) >= 2:
        terms.extend(f"ko:{word[index:index + size]}" for size in (2, 3) for index in range(len(word) - size + 1))
    return terms


def tokens(text: str) -> list[str]:
    parsed_words = words(text)
    grams: list[str] = []
    for word in parsed_words:
        if re.fullmatch(r"[가-힣]+", word) and len(word) >= 2:
            grams.extend(f"ko:{word[index:index + size]}" for size in (2, 3) for index in range(len(word) - size + 1))
    return [*parsed_words, *grams]


def weighted_tokens(document: KnowledgeDocument) -> list[str]:
    return [
        *tokens(document.id) * 4,
        *tokens(document.title) * 3,
        *tokens(" ".join(document.tags)) * 2,
        *tokens(document.body),
    ]


def _snippet(document: KnowledgeDocument, query: str, max_chars: int = 520) -> str:
    body = document.body.replace("\r", "").strip()
    if len(body) <= max_chars:
        return body
    query_words = [word for word in WORD_RE.findall(normalize(query)) if len(word) > 1]
    lower = normalize(body)
    positions = [lower.find(word) for word in query_words if lower.find(word) >= 0]
    center = min(positions) if positions else 0
    start = max(0, center - max_chars // 4)
    end = min(len(body), start + max_chars)
    prefix = "…" if start else ""
    suffix = "…" if end < len(body) else ""
    return f"{prefix}{body[start:end].strip()}{suffix}"


class HybridSearchIndex:
    def __init__(self, documents: Iterable[KnowledgeDocument]):
        self.documents = list(documents)
        self.term_frequencies: list[Counter[str]] = []
        self.lengths: list[int] = []
        self.document_frequency: Counter[str] = Counter()
        for document in self.documents:
            terms = weighted_tokens(document)
            frequencies = Counter(terms)
            self.term_frequencies.append(frequencies)
            self.lengths.append(len(terms))
            self.document_frequency.update(frequencies.keys())
        self.average_length = sum(self.lengths) / max(1, len(self.lengths))

    def search(
        self,
        query: str,
        *,
        top_k: int = 8,
        authorities: set[str] | None = None,
        source_contains: str | None = None,
        status_include: set[str] | None = None,
        status_exclude: set[str] | None = None,
    ) -> list[SearchHit]:
        if top_k < 1 or top_k > 30:
            raise ValueError("top_k must be between 1 and 30")
        query = query.strip()
        if not query:
            return []
        query_terms = Counter(tokens(query))
        query_words = words(query)
        normalized_query = normalize(query)
        count = len(self.documents)
        scores: list[tuple[float, int]] = []
        for index, document in enumerate(self.documents):
            if authorities and document.authority not in authorities:
                continue
            if source_contains and source_contains not in document.source_path:
                continue
            if status_include and document.status not in status_include:
                continue
            if status_exclude and document.status.lower() in status_exclude:
                continue
            frequencies = self.term_frequencies[index]
            length = self.lengths[index]
            score = 0.0
            for term, query_count in query_terms.items():
                frequency = frequencies.get(term, 0)
                if not frequency:
                    continue
                df = self.document_frequency[term]
                inverse = math.log(1 + (count - df + 0.5) / (df + 0.5))
                denominator = frequency + 1.2 * (1 - 0.75 + 0.75 * length / max(1, self.average_length))
                score += query_count * inverse * (frequency * 2.2 / denominator)
            searchable = normalize(document.searchable_text)
            if re.fullmatch(r"[0-9a-z_.+%-]+", normalized_query):
                exact_phrase = re.search(
                    rf"(?<![0-9a-z_]){re.escape(normalized_query)}(?![0-9a-z_])",
                    searchable,
                ) is not None
            else:
                exact_phrase = normalized_query in searchable
            if exact_phrase:
                score += 8.0
            if normalized_query == normalize(document.id) or normalized_query == normalize(document.title):
                score += 25.0
            if len(query_words) > 1:
                matched_words = sum(
                    any(frequencies.get(term, 0) for term in word_terms(word))
                    for word in query_words
                )
                coverage = matched_words / len(query_words)
                score *= 0.30 + 0.70 * coverage
            score *= AUTHORITY_BOOST.get(document.authority, 1.0)
            score *= STATUS_BOOST.get(document.status.lower(), 1.0)
            if score > 0:
                scores.append((score, index))
        scores.sort(reverse=True)
        return [
            SearchHit(self.documents[index], score, _snippet(self.documents[index], query))
            for score, index in scores[:top_k]
        ]


def group_hits(hits: Iterable[SearchHit]) -> dict[str, list[SearchHit]]:
    grouped: dict[str, list[SearchHit]] = defaultdict(list)
    for hit in hits:
        grouped[hit.document.authority].append(hit)
    return dict(grouped)

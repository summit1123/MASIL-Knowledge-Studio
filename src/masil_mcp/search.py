from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter, defaultdict
from typing import Any, Iterable

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
    "masil",
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

FIELD_WEIGHTS = {
    "id": 3.2,
    "title": 5.0,
    "tags": 3.4,
    "metadata": 2.2,
    "body": 1.0,
}
FIELD_LENGTH_NORMALIZATION = {
    "id": 0.15,
    "title": 0.20,
    "tags": 0.25,
    "metadata": 0.40,
    "body": 0.75,
}

# Presentation teammates mix Korean deck terms, spoken Korean, and the fixed
# English labels. Expand only domain-specific concepts; generic words such as
# "risk" or "AI" are deliberately omitted because they create noisy matches.
QUERY_ALIAS_GROUPS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("masil은", "masil 뜻", "마실 뜻", "마실 나가다"),
     "MASIL 이름 뜻 마실 나가다 가까운 일상 활동"),
    (("생활권 밖", "생활권밖", "out-of-zone", "outer zone", "unfamiliar road", "낯선 도로"),
     "생활권 밖 생활권밖 out-of-zone outer zone unfamiliar road 낯선 도로"),
    (("무감점", "감점 안", "감점하지", "location penalty", "no penalty", "위치 벌점"),
     "위치만으로 감점하지 않음 위치 벌점 없음 no location-only penalty"),
    (("생활권", "마실존", "masil zone", "activity zone", "familiar zone"),
     "생활권 MASIL Zone 개인 활동영역 personal activity zone familiar zone"),
    (("반복 방문", "반복방문", "anchor", "앵커"),
     "반복 방문 anchor 서로 다른 방문일 distinct visit days DBSCAN"),
    (("p90", "개인 반경", "버퍼", "buffer"),
     "P90 개인 반경 per-anchor buffer 익숙한 반경"),
    (("우대", "favorable"), "우대 Favorable 추가 할인"),
    (("기본", "standard"), "기본 Standard"),
    (("케어", "care review", "care"), "케어 Care review 예방 안내 직원 검토"),
    (("care가 할인", "care 할인", "케어가 할인", "케어 할인"),
     "Care review 직접 가격 영향 없음 연간 할인율 별도 계산"),
    (("보류", "hold"), "보류 Hold 데이터 부족 no-penalty hold"),
    (("세 등급", "3-tier", "three tiers"), "세 등급 three monthly tiers Favorable Standard Care"),
    (("패턴 변화", "pattern change", "co-change", "동시 급변"),
     "패턴 변화 Pattern Change Risk co-change 이동 위험행동 동시 급변"),
    (("할인율", "할인률", "discount rate", "premium discount"),
     "할인율 discount rate premium discount 연간 할인"),
    (("개인정보", "프라이버시", "privacy", "위치정보"),
     "개인정보 privacy GPS 위치정보 최소수집 POI masking 권한분리 동의"),
    (("부주의", "인지 처리", "situational judgment", "looking but not seeing"),
     "부주의 situational judgment 상황 판단 looking but not seeing 인지 처리"),
    (("보험사", "insurer"), "보험사 insurer 역선택 adverse selection 위험관리 retention"),
    (("사회적 가치", "이동권", "mobility rights"),
     "사회적 가치 이동권 mobility rights 자기조절 self-regulation 가족 사회"),
)

IMPLEMENTATION_INTENT_TERMS = (
    "구현",
    "코드",
    "현재 화면",
    "대시보드 계산",
    "데모",
    "implementation",
    "current demo",
)


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


def _scalar_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (str, int, float, bool)):
        return str(value)
    if isinstance(value, list):
        return " ".join(_scalar_text(item) for item in value)
    if isinstance(value, dict):
        return " ".join(f"{key} {_scalar_text(item)}" for key, item in value.items())
    return str(value)


def document_fields(document: KnowledgeDocument) -> dict[str, str]:
    return {
        "id": f"{document.id} {document.source_path}",
        "title": document.title,
        "tags": " ".join([document.topic, *document.tags]),
        "metadata": _scalar_text(document.metadata),
        "body": document.body,
    }


def expand_query(query: str) -> str:
    normalized = normalize(query)
    expansions: list[str] = []
    for triggers, aliases in QUERY_ALIAS_GROUPS:
        if any(normalize(trigger) in normalized for trigger in triggers):
            expansions.append(aliases)
    return " ".join([query, *expansions])


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
        self.field_texts: list[dict[str, str]] = []
        self.field_term_frequencies: list[dict[str, Counter[str]]] = []
        self.field_lengths: dict[str, list[int]] = {field: [] for field in FIELD_WEIGHTS}
        self.document_frequency: Counter[str] = Counter()
        for document in self.documents:
            fields = document_fields(document)
            field_frequencies: dict[str, Counter[str]] = {}
            document_terms: set[str] = set()
            for field, text in fields.items():
                frequencies = Counter(tokens(text))
                field_frequencies[field] = frequencies
                self.field_lengths[field].append(sum(frequencies.values()))
                document_terms.update(frequencies)
            self.field_texts.append(fields)
            self.field_term_frequencies.append(field_frequencies)
            self.document_frequency.update(document_terms)
        self.field_average_lengths = {
            field: sum(lengths) / max(1, len(lengths))
            for field, lengths in self.field_lengths.items()
        }

    def search(
        self,
        query: str,
        *,
        top_k: int = 8,
        expand_aliases: bool = True,
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
        query_terms: Counter[str] = Counter(tokens(query))
        if expand_aliases:
            expanded_terms = Counter(tokens(expand_query(query)))
            for term, count_for_term in expanded_terms.items():
                if term not in query_terms:
                    query_terms[term] = count_for_term * 0.35
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
            field_frequencies = self.field_term_frequencies[index]
            score = 0.0
            for term, query_count in query_terms.items():
                df = self.document_frequency[term]
                if not df:
                    continue
                inverse = math.log(1 + (count - df + 0.5) / (df + 0.5))
                field_score = 0.0
                for field, weight in FIELD_WEIGHTS.items():
                    frequency = field_frequencies[field].get(term, 0)
                    if not frequency:
                        continue
                    length = self.field_lengths[field][index]
                    average = max(1.0, self.field_average_lengths[field])
                    b = FIELD_LENGTH_NORMALIZATION[field]
                    denominator = frequency + 1.2 * (1 - b + b * length / average)
                    field_score += weight * (frequency * 2.2 / denominator)
                score += query_count * inverse * field_score
            searchable = normalize(document.searchable_text)
            if re.fullmatch(r"[0-9a-z_.+%-]+", normalized_query):
                exact_phrase = re.search(
                    rf"(?<![0-9a-z_]){re.escape(normalized_query)}(?![0-9a-z_])",
                    searchable,
                ) is not None
            else:
                exact_phrase = normalized_query in searchable
            if exact_phrase:
                score += 6.0
            normalized_fields = {
                field: normalize(text) for field, text in self.field_texts[index].items()
            }
            if normalized_query and normalized_query in normalized_fields["title"]:
                score += 18.0
            if normalized_query and normalized_query in normalized_fields["tags"]:
                score += 12.0
            if normalized_query and normalized_query in normalized_fields["metadata"]:
                score += 9.0
            if normalized_query and normalized_query in normalized_fields["body"]:
                score += 5.0
            if normalized_query == normalize(document.id) or normalized_query == normalize(document.title):
                score += 25.0
            if len(query_words) > 1:
                matched_words = sum(
                    any(
                        frequencies.get(term, 0)
                        for frequencies in field_frequencies.values()
                        for term in word_terms(word)
                    )
                    for word in query_words
                )
                coverage = matched_words / len(query_words)
                score *= 0.15 + 0.85 * (coverage ** 1.5)
            score *= AUTHORITY_BOOST.get(document.authority, 1.0)
            score *= STATUS_BOOST.get(document.status.lower(), 1.0)
            if document.source_path == "IMPLEMENTATION.md":
                score *= (
                    1.18
                    if any(term in normalized_query for term in IMPLEMENTATION_INTENT_TERMS)
                    else 0.72
                )
            if score > 0:
                scores.append((score, index))
        scores.sort(key=lambda item: (-item[0], self.documents[item[1]].id))
        return [
            SearchHit(self.documents[index], score, _snippet(self.documents[index], query))
            for score, index in scores[:top_k]
        ]


def group_hits(hits: Iterable[SearchHit]) -> dict[str, list[SearchHit]]:
    grouped: dict[str, list[SearchHit]] = defaultdict(list)
    for hit in hits:
        grouped[hit.document.authority].append(hit)
    return dict(grouped)

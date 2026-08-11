from __future__ import annotations

from dataclasses import asdict, dataclass

from .search import normalize


@dataclass(frozen=True)
class AnswerRoute:
    route: str
    confidence: str
    material_priority: tuple[str, ...]
    reason: str

    def as_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["material_priority"] = list(self.material_priority)
        return payload


ROUTE_TERMS: tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...] = (
    (
        "qa_practice",
        (
            "예상 질문", "예상질문", "질의응답", "q&a", "qna", "킬러 질문", "킬러질문",
            "후속 질문", "후속질문", "답변 연습", "질문 뽑", "judge question", "practice question",
        ),
        ("curated_qa_catalog", "current_contract", "presentation_script"),
    ),
    (
        "claim_conflict_history",
        ("과거", "예전", "이전", "바뀌", "변경", "충돌", "원래", "히스토리", "history", "previous", "changed"),
        ("current_contract", "decision_history", "conflict_boundaries"),
    ),
    (
        "literature_evidence",
        ("문헌", "논문", "출처", "근거", "원문", "캡처", "이미지", "연구", "citation", "source", "study", "evidence"),
        ("literature_cards", "exact_captures", "claim_boundaries"),
    ),
    (
        "deck_context",
        ("장표", "슬라이드", "페이지", "summary", "appendix", "덱", "ppt", "deck", "slide"),
        ("deck_claims", "spoken_context", "corrections"),
    ),
    (
        "validation_open_items",
        ("미확정", "검증 필요", "검증됐", "파일럿", "가설", "아직", "한계", "unresolved", "validated", "pilot", "limitation"),
        ("current_boundaries", "open_items", "pilot_hypotheses"),
    ),
    (
        "stakeholder_value",
        ("보험사", "고객", "가족", "사회", "이동권", "가치", "insurer", "family", "society", "mobility rights"),
        ("presentation_story", "stakeholder_value", "validation_boundaries"),
    ),
    (
        "product_logic",
        (
            "생활권", "마실존", "zone", "dbscan", "p90", "등급", "우대", "기본", "케어", "hold",
            "점수", "산식", "할인", "pattern change", "favorable", "standard", "care",
        ),
        ("product_contract", "deck_claims", "implementation_boundary"),
    ),
)

DRAFT_TERMS = ("대본", "답변", "문장", "초안", "고쳐", "수정", "검토", "script", "draft", "rewrite")


def route_question(question: str) -> AnswerRoute:
    """Select answer materials without deciding or generating the answer itself."""

    normalized = normalize(question)
    scores: list[tuple[int, int, str, tuple[str, ...], list[str]]] = []
    for priority, (route, terms, material_priority) in enumerate(ROUTE_TERMS):
        matched = [term for term in terms if normalize(term) in normalized]
        scores.append((len(matched), -priority, route, material_priority, matched))

    draft_matches = [term for term in DRAFT_TERMS if normalize(term) in normalized]
    looks_like_draft = bool(draft_matches) and (len(question) >= 160 or "\n" in question)
    if looks_like_draft:
        return AnswerRoute(
            route="draft_review",
            confidence="high",
            material_priority=("fixed_terms", "current_contract", "deck_claims", "evidence_if_needed"),
            reason="draft markers with pasted or extended text",
        )

    best = max(scores, key=lambda item: (item[0], item[1]))
    count, _, route, material_priority, matched = best
    if count:
        confidence = "high" if count >= 2 else "medium"
        return AnswerRoute(
            route=route,
            confidence=confidence,
            material_priority=material_priority,
            reason=f"matched {len(matched)} domain cue(s)",
        )

    return AnswerRoute(
        route="presentation_overview",
        confidence="fallback",
        material_priority=("one_line_definition", "presentation_story", "current_contract"),
        reason="no specialized route cue; use broad current-material retrieval",
    )

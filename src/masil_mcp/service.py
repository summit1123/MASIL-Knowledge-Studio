from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .corpus import KnowledgeCorpus
from .models import SearchHit
from .search import HybridSearchIndex, normalize


SCOPES: dict[str, set[str] | None] = {
    "all": None,
    "current": {"canonical", "deck"},
    "canonical": {"canonical"},
    "slides": {"deck"},
    "evidence": {"evidence"},
    "supporting": {"supporting"},
    "history": {"historical"},
}

EXCLUDED_CURRENT_STATUSES = {
    "banned",
    "prohibited",
    "historical",
    "archived",
    "superseded",
    "deprecated",
    "legacy_reference",
    "archived_meeting_note",
    "historical_demo",
}
MIN_EVIDENCE_SCORE = 8.0
EVIDENCE_SCOPES = {"stage", "qa_only", "listed_only", "all"}
SOURCE_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9-]{3,}")
SOURCE_TOKEN_STOPWORDS = {
    "looking",
    "seeing",
    "driver",
    "drivers",
    "driving",
    "route",
    "road",
    "risk",
    "safety",
    "source",
    "study",
}
CAPTURE_REQUEST_TERMS = {"캡처", "원문", "이미지", "스크린샷", "capture", "screenshot", "source image"}
HISTORY_REQUEST_TERMS = {"과거", "이전", "변경", "바뀌", "충돌", "히스토리", "history", "changed", "previous"}
ANSWER_FACT_SOURCES = {
    "IMPLEMENTATION.md",
    "knowledge/product_model.yaml",
    "knowledge/official_positions.yaml",
    "knowledge/key_numbers.yaml",
    "knowledge/presentation_story.yaml",
    "knowledge/claims/deck_claims.yaml",
}
GUARDRAIL_SOURCES = {
    "knowledge/conflict_map.yaml",
    "knowledge/forbidden_claims.yaml",
    "knowledge/glossary.yaml",
}


class KnowledgeService:
    def __init__(self, root: Path | None = None):
        self.corpus = KnowledgeCorpus(root)
        self.index = HybridSearchIndex(self.corpus.documents)
        self.root = self.corpus.root

    def stats(self) -> dict[str, Any]:
        authorities: dict[str, int] = {}
        for document in self.corpus.documents:
            authorities[document.authority] = authorities.get(document.authority, 0) + 1
        captures = sum(document.id.startswith("capture://") for document in self.corpus.documents)
        return {
            "documents": len(self.corpus.documents),
            "captures": captures,
            "authorities": authorities,
            "fingerprint": self.corpus.fingerprint(),
        }

    @staticmethod
    def _validate_top_k(top_k: int, maximum: int = 30) -> None:
        if top_k < 1 or top_k > maximum:
            raise ValueError(f"top_k must be between 1 and {maximum}")

    def _filtered_search(
        self,
        query: str,
        *,
        top_k: int,
        predicate: Any,
    ) -> list[SearchHit]:
        documents = [document for document in self.corpus.documents if predicate(document)]
        return HybridSearchIndex(documents).search(query, top_k=top_k) if documents else []

    def search(self, query: str, top_k: int = 8, scope: str = "current", detail: str = "compact") -> dict[str, Any]:
        self._validate_top_k(top_k)
        if scope not in SCOPES:
            raise ValueError(f"scope must be one of: {', '.join(SCOPES)}")
        if scope == "current":
            # The default search is the material Claude may safely use as an
            # answer premise.  Glossary/conflict/forbidden records are useful
            # guardrails, but must not compete with the current product facts.
            hits = self._filtered_search(
                query,
                top_k=top_k,
                predicate=lambda document: (
                    document.authority in SCOPES["current"]
                    and document.source_path in ANSWER_FACT_SOURCES
                    and document.status.lower() not in EXCLUDED_CURRENT_STATUSES
                ),
            )
        else:
            hits = self.index.search(
                query,
                top_k=top_k,
                authorities=SCOPES[scope],
                status_exclude=EXCLUDED_CURRENT_STATUSES if scope in {"canonical", "slides", "evidence"} else None,
            )
        return {
            "query": query,
            "scope": scope,
            "result_count": len(hits),
            "results": [hit.as_dict(include_body=detail == "full") for hit in hits],
        }

    def _search_source(
        self,
        query: str,
        source: str,
        top_k: int = 8,
        statuses: set[str] | None = None,
    ) -> list[SearchHit]:
        self._validate_top_k(top_k)
        if statuses is None:
            return self.index.search(query, top_k=top_k, source_contains=source)
        return self._filtered_search(
            query,
            top_k=top_k,
            predicate=lambda document: source in document.source_path and document.status in statuses,
        )

    def _literature_hits(self, query: str, top_k: int, usage_scope: str = "stage") -> list[SearchHit]:
        self._validate_top_k(top_k)
        if usage_scope not in EVIDENCE_SCOPES:
            raise ValueError(f"usage_scope must be one of: {', '.join(sorted(EVIDENCE_SCOPES))}")
        allowed_tiers = {
            "stage": {"stage_citable"},
            "qa_only": {"qa_only"},
            "listed_only": set(),
            "all": {"stage_citable", "qa_only"},
        }[usage_scope]
        if not allowed_tiers:
            return []
        hits = self.index.search(
            query,
            top_k=top_k,
            authorities={"evidence", "supporting"},
            source_contains="knowledge/evidence/registry.yaml",
            status_include=allowed_tiers,
        )
        named_hits = self._prefer_named_source(query, hits)
        minimum_score = 0.0 if len(named_hits) < len(hits) else MIN_EVIDENCE_SCORE
        # 문헌명이 없고 공통 숫자·짧은 단어만 겹친 결과는 Q&A에 근거처럼 주입하지 않는다.
        return [
            hit for hit in named_hits
            if hit.score >= minimum_score
        ]

    @staticmethod
    def _prefer_named_source(query: str, hits: list[SearchHit]) -> list[SearchHit]:
        source_tokens = {
            token.lower()
            for token in SOURCE_TOKEN_RE.findall(query)
            if token.lower() not in SOURCE_TOKEN_STOPWORDS and not token.isdigit()
        }
        if not source_tokens:
            return hits
        matched = [
            hit
            for hit in hits
            if any(
                token in normalize(f"{hit.document.id} {hit.document.title}")
                for token in source_tokens
            )
        ]
        return matched or hits

    def _reference_only_hits(self, query: str, top_k: int, usage_scope: str = "stage") -> list[SearchHit]:
        self._validate_top_k(top_k)
        if usage_scope not in {"listed_only", "all"}:
            return []
        hits = self.index.search(
            query,
            top_k=top_k,
            authorities={"historical"},
            source_contains="knowledge/evidence/registry.yaml",
            status_include={"listed_only"},
        )
        named_hits = self._prefer_named_source(query, hits)
        minimum_score = 0.0 if len(named_hits) < len(hits) else MIN_EVIDENCE_SCORE
        return [
            hit for hit in named_hits
            if hit.score >= minimum_score
        ]

    def _capture_groups_for(self, literature: list[SearchHit], usage_scope: str = "stage") -> list[SearchHit]:
        allowed_statuses = {
            "stage": {"active"},
            "qa_only": {"qa_only"},
            "listed_only": {"listed_only"},
            "all": {"active", "qa_only", "listed_only"},
        }[usage_scope]
        evidence_keys = {
            hit.document.id.rsplit("#", 1)[-1]
            for hit in literature
        }
        groups: list[SearchHit] = []
        for document in self.corpus.documents:
            if document.source_path != "knowledge/evidence/capture_index.yaml":
                continue
            if document.metadata.get("card_status") not in allowed_statuses:
                continue
            refs = set(document.metadata.get("evidence_refs", []))
            if refs & evidence_keys:
                groups.append(SearchHit(document, 1.0, document.body[:520]))
        return groups

    def _capture_records(self, capture_ids: list[str]) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for capture_id in capture_ids:
            metadata, _ = self.capture(capture_id)
            records.append(metadata)
        return records

    def _answer_capture_records(self, capture_ids: list[str]) -> list[dict[str, Any]]:
        keep = {"id", "source", "heading", "caption", "card_status", "deck_location", "capture_kind"}
        return [
            {key: value for key, value in record.items() if key in keep}
            for record in self._capture_records(capture_ids)
        ]

    def explain_product_logic(self, topic: str, detail: str = "compact") -> dict[str, Any]:
        hits = self._filtered_search(
            topic,
            top_k=10,
            predicate=lambda document: (
                document.source_path in ANSWER_FACT_SOURCES
                and document.authority in {"canonical", "deck"}
                and document.status.lower() not in EXCLUDED_CURRENT_STATUSES
            ),
        )
        guardrails = self._filtered_search(
            topic,
            top_k=5,
            predicate=lambda document: (
                document.source_path in GUARDRAIL_SOURCES
                and document.authority == "canonical"
                and document.status.lower() not in EXCLUDED_CURRENT_STATUSES
            ),
        )
        return {
            "topic": topic,
            "contract": "최신 상품 계약과 현재 구현 후보값을 구분해 반환합니다.",
            "facts": [hit.as_dict(include_body=detail == "full") for hit in hits],
            "terms_and_guardrails": [
                hit.as_dict(include_body=detail == "full") for hit in guardrails
            ],
            "boundary": "candidate_parameter와 unresolved는 확정 요율·검증 결과로 바꾸지 마세요.",
        }

    def get_slide_context(self, page: int, detail: str = "compact") -> dict[str, Any]:
        hits = [
            SearchHit(document, 1.0, document.body[:520])
            for document in self.corpus.documents
            if document.authority == "deck" and document.metadata.get("page") == page
        ]
        return {
            "page": page,
            "claims": [hit.as_dict(include_body=detail == "full") for hit in hits[:20]],
            "status_rule": "as_printed는 그대로, needs_context는 구두 보완과 함께, correction_planned는 교정 상태를 함께 설명합니다.",
        }

    def get_evidence(
        self,
        query: str,
        top_k: int = 6,
        include_captures: bool = True,
        usage_scope: str = "stage",
    ) -> dict[str, Any]:
        self._validate_top_k(top_k)
        literature = self._literature_hits(query, top_k=top_k, usage_scope=usage_scope)
        reference_only = self._reference_only_hits(query, top_k=top_k, usage_scope=usage_scope)
        selected = sorted([*literature, *reference_only], key=lambda hit: hit.score, reverse=True)
        capture_groups = self._capture_groups_for(selected, usage_scope=usage_scope) if include_captures else []
        capture_ids: list[str] = []
        if include_captures:
            for hit in selected:
                metadata = hit.document.metadata
                ordered = [
                    *metadata.get("source_capture_ids", []),
                    *metadata.get("deck_capture_ids", []),
                ]
                for capture_id in ordered or metadata.get("capture_ids", []):
                    if capture_id not in capture_ids:
                        capture_ids.append(capture_id)
        recommended_ids: list[str] = []
        if selected and include_captures:
            top_metadata = selected[0].document.metadata
            recommended_ids = list(top_metadata.get("source_capture_ids", []))
            if not recommended_ids:
                recommended_ids = list(top_metadata.get("deck_capture_ids", []))
        return {
            "query": query,
            "usage_scope": usage_scope,
            "literature": [hit.as_dict(include_body=True) for hit in literature],
            "reference_only": [hit.as_dict(include_body=True) for hit in reference_only],
            "capture_groups": [hit.as_dict(include_body=True) for hit in capture_groups],
            "capture_ids": capture_ids,
            "recommended_captures": self._capture_records(recommended_ids),
            "citation_rule": "기본 stage는 Summary·Appendix의 active 근거만 반환합니다. qa_only·listed_only는 사용자가 그 범위를 명시적으로 요청한 경우에만 사용하고, banned는 반환하지 않습니다.",
            "capture_display_rule": (
                "사용자가 근거 원문·캡처·어디에 쓰였는지를 요청하면 recommended_captures의 id를 "
                "get_capture_image에 넘겨 이미지를 직접 표시하세요. source 캡처가 없으면 deck_only 상태를 밝혀야 합니다."
            ),
        }

    def get_implementation(self, topic: str = "점수 Care 할인 생활권") -> dict[str, Any]:
        audit = self._search_source(topic, "IMPLEMENTATION.md", top_k=10)
        model = self._filtered_search(
            topic,
            top_k=8,
            predicate=lambda document: (
                document.source_path in ANSWER_FACT_SOURCES
                and document.authority in {"canonical", "deck"}
                and document.status.lower() not in EXCLUDED_CURRENT_STATUSES
            ),
        )
        return {
            "topic": topic,
            "observed_implementation": [hit.as_dict(include_body=True) for hit in audit],
            "product_contract": [hit.as_dict(include_body=True) for hit in model],
            "warning": "IMPLEMENTATION.md는 외부 dirty checkout을 관측한 스냅샷입니다. product_rule과 current_sandbox_parameter를 구분하세요.",
        }

    def compare_claims(self, query: str) -> dict[str, Any]:
        current = self._filtered_search(
            query,
            top_k=6,
            predicate=lambda document: (
                document.source_path in ANSWER_FACT_SOURCES
                and document.authority in {"canonical", "deck"}
                and document.status.lower() not in EXCLUDED_CURRENT_STATUSES
            ),
        )
        conflicts = self._search_source(query, "knowledge/conflict_map.yaml", top_k=6)
        history = self.index.search(query, top_k=5, authorities={"historical"})
        return {
            "query": query,
            "current": [hit.as_dict(include_body=True) for hit in current],
            "conflicts": [hit.as_dict(include_body=True) for hit in conflicts],
            "history": [hit.as_dict() for hit in history],
            "resolution_rule": "현재 계약이 결론을 정합니다. 과거 자료는 왜 바뀌었는지 설명할 때만 사용합니다.",
        }

    def prepare_answer_context(
        self,
        question: str,
        language: str = "ko",
        max_chars: int = 7000,
        evidence_scope: str = "stage",
    ) -> dict[str, Any]:
        current = self._filtered_search(
            question,
            top_k=7,
            predicate=lambda document: (
                document.authority in {"canonical", "deck"}
                and document.status.lower() not in EXCLUDED_CURRENT_STATUSES
                and document.source_path in ANSWER_FACT_SOURCES
            ),
        )
        evidence = self._literature_hits(question, top_k=4, usage_scope=evidence_scope)
        reference_only = self._reference_only_hits(question, top_k=2, usage_scope=evidence_scope)
        supporting = self._filtered_search(
            question,
            top_k=4,
            predicate=lambda document: (
                document.authority == "supporting"
                and document.source_path == "knowledge/qa/cards.yaml"
                and document.status == "active"
            ),
        )
        history_requested = any(term in question.lower() for term in HISTORY_REQUEST_TERMS)
        history_material: list[SearchHit] = []
        if history_requested:
            history_material.extend(self._filtered_search(
                question,
                top_k=2,
                predicate=lambda document: (
                    document.authority == "historical"
                    and document.source_path in {
                        "knowledge/history/decision_log.yaml",
                        "knowledge/official_positions.yaml",
                    }
                ),
            ))
            history_material.extend(self._filtered_search(
                question,
                top_k=1,
                predicate=lambda document: (
                    document.authority == "historical"
                    and document.source_path == "knowledge/qa/cards.yaml"
                ),
            ))
        conflicts = self._search_source(question, "knowledge/conflict_map.yaml", top_k=3)
        glossary = self._search_source(
            question,
            "knowledge/glossary.yaml",
            top_k=4,
            statuses={"active"},
        )

        def answer_hit(hit: SearchHit, body_chars: int = 0) -> dict[str, Any]:
            payload = hit.as_dict(include_body=False)
            payload["snippet"] = payload["snippet"][:520]
            if body_chars:
                body = hit.document.body
                payload["body"] = body if len(body) <= body_chars else f"{body[:body_chars].rstrip()}…"
            return payload

        packet: dict[str, Any] = {
            "question": question,
            "language": language,
            "evidence_scope": evidence_scope,
            "answer_instruction": (
                "아래 재료로 의미가 정확한 짧은 문장을 만드세요. 확정 답안을 복사하지 말고 질문에 직접 답하세요. "
                "후보값·미검증 가설·과거 이력은 상태를 숨기지 마세요. historical_material은 현재 사실을 "
                "정하는 근거가 아니라 질문 의도·변경 이유·후속 질문을 이해하는 재료로만 사용하세요."
            ),
            "current_facts": [answer_hit(hit, 900) for hit in current[:5]],
            "evidence": [answer_hit(hit, 700) for hit in evidence[:3]],
            "reference_only": [answer_hit(hit, 700) for hit in reference_only[:2]],
            "evidence_captures": [],
            "explanation_material": [answer_hit(hit) for hit in supporting[:2]],
            "historical_material": [answer_hit(hit) for hit in history_material[:2]],
            "conflicts_and_avoid": [answer_hit(hit, 650) for hit in conflicts[:2]],
            "fixed_terms": [answer_hit(hit) for hit in glossary[:2]],
            "truncated": False,
            "packet_chars": max_chars,
        }
        wants_capture = any(term in question.lower() for term in CAPTURE_REQUEST_TERMS)
        capture_source = (evidence[0] if evidence else (reference_only[0] if reference_only else None)) if wants_capture else None
        if capture_source:
            metadata = capture_source.document.metadata
            capture_ids = list(metadata.get("source_capture_ids", []))
            if not capture_ids:
                capture_ids = list(metadata.get("deck_capture_ids", []))
            packet["evidence_captures"] = self._answer_capture_records(capture_ids)
            packet["answer_instruction"] += (
                " 사용자가 근거 캡처를 요청했다면 evidence_captures의 id로 get_capture_image를 호출해 이미지를 직접 보여주세요."
            )

        def packet_size() -> int:
            return len(json.dumps(packet, ensure_ascii=False))

        original_counts = {key: len(value) for key, value in packet.items() if isinstance(value, list)}
        minimums = {
            "current_facts": 1 if packet["evidence_captures"] else 2,
            "evidence": 1 if packet["evidence_captures"] and evidence else 0,
            "reference_only": 1 if packet["evidence_captures"] and not evidence and reference_only else 0,
            "evidence_captures": 1 if packet["evidence_captures"] else 0,
            "explanation_material": 1 if packet["explanation_material"] and not packet["evidence_captures"] else 0,
            "historical_material": 1 if packet["historical_material"] else 0,
            "conflicts_and_avoid": 0,
            "fixed_terms": 0,
        }
        drop_order = (
            "explanation_material",
            "historical_material",
            "fixed_terms",
            "evidence_captures",
            "evidence",
            "reference_only",
            "conflicts_and_avoid",
            "current_facts",
        )
        while packet_size() > max_chars:
            for key in drop_order:
                if len(packet[key]) > minimums[key]:
                    packet[key].pop()
                    break
            else:
                break

        if packet_size() > max_chars:
            for key in ("current_facts", "conflicts_and_avoid", "evidence", "reference_only"):
                for item in packet[key]:
                    for field, limit in (("body", 360), ("snippet", 240)):
                        value = item.get(field)
                        if isinstance(value, str) and len(value) > limit:
                            item[field] = f"{value[:limit].rstrip()}…"

        if packet_size() > max_chars:
            for key in (
                "current_facts",
                "evidence",
                "reference_only",
                "explanation_material",
                "historical_material",
                "conflicts_and_avoid",
                "fixed_terms",
            ):
                for item in packet[key]:
                    item.pop("metadata", None)

        if packet_size() > max_chars:
            for key in ("current_facts", "evidence", "reference_only", "conflicts_and_avoid"):
                for item in packet[key]:
                    if isinstance(item.get("body"), str):
                        item["body"] = f"{item['body'][:240].rstrip()}…"
                    if isinstance(item.get("snippet"), str):
                        item["snippet"] = f"{item['snippet'][:160].rstrip()}…"

        while packet_size() > max_chars and len(packet["current_facts"]) > 1:
            packet["current_facts"].pop()

        packet["truncated"] = any(
            len(packet[key]) < count for key, count in original_counts.items()
        )
        packet["packet_chars"] = 0
        while True:
            final_size = packet_size()
            if packet["packet_chars"] == final_size:
                break
            packet["packet_chars"] = final_size
        return packet

    def list_open_items(self, query: str = "미확정 unresolved 검증 필요", top_k: int = 12) -> dict[str, Any]:
        self._validate_top_k(top_k)
        unresolved = [
            document
            for document in self.corpus.documents
            if document.status in {"unresolved", "pilot_hypothesis", "candidate_parameter", "planned_not_implemented"}
        ]
        local = HybridSearchIndex(unresolved)
        hits = local.search(query, top_k=top_k) if unresolved else []
        return {
            "query": query,
            "items": [hit.as_dict(include_body=True) for hit in hits],
            "rule": "미확정은 숨기지 않고 현재 상태, 권고 표현, 필요한 검증을 함께 말합니다.",
        }

    def list_captures(self, query: str = "문헌", top_k: int = 20, usage_scope: str = "stage") -> dict[str, Any]:
        self._validate_top_k(top_k, maximum=50)
        if usage_scope not in EVIDENCE_SCOPES:
            raise ValueError(f"usage_scope must be one of: {', '.join(sorted(EVIDENCE_SCOPES))}")
        allowed_statuses = {
            "stage": {"active"},
            "qa_only": {"qa_only"},
            "listed_only": {"listed_only"},
            "all": {"active", "qa_only", "listed_only"},
        }[usage_scope]
        generic_queries = {"", "문헌", "문헌 캡처", "근거", "근거 캡처", "captures", "literature"}
        is_generic_query = query.strip().lower() in generic_queries
        eligible_groups = [
            document
            for document in self.corpus.documents
            if document.source_path == "knowledge/evidence/capture_index.yaml"
            and document.metadata.get("card_status") in allowed_statuses
        ]
        if is_generic_query:
            groups = [
                SearchHit(document, 1.0, document.body[:520])
                for document in eligible_groups
            ][: min(top_k, 30)]
        else:
            raw_groups = self.index.search(
                query,
                top_k=30,
                authorities={"evidence", "supporting", "historical"},
                source_contains="knowledge/evidence/capture_index.yaml",
            )
            groups = [
                hit for hit in raw_groups
                if hit.document.metadata.get("card_status") in allowed_statuses
            ][: min(top_k, 30)]
        capture_ids: list[str] = []
        for group in groups:
            for capture_id in group.document.metadata.get("capture_ids", []):
                if capture_id not in capture_ids:
                    capture_ids.append(capture_id)
        captures = []
        for capture_id in capture_ids[:top_k]:
            metadata, _ = self.capture(capture_id)
            captures.append(metadata)
        eligible_capture_ids = {
            capture_id
            for document in eligible_groups
            for capture_id in document.metadata.get("capture_ids", [])
        }
        return {
            "query": query,
            "usage_scope": usage_scope,
            "total_group_count": len(eligible_groups),
            "total_capture_count": len(eligible_capture_ids),
            "groups": [hit.as_dict(include_body=True) for hit in groups],
            "captures": captures,
            "truncated": is_generic_query and (
                len(groups) < len(eligible_groups) or len(captures) < len(eligible_capture_ids)
            ),
        }

    def capture(self, capture_id: str) -> tuple[dict[str, Any], Path]:
        normalized = capture_id if capture_id.startswith("capture://") else f"capture://{capture_id}"
        document = self.corpus.by_id.get(normalized)
        if not document:
            raise KeyError(f"unknown capture_id: {capture_id}")
        path = (self.root / document.source_path).resolve()
        if not path.is_relative_to(self.root) or not path.exists():
            raise FileNotFoundError(document.source_path)
        return document.metadata, path

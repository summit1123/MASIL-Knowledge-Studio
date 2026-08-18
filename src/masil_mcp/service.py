from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

from .corpus import KnowledgeCorpus
from .models import KnowledgeDocument, SearchHit
from .routing import route_question
from .search import HybridSearchIndex, normalize


SCOPES: dict[str, set[str] | None] = {
    "current": {"canonical", "deck"},
    "canonical": {"canonical"},
    "slides": {"deck"},
    "evidence": {"evidence"},
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
EVIDENCE_SCOPES = {"stage"}
OPEN_ITEM_STATUSES = {"unresolved", "pilot_hypothesis", "candidate_parameter", "planned_not_implemented"}
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
EVIDENCE_QUERY_HINTS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("초행 도로", "처음 가는 도로", "처음 가는 경로", "낯선 도로", "unfamiliar road"), "Ehsani Tefft 2021"),
)
ANSWER_FACT_SOURCES = {
    "knowledge/qa/field_regression_36.yaml",
    "knowledge/qa/field_qna_100.yaml",
    "knowledge/field_contract.yaml",
    "knowledge/claims/deck_claims.yaml",
}
GUARDRAIL_SOURCES = {
    "knowledge/field_contract.yaml",
}
FINAL_QA_SOURCE = "knowledge/qa/field_qna_100.yaml"
FIELD_QA_SOURCE = "knowledge/qa/field_regression_36.yaml"
CURRENT_SCRIPT_SOURCE = "sources/13_presentation_script_final_0818.md"


class KnowledgeService:
    def __init__(self, root: Path | None = None):
        self.corpus = KnowledgeCorpus(root)
        self.index = HybridSearchIndex(self.corpus.documents)
        self.root = self.corpus.root
        self.qa_catalog = yaml.safe_load((self.root / FINAL_QA_SOURCE).read_text(encoding="utf-8"))
        self.qa_by_id = {item["id"]: item for item in self.qa_catalog["questions"]}
        self.field_qa = yaml.safe_load((self.root / FIELD_QA_SOURCE).read_text(encoding="utf-8"))
        self.field_qa_by_question = {
            normalize(question): item
            for item in self.field_qa["questions"]
            for question in (item["question_ko"], item["question_en"])
        }
        self.qa_by_question = {
            normalize(question): item
            for item in self.qa_catalog["questions"]
            for question in (item["question_ko"], item["question_en"])
        }

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
        allowed_tiers = {"stage_citable"}
        if not allowed_tiers:
            return []
        normalized_query = normalize(query)
        query_hints = [
            hint
            for triggers, hint in EVIDENCE_QUERY_HINTS
            if any(normalize(trigger) in normalized_query for trigger in triggers)
        ]
        evidence_query = " ".join([query, *query_hints])
        hits = self.index.search(
            evidence_query,
            top_k=top_k,
            expand_aliases=False,
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

    def _capture_groups_for(self, literature: list[SearchHit], usage_scope: str = "stage") -> list[SearchHit]:
        if usage_scope not in EVIDENCE_SCOPES:
            raise ValueError(f"usage_scope must be one of: {', '.join(sorted(EVIDENCE_SCOPES))}")
        allowed_statuses = {"active"}
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

    @staticmethod
    def _registry_ref(value: Any) -> str | None:
        ref = str(value).strip()
        if ref.startswith("knowledge/evidence/registry.yaml#presentation-"):
            return ref
        if ref.startswith("presentation-"):
            return f"knowledge/evidence/registry.yaml#{ref}"
        return None

    def _linked_evidence_hits(
        self,
        fact_hits: list[SearchHit],
        query: str,
        *,
        usage_scope: str = "stage",
        limit: int = 4,
    ) -> tuple[list[SearchHit], dict[str, list[dict[str, Any]]]]:
        """Traverse curated claim-to-literature links and rank only inside that set.

        Generic source_refs/material_refs/evidence_ref fields describe provenance or
        preparation material. They are deliberately not treated as proof. Only an
        explicit evidence_links record may connect a current claim to literature.
        """
        allowed_statuses = {"stage_citable"} if usage_scope == "stage" else None
        if allowed_statuses is None:
            raise ValueError(f"usage_scope must be one of: {', '.join(sorted(EVIDENCE_SCOPES))}")

        documents: list[KnowledgeDocument] = []
        links_by_ref: dict[str, list[dict[str, Any]]] = {}
        seen: set[str] = set()
        for hit in fact_hits:
            metadata = hit.document.metadata
            for link in metadata.get("evidence_links", []):
                if not isinstance(link, dict) or not link.get("ref"):
                    continue
                normalized = self._registry_ref(link["ref"])
                if not normalized:
                    continue
                relation = str(link.get("relation", "")).strip()
                if relation not in {
                    "direct",
                    "method_reference",
                    "supporting_context",
                    "indirect_background",
                }:
                    continue
                ref = normalized
                links_by_ref.setdefault(ref, []).append(
                    {
                        "supports": str(link.get("supports", "")).strip(),
                        "relation": relation,
                        "auto_show_source": bool(link.get("auto_show_source", False)),
                    }
                )
                if not ref or ref in seen:
                    continue
                document = self.corpus.by_id.get(ref)
                if not document or document.status not in allowed_statuses:
                    continue
                documents.append(document)
                seen.add(ref)

        if not documents:
            return [], links_by_ref

        ranking_documents = [
            KnowledgeDocument(
                id=document.id,
                title=document.title,
                body="\n".join([
                    *[
                        str(link.get("supports", ""))
                        for link in links_by_ref.get(document.id, [])
                        if link.get("supports")
                    ],
                    document.body,
                ]),
                source_path=document.source_path,
                authority=document.authority,
                status=document.status,
                layer=document.layer,
                topic=document.topic,
                tags=document.tags,
                metadata=document.metadata,
            )
            for document in documents
        ]
        ranked = HybridSearchIndex(ranking_documents).search(
            query,
            top_k=min(30, len(ranking_documents)),
        )
        ranked_before_source_filter = ranked
        ranked = self._prefer_named_source(query, ranked)
        named_source_filter_applied = len(ranked) < len(ranked_before_source_filter)
        rank_by_id = {hit.document.id: hit.score for hit in ranked}
        ordered_ids = [hit.document.id for hit in ranked]
        if not named_source_filter_applied:
            ordered_ids.extend(document.id for document in documents if document.id not in rank_by_id)
        document_by_id = {document.id: document for document in documents}
        return (
            [
                SearchHit(
                    document_by_id[document_id],
                    rank_by_id.get(document_id, 0.01),
                    document_by_id[document_id].body[:520],
                )
                for document_id in ordered_ids[:limit]
            ],
            links_by_ref,
        )

    @staticmethod
    def _merge_unique_hits(*groups: list[SearchHit], limit: int) -> list[SearchHit]:
        merged: list[SearchHit] = []
        seen: set[str] = set()
        for group in groups:
            for hit in group:
                if hit.document.id in seen:
                    continue
                merged.append(hit)
                seen.add(hit.document.id)
                if len(merged) >= limit:
                    return merged
        return merged

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
        capture_kind: str = "source",
    ) -> dict[str, Any]:
        self._validate_top_k(top_k)
        if capture_kind not in {"source", "deck"}:
            raise ValueError("capture_kind must be source or deck")
        literature = self._literature_hits(query, top_k=top_k, usage_scope=usage_scope)
        selected = literature
        capture_groups = self._capture_groups_for(selected, usage_scope=usage_scope) if include_captures else []
        capture_ids: list[str] = []
        if include_captures:
            for hit in selected:
                metadata = hit.document.metadata
                ordered = list(metadata.get(f"{capture_kind}_capture_ids", []))
                for capture_id in ordered:
                    if capture_id not in capture_ids:
                        capture_ids.append(capture_id)
        recommended_ids: list[str] = []
        if selected and include_captures:
            top_metadata = selected[0].document.metadata
            recommended_ids = list(top_metadata.get(f"{capture_kind}_capture_ids", []))
        capture_gaps = []
        if include_captures:
            for hit in selected:
                metadata = hit.document.metadata
                if not metadata.get(f"{capture_kind}_capture_ids", []):
                    capture_gaps.append({
                        "id": hit.document.id,
                        "source": metadata.get("source", hit.document.title),
                        "requested_capture_kind": capture_kind,
                    })
        return {
            "query": query,
            "usage_scope": usage_scope,
            "literature": [hit.as_dict(include_body=True) for hit in literature],
            "capture_groups": [hit.as_dict(include_body=True) for hit in capture_groups],
            "capture_ids": capture_ids,
            "recommended_captures": self._capture_records(recommended_ids),
            "capture_kind": capture_kind,
            "capture_gaps": capture_gaps,
            "citation_rule": "최종 Summary·Appendix에서 실제 사용하는 active 문헌만 반환합니다. 참고문헌 전용·폐기·과거 자료는 런타임에 포함하지 않습니다.",
            "capture_display_rule": (
                "source는 실제 원문 캡처만, deck은 덱 사용 위치의 발췌만 반환합니다. source가 없을 때 deck으로 "
                "자동 대체하지 마세요. 사용자가 덱 사용 위치를 요청한 경우에만 capture_kind=deck을 사용하세요."
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
        conflicts = self._search_source(query, "knowledge/field_contract.yaml", top_k=6)
        return {
            "query": query,
            "current": [hit.as_dict(include_body=True) for hit in current],
            "conflicts": [hit.as_dict(include_body=True) for hit in conflicts],
            "resolution_rule": "최종 덱과 현재 상품 계약만 사용합니다. 폐기된 표현과 변경 이력은 공개 런타임에 포함하지 않습니다.",
        }

    def prepare_qa_practice(
        self,
        query: str = "",
        theme: str = "all",
        rank: str = "all",
        top_only: bool = False,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Return the final 100-question Q&A canon used by both the app and MCP."""
        self._validate_top_k(limit, maximum=100)
        valid_themes = {item["id"] for item in self.qa_catalog["groups"]}
        if theme != "all" and theme not in valid_themes:
            raise ValueError(f"theme must be all or one of: {', '.join(sorted(valid_themes))}")
        if rank not in {"all", "CORE", "GENERAL", "DEEP"}:
            raise ValueError("rank must be all, CORE, GENERAL, or DEEP")

        allowed_ids = {
            item["id"]
            for item in self.qa_catalog["questions"]
            if (theme == "all" or item["group"] == theme)
            and (rank == "all" or item["tier"] == rank)
            and (not top_only or item["tier"] == "CORE")
        }
        if query.strip():
            hits = self._filtered_search(
                query,
                top_k=30,
                predicate=lambda document: (
                    document.source_path == FINAL_QA_SOURCE
                    and document.id.rsplit("#", 1)[-1] in allowed_ids
                ),
            )
            ordered_ids = [hit.document.id.rsplit("#", 1)[-1] for hit in hits]
        else:
            ordered_ids = [
                item["id"]
                for item in self.qa_catalog["questions"]
                if item["id"] in allowed_ids
            ]

        selected = [self.qa_by_id[item_id] for item_id in ordered_ids[:limit]]
        return {
            "query": query,
            "theme": theme,
            "rank": rank,
            "top_only": top_only,
            "catalog_version": self.qa_catalog["meta"]["version"],
            "total_catalog_questions": len(self.qa_catalog["questions"]),
            "matched_count": len(ordered_ids),
            "questions": selected,
            "response_contract": {
                "answer": "앱과 MCP가 같은 100문항 정본의 짧은 한·영 답변, 상세 논리, 검증 경계와 후속 질문을 사용함",
                "language": "질문 언어와 같은 언어, 영어는 짧고 쉬운 문장",
                "boundary": "최종 덱과 대본이 최우선이며 100문항의 설명은 이를 덮어쓸 수 없음",
            },
            "authority_rule": "정확히 일치하는 36문항 공식 답변을 먼저 사용하고, 그 외에는 최종 덱·대본을 기준으로 정리한 100문항 정본을 사용합니다.",
        }

    def prepare_answer_context(
        self,
        question: str,
        language: str = "ko",
        max_chars: int = 5000,
        evidence_scope: str = "stage",
    ) -> dict[str, Any]:
        routing = route_question(question)
        normalized = normalize(question)
        approved_answer = self.field_qa_by_question.get(normalized) or self.qa_by_question.get(normalized)
        approved_answer_source = (
            FIELD_QA_SOURCE if normalized in self.field_qa_by_question else FINAL_QA_SOURCE
        ) if approved_answer else None
        normalized_question = question.lower()
        calculation_requested = any(
            term in normalized_question
            for term in ("계산", "산식", "공식", "계수", "수치", "숫자", "formula", "calculate", "coefficient")
        )
        evidence_requested = routing.route == "literature_evidence"
        capture_requested = any(term in normalized_question for term in CAPTURE_REQUEST_TERMS)
        current = self._filtered_search(
            question,
            top_k=7,
            predicate=lambda document: (
                document.authority in {"canonical", "deck"}
                and document.status.lower() not in EXCLUDED_CURRENT_STATUSES
                and document.source_path in ANSWER_FACT_SOURCES
            ),
        )
        if approved_answer:
            approved_id = approved_answer["id"]
            approved_hits = self._filtered_search(
                approved_id,
                top_k=1,
                predicate=lambda document: (
                    document.source_path == approved_answer_source
                    and document.id.rsplit("#", 1)[-1] == approved_id
                ),
            )
            current = self._merge_unique_hits(approved_hits, current, limit=7)
        if routing.route == "deck_context":
            deck = self._search_source(question, "knowledge/claims/deck_claims.yaml", top_k=5)
            current = self._merge_unique_hits(deck, current, limit=7)

        # The roadmap slide still prints early planning numbers, but the team
        # now uses only the Pilot -> Scale up -> Roll out direction by default.
        # Keep the numeric slide claim out of ordinary roadmap answers unless
        # the user explicitly asks about timing, scale, or the printed values.
        roadmap_number_terms = (
            "500",
            "15%",
            "20%",
            "+2",
            "0-6",
            "6-18",
            "18+",
            "숫자",
            "수치",
            "인원",
            "기간",
            "일정",
            "가입률",
            "유지율",
        )
        if not any(term in question for term in roadmap_number_terms):
            current = [
                hit
                for hit in current
                if not hit.document.id.endswith("#p2-roadmap-targets")
            ]

        # Semantic literature search is only safe when the user is actually
        # asking about a source. Product questions must traverse the curated
        # evidence_links on the matched current claim; otherwise a thematically
        # similar paper can be presented as proof of a product decision.
        direct_evidence = (
            self._literature_hits(question, top_k=6, usage_scope=evidence_scope)
            if routing.route == "literature_evidence"
            else []
        )
        # Evidence must support the best-matched current claim, not merely a
        # neighboring fact from the same broad topic. Traversing several facts
        # caused methodology/persona captures to appear beside unrelated product
        # answers (for example a DBSCAN paper on a location-penalty question).
        contract_link_facts = self._search_source(
            question,
            "knowledge/field_contract.yaml",
            top_k=2,
            statuses={"active"},
        )
        link_facts = self._merge_unique_hits(current[:1], contract_link_facts, limit=3)
        linked_evidence, evidence_links = self._linked_evidence_hits(
            link_facts,
            question,
            usage_scope=evidence_scope,
            limit=4,
        )
        evidence = self._merge_unique_hits(
            direct_evidence if routing.route == "literature_evidence" else linked_evidence,
            linked_evidence if routing.route == "literature_evidence" else direct_evidence,
            limit=4,
        )
        script_context_requested = any(
            term in question.lower()
            for term in ("대본", "발표자", "파트 배분", "script", "speaker part")
        )
        curated_qa = [] if approved_answer else self._filtered_search(
            question,
            top_k=4,
            predicate=lambda document: (
                document.source_path == FINAL_QA_SOURCE
                and document.status == "active"
            ),
        )
        legacy_examples = self._filtered_search(
            question,
            top_k=3,
            predicate=lambda document: (
                document.authority == "supporting"
                and script_context_requested
                and document.source_path == CURRENT_SCRIPT_SOURCE
            ),
        )
        supporting = self._merge_unique_hits(
            legacy_examples if script_context_requested else [],
            curated_qa,
            limit=6,
        )
        conflicts = self._search_source(question, "knowledge/field_contract.yaml", top_k=3)
        glossary = self._search_source(
            question,
            "knowledge/field_contract.yaml",
            top_k=4,
            statuses={"active"},
        )
        validation_material: list[SearchHit] = []
        if routing.route == "validation_open_items":
            validation_material = self._filtered_search(
                question,
                top_k=5,
                predicate=lambda document: (
                    document.source_path == "knowledge/field_contract.yaml"
                    and document.status in OPEN_ITEM_STATUSES
                ),
            )

        def answer_hit(hit: SearchHit, body_chars: int = 0) -> dict[str, Any]:
            full = hit.as_dict(include_body=False)
            payload = {
                "id": full["id"],
                "title": full["title"],
                "authority": full["authority"],
                "status": full["status"],
                "source": full["source"],
                "snippet": full["snippet"][:420],
            }
            if body_chars:
                body = hit.document.body
                payload["body"] = body if len(body) <= body_chars else f"{body[:body_chars].rstrip()}…"
            return payload

        packet: dict[str, Any] = {
            "question": question,
            "language": language,
            "evidence_scope": evidence_scope,
            "routing": {
                "route": routing.route,
                "confidence": routing.confidence,
                "material_priority": list(routing.material_priority),
            },
            "response_contract": {
                "default": "질문 언어로 직접 답하고, 기본 80~150단어 안에서 짧고 쉬운 결론을 먼저 제시",
                "evidence": "근거 요청 시 직접 연결된 대표 결과 하나와 적용 범위만 설명",
                "expand": "계산·추가 수치·한계는 요청받은 층만 확장",
                "capture_gap": "캡처 요청에 정확한 원문이 없으면 '현재 연결된 원문 캡처는 없습니다.' 한 문장만 추가",
                "hide": "도구명·내부 ID·YAML 필드·통계·검색/캡처 처리 규칙",
                "english": "GAIP 현장에서 말하기 쉬운 짧은 문장과 고정 용어",
                "requested_layers": {
                    "evidence": evidence_requested,
                    "calculation": calculation_requested,
                    "capture": capture_requested,
                },
            },
            "answer_instruction": (
                "질문과 같은 언어로 답하고 첫 1~2문장에 결론을 제시하세요. 기본 답은 80~150단어 이내로 하되, "
                "필요하면 Main answer / Evidence / Limitation 순서로 구성하세요. 질문하지 않은 다른 수치·경고·구현 이력을 한꺼번에 나열하지 "
                "마세요. 근거는 대표 결과 하나와 사용 범위만 말하고, 계산·캡처는 requested_layers가 true인 층만 "
                "설명하세요. 원문 캡처가 없으면 내부 사유 없이 '현재 연결된 원문 캡처는 없습니다.'라고만 하세요. "
                "덱 발췌를 원문처럼 대체하거나 상품 결정을 문헌이 증명했다고 말하지 마세요."
            ),
            "approved_answer": approved_answer,
            "current_facts": [answer_hit(hit, 700) for hit in current[:4]],
            "evidence": [
                {
                    **answer_hit(hit, 480),
                    "claim_links": evidence_links.get(hit.document.id, []),
                    "supports": [
                        link["supports"]
                        for link in evidence_links.get(hit.document.id, [])
                        if link.get("supports")
                    ],
                }
                for hit in evidence[:3]
            ],
            "evidence_captures": [],
            "source_capture_gaps": [],
            "explanation_material": [
                answer_hit(
                    hit,
                    900 if hit.document.source_path == CURRENT_SCRIPT_SOURCE else 0,
                )
                for hit in supporting[:3]
            ],
            "validation_material": [answer_hit(hit, 600) for hit in validation_material[:3]],
            "conflicts_and_avoid": [answer_hit(hit, 480) for hit in conflicts[:2]],
            "fixed_terms": [answer_hit(hit) for hit in glossary[:2]],
            "truncated": False,
            "packet_chars": max_chars,
        }
        explicit_capture_request = capture_requested
        capture_sources = []
        for source in evidence:
            links = evidence_links.get(source.document.id, [])
            if explicit_capture_request or any(link.get("auto_show_source") for link in links):
                capture_sources.append(source)
            if len(capture_sources) >= 2:
                break
        if not capture_sources and explicit_capture_request:
            capture_sources = evidence[:1]
        for source in capture_sources:
            metadata = source.document.metadata
            capture_ids = list(metadata.get("source_capture_ids", []))
            if not capture_ids:
                packet["source_capture_gaps"].append({
                    "evidence_id": source.document.id,
                    "source": metadata.get("source", source.document.title),
                    "rule": "원문 캡처가 없어 덱 발췌로 대체하지 않음",
                })
                continue
            records = self._answer_capture_records(capture_ids[:1])
            for record in records:
                record["evidence_id"] = source.document.id
                record["supports"] = [
                    link["supports"]
                    for link in evidence_links.get(source.document.id, [])
                    if link.get("supports")
                ]
                if record["id"] not in {item["id"] for item in packet["evidence_captures"]}:
                    packet["evidence_captures"].append(record)

        def packet_size() -> int:
            return len(json.dumps(packet, ensure_ascii=False))

        original_counts = {key: len(value) for key, value in packet.items() if isinstance(value, list)}
        visual_count = min(2, len(packet["evidence_captures"]))
        minimums = {
            "current_facts": 1 if packet["evidence_captures"] else 2,
            # Keep at least one directly linked source even when that paper has
            # no source-image asset. Otherwise compact product answers can lose
            # the exact literature boundary merely because no capture exists.
            "evidence": 1 if packet["evidence"] else 0,
            "evidence_captures": visual_count,
            "source_capture_gaps": 1 if packet["source_capture_gaps"] else 0,
            "explanation_material": 1 if packet["explanation_material"] and not packet["evidence_captures"] else 0,
            "validation_material": 1 if packet["validation_material"] else 0,
            "conflicts_and_avoid": 0,
            "fixed_terms": 0,
        }
        drop_order = (
            "explanation_material",
            "fixed_terms",
            "conflicts_and_avoid",
            "current_facts",
            "validation_material",
            "evidence",
            "evidence_captures",
            "source_capture_gaps",
        )
        while packet_size() > max_chars:
            for key in drop_order:
                if len(packet[key]) > minimums[key]:
                    packet[key].pop()
                    break
            else:
                break

        if packet_size() > max_chars:
            packet["routing"].pop("material_priority", None)

        if packet_size() > max_chars:
            for key in ("current_facts", "validation_material", "conflicts_and_avoid", "evidence"):
                for item in packet[key]:
                    for field, limit in (("body", 360), ("snippet", 240)):
                        value = item.get(field)
                        if isinstance(value, str) and len(value) > limit:
                            item[field] = f"{value[:limit].rstrip()}…"

        if packet_size() > max_chars:
            for key in (
                "current_facts",
                "evidence",
                "explanation_material",
                "conflicts_and_avoid",
                "fixed_terms",
            ):
                for item in packet[key]:
                    item.pop("metadata", None)

        if packet_size() > max_chars:
            for key in ("current_facts", "evidence", "conflicts_and_avoid"):
                for item in packet[key]:
                    if isinstance(item.get("body"), str):
                        item["body"] = f"{item['body'][:240].rstrip()}…"
                    if isinstance(item.get("snippet"), str):
                        item["snippet"] = f"{item['snippet'][:160].rstrip()}…"

        while packet_size() > max_chars and len(packet["current_facts"]) > 1:
            packet["current_facts"].pop()

        if packet_size() > max_chars:
            for key in ("current_facts", "evidence"):
                for item in packet[key]:
                    item.pop("snippet", None)
                    if isinstance(item.get("body"), str) and len(item["body"]) > 180:
                        item["body"] = f"{item['body'][:180].rstrip()}…"
                    if isinstance(item.get("claim_links"), list):
                        item["claim_links"] = item["claim_links"][:1]
                    if isinstance(item.get("supports"), list):
                        item["supports"] = list(dict.fromkeys(item["supports"]))[:1]
            for capture in packet["evidence_captures"]:
                if isinstance(capture.get("supports"), list):
                    capture["supports"] = list(dict.fromkeys(capture["supports"]))[:1]

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

    @staticmethod
    def _focused_hits(
        hits: list[SearchHit],
        *,
        limit: int,
        absolute_floor: float = 5.0,
        relative_floor: float = 0.12,
    ) -> list[SearchHit]:
        """Drop weak tail matches instead of presenting them as relevant material."""
        if not hits:
            return []
        cutoff = max(absolute_floor, hits[0].score * relative_floor)
        return [hit for hit in hits if hit.score >= cutoff][:limit]

    def prepare_topic_brief(self, topic: str) -> dict[str, Any]:
        """Return sourced interpretation material without inventing likely questions."""
        contract_current = self._filtered_search(
            topic,
            top_k=4,
            predicate=lambda document: (
                document.source_path == "knowledge/field_contract.yaml"
                and document.status.lower() not in EXCLUDED_CURRENT_STATUSES
            ),
        )
        supporting_current = self._filtered_search(
            topic,
            top_k=6,
            predicate=lambda document: (
                document.authority in {"canonical", "deck"}
                and document.source_path in ANSWER_FACT_SOURCES
                and document.source_path != "knowledge/field_contract.yaml"
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
        open_material = self._filtered_search(
            topic,
            top_k=5,
            predicate=lambda document: (
                document.source_path == "knowledge/field_contract.yaml"
                and document.status in OPEN_ITEM_STATUSES
            ),
        )
        examples = self._filtered_search(
            topic,
            top_k=3,
            predicate=lambda document: (
                document.source_path == FINAL_QA_SOURCE
                and document.status == "active"
            ),
        )

        # The field contract is the public interpretation layer.  Keep its best
        # matches ahead of deck/Q&A supplements so a detailed Q&A card cannot
        # displace the current official position in a topic brief.
        current = self._focused_hits(contract_current, limit=3)
        seen = {hit.document.id for hit in current}
        current.extend(
            hit
            for hit in self._focused_hits(supporting_current, limit=5)
            if hit.document.id not in seen
        )
        current = current[:5]
        guardrails = self._focused_hits(guardrails, limit=4)
        open_material = self._focused_hits(open_material, limit=4)
        examples = self._focused_hits(examples, limit=2)

        linked_hits, linked_links = self._linked_evidence_hits(
            current,
            topic,
            usage_scope="stage",
            limit=4,
        )

        return {
            "topic": topic,
            "purpose": "이 주제를 이해하고 설명할 재료를 제공합니다. 예상 질문이나 정답 문장을 자동 생성하지 않습니다.",
            "usage_rules": [
                "current_position은 현재 팀 입장과 덱 사실입니다.",
                "claim_boundaries는 과장·오해를 피하기 위한 경계이며 질문 목록이 아닙니다.",
                "validation_boundaries는 검증 전 항목입니다. 비어 있으면 억지로 약점을 만들지 마세요.",
                "forbidden_claims와 must_not_say를 likely questions로 변환하지 마세요.",
                "사용자가 실제 질문을 주면 이 재료를 prepare_answer_context와 함께 사용해 짧고 쉬운 답을 구성하세요.",
                "사용자가 예상 질문 생성을 명시적으로 요청한 경우에만 별도로 생성하고, generated by Claude라고 표시하세요.",
            ],
            "current_position": [hit.as_dict(include_body=True) for hit in current],
            "claim_boundaries": [hit.as_dict(include_body=True) for hit in guardrails],
            "validation_boundaries": [hit.as_dict(include_body=True) for hit in open_material],
            "linked_literature": [
                {
                    "id": hit.document.id,
                    "title": hit.document.title,
                    "status": hit.document.status,
                    "claim_links": linked_links.get(hit.document.id, []),
                    "supports": [
                        link["supports"]
                        for link in linked_links.get(hit.document.id, [])
                        if link.get("supports")
                    ],
                    "body": hit.document.body,
                    "metadata": hit.document.metadata,
                }
                for hit in linked_hits[:4]
            ],
            "plain_wording_material": [hit.as_dict(include_body=True) for hit in examples],
        }

    def resolve_evidence_capture(
        self,
        query: str,
        usage_scope: str = "stage",
        capture_kind: str = "source",
    ) -> dict[str, Any]:
        """Resolve a capture through an exact literature mapping before display."""
        evidence = self.get_evidence(
            query,
            top_k=6,
            include_captures=True,
            usage_scope=usage_scope,
            capture_kind=capture_kind,
        )
        recommended = evidence["recommended_captures"]
        if recommended:
            return {
                "query": query,
                "usage_scope": usage_scope,
                "literature": evidence["literature"],
                "capture": recommended[0],
                "resolution": f"direct_evidence_search_{capture_kind}",
            }

        brief = self.prepare_topic_brief(query)
        allowed_statuses = {"stage_citable"} if usage_scope == "stage" else None
        if allowed_statuses is None:
            raise ValueError(f"usage_scope must be one of: {', '.join(sorted(EVIDENCE_SCOPES))}")
        # Never skip a missing capture on the best-matched claim and silently
        # substitute a lower-ranked paper. That was the source of unrelated
        # persona/methodology images appearing beside product answers.
        for literature in brief["linked_literature"][:1]:
            if literature["status"] not in allowed_statuses:
                continue
            metadata = literature.get("metadata", {})
            capture_ids = list(metadata.get(f"{capture_kind}_capture_ids", []))
            for capture_id in capture_ids:
                capture, _ = self.capture(capture_id)
                if capture.get("card_status") == "active":
                    return {
                        "query": query,
                        "usage_scope": usage_scope,
                        "literature": [literature],
                        "capture": capture,
                        "resolution": f"current_position_evidence_link_{capture_kind}",
                    }
        raise ValueError(
            f"No exact mapped {capture_kind} capture was found for this topic. Do not substitute another capture kind or guess an ID."
        )

    def list_open_items(
        self,
        query: str = "미확정 unresolved 검증 필요",
        top_k: int = 20,
        status_filter: str = "unresolved",
    ) -> dict[str, Any]:
        self._validate_top_k(top_k)
        if status_filter not in {*OPEN_ITEM_STATUSES, "all"}:
            raise ValueError(
                "status_filter must be one of: unresolved, pilot_hypothesis, candidate_parameter, planned_not_implemented, all"
            )
        eligible = [
            document
            for document in self.corpus.documents
            if document.source_path == "knowledge/field_contract.yaml"
            and document.status in OPEN_ITEM_STATUSES
            and (status_filter == "all" or document.status == status_filter)
        ]
        generic_queries = {
            "",
            "미확정",
            "미확정 항목",
            "미확정 unresolved 검증 필요",
            "unresolved",
            "open items",
        }
        if query.strip().lower() in generic_queries:
            hits = [SearchHit(document, 1.0, document.body[:520]) for document in eligible[:top_k]]
        else:
            local = HybridSearchIndex(eligible)
            hits = local.search(query, top_k=top_k) if eligible else []
        status_counts = {
            status: sum(document.status == status for document in eligible)
            for status in sorted(OPEN_ITEM_STATUSES)
            if any(document.status == status for document in eligible)
        }
        return {
            "query": query,
            "status_filter": status_filter,
            "total_count": len(eligible),
            "returned_count": len(hits),
            "status_counts": status_counts,
            "truncated": len(hits) < len(eligible),
            "items": [hit.as_dict(include_body=True) for hit in hits],
            "rule": "items 길이를 전체 개수로 추정하지 말고 total_count를 사용합니다. unresolved, pilot_hypothesis, candidate_parameter를 서로 섞어 말하지 않습니다.",
        }

    def list_captures(self, query: str = "문헌", top_k: int = 20, usage_scope: str = "stage") -> dict[str, Any]:
        self._validate_top_k(top_k, maximum=50)
        if usage_scope not in EVIDENCE_SCOPES:
            raise ValueError(f"usage_scope must be one of: {', '.join(sorted(EVIDENCE_SCOPES))}")
        allowed_statuses = {"active"}
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
                authorities={"evidence"},
                source_contains="knowledge/evidence/capture_index.yaml",
            )
            raw_groups = self._prefer_named_source(query, raw_groups)
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

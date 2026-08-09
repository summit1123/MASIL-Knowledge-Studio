from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .corpus import KnowledgeCorpus
from .models import SearchHit
from .search import HybridSearchIndex


SCOPES: dict[str, set[str] | None] = {
    "all": None,
    "current": {"canonical", "deck", "evidence"},
    "canonical": {"canonical"},
    "slides": {"deck"},
    "evidence": {"evidence"},
    "supporting": {"supporting"},
    "history": {"historical"},
}

EXCLUDED_CURRENT_STATUSES = {"banned", "prohibited", "historical", "archived", "superseded", "deprecated"}


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

    def search(self, query: str, top_k: int = 8, scope: str = "all", detail: str = "compact") -> dict[str, Any]:
        if scope not in SCOPES:
            raise ValueError(f"scope must be one of: {', '.join(SCOPES)}")
        hits = self.index.search(
            query,
            top_k=top_k,
            authorities=SCOPES[scope],
            status_exclude=EXCLUDED_CURRENT_STATUSES if scope in {"current", "canonical", "slides", "evidence"} else None,
        )
        return {
            "query": query,
            "scope": scope,
            "result_count": len(hits),
            "results": [hit.as_dict(include_body=detail == "full") for hit in hits],
        }

    def _search_source(self, query: str, source: str, top_k: int = 8) -> list[SearchHit]:
        return self.index.search(query, top_k=top_k, source_contains=source)

    def explain_product_logic(self, topic: str, detail: str = "compact") -> dict[str, Any]:
        hits = self.index.search(
            topic,
            top_k=10,
            authorities={"canonical"},
            status_exclude=EXCLUDED_CURRENT_STATUSES,
        )
        return {
            "topic": topic,
            "contract": "최신 상품 계약과 현재 구현 후보값을 구분해 반환합니다.",
            "facts": [hit.as_dict(include_body=detail == "full") for hit in hits],
            "boundary": "candidate_parameter와 unresolved는 확정 요율·검증 결과로 바꾸지 마세요.",
        }

    def get_slide_context(self, page: int, detail: str = "compact") -> dict[str, Any]:
        page_terms = [f"page: {page}", f"page_number: {page}", f"slide: {page}", f"p.{page}"]
        hits: list[SearchHit] = []
        for document in self.corpus.documents:
            if document.authority != "deck":
                continue
            metadata = json.dumps(document.metadata, ensure_ascii=False)
            searchable = f"{document.title}\n{document.body}\n{metadata}".lower()
            if any(term.lower() in searchable for term in page_terms):
                hits.append(SearchHit(document, 1.0, document.body[:520]))
        if not hits:
            hits = self._search_source(str(page), "deck_claims.yaml", top_k=12)
        return {
            "page": page,
            "claims": [hit.as_dict(include_body=detail == "full") for hit in hits[:20]],
            "status_rule": "as_printed는 그대로, needs_context는 구두 보완과 함께, correction_planned는 교정 상태를 함께 설명합니다.",
        }

    def get_evidence(self, query: str, top_k: int = 6, include_captures: bool = True) -> dict[str, Any]:
        literature = self.index.search(query, top_k=top_k, source_contains="knowledge/evidence/registry.yaml")
        capture_groups = (
            self.index.search(query, top_k=min(top_k, 6), source_contains="knowledge/evidence/capture_index.yaml")
            if include_captures
            else []
        )
        capture_ids: list[str] = []
        for hit in [*literature, *capture_groups]:
            for capture_id in hit.document.metadata.get("capture_ids", []):
                if capture_id not in capture_ids:
                    capture_ids.append(capture_id)
        return {
            "query": query,
            "literature": [hit.as_dict(include_body=True) for hit in literature],
            "capture_groups": [hit.as_dict(include_body=True) for hit in capture_groups],
            "capture_ids": capture_ids,
            "citation_rule": "allowed_claim과 caveat 범위 안에서만 사용하고 banned·listed_only를 선제 근거로 쓰지 마세요.",
        }

    def get_implementation(self, topic: str = "점수 Care 할인 생활권") -> dict[str, Any]:
        audit = self._search_source(topic, "IMPLEMENTATION.md", top_k=10)
        model = self.index.search(topic, top_k=8, authorities={"canonical"}, status_exclude=EXCLUDED_CURRENT_STATUSES)
        return {
            "topic": topic,
            "observed_implementation": [hit.as_dict(include_body=True) for hit in audit],
            "product_contract": [hit.as_dict(include_body=True) for hit in model],
            "warning": "IMPLEMENTATION.md는 외부 dirty checkout을 관측한 스냅샷입니다. product_rule과 current_sandbox_parameter를 구분하세요.",
        }

    def compare_claims(self, query: str) -> dict[str, Any]:
        current = self.index.search(query, top_k=6, authorities={"canonical", "deck"}, status_exclude=EXCLUDED_CURRENT_STATUSES)
        conflicts = self._search_source(query, "knowledge/conflict_map.yaml", top_k=6)
        history = self.index.search(query, top_k=5, authorities={"historical"})
        return {
            "query": query,
            "current": [hit.as_dict(include_body=True) for hit in current],
            "conflicts": [hit.as_dict(include_body=True) for hit in conflicts],
            "history": [hit.as_dict() for hit in history],
            "resolution_rule": "현재 계약이 결론을 정합니다. 과거 자료는 왜 바뀌었는지 설명할 때만 사용합니다.",
        }

    def prepare_answer_context(self, question: str, language: str = "ko", max_chars: int = 7000) -> dict[str, Any]:
        current = self.index.search(
            question,
            top_k=7,
            authorities={"canonical", "deck"},
            status_exclude=EXCLUDED_CURRENT_STATUSES,
        )
        evidence = self.index.search(question, top_k=4, authorities={"evidence"}, status_exclude=EXCLUDED_CURRENT_STATUSES)
        supporting = self.index.search(question, top_k=4, authorities={"supporting"})
        conflicts = self._search_source(question, "knowledge/conflict_map.yaml", top_k=3)
        glossary = self._search_source(question, "knowledge/glossary.yaml", top_k=4)

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
            "answer_instruction": (
                "아래 재료로 의미가 정확한 짧은 문장을 만드세요. 확정 답안을 복사하지 말고 질문에 직접 답하세요. "
                "후보값·미검증 가설·과거 이력은 상태를 숨기지 마세요."
            ),
            "current_facts": [answer_hit(hit, 900) for hit in current[:5]],
            "evidence": [answer_hit(hit, 700) for hit in evidence[:3]],
            "explanation_material": [answer_hit(hit) for hit in supporting[:2]],
            "conflicts_and_avoid": [answer_hit(hit, 650) for hit in conflicts[:2]],
            "fixed_terms": [answer_hit(hit) for hit in glossary[:2]],
        }

        def packet_size() -> int:
            return len(json.dumps(packet, ensure_ascii=False))

        original_counts = {key: len(value) for key, value in packet.items() if isinstance(value, list)}
        minimums = {
            "current_facts": 2,
            "evidence": 0,
            "explanation_material": 0,
            "conflicts_and_avoid": 0,
            "fixed_terms": 0,
        }
        drop_order = (
            "explanation_material",
            "fixed_terms",
            "evidence",
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
            for key in ("current_facts", "conflicts_and_avoid", "evidence"):
                for item in packet[key]:
                    for field, limit in (("body", 360), ("snippet", 240)):
                        value = item.get(field)
                        if isinstance(value, str) and len(value) > limit:
                            item[field] = f"{value[:limit].rstrip()}…"

        if packet_size() > max_chars:
            for item in packet["current_facts"]:
                item.pop("metadata", None)
                item.pop("body", None)

        packet["truncated"] = any(
            len(packet[key]) < count for key, count in original_counts.items()
        )
        packet["packet_chars"] = packet_size()
        return packet

    def list_open_items(self, query: str = "미확정 unresolved 검증 필요", top_k: int = 12) -> dict[str, Any]:
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

    def list_captures(self, query: str = "문헌", top_k: int = 20) -> dict[str, Any]:
        groups = self.index.search(query, top_k=min(top_k, 12), source_contains="knowledge/evidence/capture_index.yaml")
        capture_ids: list[str] = []
        for group in groups:
            for capture_id in group.document.metadata.get("capture_ids", []):
                if capture_id not in capture_ids:
                    capture_ids.append(capture_id)
        if not capture_ids:
            capture_ids = [document.id.removeprefix("capture://") for document in self.corpus.documents if document.id.startswith("capture://")]
        captures = []
        for capture_id in capture_ids[:top_k]:
            metadata, _ = self.capture(capture_id)
            captures.append(metadata)
        return {
            "query": query,
            "groups": [hit.as_dict(include_body=True) for hit in groups],
            "captures": captures,
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

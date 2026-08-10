from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable

import yaml

from .models import KnowledgeDocument, repository_root


CANONICAL_YAML = {
    "knowledge/product_model.yaml",
    "knowledge/official_positions.yaml",
    "knowledge/key_numbers.yaml",
    "knowledge/glossary.yaml",
    "knowledge/forbidden_claims.yaml",
    "knowledge/conflict_map.yaml",
    "knowledge/coverage_matrix.yaml",
    "knowledge/presentation_story.yaml",
    "knowledge/snapshot.yaml",
    "knowledge/mcp_manifest.yaml",
}

DECK_YAML = {"knowledge/claims/deck_claims.yaml"}
EVIDENCE_YAML = {
    "knowledge/evidence/registry.yaml",
    "knowledge/evidence/capture_index.yaml",
}
SUPPORTING_YAML = {
    "knowledge/qa/cards.yaml",
    "knowledge/history/decision_log.yaml",
}

MARKDOWN_FILES = {
    "IMPLEMENTATION.md": "canonical",
    "OPEN_ITEMS.md": "canonical",
    "COVERAGE.md": "supporting",
    "README.md": "supporting",
    "REVIEW.md": "supporting",
    "INDEX.md": "supporting",
    "sources/00_확정수치카드.md": "supporting",
    "sources/02_마스터답변안_전항목.md": "supporting",
    "sources/07_근거지도.md": "supporting",
    "sources/08_출처부록_주제별.md": "supporting",
    "sources/11_V20_결정_기록_0810.md": "historical",
    "sources/데이터생성_상세정리.md": "supporting",
    "sources/부록B_해설_팀원용.md": "supporting",
    "sources/부록D_해설_팀원용.md": "supporting",
    "sources/브리핑_0803_이슈정리.md": "historical",
    "sources/생활권_형성주기_이슈정리.md": "supporting",
    "sources/생활권반경_eps_정리.md": "supporting",
    "sources/안전운전자_매력도_정리.md": "supporting",
    "sources/master_qa_artifact_2026-08-10.txt": "historical",
}

IDENTITY_FIELDS = (
    "id",
    "key",
    "domain_id",
    "claim_id",
    "page_id",
    "position_id",
    "name",
)
TITLE_FIELDS = (
    "title_ko",
    "title_en",
    "title",
    "name",
    "source",
    "question_ko",
    "question_en",
    "topic",
    "statement_ko",
)
STATUS_FIELDS = ("status", "claim_status", "citation_tier", "state")
BODY_PRIORITY_FIELDS = (
    "statement_ko",
    "statement_en",
    "text_en",
    "note_ko",
    "direct_answer_ko",
    "spoken_answer_en",
    "allowed_claim",
    "prohibited_claim",
    "current_resolution",
    "recommended_position_ko",
    "plain_english",
    "note",
    "notes",
    "caveat",
    "caveats",
    "formula",
    "value",
    "context",
    "reason",
    "validation_needed",
    "decision_needed",
)


def _scalar_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (str, int, float)):
        return str(value).strip()
    if isinstance(value, list):
        return "\n".join(filter(None, (_scalar_text(item) for item in value)))
    if isinstance(value, dict):
        return "\n".join(
            f"{key}: {text}" for key, item in value.items() if (text := _scalar_text(item))
        )
    return str(value)


def _safe_id(value: str) -> str:
    normalized = re.sub(r"[^0-9A-Za-z가-힣_.:-]+", "-", value.strip()).strip("-")
    return normalized[:180] or hashlib.sha1(value.encode("utf-8")).hexdigest()[:16]


def _first(mapping: dict[str, Any], fields: Iterable[str], default: str = "") -> str:
    for field in fields:
        value = mapping.get(field)
        if value not in (None, "", [], {}):
            return _scalar_text(value)
    return default


def _authority(path: str, item: dict[str, Any]) -> str:
    status = _first(item, STATUS_FIELDS).lower()
    if status in {"banned", "prohibited", "historical", "archived", "superseded", "deprecated"}:
        return "historical"
    if path in DECK_YAML:
        return "deck"
    if path == "knowledge/evidence/capture_index.yaml":
        return "evidence" if item.get("card_status") in {"active", "qa_only"} else "historical"
    if path in EVIDENCE_YAML:
        tier = str(item.get("citation_tier", ""))
        return "evidence" if tier in {"stage_citable", "qa_only"} else "historical"
    if path in CANONICAL_YAML:
        return "canonical"
    if path == "knowledge/qa/cards.yaml":
        return "supporting" if status == "active" else "historical"
    return "supporting"


def _yaml_body(item: dict[str, Any]) -> str:
    lines: list[str] = []
    seen: set[str] = set()
    for field in BODY_PRIORITY_FIELDS:
        if field in item:
            text = _scalar_text(item[field])
            if text and text not in seen:
                lines.append(f"{field}: {text}")
                seen.add(text)
    for field, value in item.items():
        if field in IDENTITY_FIELDS or field in TITLE_FIELDS or field in BODY_PRIORITY_FIELDS:
            continue
        if isinstance(value, (str, int, float, bool)):
            text = _scalar_text(value)
            if text and text not in seen:
                lines.append(f"{field}: {text}")
                seen.add(text)
    return "\n".join(lines)


def _iter_yaml_items(node: Any, trail: list[str] | None = None) -> Iterable[tuple[list[str], dict[str, Any]]]:
    trail = trail or []
    if isinstance(node, dict):
        has_identity = any(field in node for field in IDENTITY_FIELDS)
        has_claim = any(field in node for field in BODY_PRIORITY_FIELDS)
        if has_identity and has_claim:
            yield trail, node
        for key, value in node.items():
            if isinstance(value, (dict, list)):
                yield from _iter_yaml_items(value, [*trail, str(key)])
    elif isinstance(node, list):
        for index, value in enumerate(node):
            if isinstance(value, (dict, list)):
                yield from _iter_yaml_items(value, [*trail, str(index)])


def _metadata(item: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "page",
        "page_number",
        "slide",
        "deck_location",
        "citation_tier",
        "usage_scope",
        "source_refs",
        "answer_authority",
        "implementation_status",
        "claim_type",
        "url",
        "local_capture_available",
        "capture_ids",
        "deck_capture_ids",
        "source_capture_ids",
        "capture_status",
        "evidence_refs",
        "card_status",
    }
    return {key: value for key, value in item.items() if key in allowed}


def load_yaml_documents(root: Path, relative_path: str) -> list[KnowledgeDocument]:
    path = root / relative_path
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    documents: list[KnowledgeDocument] = []
    for trail, item in _iter_yaml_items(data):
        # deck_claims.yaml groups claims under a page object. The recursive
        # flattener yields each claim, so carry the parent page number into the
        # flattened document instead of losing the slide-to-claim mapping.
        if relative_path in DECK_YAML and "page" not in item and len(trail) >= 2 and trail[0] == "pages":
            try:
                parent_page = data["pages"][int(trail[1])]
            except (KeyError, IndexError, TypeError, ValueError):
                parent_page = {}
            if parent_page.get("page") is not None:
                item = {**item, "page": parent_page["page"]}
        raw_id = _first(item, IDENTITY_FIELDS, "/".join(trail))
        title = _first(item, TITLE_FIELDS, raw_id)
        body = _yaml_body(item)
        source_text = _scalar_text(item.get("source"))
        if source_text and source_text != title and source_text not in body:
            body = f"source: {source_text}\n{body}".strip()
        if not body:
            continue
        status = _first(item, STATUS_FIELDS, "unspecified")
        layer = str(item.get("layer", "unspecified"))
        topic = str(item.get("topic", item.get("domain_id", trail[-2] if len(trail) > 1 else "general")))
        tags = [str(value) for key in ("topics", "tags", "keywords", "banned_variants") for value in (item.get(key) or [])]
        documents.append(
            KnowledgeDocument(
                id=f"{relative_path}#{_safe_id(raw_id)}",
                title=title[:300],
                body=body,
                source_path=relative_path,
                authority=_authority(relative_path, item),
                status=status,
                layer=layer,
                topic=topic,
                tags=tags,
                metadata=_metadata(item),
            )
        )
    return documents


HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)


def load_text_documents(root: Path, relative_path: str, authority: str) -> list[KnowledgeDocument]:
    path = root / relative_path
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8", errors="replace")
    matches = list(HEADING_RE.finditer(text))
    if not matches:
        paragraphs = [part.strip() for part in re.split(r"\n{2,}", text) if part.strip()]
        chunks: list[str] = []
        current = ""
        for paragraph in paragraphs:
            if current and len(current) + len(paragraph) > 5000:
                chunks.append(current)
                current = paragraph
            else:
                current = f"{current}\n\n{paragraph}".strip()
        if current:
            chunks.append(current)
        return [
            KnowledgeDocument(
                id=f"{relative_path}#chunk-{index + 1}",
                title=f"{path.name} chunk {index + 1}",
                body=chunk,
                source_path=relative_path,
                authority=authority,
                status="historical" if authority == "historical" else "unspecified",
                topic="master_qa" if "master_qa" in relative_path else "notes",
            )
            for index, chunk in enumerate(chunks)
        ]

    documents: list[KnowledgeDocument] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        if not body:
            continue
        title = match.group(2).strip()
        documents.append(
            KnowledgeDocument(
                id=f"{relative_path}#{_safe_id(title)}-{index + 1}",
                title=title,
                body=body,
                source_path=relative_path,
                authority=authority,
                status="historical" if authority == "historical" else "unspecified",
                topic="implementation" if relative_path == "IMPLEMENTATION.md" else "notes",
            )
        )
    return documents


def load_capture_documents(root: Path) -> list[KnowledgeDocument]:
    manifest_path = root / "assets/evidence/captures/manifest.json"
    if not manifest_path.exists():
        return []
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    documents: list[KnowledgeDocument] = []
    for capture in manifest.get("captures", []):
        body = "\n".join(
            filter(None, [capture.get("heading", ""), capture.get("caption", ""), capture.get("context", ""), capture.get("alt", "")])
        )
        documents.append(
            KnowledgeDocument(
                id=f"capture://{capture['id']}",
                title=f"{capture.get('alt') or '문헌 캡처'} {capture['id']}",
                body=body or "MASIL 결선 마스터 Q&A 문헌 사용 카드 캡처",
                source_path=capture["file"],
                authority="evidence",
                status="captured",
                layer="evidence",
                topic="literature_capture",
                metadata=dict(capture),
            )
        )
    return documents


class KnowledgeCorpus:
    def __init__(self, root: Path | None = None):
        self.root = (root or repository_root()).resolve()
        self.documents = self._load()
        self.by_id = {document.id: document for document in self.documents}

    def _load(self) -> list[KnowledgeDocument]:
        documents: list[KnowledgeDocument] = []
        for relative_path in sorted(CANONICAL_YAML | DECK_YAML | EVIDENCE_YAML | SUPPORTING_YAML):
            documents.extend(load_yaml_documents(self.root, relative_path))
        for relative_path, authority in MARKDOWN_FILES.items():
            documents.extend(load_text_documents(self.root, relative_path, authority))
        documents.extend(load_capture_documents(self.root))
        return documents

    def fingerprint(self) -> str:
        digest = hashlib.sha256()
        for document in sorted(self.documents, key=lambda item: item.id):
            digest.update(document.id.encode("utf-8"))
            digest.update(document.body.encode("utf-8"))
        return digest.hexdigest()

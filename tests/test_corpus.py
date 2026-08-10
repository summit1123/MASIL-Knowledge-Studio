from __future__ import annotations

import json
import hashlib

import pytest

from masil_mcp.service import KnowledgeService


def test_corpus_loads_canonical_and_capture_assets() -> None:
    service = KnowledgeService()
    stats = service.stats()
    assert stats["documents"] > 400
    assert stats["captures"] > 30
    assert "historical" not in stats["authorities"]
    assert len(stats["fingerprint"]) == 64


def test_current_search_prefers_current_care_contract() -> None:
    service = KnowledgeService()
    result = service.search("평소부터 계속 위험한 운전자는 Care인가", top_k=5, scope="current")
    combined = "\n".join(item["snippet"] for item in result["results"])
    assert "급변" in combined
    assert all("master_qa_artifact" not in item["source"] for item in result["results"])


def test_three_tiers_and_hold_are_retrievable() -> None:
    service = KnowledgeService()
    result = service.search("Favorable Standard Care 세 등급 Hold", top_k=8, scope="current", detail="full")
    combined = json.dumps(result, ensure_ascii=False)
    assert "세 등급" in combined
    assert "데이터 부족" in combined


def test_answer_packet_is_compact_and_contains_conflict_guards() -> None:
    service = KnowledgeService()
    packet = service.prepare_answer_context("생활권 밖이면 위험해서 감점하나요?", max_chars=7000)
    encoded = json.dumps(packet, ensure_ascii=False)
    assert len(encoded) < 10000
    assert packet["current_facts"]
    assert "conflicts_and_avoid" in packet


def test_answer_packet_reports_its_final_serialized_size_within_budget() -> None:
    service = KnowledgeService()
    packet = service.prepare_answer_context("생활권 밖 주행은 왜 보는 건가요?", max_chars=7000)
    assert packet["packet_chars"] <= 7000
    assert packet["packet_chars"] == len(json.dumps(packet, ensure_ascii=False))


def test_capture_path_is_confined_to_repository() -> None:
    service = KnowledgeService()
    metadata, path = service.capture("capture-001")
    assert metadata["id"] == "capture-001"
    assert path.exists()
    assert path.is_relative_to(service.root)


def test_runtime_corpus_loads_every_current_contract_collection() -> None:
    service = KnowledgeService()
    expected = {
        "knowledge/official_positions.yaml": ("active", 17),
        "knowledge/glossary.yaml": ("active", 24),
        "knowledge/forbidden_claims.yaml": ("active", 11),
        "knowledge/key_numbers.yaml": ("active", 24),
        "knowledge/qa/cards.yaml": ("active", 25),
        "knowledge/presentation_story.yaml": ("unspecified", 14),
        "knowledge/coverage_matrix.yaml": ("unspecified", 15),
        "knowledge/claims/deck_claims.yaml": (None, 64),
    }
    for source, (status, count) in expected.items():
        documents = [document for document in service.corpus.documents if document.source_path == source]
        if status is not None:
            documents = [document for document in documents if document.status == status]
        assert len(documents) == count, source


def test_missing_status_defaults_are_not_loaded_into_team_runtime() -> None:
    service = KnowledgeService()
    legacy_sources = {
        "knowledge/official_positions.yaml",
        "knowledge/glossary.yaml",
        "knowledge/forbidden_claims.yaml",
        "knowledge/key_numbers.yaml",
        "knowledge/qa/cards.yaml",
    }
    legacy = [
        document
        for document in service.corpus.documents
        if document.source_path in legacy_sources and document.status == "legacy_reference"
    ]
    assert legacy == []

    result = service.search("Care 할인 보너스", top_k=20)
    assert result["scope"] == "current"
    assert all(item["status"] != "legacy_reference" for item in result["results"])
    assert all(item["authority"] != "historical" for item in result["results"])


def test_official_positions_and_presentation_story_are_searchable() -> None:
    service = KnowledgeService()
    care = service.search("Care 다음 달 자동 할인", top_k=8)
    assert any(item["source"] == "knowledge/official_positions.yaml" for item in care["results"])

    target = service.search("왜 고령 운전자부터 시작하는가", top_k=8)
    assert any(item["source"] == "knowledge/presentation_story.yaml" for item in target["results"])


def test_history_is_absent_from_answer_packet_and_runtime_index() -> None:
    service = KnowledgeService()
    packet = service.prepare_answer_context("Care와 할인 관계가 왜 바뀌었나요?", max_chars=12000)
    assert "historical_material" not in packet
    assert all(item["authority"] != "historical" for item in packet["current_facts"])
    assert all(document.authority != "historical" for document in service.corpus.documents)


def test_capture_manifest_dimensions_and_hashes_match_every_asset() -> None:
    service = KnowledgeService()
    manifest = json.loads((service.root / "assets/evidence/captures/manifest.json").read_text(encoding="utf-8"))
    assert manifest["capture_count"] == len(manifest["captures"]) == 44
    for capture in manifest["captures"]:
        path = service.root / capture["file"]
        assert capture["width"] > 0, capture["id"]
        assert capture["height"] > 0, capture["id"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == capture["sha256"], capture["id"]


@pytest.mark.parametrize("top_k", [0, -1, 31])
def test_search_rejects_invalid_top_k(top_k: int) -> None:
    service = KnowledgeService()
    with pytest.raises(ValueError):
        service.search("Care", top_k=top_k)

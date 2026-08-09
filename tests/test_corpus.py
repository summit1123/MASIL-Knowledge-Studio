from __future__ import annotations

import json

from masil_mcp.service import KnowledgeService


def test_corpus_loads_canonical_and_capture_assets() -> None:
    service = KnowledgeService()
    stats = service.stats()
    assert stats["documents"] > 600
    assert stats["captures"] == 44
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


def test_capture_path_is_confined_to_repository() -> None:
    service = KnowledgeService()
    metadata, path = service.capture("capture-001")
    assert metadata["id"] == "capture-001"
    assert path.exists()
    assert path.is_relative_to(service.root)


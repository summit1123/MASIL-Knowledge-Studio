from __future__ import annotations

import json
import hashlib

import pytest

from masil_mcp.service import KnowledgeService


def test_corpus_loads_canonical_and_capture_assets() -> None:
    service = KnowledgeService()
    stats = service.stats()
    assert stats["documents"] > 300
    assert stats["captures"] > 30
    assert "historical" not in stats["authorities"]
    assert len(stats["fingerprint"]) == 64


def test_current_search_prefers_current_care_contract() -> None:
    service = KnowledgeService()
    result = service.search("평소부터 계속 위험한 운전자는 Care인가", top_k=5, scope="current")
    combined = "\n".join(item["snippet"] for item in result["results"])
    assert "Standard" in combined
    assert "동시 변화" in combined
    assert all("master_qa_artifact" not in item["source"] for item in result["results"])


def test_three_tiers_and_hold_are_retrievable() -> None:
    service = KnowledgeService()
    result = service.search("Favorable Standard Care 세 등급 Hold", top_k=8, scope="current", detail="full")
    combined = json.dumps(result, ensure_ascii=False)
    assert "세 등급" in combined
    assert "데이터 부족" in combined


def test_payd_term_and_simple_comparison_are_retrievable() -> None:
    service = KnowledgeService()
    packet = service.prepare_answer_context("Pay-As-You-Drive PAYD UBI MASIL 차이", max_chars=8000)
    combined = json.dumps(packet, ensure_ascii=False)
    assert "Pay-As-You-Drive" in combined
    assert "얼마나 운전" in combined or "how much you drive" in combined
    assert "어떻게 운전" in combined or "how you drive" in combined


def test_latest_dashboard_uses_annual_scores_not_annual_care_favorable_grades() -> None:
    service = KnowledgeService()
    packet = service.prepare_answer_context(
        "Jackie와 Tom 사례가 보여주는 핵심은 무엇인가?",
        max_chars=8000,
    )
    dashboard = service.search("Jackie Tom 81.6 98.4", top_k=8, detail="full")
    encoded = json.dumps({"packet": packet, "dashboard": dashboard}, ensure_ascii=False)
    assert "81.6" in encoded
    assert "98.4" in encoded
    assert "209" in encoded
    assert "10" in encoded
    assert "Care 자체" in encoded or "Care itself" in encoded


def test_current_script_is_supporting_question_surface_not_fact_authority() -> None:
    service = KnowledgeService()
    documents = [
        document
        for document in service.corpus.documents
        if document.source_path == "sources/13_presentation_script_final_0818.md"
    ]
    assert documents
    assert {document.authority for document in documents} == {"supporting"}

    script_text = "\n".join(document.body for document in documents)
    assert "다현" in script_text
    assert "은서" in script_text
    assert "진영" in script_text
    packet = service.prepare_answer_context("최종 발표 대본이 들어왔나요? 발표자 파트를 알려줘", max_chars=7000)
    assert "사용자 업데이트 대기" not in json.dumps(packet, ensure_ascii=False)
    assert any(
        item["source"] == "sources/13_presentation_script_final_0818.md"
        for item in packet["explanation_material"]
    )


def test_answer_packet_is_compact_and_contains_conflict_guards() -> None:
    service = KnowledgeService()
    packet = service.prepare_answer_context("생활권 밖이면 위험해서 감점하나요?", max_chars=7000)
    encoded = json.dumps(packet, ensure_ascii=False)
    assert len(encoded) < 10000
    assert packet["current_facts"]
    assert "conflicts_and_avoid" in packet


def test_out_of_zone_packet_explains_location_neutrality_without_retired_coefficients() -> None:
    service = KnowledgeService()
    packet = service.prepare_answer_context(
        "생활권 밖은 왜 감점하지 않으면서 위험행동 계수는 더 크게 두나요?",
        max_chars=9000,
    )
    encoded = json.dumps(packet, ensure_ascii=False)
    assert "위치 자체" in encoded or "위치만으로" in encoded
    assert "생활권 밖" in encoded and "위험행동" in encoded
    assert "8/12" not in encoded


def test_roadmap_packet_treats_numbers_as_uncommitted_slide_examples() -> None:
    service = KnowledgeService()
    packet = service.prepare_answer_context(
        "Pilot Scale up Roll out 일정과 인원은 확정됐나요?",
        max_chars=7000,
    )
    encoded = json.dumps(packet, ensure_ascii=False)
    assert "단계 방향" in encoded
    assert "미정" in encoded or "확정" in encoded
    assert "초기 사업 가정" in encoded

    generic = service.prepare_answer_context("로드맵을 설명해줘", max_chars=5000)
    generic_facts = json.dumps(generic["current_facts"], ensure_ascii=False)
    assert "p2-roadmap-targets" not in generic_facts
    assert "500 drivers" not in generic_facts


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
        "knowledge/field_contract.yaml": (None, 24),
        "knowledge/qa/field_regression_36.yaml": ("active", 36),
        "knowledge/qa/field_qna_100.yaml": ("active", 100),
        "knowledge/claims/deck_claims.yaml": (None, 30),
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
    }
    legacy = [
        document
        for document in service.corpus.documents
        if document.source_path in legacy_sources and document.status == "legacy_reference"
    ]
    assert legacy == []
    assert not any(
        document.source_path == "knowledge/qa/final_qa_50.yaml"
        for document in service.corpus.documents
    )

    result = service.search("Care 할인 보너스", top_k=20)
    assert result["scope"] == "current"
    assert all(item["status"] != "legacy_reference" for item in result["results"])
    assert all(item["authority"] != "historical" for item in result["results"])


def test_retired_contract_sources_are_not_searchable() -> None:
    service = KnowledgeService()
    care = service.search("Care 다음 달 자동 할인", top_k=8)
    assert any(item["source"] == "knowledge/field_contract.yaml" for item in care["results"])
    assert all(item["source"] != "knowledge/official_positions.yaml" for item in care["results"])

    multiplier = service.search("3배에서 6배 위험이라고 말해도 되나", top_k=5)
    assert all(item["source"] != "knowledge/presentation_story.yaml" for item in multiplier["results"])


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

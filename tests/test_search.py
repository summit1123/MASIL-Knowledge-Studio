from __future__ import annotations

import json

import pytest

from masil_mcp.service import KnowledgeService


def test_korean_ngram_handles_compound_query() -> None:
    service = KnowledgeService()
    result = service.search("생활권밖주행", top_k=6, scope="current")
    assert result["results"]
    assert any("생활권" in item["snippet"] for item in result["results"])


@pytest.mark.parametrize(
    ("query", "expected_id"),
    [
        ("생활권 밖이 위험하다면서 왜 감점은 안 해?", "out-of-zone-risk-and-no-location-penalty"),
        ("out-of-zone travel can be risky, so why is there no location penalty?", "out-of-zone-risk-and-no-location-penalty"),
        ("우대 기본 케어는 세 등급인가?", "product-monthly-tiers-contract"),
        ("MASIL Zone은 어떻게 만들고 매달 어떻게 갱신하나요?", "story-06-how-zone-works"),
        ("MASIL은 무슨 뜻이야?", "model-language-masil-name"),
        ("Care가 할인율을 깎나요?", "care-review-no-direct-price-effect"),
    ],
)
def test_fielded_index_routes_bilingual_presentation_questions(
    query: str,
    expected_id: str,
) -> None:
    service = KnowledgeService()
    result = service.search(query, top_k=3)

    assert result["results"][0]["id"].endswith(expected_id)


def test_default_search_excludes_guardrail_records_from_answer_facts() -> None:
    service = KnowledgeService()
    result = service.search("Favorable Standard Care 세 등급", top_k=10)

    assert result["results"]
    assert all(item["source"] not in {
        "knowledge/conflict_map.yaml",
        "knowledge/forbidden_claims.yaml",
        "knowledge/glossary.yaml",
    } for item in result["results"])
    assert any(item["source"] == "knowledge/official_positions.yaml" for item in result["results"])


@pytest.mark.parametrize(
    ("query", "expected_id"),
    [
        ("GPS 개인정보는 어떻게 보호하나", "story-09-ai-trust-and-privacy"),
        ("보험사가 MASIL을 도입할 이유는 무엇인가", "story-12-social-value"),
        ("아직 검증되지 않았거나 미확정인 것은 무엇인가", "story-13-feasibility-and-roadmap"),
    ],
)
def test_presentation_intents_route_to_the_specific_story(query: str, expected_id: str) -> None:
    service = KnowledgeService()
    result = service.search(query, top_k=3)

    assert result["results"][0]["id"].endswith(expected_id)


def test_literature_search_returns_caveat() -> None:
    service = KnowledgeService()
    result = service.get_evidence("looking but not seeing 71%", top_k=4)
    combined = "\n".join(item["body"] for item in result["literature"])
    assert "71%" in combined
    assert "전체 사고" in combined


@pytest.mark.parametrize(
    ("query", "literature_key", "recommended_capture"),
    [
        ("Cicchino looking but not seeing 71%", "presentation-cicchino-mccartt-2015", "capture-024"),
        ("ERSO 75세 5배", "presentation-erso-older-driver-risk", "capture-015"),
        ("Ehsani 2.5배 초행 도로", "presentation-ehsani-tefft-2021", "capture-006"),
        ("Vivoda 58.8% 자기조절", "presentation-vivoda-2021", "capture-025"),
        ("Chen 2025 AUC 0.82", "presentation-chen-2025-neurology", "capture-009"),
        ("LongROAD 자기조절", "presentation-longroad-self-regulation", "capture-035"),
    ],
)
def test_literature_recommends_exact_capture(
    query: str,
    literature_key: str,
    recommended_capture: str,
) -> None:
    service = KnowledgeService()
    result = service.get_evidence(query, top_k=4)
    assert result["literature"][0]["id"].endswith(literature_key)
    assert [capture["id"] for capture in result["recommended_captures"]] == [recommended_capture]


def test_qa_and_reference_cards_are_retrievable_with_their_usage_status() -> None:
    service = KnowledgeService()
    result = service.list_captures("Candrive", top_k=5, usage_scope="qa_only")
    assert [capture["id"] for capture in result["captures"]] == ["capture-042"]
    assert result["captures"][0]["card_status"] == "qa_only"
    assert result["captures"][0]["deck_location"] == "References only"

    evidence = service.get_evidence("Candrive 5.26배", top_k=5, usage_scope="qa_only")
    assert evidence["literature"][0]["id"].endswith("presentation-candrive-marshall-2023")
    assert [capture["id"] for capture in evidence["recommended_captures"]] == ["capture-042"]

    reference = service.get_evidence("Harms route familiarity 94편", top_k=5, usage_scope="listed_only")
    assert reference["literature"] == []
    assert reference["reference_only"][0]["id"].endswith("presentation-harms-2021")
    assert [capture["id"] for capture in reference["recommended_captures"]] == ["capture-040"]

    ji = service.get_evidence("Ji mobility regularity", top_k=5, usage_scope="listed_only")
    assert ji["reference_only"][0]["id"].endswith("presentation-ji-2023")
    assert [capture["id"] for capture in ji["recommended_captures"]] == ["capture-041"]

    statistics = service.get_evidence("Statistics Korea 2025", top_k=5, usage_scope="listed_only")
    assert statistics["reference_only"][0]["id"].endswith("presentation-statistics-korea-2025")
    assert [capture["id"] for capture in statistics["recommended_captures"]] == ["capture-041"]


def test_banned_cards_remain_out_of_current_evidence_and_capture_discovery() -> None:
    service = KnowledgeService()
    result = service.get_evidence("LexisNexis 45% non-UBI", top_k=5)
    assert result["literature"] == []
    assert result["reference_only"] == []
    assert result["recommended_captures"] == []
    captures = service.list_captures("LexisNexis", top_k=5)
    assert all(capture["id"] != "capture-027" for capture in captures["captures"])


def test_default_capture_and_evidence_scope_excludes_supporting_references() -> None:
    service = KnowledgeService()

    generic = service.list_captures("문헌", top_k=50)
    assert generic["captures"]
    assert {capture["card_status"] for capture in generic["captures"]} == {"active"}

    candrive = service.get_evidence("Candrive 5.26배", top_k=5)
    assert candrive["literature"] == []
    assert candrive["reference_only"] == []
    assert candrive["recommended_captures"] == []


def test_evidence_without_captures_returns_no_capture_fields() -> None:
    service = KnowledgeService()
    result = service.get_evidence(
        "Cicchino looking but not seeing 71%",
        top_k=4,
        include_captures=False,
    )
    assert result["literature"]
    assert result["capture_groups"] == []
    assert result["capture_ids"] == []
    assert result["recommended_captures"] == []


def test_short_source_name_does_not_match_a_substring_in_another_source() -> None:
    service = KnowledgeService()
    result = service.list_captures("ERSO", top_k=5)
    assert [group["id"] for group in result["groups"]] == [
        "knowledge/evidence/capture_index.yaml#capture-group-erso"
    ]
    assert [capture["id"] for capture in result["captures"]] == ["capture-014", "capture-015"]


def test_answer_context_includes_the_top_literature_capture() -> None:
    service = KnowledgeService()
    result = service.prepare_answer_context("Cicchino looking but not seeing 71% 원문 캡처", max_chars=7000)
    assert [capture["id"] for capture in result["evidence_captures"]] == ["capture-024"]


def test_capture_answer_context_stays_within_minimum_budget() -> None:
    service = KnowledgeService()
    result = service.prepare_answer_context(
        "Cicchino looking but not seeing 71% 원문 캡처",
        max_chars=2500,
    )
    assert result["packet_chars"] <= 2500
    assert result["packet_chars"] == len(json.dumps(result, ensure_ascii=False))
    assert result["evidence"]
    assert [capture["id"] for capture in result["evidence_captures"]] == ["capture-024"]


def test_product_question_does_not_receive_a_low_confidence_literature_capture() -> None:
    service = KnowledgeService()
    result = service.prepare_answer_context("3등급 판정과 연간 할인률은 어떻게 연결되나요?", max_chars=7000)
    assert result["evidence"] == []
    assert result["evidence_captures"] == []


def test_out_of_zone_answer_context_traverses_both_exact_evidence_links() -> None:
    service = KnowledgeService()
    result = service.prepare_answer_context(
        "생활권 밖이 위험하다면서 왜 위치만으로 감점하지 않아?",
        max_chars=5000,
    )

    assert {item["id"].split("#")[-1] for item in result["evidence"]} == {
        "presentation-ehsani-tefft-2021",
        "presentation-hirsch-activity-space-2014",
    }
    assert {capture["id"] for capture in result["evidence_captures"]} == {
        "capture-006",
        "capture-037",
    }
    assert result["packet_chars"] <= 5000
    assert "도구명" in result["response_contract"]["hide"]


def test_open_items_do_not_turn_into_facts() -> None:
    service = KnowledgeService()
    result = service.list_open_items("공정성")
    assert result["items"]
    assert any(item["status"] in {"unresolved", "pilot_hypothesis", "candidate_parameter", "planned_not_implemented"} for item in result["items"])


@pytest.mark.parametrize(
    ("question", "expected_first"),
    [
        ("30초 안에 MASIL을 설명해줘", "story-01-one-line-definition"),
        ("MASIL Zone은 어떻게 만들고 매달 어떻게 갱신하나요?", "story-06-how-zone-works"),
        ("Favorable Standard Care 세 등급은 어떻게 나뉘나요?", "product-monthly-tiers-contract"),
        ("보험사는 왜 이 상품을 도입하나요?", "story-12-social-value"),
    ],
)
def test_answer_context_routes_core_questions_to_the_right_material(
    question: str,
    expected_first: str,
) -> None:
    service = KnowledgeService()
    packet = service.prepare_answer_context(question, max_chars=7000)
    assert packet["current_facts"][0]["id"].endswith(expected_first)
    assert packet["response_contract"]["default"].startswith("직접 답하는")


def test_history_material_requires_change_intent_and_prefers_decision_log() -> None:
    service = KnowledgeService()
    ordinary = service.prepare_answer_context("Care와 할인은 어떤 관계인가요?", max_chars=7000)
    assert ordinary["historical_material"] == []

    changed = service.prepare_answer_context("Care와 할인 관계가 왜 바뀌었나요?", max_chars=7000)
    assert changed["historical_material"]
    assert changed["historical_material"][0]["id"].endswith("decision-2026-08-09-care-price-decoupling")

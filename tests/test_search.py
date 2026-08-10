from __future__ import annotations

import pytest

from masil_mcp.service import KnowledgeService


def test_korean_ngram_handles_compound_query() -> None:
    service = KnowledgeService()
    result = service.search("생활권밖주행", top_k=6, scope="current")
    assert result["results"]
    assert any("생활권" in item["snippet"] for item in result["results"])


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


def test_product_question_does_not_receive_a_low_confidence_literature_capture() -> None:
    service = KnowledgeService()
    result = service.prepare_answer_context("3등급 판정과 연간 할인률은 어떻게 연결되나요?", max_chars=7000)
    assert result["evidence"] == []
    assert result["evidence_captures"] == []


def test_open_items_do_not_turn_into_facts() -> None:
    service = KnowledgeService()
    result = service.list_open_items("공정성")
    assert result["items"]
    assert any(item["status"] in {"unresolved", "pilot_hypothesis", "candidate_parameter", "planned_not_implemented"} for item in result["items"])

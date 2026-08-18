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
        ("생활권 밖이 위험하다면서 왜 감점은 안 해?", "C09"),
        ("out-of-zone travel can be risky, so why is there no location penalty?", "G27"),
        ("우대 기본 케어는 세 등급인가?", "G31"),
        ("MASIL Zone은 어떻게 만들고 매달 어떻게 갱신하나요?", "C07"),
        ("MASIL은 무슨 뜻이야?", "G08"),
        ("Care가 할인율을 깎나요?", "G56"),
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
    assert any(item["source"] in {"knowledge/field_contract.yaml", "knowledge/qa/field_regression_36.yaml"} for item in result["results"])


@pytest.mark.parametrize(
    ("query", "expected_id"),
    [
        ("GPS 개인정보는 어떻게 보호하나", "R34"),
        ("보험사가 MASIL을 도입할 이유는 무엇인가", "R29"),
        ("아직 검증되지 않았거나 미확정인 것은 무엇인가", "R01"),
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
        ("Ehsani 2.5배 초행 도로", "presentation-ehsani-tefft-2021", None),
        ("Vivoda 58.8% 자기조절", "presentation-vivoda-2021", None),
        ("Chen 2025 AUC 0.82", "presentation-chen-2025-neurology", None),
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
    expected = [] if recommended_capture is None else [recommended_capture]
    assert [capture["id"] for capture in result["recommended_captures"]] == expected


def test_qa_and_reference_only_material_is_not_in_team_runtime() -> None:
    service = KnowledgeService()
    assert service.get_evidence("Candrive 5.26배", top_k=5)["literature"] == []
    assert service.list_captures("Candrive", top_k=5)["captures"] == []
    assert all(document.status not in {"qa_only", "listed_only"} for document in service.corpus.documents)


def test_banned_cards_remain_out_of_current_evidence_and_capture_discovery() -> None:
    service = KnowledgeService()
    result = service.get_evidence("LexisNexis 45% non-UBI", top_k=5)
    assert result["literature"] == []
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


def test_answer_contract_uses_progressive_disclosure_for_evidence_and_capture_gap() -> None:
    service = KnowledgeService()
    result = service.prepare_answer_context(
        "초행 도로 위험 근거와 상품에서 어디까지 쓰는지 캡처와 함께 보여줘",
        max_chars=7000,
    )
    contract = result["response_contract"]
    assert contract["requested_layers"] == {
        "evidence": True,
        "calculation": False,
        "capture": True,
    }
    assert "대표 결과 하나" in contract["evidence"]
    assert "현재 연결된 원문 캡처는 없습니다" in contract["capture_gap"]
    assert "한꺼번에 나열하지" in result["answer_instruction"]
    assert [item["id"] for item in result["evidence"]] == [
        "knowledge/evidence/registry.yaml#presentation-ehsani-tefft-2021"
    ]
    assert result["evidence_captures"] == []
    assert result["source_capture_gaps"][0]["evidence_id"].endswith(
        "#presentation-ehsani-tefft-2021"
    )


def test_calculation_layer_is_only_requested_by_calculation_question() -> None:
    service = KnowledgeService()
    simple = service.prepare_answer_context("Care가 나오면 할인율이 줄어드나요?", max_chars=7000)
    detailed = service.prepare_answer_context("Care의 월 점수 계산식과 숫자 예시를 보여줘", max_chars=7000)
    assert simple["response_contract"]["requested_layers"]["calculation"] is False
    assert detailed["response_contract"]["requested_layers"]["calculation"] is True


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


def test_current_contract_drives_annual_refund_answer_material() -> None:
    service = KnowledgeService()
    result = service.prepare_answer_context(
        "연간 환급률은 어떻게 정하나요?",
        max_chars=7000,
    )
    assert result["current_facts"]
    encoded = json.dumps(result, ensure_ascii=False)
    assert "유효한 12개월 점수" in encoded
    assert "Care가 나온 달이 있다는 이유만으로 환급률을 자동 차감하지 않습니다" in encoded


def test_qa_practice_filters_by_group_and_depth() -> None:
    service = KnowledgeService()
    result = service.prepare_qa_practice(theme="VALUE", rank="GENERAL", limit=100)
    assert result["questions"]
    assert all(item["group"] == "VALUE" and item["tier"] == "GENERAL" for item in result["questions"])


def test_qa_practice_keyword_search_stays_within_search_limit() -> None:
    service = KnowledgeService()
    result = service.prepare_qa_practice(query="민감도", limit=10)
    encoded = json.dumps(result, ensure_ascii=False)
    assert "969" in encoded
    assert "stable region" in encoded


def test_exact_final_qna_returns_detailed_approved_answer() -> None:
    service = KnowledgeService()
    result = service.prepare_answer_context("AI는 정확히 무엇을 하고, 무엇을 하지 않나요?")
    assert result["approved_answer"]["id"] == "C16"
    encoded = json.dumps(result["approved_answer"], ensure_ascii=False)
    assert "DBSCAN" in encoded
    assert "P90" in encoded
    assert "Reason Code" in encoded


def test_out_of_zone_answer_context_uses_only_direct_problem_evidence() -> None:
    service = KnowledgeService()
    result = service.prepare_answer_context(
        "생활권 밖이 위험하다면서 왜 위치만으로 감점하지 않아?",
        max_chars=5000,
    )

    assert {item["id"].split("#")[-1] for item in result["evidence"]} == {
        "presentation-ehsani-tefft-2021",
    }
    assert result["evidence_captures"] == []
    assert result["source_capture_gaps"] == []
    assert result["packet_chars"] <= 5000
    assert "도구명" in result["response_contract"]["hide"]


def test_open_items_do_not_turn_into_facts() -> None:
    service = KnowledgeService()
    result = service.list_open_items("공정성", status_filter="all")
    assert result["items"]
    assert any(item["status"] in {"unresolved", "pilot_hypothesis", "candidate_parameter", "planned_not_implemented"} for item in result["items"])


@pytest.mark.parametrize(
    ("question", "expected_first"),
    [
        ("30초 안에 MASIL을 설명해줘", "G26"),
        ("MASIL Zone은 어떻게 만들고 매달 어떻게 갱신하나요?", "C07"),
        ("Favorable Standard Care 세 등급은 어떻게 나뉘나요?", "G31"),
        ("보험사는 왜 이 상품을 도입하나요?", "C20"),
    ],
)
def test_answer_context_routes_core_questions_to_the_right_material(
    question: str,
    expected_first: str,
) -> None:
    service = KnowledgeService()
    packet = service.prepare_answer_context(question, max_chars=7000)
    assert packet["current_facts"][0]["id"].endswith(expected_first)
    assert "직접 답" in packet["response_contract"]["default"]


def test_history_material_is_never_returned_by_team_runtime() -> None:
    service = KnowledgeService()
    ordinary = service.prepare_answer_context("Care와 할인은 어떤 관계인가요?", max_chars=7000)
    assert "historical_material" not in ordinary

    changed = service.prepare_answer_context("Care와 할인 관계가 왜 바뀌었나요?", max_chars=7000)
    assert "historical_material" not in changed
    assert all(item["authority"] != "historical" for item in changed["current_facts"])

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from masil_mcp.service import KnowledgeService


ROOT = Path(__file__).resolve().parents[1]
REGRESSION_PATH = ROOT / "knowledge/qa/field_regression_36.yaml"
RETIRED_RUNTIME_SOURCES = {
    "knowledge/official_positions.yaml",
    "knowledge/product_model.yaml",
    "knowledge/glossary.yaml",
    "knowledge/forbidden_claims.yaml",
    "knowledge/conflict_map.yaml",
    "knowledge/key_numbers.yaml",
    "knowledge/presentation_story.yaml",
    "knowledge/qa/cards.yaml",
}


def _questions() -> list[dict[str, str]]:
    payload = yaml.safe_load(REGRESSION_PATH.read_text(encoding="utf-8"))
    return payload["questions"]


def test_field_regression_catalog_has_36_unique_active_questions() -> None:
    questions = _questions()
    assert len(questions) == 36
    assert len({item["id"] for item in questions}) == 36
    assert all(item["status"] == "active" for item in questions)
    assert all(item["question_ko"] and item["question_en"] for item in questions)
    assert all(item["main_answer_ko"] and item["main_answer_en"] for item in questions)


@pytest.mark.parametrize("item", _questions(), ids=lambda item: item["id"])
@pytest.mark.parametrize(("question_key", "language"), [("question_ko", "ko"), ("question_en", "en")])
def test_every_field_question_resolves_to_its_approved_answer(
    item: dict[str, str],
    question_key: str,
    language: str,
) -> None:
    service = KnowledgeService()
    packet = service.prepare_answer_context(
        item[question_key],
        language=language,
        max_chars=12000,
    )

    assert packet["approved_answer"]["id"] == item["id"]
    assert packet["approved_answer"]["main_answer_ko"] == item["main_answer_ko"]
    assert packet["approved_answer"]["main_answer_en"] == item["main_answer_en"]
    assert packet["packet_chars"] <= 12000
    assert packet["packet_chars"] == len(json.dumps(packet, ensure_ascii=False))

    returned_sources = {
        result["source"]
        for section in (
            "current_facts",
            "evidence",
            "explanation_material",
            "validation_material",
            "conflicts_and_avoid",
            "fixed_terms",
        )
        for result in packet[section]
    }
    assert returned_sources.isdisjoint(RETIRED_RUNTIME_SOURCES)


def test_high_risk_answer_boundaries_match_the_field_contract() -> None:
    questions = {item["id"]: item for item in _questions()}

    assert "위치만으로 불이익" in questions["R07"]["main_answer_ko"]
    assert "중립적인 이동 맥락" in questions["R08"]["main_answer_ko"]
    assert "rolling" in questions["R14"]["main_answer_ko"]
    assert "초기 후보" in questions["R18"]["main_answer_ko"]
    assert "세 단계" in questions["R20"]["main_answer_ko"]
    assert "Care 자체가 환급을 깎" in questions["R22"]["main_answer_ko"]
    assert "손해율" in questions["R27"]["main_answer_ko"]
    assert "실제 손해율 개선폭" in questions["R30"]["main_answer_ko"]


def test_retired_product_contracts_are_absent_from_runtime_index() -> None:
    service = KnowledgeService()
    loaded_sources = {document.source_path for document in service.corpus.documents}
    assert loaded_sources.isdisjoint(RETIRED_RUNTIME_SOURCES)

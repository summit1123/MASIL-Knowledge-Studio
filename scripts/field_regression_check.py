from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
REGRESSION_PATH = ROOT / "knowledge/qa/field_regression_36.yaml"


def load_field_questions() -> list[dict[str, Any]]:
    payload = yaml.safe_load(REGRESSION_PATH.read_text(encoding="utf-8"))
    questions = payload["questions"]
    if len(questions) != 36:
        raise RuntimeError(f"expected 36 field questions, got {len(questions)}")
    return questions


async def verify_field_answers(client: Any) -> dict[str, int]:
    questions = load_field_questions()
    checked = 0
    for item in questions:
        for question_key, language in (("question_ko", "ko"), ("question_en", "en")):
            result = await client.call_tool(
                "prepare_answer_context",
                {"question": item[question_key], "language": language},
            )
            approved = (result.structured_content or {}).get("approved_answer") or {}
            if result.is_error:
                raise RuntimeError(f"{item['id']} {language}: MCP call failed")
            if approved.get("id") != item["id"]:
                raise RuntimeError(
                    f"{item['id']} {language}: expected approved answer {item['id']}, "
                    f"got {approved.get('id')!r}"
                )
            for key in ("main_answer_ko", "main_answer_en"):
                if approved.get(key) != item[key]:
                    raise RuntimeError(f"{item['id']} {language}: {key} drifted from field contract")
            checked += 1
    return {"questions": len(questions), "bilingual_answer_calls": checked}

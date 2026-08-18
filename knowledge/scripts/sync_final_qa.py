#!/usr/bin/env python3
"""Import the approved MASIL Q&A site catalog into the MCP knowledge corpus."""

from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE = Path("/Users/gimdonghyeon/Desktop/seniordrive/masil-qa-site/app/qa-data.json")
DEFAULT_TARGET = ROOT / "knowledge/qa/final_qa_50.yaml"


def plain_text(value: str) -> str:
    value = re.sub(r"<br\s*/?>", "\n", value, flags=re.IGNORECASE)
    value = re.sub(r"</?(?:strong|b|em|i)>", "", value, flags=re.IGNORECASE)
    value = re.sub(r"<[^>]+>", "", value)
    value = html.unescape(value)
    value = re.sub(r"[ \t]+\n", "\n", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    args = parser.parse_args()

    source = json.loads(args.source.read_text(encoding="utf-8"))
    questions = source["questions"]
    ids = [item["id"] for item in questions]
    if len(questions) != 50 or len(ids) != len(set(ids)):
        raise SystemExit("Expected exactly 50 uniquely identified Q&A records")

    payload = {
        "version": "2026-08-11-final-qna-v1",
        "status": "active",
        "purpose": "8분 질의응답 대비용 승인 질문·답변·심화 논리 카탈로그",
        "canonical_for_facts": False,
        "answer_rule": (
            "짧은 한국어 또는 쉬운 영어 답변을 먼저 말하고, 사용자가 더 물을 때만 "
            "상품 논리·계산·검증·후속답변을 단계적으로 확장한다. 사실 판단은 current canon을 우선한다."
        ),
        "themes": source["themes"],
        "top10": source["top10"],
        "questions": [
            {
                "id": item["id"],
                "status": "active",
                "theme": item["theme"],
                "rank": item["rank"],
                "question_ko": plain_text(item["q"]),
                "short_answer_ko": plain_text(item["ko"]),
                "short_answer_en": plain_text(item["en"]),
                "why_this_answer": plain_text(item["why"]),
                "product_logic": plain_text(item["deep"]),
                "calculation_or_validation": plain_text(item["number"]),
                "follow_up": plain_text(item["follow"]),
                "answer_boundary": plain_text(item["avoid"]),
                "presentation_source": plain_text(item["source"]),
                "priority": "top10" if item["id"] in source["top10"] else item["rank"],
            }
            for item in questions
        ],
    }
    args.target.parent.mkdir(parents=True, exist_ok=True)
    args.target.write_text(
        yaml.safe_dump(payload, allow_unicode=True, sort_keys=False, width=120),
        encoding="utf-8",
    )
    print(f"wrote {len(questions)} questions to {args.target}")


if __name__ == "__main__":
    main()

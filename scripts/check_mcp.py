from __future__ import annotations

import argparse
import asyncio
import json

from fastmcp import Client

from field_regression_check import verify_field_answers


async def check(url: str, auth: str | None) -> None:
    async with Client(url, auth=auth, timeout=30) as client:
        tools = await client.list_tools()
        names = sorted(tool.name for tool in tools)
        required = {
            "connector_guide",
            "search_knowledge",
            "explain_product_logic",
            "get_slide_context",
            "get_evidence",
            "get_implementation",
            "compare_claims",
            "prepare_topic_brief",
            "prepare_qa_practice",
            "prepare_answer_context",
            "show_answer_evidence",
            "list_open_items",
            "list_captures",
            "show_evidence_capture",
            "knowledge_status",
            "usage_telemetry",
            "record_usage_feedback",
        }
        missing = required - set(names)
        if missing:
            raise RuntimeError(f"missing tools: {sorted(missing)}")
        guide = await client.call_tool("connector_guide", {})
        if guide.is_error or "고정 답변집" not in guide.structured_content.get("purpose", ""):
            raise RuntimeError("connector guide call failed")

        practice = await client.call_tool(
            "prepare_qa_practice",
            {"top_only": True, "limit": 10},
        )
        if (
            practice.is_error
            or practice.structured_content.get("total_catalog_questions") != 50
            or len(practice.structured_content.get("questions", [])) != 10
            or practice.structured_content.get("questions", [{}])[0].get("id") != "T1-01"
        ):
            raise RuntimeError("final Q&A practice tool call failed")

        search = await client.call_tool(
            "search_knowledge",
            {"query": "평소부터 계속 점수가 낮은 운전자는 Care인가"},
        )
        if (
            search.is_error
            or search.structured_content.get("result_count", 0) < 1
            or search.structured_content.get("scope") != "current"
            or any(item.get("authority") == "historical" for item in search.structured_content.get("results", []))
        ):
            raise RuntimeError("real search tool call failed")

        product = await client.call_tool("explain_product_logic", {"topic": "세 등급 Care 할인"})
        if product.is_error or not product.structured_content.get("facts"):
            raise RuntimeError("product logic tool call failed")

        slide = await client.call_tool("get_slide_context", {"page": 2})
        slide_claim_ids = {
            item.get("id", "").split("#")[-1]
            for item in slide.structured_content.get("claims", [])
        }
        if slide.is_error or slide_claim_ids != {
            "p2-jackie-month",
            "p2-twelve-to-refund",
            "p2-contrast",
            "p2-contrast-values",
            "p2-outer-neutral",
        }:
            raise RuntimeError("slide context tool call failed")

        answer = await client.call_tool(
            "prepare_answer_context",
            {"question": "MASIL Zone 밖으로 나가면 불이익을 받는가?", "language": "ko"},
        )
        approved = answer.structured_content.get("approved_answer") or {}
        if (
            answer.is_error
            or approved.get("id") != "R07"
            or not answer.structured_content.get("current_facts")
        ):
            raise RuntimeError("answer packet tool call failed")
        if answer.structured_content.get("routing", {}).get("route") != "product_logic":
            raise RuntimeError("answer packet did not select the product-logic route")

        field_regression = await verify_field_answers(client)

        inline = await client.call_tool(
            "show_answer_evidence",
            {"question": "Cicchino looking but not seeing 71% 원문 캡처"},
        )
        if (
            inline.is_error
            or {item.get("id") for item in inline.structured_content.get("captures", [])}
            != {"capture-024"}
            or sum(content.type == "image" for content in inline.content) != 1
        ):
            raise RuntimeError("inline evidence tool call failed")

        brief = await client.call_tool(
            "prepare_topic_brief",
            {"topic": "생활권 밖 위험과 위치 무감점"},
        )
        literature_ids = {
            item.get("id", "").split("#")[-1]
            for item in brief.structured_content.get("linked_literature", [])
        }
        if (
            brief.is_error
            or not brief.structured_content.get("current_position", [{}])[0].get("id", "").endswith(
                "field-outer-zone-neutral"
            )
            or literature_ids
            != {"presentation-ehsani-tefft-2021"}
            or "likely_questions" in brief.structured_content
        ):
            raise RuntimeError("topic brief tool call failed")

        implementation = await client.call_tool("get_implementation", {"topic": "위험 이벤트 계수 8"})
        if implementation.is_error or not implementation.structured_content.get("observed_implementation"):
            raise RuntimeError("implementation tool call failed")

        comparison = await client.call_tool("compare_claims", {"query": "Care 할인 13%p"})
        if comparison.is_error or not comparison.structured_content.get("conflicts"):
            raise RuntimeError("claim comparison tool call failed")

        open_items = await client.call_tool("list_open_items", {})
        if (
            open_items.is_error
            or open_items.structured_content.get("total_count") != 1
            or open_items.structured_content.get("returned_count") != 1
            or not open_items.structured_content.get("items", [{}])[0].get("id", "").endswith(
                "field-open-privacy-operations"
            )
            or open_items.structured_content.get("truncated") is not False
        ):
            raise RuntimeError("open-items tool call failed")

        captures = await client.call_tool("list_captures", {"query": "문헌", "top_k": 50})
        if (
            captures.is_error
            or captures.structured_content.get("total_group_count") != 22
            or captures.structured_content.get("total_capture_count") != 38
            or captures.structured_content.get("truncated") is not False
        ):
            raise RuntimeError("capture inventory tool call failed")

        image = await client.call_tool(
            "show_evidence_capture",
            {"query": "European Road Safety Observatory 원문 캡처", "capture_kind": "source"},
        )
        if (
            image.is_error
            or not any(content.type == "image" for content in image.content)
            or not image.structured_content.get("display_markdown", "").startswith("![")
        ):
            raise RuntimeError("image tool call failed")

        resolved_image = await client.call_tool(
            "show_evidence_capture",
            {"query": "Cicchino looking but not seeing 71%", "capture_kind": "source"},
        )
        if (
            resolved_image.is_error
            or resolved_image.structured_content.get("id") != "capture-024"
            or not any(content.type == "image" for content in resolved_image.content)
            or not resolved_image.structured_content.get("display_url")
        ):
            raise RuntimeError("resolved evidence image call failed")

        status = await client.call_tool("knowledge_status", {})
        if status.is_error or status.structured_content.get("captures") != 38:
            raise RuntimeError("knowledge status tool call failed")

        telemetry = await client.call_tool("usage_telemetry", {"days": 7})
        if telemetry.is_error or "privacy" not in telemetry.structured_content:
            raise RuntimeError("privacy telemetry call failed")

        print(
            json.dumps(
                {
                    "url": url,
                    "tool_count": len(names),
                    "tools": names,
                    "search_results": search.structured_content["result_count"],
                    "qa_practice_questions": len(practice.structured_content["questions"]),
                    "topic_brief_literature": sorted(literature_ids),
                    "answer_facts": len(answer.structured_content["current_facts"]),
                    "field_regression": field_regression,
                    "inline_evidence": sorted(item["id"] for item in inline.structured_content["captures"]),
                    "native_image_content": "PASS",
                    "markdown_image_fallback": "PASS",
                    "slide_2_claims": len(slide_claim_ids),
                    "active_capture_groups": captures.structured_content["total_group_count"],
                    "image_returned": True,
                    "resolved_image": resolved_image.structured_content["id"],
                    "status": "PASS",
                    "telemetry": "PASS",
                },
                ensure_ascii=False,
                indent=2,
            )
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("--token")
    args = parser.parse_args()
    asyncio.run(check(args.url, args.token))


if __name__ == "__main__":
    main()

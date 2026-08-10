from __future__ import annotations

import argparse
import asyncio
import json

from fastmcp import Client


async def check(url: str, auth: str | None) -> None:
    async with Client(url, auth=auth, timeout=30) as client:
        tools = await client.list_tools()
        names = sorted(tool.name for tool in tools)
        required = {
            "search_knowledge",
            "explain_product_logic",
            "get_slide_context",
            "get_evidence",
            "get_implementation",
            "compare_claims",
            "prepare_answer_context",
            "list_open_items",
            "list_captures",
            "get_capture_image",
            "knowledge_status",
        }
        missing = required - set(names)
        if missing:
            raise RuntimeError(f"missing tools: {sorted(missing)}")

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
        if slide.is_error or len(slide.structured_content.get("claims", [])) != 7:
            raise RuntimeError("slide context tool call failed")

        answer = await client.call_tool(
            "prepare_answer_context",
            {"question": "생활권 밖으로 나가면 자동으로 감점하나요?", "language": "ko"},
        )
        if answer.is_error or not answer.structured_content.get("current_facts"):
            raise RuntimeError("answer packet tool call failed")

        implementation = await client.call_tool("get_implementation", {"topic": "위험 이벤트 계수 8"})
        if implementation.is_error or not implementation.structured_content.get("observed_implementation"):
            raise RuntimeError("implementation tool call failed")

        comparison = await client.call_tool("compare_claims", {"query": "Care 할인 13%p"})
        if comparison.is_error or not comparison.structured_content.get("conflicts"):
            raise RuntimeError("claim comparison tool call failed")

        open_items = await client.call_tool("list_open_items", {"query": "개인정보 공정성"})
        if open_items.is_error or not open_items.structured_content.get("items"):
            raise RuntimeError("open-items tool call failed")

        captures = await client.call_tool("list_captures", {"query": "문헌", "top_k": 50})
        if (
            captures.is_error
            or captures.structured_content.get("total_group_count") != 22
            or captures.structured_content.get("total_capture_count") != 38
            or captures.structured_content.get("truncated") is not False
        ):
            raise RuntimeError("capture inventory tool call failed")

        image = await client.call_tool("get_capture_image", {"capture_id": "capture-015"})
        if image.is_error or not any(content.type == "image" for content in image.content):
            raise RuntimeError("image tool call failed")

        status = await client.call_tool("knowledge_status", {})
        if status.is_error or status.structured_content.get("captures") != 44:
            raise RuntimeError("knowledge status tool call failed")

        print(
            json.dumps(
                {
                    "url": url,
                    "tool_count": len(names),
                    "tools": names,
                    "search_results": search.structured_content["result_count"],
                    "answer_facts": len(answer.structured_content["current_facts"]),
                    "slide_2_claims": len(slide.structured_content["claims"]),
                    "active_capture_groups": captures.structured_content["total_group_count"],
                    "image_returned": True,
                    "status": "PASS",
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

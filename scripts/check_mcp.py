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
            {"query": "평소부터 계속 점수가 낮은 운전자는 Care인가", "scope": "current"},
        )
        if search.is_error or search.structured_content.get("result_count", 0) < 1:
            raise RuntimeError("real search tool call failed")

        answer = await client.call_tool(
            "prepare_answer_context",
            {"question": "생활권 밖으로 나가면 자동으로 감점하나요?", "language": "ko"},
        )
        if answer.is_error or not answer.structured_content.get("current_facts"):
            raise RuntimeError("answer packet tool call failed")

        image = await client.call_tool("get_capture_image", {"capture_id": "capture-015"})
        if image.is_error or not any(content.type == "image" for content in image.content):
            raise RuntimeError("image tool call failed")

        print(
            json.dumps(
                {
                    "url": url,
                    "tool_count": len(names),
                    "tools": names,
                    "search_results": search.structured_content["result_count"],
                    "answer_facts": len(answer.structured_content["current_facts"]),
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


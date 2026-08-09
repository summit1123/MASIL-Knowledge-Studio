from __future__ import annotations

import pytest
from fastmcp import Client

from masil_mcp.server import create_server


@pytest.mark.asyncio
async def test_in_memory_server_lists_and_calls_tools() -> None:
    server = create_server(auth_mode="none")
    async with Client(server) as client:
        tools = await client.list_tools()
        names = {tool.name for tool in tools}
        assert {
            "search_knowledge",
            "prepare_answer_context",
            "get_evidence",
            "get_capture_image",
            "get_implementation",
        }.issubset(names)
        result = await client.call_tool("search_knowledge", {"query": "Care 다음 달", "scope": "current"})
        assert not result.is_error
        assert result.structured_content["result_count"] > 0


@pytest.mark.asyncio
async def test_capture_tool_returns_image_content() -> None:
    server = create_server(auth_mode="none")
    async with Client(server) as client:
        result = await client.call_tool("get_capture_image", {"capture_id": "capture-001"})
        assert not result.is_error
        assert any(content.type == "image" for content in result.content)


@pytest.mark.asyncio
async def test_answer_packet_respects_character_budget() -> None:
    server = create_server(auth_mode="none")
    async with Client(server) as client:
        result = await client.call_tool(
            "prepare_answer_context",
            {
                "question": "3등급 판정과 연간 할인률은 어떻게 연결되나요?",
                "language": "ko",
                "max_chars": 7000,
            },
        )
        packet = result.structured_content
        assert packet["packet_chars"] <= 7000
        assert len(packet["current_facts"]) >= 2

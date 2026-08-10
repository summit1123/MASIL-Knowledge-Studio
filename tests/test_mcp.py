from __future__ import annotations

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError
from starlette.testclient import TestClient

from masil_mcp.server import create_server


def test_server_publishes_brand_icon() -> None:
    server = create_server(auth_mode="none")
    assert server.icons
    assert server.icons[0].src.endswith("/favicon.png")
    assert server.icons[0].mimeType == "image/png"

    with TestClient(server.http_app(path="/mcp")) as client:
        icon = client.get("/favicon.png")
        assert icon.status_code == 200
        assert icon.headers["content-type"].startswith("image/png")
        assert icon.content.startswith(b"\x89PNG")

        landing = client.get("/")
        assert landing.status_code == 200
        assert 'href="/favicon.png"' in landing.text


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
        search_tool = next(tool for tool in tools if tool.name == "search_knowledge")
        assert search_tool.inputSchema["properties"]["scope"]["default"] == "current"
        result = await client.call_tool("search_knowledge", {"query": "Care 다음 달", "scope": "current"})
        assert not result.is_error
        assert result.structured_content["result_count"] > 0


@pytest.mark.asyncio
async def test_slide_context_keeps_parent_page_mapping() -> None:
    server = create_server(auth_mode="none")
    async with Client(server) as client:
        page_two = await client.call_tool("get_slide_context", {"page": 2})
        claim_ids = {claim["id"] for claim in page_two.structured_content["claims"]}

        assert len(claim_ids) == 7
        assert "knowledge/claims/deck_claims.yaml#p2-pipeline" in claim_ids
        assert "knowledge/claims/deck_claims.yaml#p2-mobility-rights" in claim_ids


@pytest.mark.asyncio
async def test_capture_tool_returns_image_content() -> None:
    server = create_server(auth_mode="none")
    async with Client(server) as client:
        result = await client.call_tool("get_capture_image", {"capture_id": "capture-001"})
        assert not result.is_error
        assert any(content.type == "image" for content in result.content)


@pytest.mark.asyncio
async def test_non_stage_capture_requires_explicit_supporting_access() -> None:
    server = create_server(auth_mode="none")
    async with Client(server) as client:
        with pytest.raises(ToolError):
            await client.call_tool("get_capture_image", {"capture_id": "capture-042"})

        allowed = await client.call_tool(
            "get_capture_image",
            {"capture_id": "capture-042", "allow_supporting": True},
        )
        assert not allowed.is_error
        assert any(content.type == "image" for content in allowed.content)


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

from __future__ import annotations

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError
from starlette.testclient import TestClient

from masil_mcp.server import create_server
from masil_mcp.service import KnowledgeService


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
            "connector_guide",
            "search_knowledge",
            "prepare_topic_brief",
            "prepare_answer_context",
            "show_answer_evidence",
            "get_evidence",
            "show_evidence_capture",
            "get_capture_image",
            "get_implementation",
        }.issubset(names)
        assert "prepare_qa_strategy" not in names
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
        assert result.structured_content["display_url"].startswith(
            "https://masil-mcp.summit1123.co.kr/evidence/capture-001/"
        )
        assert result.structured_content["display_markdown"].startswith("![")
        assert result.structured_content["client_rendering"] == "mcp_app_inline_with_markdown_fallback"


@pytest.mark.asyncio
async def test_evidence_tools_publish_an_inline_mcp_app_resource() -> None:
    server = create_server(auth_mode="none")
    async with Client(server) as client:
        tools = await client.list_tools()
        visual = next(tool for tool in tools if tool.name == "show_answer_evidence")
        assert visual.meta["ui"]["resourceUri"] == "ui://masil/evidence-view.html"
        assert visual.meta["ui/resourceUri"] == "ui://masil/evidence-view.html"

        resources = await client.list_resources()
        resource = next(item for item in resources if str(item.uri) == "ui://masil/evidence-view.html")
        assert resource.mimeType == "text/html;profile=mcp-app"
        rendered = await client.read_resource("ui://masil/evidence-view.html")
        assert "MASIL Evidence Viewer" in rendered[0].text

        result = await client.call_tool(
            "show_answer_evidence",
            {"question": "생활권 밖이 위험하다면서 왜 감점은 안 해?"},
        )
        assert not result.is_error
        assert [capture["id"] for capture in result.structured_content["captures"]] == [
            "capture-006",
            "capture-037",
        ]
        assert [content.type for content in result.content].count("image") == 2


def test_capture_fallback_route_uses_opaque_verified_token() -> None:
    service = KnowledgeService()
    metadata, path = service.capture("capture-001")
    token = f"{metadata['sha256'][:16]}{path.suffix.lower()}"
    server = create_server(auth_mode="none", service=service)

    with TestClient(server.http_app(path="/mcp")) as client:
        image = client.get(f"/evidence/capture-001/{token}")
        assert image.status_code == 200
        assert image.headers["content-type"].startswith("image/")
        assert image.headers["content-disposition"].startswith("inline;")

        invalid = client.get("/evidence/capture-001/not-the-token.png")
        assert invalid.status_code == 404


@pytest.mark.asyncio
async def test_topic_brief_returns_materials_without_invented_questions() -> None:
    server = create_server(auth_mode="none")
    async with Client(server) as client:
        result = await client.call_tool(
            "prepare_topic_brief",
            {"topic": "생활권 밖 위험과 위치 무감점"},
        )
        brief = result.structured_content

        assert brief["current_position"][0]["id"].endswith(
            "out-of-zone-risk-and-no-location-penalty"
        )
        assert {item["id"].split("#")[-1] for item in brief["linked_literature"]} == {
            "presentation-ehsani-tefft-2021",
            "presentation-hirsch-activity-space-2014",
        }
        assert "likely_questions" not in brief
        assert "generated_questions" not in brief
        assert any("예상 질문" in rule for rule in brief["usage_rules"])
        assert brief["validation_boundaries"] == []

        zone = await client.call_tool(
            "prepare_topic_brief",
            {"topic": "rolling 2개월 MASIL Zone 갱신과 계절성"},
        )
        assert any(
            item["id"].endswith("model-zone-seasonality")
            for item in zone.structured_content["validation_boundaries"]
        )


@pytest.mark.asyncio
async def test_show_evidence_capture_resolves_each_side_of_out_of_zone_position() -> None:
    server = create_server(auth_mode="none")
    async with Client(server) as client:
        risk = await client.call_tool(
            "show_evidence_capture",
            {"query": "생활권 밖 위험 근거 캡처"},
        )
        assert not risk.is_error
        assert risk.structured_content["id"] == "capture-006"
        assert risk.structured_content["literature"][0]["id"].endswith(
            "presentation-ehsani-tefft-2021"
        )
        assert any(content.type == "image" for content in risk.content)

        no_penalty = await client.call_tool(
            "show_evidence_capture",
            {"query": "활동공간 확대 자체를 위험으로 해석하지 않는 무감점 근거 캡처"},
        )
        assert not no_penalty.is_error
        assert no_penalty.structured_content["id"] == "capture-037"
        assert no_penalty.structured_content["literature"][0]["id"].endswith(
            "presentation-hirsch-activity-space-2014"
        )


@pytest.mark.asyncio
async def test_open_items_reports_exact_total_for_each_scope() -> None:
    server = create_server(auth_mode="none")
    async with Client(server) as client:
        unresolved = await client.call_tool("list_open_items", {})
        assert unresolved.structured_content["total_count"] == 16
        assert unresolved.structured_content["returned_count"] == 16
        assert unresolved.structured_content["status_counts"] == {"unresolved": 16}
        assert unresolved.structured_content["truncated"] is False

        all_open = await client.call_tool(
            "list_open_items",
            {"status_filter": "all", "top_k": 30},
        )
        assert all_open.structured_content["total_count"] == 29
        assert all_open.structured_content["returned_count"] == 29
        assert all_open.structured_content["status_counts"] == {
            "candidate_parameter": 5,
            "pilot_hypothesis": 8,
            "unresolved": 16,
        }
        assert all_open.structured_content["truncated"] is False


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

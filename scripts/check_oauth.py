from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import json
import os
import secrets
from urllib.parse import parse_qs, urlparse

import httpx
from dotenv import load_dotenv
from fastmcp import Client

from field_regression_check import verify_field_answers


def pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(48)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return verifier, challenge


async def check(base_url: str) -> None:
    client_id = os.environ["MASIL_OAUTH_CLIENT_ID"]
    client_secret = os.environ["MASIL_OAUTH_CLIENT_SECRET"]
    redirect_uri = os.environ["MASIL_OAUTH_REDIRECT_URI"]
    verifier, challenge = pkce_pair()
    state = secrets.token_urlsafe(20)

    async with httpx.AsyncClient(follow_redirects=False, timeout=20) as http:
        authorize = await http.get(
            f"{base_url}/authorize",
            params={
                "response_type": "code",
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "scope": "masil:read",
                "state": state,
                "code_challenge": challenge,
                "code_challenge_method": "S256",
            },
        )
        if authorize.status_code not in {302, 303, 307}:
            raise RuntimeError(f"authorization failed: {authorize.status_code} {authorize.text[:300]}")
        query = parse_qs(urlparse(authorize.headers["location"]).query)
        if query.get("state", [None])[0] != state or "code" not in query:
            raise RuntimeError("authorization redirect did not contain the expected state and code")
        code = query["code"][0]

        token_response = await http.post(
            f"{base_url}/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": client_id,
                "client_secret": client_secret,
                "code_verifier": verifier,
            },
        )
        if token_response.status_code != 200:
            raise RuntimeError(f"token exchange failed: {token_response.status_code} {token_response.text[:300]}")
        token = token_response.json()["access_token"]

    async with Client(f"{base_url}/mcp", auth=token, timeout=30) as client:
        tools = await client.list_tools()
        names = {tool.name for tool in tools}
        required = {
            "connector_guide",
            "prepare_topic_brief",
            "prepare_qa_practice",
            "show_answer_evidence",
            "show_evidence_capture",
            "list_open_items",
            "usage_telemetry",
            "record_usage_feedback",
        }
        if not required.issubset(names):
            raise RuntimeError(f"authenticated MCP missing tools: {sorted(required - names)}")
        guide = await client.call_tool("connector_guide", {})
        if guide.is_error or "고정 답변집" not in guide.structured_content.get("purpose", ""):
            raise RuntimeError("authenticated connector-guide call failed")

        practice = await client.call_tool(
            "prepare_qa_practice",
            {"top_only": True, "limit": 10},
        )
        if (
            practice.is_error
            or practice.structured_content.get("total_catalog_questions") != 50
            or len(practice.structured_content.get("questions", [])) != 10
        ):
            raise RuntimeError("authenticated Q&A practice call failed")

        search = await client.call_tool(
            "search_knowledge",
            {"query": "Care가 나온 다음 달은 어떻게 되나요"},
        )
        if (
            search.is_error
            or search.structured_content.get("result_count", 0) < 1
            or search.structured_content.get("scope") != "current"
            or any(item.get("authority") == "historical" for item in search.structured_content.get("results", []))
        ):
            raise RuntimeError("authenticated MCP tool call failed")

        product = await client.call_tool("explain_product_logic", {"topic": "세 등급 Care 할인"})
        if product.is_error or not product.structured_content.get("facts"):
            raise RuntimeError("authenticated product logic call failed")

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
            raise RuntimeError("authenticated slide-context call failed")

        answer = await client.call_tool(
            "prepare_answer_context",
            {"question": "MASIL Zone 밖으로 나가면 불이익을 받는가?", "language": "ko"},
        )
        approved = answer.structured_content.get("approved_answer") or {}
        if (
            answer.is_error
            or approved.get("id") != "R07"
            or not answer.structured_content.get("current_facts")
            or answer.structured_content.get("packet_chars", 999999) > 5000
            or answer.structured_content.get("routing", {}).get("route") != "product_logic"
        ):
            raise RuntimeError("authenticated answer-context call failed")

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
            raise RuntimeError("authenticated inline-evidence call failed")

        brief = await client.call_tool(
            "prepare_topic_brief",
            {"topic": "생활권 밖 위험과 위치 무감점"},
        )
        if (
            brief.is_error
            or "likely_questions" in brief.structured_content
            or len(brief.structured_content.get("linked_literature", [])) != 1
        ):
            raise RuntimeError("authenticated topic-brief call failed")

        implementation = await client.call_tool("get_implementation", {"topic": "위험 이벤트 계수 8"})
        if implementation.is_error or not implementation.structured_content.get("observed_implementation"):
            raise RuntimeError("authenticated implementation call failed")

        comparison = await client.call_tool("compare_claims", {"query": "Care 할인 13%p"})
        if comparison.is_error or not comparison.structured_content.get("conflicts"):
            raise RuntimeError("authenticated claim-comparison call failed")

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
            raise RuntimeError("authenticated open-items call failed")

        captures = await client.call_tool("list_captures", {"query": "문헌", "top_k": 50})
        if (
            captures.is_error
            or captures.structured_content.get("total_group_count") != 22
            or captures.structured_content.get("total_capture_count") != 38
            or captures.structured_content.get("truncated") is not False
        ):
            raise RuntimeError("authenticated capture-inventory call failed")

        evidence = await client.call_tool(
            "get_evidence",
            {"query": "Cicchino looking but not seeing 71%", "top_k": 4},
        )
        recommended = evidence.structured_content.get("recommended_captures", [])
        if (
            evidence.is_error
            or not evidence.structured_content.get("literature", [{}])[0].get("id", "").endswith(
                "presentation-cicchino-mccartt-2015"
            )
            or [capture.get("id") for capture in recommended] != ["capture-024"]
        ):
            raise RuntimeError("authenticated evidence-to-capture mapping failed")

        image = await client.call_tool(
            "show_evidence_capture",
            {"query": "Cicchino looking but not seeing 원문 캡처", "capture_kind": "source"},
        )
        if (
            image.is_error
            or not any(content.type == "image" for content in image.content)
            or not image.structured_content.get("display_url")
        ):
            raise RuntimeError("authenticated image call failed")

        resolved_image = await client.call_tool(
            "show_evidence_capture",
            {"query": "Cicchino looking but not seeing 71%", "capture_kind": "source"},
        )
        if (
            resolved_image.is_error
            or resolved_image.structured_content.get("id") != "capture-024"
            or not any(content.type == "image" for content in resolved_image.content)
        ):
            raise RuntimeError("authenticated resolved-image call failed")

        status = await client.call_tool("knowledge_status", {})
        if status.is_error or status.structured_content.get("captures") != 38:
            raise RuntimeError("authenticated knowledge-status call failed")

        telemetry = await client.call_tool("usage_telemetry", {"days": 7})
        if telemetry.is_error or "privacy" not in telemetry.structured_content:
            raise RuntimeError("authenticated privacy-telemetry call failed")

    async with httpx.AsyncClient(follow_redirects=True, timeout=20) as http:
        fallback_image = await http.get(resolved_image.structured_content["display_url"])
        if fallback_image.status_code != 200 or not fallback_image.headers.get("content-type", "").startswith(
            "image/"
        ):
            raise RuntimeError("public fallback image URL failed")

    print(
        json.dumps(
            {
                "authorization_code_flow": "PASS",
                "confidential_client_secret": "PASS",
                "pkce_s256": "PASS",
                "mcp_tool_count": len(tools),
                "authenticated_tool_call": "PASS",
                "connector_guide_call": "PASS",
                "qa_practice_call": "PASS",
                "topic_brief_call": "PASS",
                "product_logic_call": "PASS",
                "slide_context_call": "PASS",
                "answer_context_call": "PASS",
                "field_regression_questions": field_regression["questions"],
                "field_regression_bilingual_calls": field_regression["bilingual_answer_calls"],
                "inline_evidence_call": "PASS",
                "native_image_content": "PASS",
                "markdown_image_fallback": "PASS",
                "implementation_call": "PASS",
                "claim_comparison_call": "PASS",
                "open_items_call": "PASS",
                "capture_inventory_call": "PASS",
                "evidence_capture_mapping": "PASS",
                "historical_material_excluded": "PASS",
                "capture_image_call": "PASS",
                "resolved_capture_call": "PASS",
                "public_fallback_image_url": "PASS",
                "knowledge_status_call": "PASS",
                "privacy_telemetry_call": "PASS",
            },
            indent=2,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("base_url", nargs="?", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    load_dotenv()
    asyncio.run(check(args.base_url.rstrip("/")))


if __name__ == "__main__":
    main()

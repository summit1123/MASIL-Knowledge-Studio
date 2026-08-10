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
        if slide.is_error or len(slide.structured_content.get("claims", [])) != 7:
            raise RuntimeError("authenticated slide-context call failed")

        answer = await client.call_tool(
            "prepare_answer_context",
            {"question": "생활권 밖 주행은 왜 보는 건가요?", "language": "ko"},
        )
        if (
            answer.is_error
            or not answer.structured_content.get("current_facts")
            or answer.structured_content.get("packet_chars", 999999) > 7000
        ):
            raise RuntimeError("authenticated answer-context call failed")

        implementation = await client.call_tool("get_implementation", {"topic": "위험 이벤트 계수 8"})
        if implementation.is_error or not implementation.structured_content.get("observed_implementation"):
            raise RuntimeError("authenticated implementation call failed")

        comparison = await client.call_tool("compare_claims", {"query": "Care 할인 13%p"})
        if comparison.is_error or not comparison.structured_content.get("conflicts"):
            raise RuntimeError("authenticated claim-comparison call failed")

        open_items = await client.call_tool("list_open_items", {"query": "개인정보 공정성"})
        if open_items.is_error or not open_items.structured_content.get("items"):
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

        qa_evidence = await client.call_tool(
            "get_evidence",
            {"query": "Candrive 5.26배", "top_k": 4, "usage_scope": "qa_only"},
        )
        if (
            qa_evidence.is_error
            or not qa_evidence.structured_content.get("literature", [{}])[0].get("id", "").endswith(
                "presentation-candrive-marshall-2023"
            )
            or [capture.get("id") for capture in qa_evidence.structured_content.get("recommended_captures", [])]
            != ["capture-042"]
        ):
            raise RuntimeError("authenticated Q&A-only evidence mapping failed")

        reference = await client.call_tool(
            "get_evidence",
            {"query": "Harms route familiarity 94편", "top_k": 4, "usage_scope": "listed_only"},
        )
        if (
            reference.is_error
            or not reference.structured_content.get("reference_only", [{}])[0].get("id", "").endswith(
                "presentation-harms-2021"
            )
            or [capture.get("id") for capture in reference.structured_content.get("recommended_captures", [])]
            != ["capture-040"]
        ):
            raise RuntimeError("authenticated reference-only evidence mapping failed")

        image = await client.call_tool("get_capture_image", {"capture_id": "capture-024"})
        if image.is_error or not any(content.type == "image" for content in image.content):
            raise RuntimeError("authenticated image call failed")

        status = await client.call_tool("knowledge_status", {})
        if status.is_error or status.structured_content.get("captures") != 44:
            raise RuntimeError("authenticated knowledge-status call failed")

    print(
        json.dumps(
            {
                "authorization_code_flow": "PASS",
                "confidential_client_secret": "PASS",
                "pkce_s256": "PASS",
                "mcp_tool_count": len(tools),
                "authenticated_tool_call": "PASS",
                "product_logic_call": "PASS",
                "slide_context_call": "PASS",
                "answer_context_call": "PASS",
                "implementation_call": "PASS",
                "claim_comparison_call": "PASS",
                "open_items_call": "PASS",
                "capture_inventory_call": "PASS",
                "evidence_capture_mapping": "PASS",
                "qa_only_mapping": "PASS",
                "reference_only_mapping": "PASS",
                "capture_image_call": "PASS",
                "knowledge_status_call": "PASS",
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

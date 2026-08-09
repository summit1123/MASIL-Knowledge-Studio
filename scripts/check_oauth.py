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
            {"query": "Care가 나온 다음 달은 어떻게 되나요", "scope": "current"},
        )
        if search.is_error or search.structured_content.get("result_count", 0) < 1:
            raise RuntimeError("authenticated MCP tool call failed")

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

        image = await client.call_tool("get_capture_image", {"capture_id": "capture-015"})
        if image.is_error or not any(content.type == "image" for content in image.content):
            raise RuntimeError("authenticated image call failed")

    print(
        json.dumps(
            {
                "authorization_code_flow": "PASS",
                "confidential_client_secret": "PASS",
                "pkce_s256": "PASS",
                "mcp_tool_count": len(tools),
                "authenticated_tool_call": "PASS",
                "answer_context_call": "PASS",
                "capture_image_call": "PASS",
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

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

import pytest
from fastmcp import Client
from mcp.server.auth.provider import AccessToken, AuthorizationCode, RefreshToken
from mcp.shared.auth import OAuthClientInformationFull
from pydantic import AnyUrl

from masil_mcp.persistent_oauth import PersistentOAuthProvider
from masil_mcp.routing import route_question
from masil_mcp.server import create_server
from masil_mcp.telemetry import TelemetryStore


@pytest.mark.parametrize(
    ("question", "expected_route"),
    [
        ("Appendix B 장표에서 생활권을 어떻게 설명해?", "deck_context"),
        ("Ehsani 문헌 원문 근거와 캡처를 보여줘", "literature_evidence"),
        ("Care와 할인 관계가 예전과 왜 바뀌었어?", "claim_conflict_history"),
        ("아직 검증되지 않은 파일럿 항목은 뭐야?", "validation_open_items"),
        ("보험사와 가족에게 어떤 가치가 있어?", "stakeholder_value"),
        ("Favorable Standard Care 판정은 어떻게 해?", "product_logic"),
        ("8분 Q&A 예상질문 10개를 뽑아줘", "qa_practice"),
        ("MASIL을 30초로 소개해줘", "presentation_overview"),
        ("이 대본을 검토해줘\n" + "MASIL Zone은 개인 생활권입니다. " * 12, "draft_review"),
    ],
)
def test_lightweight_answer_routing(question: str, expected_route: str) -> None:
    assert route_question(question).route == expected_route


def test_oauth_tokens_survive_provider_restart(tmp_path: Path) -> None:
    database = tmp_path / "oauth.sqlite3"
    client = OAuthClientInformationFull(
        client_id="test-client",
        client_secret="test-secret-with-more-than-24-characters",
        redirect_uris=[AnyUrl("https://claude.ai/api/mcp/auth_callback")],
        token_endpoint_auth_method="client_secret_post",
        grant_types=["authorization_code", "refresh_token"],
        response_types=["code"],
        scope="masil:read",
    )

    async def exercise() -> None:
        first = PersistentOAuthProvider(storage_path=database)
        first.clients["test-client"] = client
        code = AuthorizationCode(
            code="one-time-code",
            client_id="test-client",
            redirect_uri=AnyUrl("https://claude.ai/api/mcp/auth_callback"),
            redirect_uri_provided_explicitly=True,
            scopes=["masil:read"],
            expires_at=time.time() + 300,
            code_challenge="pkce-challenge",
        )
        first.auth_codes[code.code] = code
        issued = await first.exchange_authorization_code(client, code)

        restarted = PersistentOAuthProvider(storage_path=database)
        restarted.clients["test-client"] = client
        loaded_access = await restarted.load_access_token(issued.access_token)
        loaded_refresh = await restarted.load_refresh_token(client, issued.refresh_token)
        assert isinstance(loaded_access, AccessToken)
        assert isinstance(loaded_refresh, RefreshToken)

        rotated = await restarted.exchange_refresh_token(
            client,
            loaded_refresh,
            ["masil:read"],
        )
        after_rotation = PersistentOAuthProvider(storage_path=database)
        after_rotation.clients["test-client"] = client
        assert await after_rotation.load_access_token(issued.access_token) is None
        assert await after_rotation.load_access_token(rotated.access_token) is not None
        assert await after_rotation.load_refresh_token(client, rotated.refresh_token) is not None

    import asyncio

    asyncio.run(exercise())
    assert database.stat().st_mode & 0o777 == 0o600


@pytest.mark.asyncio
async def test_final_qa_practice_tool_returns_core20() -> None:
    server = create_server(auth_mode="none")
    async with Client(server) as client:
        result = await client.call_tool(
            "prepare_qa_practice",
            {"top_only": True, "limit": 100},
        )
    payload = result.structured_content
    assert payload["total_catalog_questions"] == 100
    assert [item["id"] for item in payload["questions"]] == [
        f"C{number:02d}" for number in range(1, 21)
    ]
    assert all(item["question_ko"] for item in payload["questions"])
    assert all(item["answer_ko_short"] and item["answer_en_short"] for item in payload["questions"])
    assert all(item["logic_ko"] for item in payload["questions"])


@pytest.mark.asyncio
async def test_telemetry_records_tools_and_routes_without_input_text(tmp_path: Path) -> None:
    database = tmp_path / "telemetry.sqlite3"
    telemetry = TelemetryStore(database)
    server = create_server(auth_mode="none", telemetry_store=telemetry)

    async with Client(server) as client:
        await client.call_tool(
            "prepare_answer_context",
            {"question": "Ehsani 문헌 원문 근거와 캡처를 보여줘"},
        )
        await client.call_tool(
            "record_usage_feedback",
            {"rating": "helpful", "reason": "good_answer"},
        )
        result = await client.call_tool("usage_telemetry", {"days": 7})

    summary = result.structured_content
    assert summary["calls"] == 2
    assert summary["routes"] == [{"route": "literature_evidence", "calls": 1}]
    assert summary["feedback"] == [
        {"rating": "helpful", "reason": "good_answer", "count": 1}
    ]
    assert "No prompts" in summary["privacy"]

    with sqlite3.connect(database) as connection:
        columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(tool_events)").fetchall()
        }
        serialized = database.read_bytes()
    assert not {"prompt", "question", "query", "arguments", "answer"} & columns
    assert "Ehsani".encode() not in serialized

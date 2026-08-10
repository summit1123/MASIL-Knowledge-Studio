from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.utilities.types import Image
from mcp.types import Icon
from starlette.requests import Request
from starlette.responses import FileResponse, HTMLResponse, JSONResponse

from .auth import build_auth
from .service import KnowledgeService


load_dotenv()

PUBLIC_URL = os.getenv("MASIL_PUBLIC_URL", "https://masil-mcp.summit1123.co.kr").rstrip("/")
ICON_PATH = Path(__file__).resolve().parent / "static" / "masil-icon.png"

INSTRUCTIONS = """
MASIL 발표 준비용 근거 서버입니다. 최신 상품 계약과 덱 사실을 먼저 사용하고,
문헌은 allowed_claim과 caveat 범위에서만 사용하세요. 과거 Master Q&A와 변경 이력은
질문 해석·충돌 탐지 재료이며 현재 규칙을 덮어쓰지 않습니다. 최종 답은 짧고 쉬운
문장으로 구성하고 candidate, unresolved, historical 상태를 숨기지 마세요. 사용자가
문헌의 원문·캡처·덱 사용 위치를 요청하면 get_evidence로 정확한 캡처 ID와 deck_location을 찾고,
get_capture_image를 이어 호출해 이미지를 답변 안에 직접 표시하세요. reference_only는
목록·한계 설명용이고 banned 문헌은 현재 근거로 사용하지 마세요.
""".strip()


def create_server(*, auth_mode: str | None = None, service: KnowledgeService | None = None) -> FastMCP:
    knowledge = service or KnowledgeService()
    mcp = FastMCP(
        "MASIL Knowledge Studio",
        instructions=INSTRUCTIONS,
        version="0.1.0",
        website_url=PUBLIC_URL,
        icons=[
            Icon(
                src=f"{PUBLIC_URL}/favicon.png",
                mimeType="image/png",
                sizes=["512x512"],
            )
        ],
        auth=build_auth(auth_mode),
        mask_error_details=True,
    )

    @mcp.custom_route("/", methods=["GET"], include_in_schema=False)
    async def landing(_: Request) -> HTMLResponse:
        return HTMLResponse(
            """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>MASIL Knowledge Studio</title>
  <link rel="icon" type="image/png" sizes="512x512" href="/favicon.png">
</head>
<body><h1>MASIL Knowledge Studio</h1><p>Remote MCP knowledge server</p></body>
</html>"""
        )

    @mcp.custom_route("/favicon.png", methods=["GET"], include_in_schema=False)
    @mcp.custom_route("/favicon.ico", methods=["GET"], include_in_schema=False)
    async def favicon(_: Request) -> FileResponse:
        return FileResponse(
            ICON_PATH,
            media_type="image/png",
            headers={"Cache-Control": "public, max-age=86400"},
        )

    @mcp.custom_route("/healthz", methods=["GET"], include_in_schema=True)
    async def healthz(_: Request) -> JSONResponse:
        return JSONResponse({"status": "ok", "service": "masil-mcp", **knowledge.stats()})

    @mcp.tool(tags={"search"})
    def search_knowledge(
        query: str,
        top_k: int = 8,
        scope: Literal["all", "current", "canonical", "slides", "evidence", "supporting", "history"] = "all",
        detail: Literal["compact", "full"] = "compact",
    ) -> dict:
        """Search MASIL with Korean/English BM25 plus Korean character n-grams.

        Use scope=current for answer facts. Use all or history only when the
        question asks why wording changed or when you need conflict clues.
        """
        return knowledge.search(query, top_k=top_k, scope=scope, detail=detail)

    @mcp.tool(tags={"product"})
    def explain_product_logic(topic: str, detail: Literal["compact", "full"] = "compact") -> dict:
        """Return the current MASIL product contract for a topic.

        It distinguishes product rules, current sandbox parameters, planned
        implementation changes, and validated results.
        """
        return knowledge.explain_product_logic(topic, detail=detail)

    @mcp.tool(tags={"deck"})
    def get_slide_context(page: int, detail: Literal["compact", "full"] = "compact") -> dict:
        """Return claims, caveats, and correction status for a final-deck page (1-9)."""
        if page < 1 or page > 9:
            raise ValueError("page must be between 1 and 9")
        return knowledge.get_slide_context(page, detail=detail)

    @mcp.tool(tags={"evidence"})
    def get_evidence(query: str, top_k: int = 6, include_captures: bool = True) -> dict:
        """Find Summary/Appendix, Q&A-only, and explicit reference-only literature mappings.

        If the user asks to see the source, quotation, screenshot, or deck use,
        call get_capture_image with a recommended_captures id immediately after
        this tool. Do not substitute a fuzzy or unrelated capture.
        """
        return knowledge.get_evidence(query, top_k=top_k, include_captures=include_captures)

    @mcp.tool(tags={"implementation"})
    def get_implementation(topic: str = "점수 Care 할인 생활권") -> dict:
        """Compare the audited current demo implementation with the product contract."""
        return knowledge.get_implementation(topic)

    @mcp.tool(tags={"conflict"})
    def compare_claims(query: str) -> dict:
        """Show the current position, known conflicts, and superseded material for a claim."""
        return knowledge.compare_claims(query)

    @mcp.tool(tags={"answer"})
    def prepare_answer_context(
        question: str,
        language: Literal["ko", "en"] = "ko",
        max_chars: int = 7000,
    ) -> dict:
        """Build a compact evidence packet so Claude can compose a short Q&A response.

        This intentionally returns answer ingredients instead of a frozen answer.
        """
        if max_chars < 2500 or max_chars > 12000:
            raise ValueError("max_chars must be between 2500 and 12000")
        return knowledge.prepare_answer_context(question, language=language, max_chars=max_chars)

    @mcp.tool(tags={"gaps"})
    def list_open_items(query: str = "미확정 unresolved 검증 필요", top_k: int = 12) -> dict:
        """List unresolved, pilot, candidate, and planned-not-implemented items."""
        return knowledge.list_open_items(query=query, top_k=top_k)

    @mcp.tool(tags={"evidence", "image"})
    def list_captures(query: str = "문헌", top_k: int = 20) -> dict:
        """List literature capture IDs with deck location and usage status. Pass an ID to get_capture_image."""
        return knowledge.list_captures(query=query, top_k=top_k)

    @mcp.tool(tags={"evidence", "image"})
    def get_capture_image(capture_id: str) -> Image:
        """Display one exact literature/deck capture inline in Claude's answer."""
        _, path = knowledge.capture(capture_id)
        return Image(path=path)

    @mcp.tool(tags={"status"})
    def knowledge_status() -> dict:
        """Return corpus counts and fingerprint for deployment diagnostics."""
        return knowledge.stats()

    return mcp


mcp = create_server()


def main() -> None:
    host = os.getenv("MASIL_HOST", "127.0.0.1")
    port = int(os.getenv("MASIL_PORT", "8000"))
    path = os.getenv("MASIL_MCP_PATH", "/mcp")
    mcp.run(
        transport="http",
        host=host,
        port=port,
        path=path,
        stateless_http=False,
        json_response=False,
    )


if __name__ == "__main__":
    main()

# MASIL MCP verification report

검증 시각: 2026-08-10 11:27 KST

## Result

| Layer | Result | Evidence |
|---|---|---|
| Knowledge model | PASS | YAML 15개 파싱, 중복 ID 0, 덱 claim 64개 51/6/7 일치, P0 15개, 누락 파일 0 |
| Evidence assets | PASS | 로컬 캡처 44개, active 22그룹·38이미지, Q&A 2그룹, References 3그룹, 공개 비밀값 노출 0 |
| Unit and MCP tests | PASS | pytest 46개 통과, 로컬 HTTP 11개 도구 호출 통과 |
| Local service | PASS | LaunchAgent 재시작, `/healthz` 200, 공개 서버와 fingerprint 일치 |
| Public tunnel | PASS | 전용 `masil-mcp` 터널, 공개 `/healthz` 200 |
| OAuth | PASS | authorization code, confidential client secret, PKCE S256 |
| Public MCP | PASS | 도구 11개 전건 호출, 기본 current 격리, 2페이지 7개 claim, 문헌 scope와 캡처 이미지 반환 |
| Claude Web connector | PASS | `MASIL Knowledge Studio` 등록·OAuth 연결 및 사용자 화면에서 도구·이미지 응답 확인 |

## Public health snapshot

```json
{
  "status": "ok",
  "service": "masil-mcp",
  "documents": 1312,
  "captures": 44,
  "authorities": {
    "deck": 64,
    "canonical": 235,
    "evidence": 82,
    "historical": 732,
    "supporting": 199
  },
  "fingerprint": "419d559e6ea901cf665905e697a189b2167e06b4084494709ba6d37e6d998f1d"
}
```

## OAuth and tool smoke test

```json
{
  "authorization_code_flow": "PASS",
  "confidential_client_secret": "PASS",
  "pkce_s256": "PASS",
  "mcp_tool_count": 11,
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
  "knowledge_status_call": "PASS"
}
```

## Cloudflare isolation

기존 `summit1123` 공유 터널은 Mac Studio 커넥터 2개와 부하 분산되어 MASIL 요청 일부가 502를 반환했다. `masil-mcp` 전용 터널을 생성하고 이 호스트의 경로와 DNS를 전용 터널로 이전했다. 다른 공개 애플리케이션 경로와 Mac Studio 커넥터는 변경하지 않았다.

## Retrieval regression checks

- 기본 `search_knowledge`는 덱과 현재 상품 계약의 답변 가능한 사실만 반환하며 historical·forbidden·conflict 기록을 섞지 않는다.
- 과거 설계와 Master Q&A는 변경·충돌 의도가 있는 질문에서만 `historical_material`로 반환한다.
- 문헌 캡처는 사용자가 원문·캡처·이미지를 요구한 경우에만 답변 패킷에 넣는다.
- Cicchino, ERSO, Ehsani, Vivoda, Chen, LongROAD의 이름 기반 검색은 각 문헌의 정확한 대표 캡처로 연결된다.
- Candrive는 `qa_only`, References 자료는 `listed_only`를 명시해야 접근할 수 있다.

## Known non-blocking warnings

- FastMCP 2.14.7의 `authlib.jose` 사용 중단 예정 경고
- Starlette `TestClient`의 httpx 사용 중단 예정 경고

둘 다 현재 테스트나 공개 MCP 호출 실패는 아니며, FastMCP 3 전환 전에 의존성 호환성을 별도로 점검한다.

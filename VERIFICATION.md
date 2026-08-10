# MASIL MCP verification report

검증 시각: 2026-08-10 11:56 KST

## Result

| Layer | Result | Evidence |
|---|---|---|
| Knowledge model | PASS | YAML 15개 파싱, 중복 ID 0, 덱 claim 64개 51/6/7 일치, P0 15개, 누락 파일 0 |
| Evidence assets | PASS | 로컬 캡처 44개, active 22그룹·38이미지, Q&A 2그룹, References 3그룹, 공개 비밀값 노출 0 |
| Unit and MCP tests | PASS | pytest 50개 통과, 로컬 HTTP 14개 도구 호출 통과 |
| Local service | PASS | LaunchAgent 재시작, `/healthz` 200, 공개 서버와 fingerprint 일치 |
| Public tunnel | PASS | 전용 `masil-mcp` 터널, 공개 `/healthz` 200 |
| OAuth | PASS | authorization code, confidential client secret, PKCE S256 |
| Public MCP | PASS | 도구 14개 전건 호출, 주제 브리프, 미확정 총계, 정확한 문헌-캡처 연결, MCP 이미지와 공개 대체 URL 반환 |
| Claude Web connector | NEEDS USER CHECK | 서버 재시작 뒤 OAuth 재연결 여부와 실제 답변 내 이미지 렌더링은 Claude 화면에서 재확인 필요 |

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
  "fingerprint": "8a097f790deb979d2af30c5a8a4c235c9a6622016b5bbb995beae58e4663c33d"
}
```

## OAuth and tool smoke test

```json
{
  "authorization_code_flow": "PASS",
  "confidential_client_secret": "PASS",
  "pkce_s256": "PASS",
  "mcp_tool_count": 14,
  "authenticated_tool_call": "PASS",
  "connector_guide_call": "PASS",
  "topic_brief_call": "PASS",
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
  "resolved_capture_call": "PASS",
  "public_fallback_image_url": "PASS",
  "knowledge_status_call": "PASS"
}
```

## Cloudflare isolation

기존 `summit1123` 공유 터널은 Mac Studio 커넥터 2개와 부하 분산되어 MASIL 요청 일부가 502를 반환했다. `masil-mcp` 전용 터널을 생성하고 이 호스트의 경로와 DNS를 전용 터널로 이전했다. 다른 공개 애플리케이션 경로와 Mac Studio 커넥터는 변경하지 않았다.

## Retrieval regression checks

- 기본 `search_knowledge`는 덱과 현재 상품 계약의 답변 가능한 사실만 반환하며 historical·forbidden·conflict 기록을 섞지 않는다.
- `prepare_topic_brief`는 현재 입장·근거·주장 경계·미검증 범위만 반환하고 예상 질문을 생성하지 않는다.
- `forbidden_claims`와 `must_not_say`는 주장 경계로만 사용하며 자동 질문 목록으로 바꾸지 않는다.
- `list_open_items` 기본 호출은 unresolved 16개를 16/16으로 반환하고, 후보·파일럿 가설까지 명시적으로 열면 29개를 상태별로 구분한다.
- 과거 설계와 Master Q&A는 변경·충돌 의도가 있는 질문에서만 `historical_material`로 반환한다.
- 문헌 캡처는 사용자가 원문·캡처·이미지를 요구한 경우에만 답변 패킷에 넣는다.
- 생활권 밖 위험 근거는 Ehsani `capture-006`, 위치만으로 감점하지 않는 경계는 Hirsch `capture-037`로 각각 연결된다.
- 이미지 도구는 MCP ImageContent와 함께 공개 대체 URL·Markdown을 반환한다. 실제 Claude 화면 렌더링 여부는 클라이언트 재확인 대상이다.
- Cicchino, ERSO, Ehsani, Vivoda, Chen, LongROAD의 이름 기반 검색은 각 문헌의 정확한 대표 캡처로 연결된다.
- Candrive는 `qa_only`, References 자료는 `listed_only`를 명시해야 접근할 수 있다.

## Known non-blocking warnings

- FastMCP 2.14.7의 `authlib.jose` 사용 중단 예정 경고
- Starlette `TestClient`의 httpx 사용 중단 예정 경고

둘 다 현재 테스트나 공개 MCP 호출 실패는 아니며, FastMCP 3 전환 전에 의존성 호환성을 별도로 점검한다.

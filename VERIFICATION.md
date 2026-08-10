# MASIL MCP verification report

검증 시각: 2026-08-10 16:32 KST

## Result

| Layer | Result | Evidence |
|---|---|---|
| Knowledge model | PASS | YAML 15개 파싱, 중복 ID 0, 덱 claim 64개 44/13/7 일치, P0 15개, 누락 파일 0 |
| Evidence assets | PASS | 저장 자산 44개 중 공개 런타임은 active 22그룹·38이미지만 제공, 공개 비밀값 노출 0 |
| Unit and MCP tests | PASS | pytest 68개 통과, 현재 자료 전용 인덱스·명시적 근거 연결·이미지 종류 분리 회귀 통과 |
| Local service | PASS | LaunchAgent 재시작, `/healthz` 200, 공개 서버와 fingerprint 일치 |
| Public tunnel | PASS | 전용 `masil-mcp` 터널, 공개 `/healthz` 200 |
| OAuth | PASS | authorization code, confidential client secret, PKCE S256, 같은 access token으로 서버 재시작 전·후 호출 성공 |
| Public MCP | PASS | 도구 17개 전건 호출, 경량 답변 라우팅, 비식별 텔레메트리, 필드 가중 검색, 정확한 근거 순회, 다중 이미지, MCP App `ui://` 리소스 반환 |
| Claude Web connector | NEEDS USER CHECK | OAuth·MCP App 프로토콜은 공개 경로에서 PASS. 새 대화에서 자연어 질문별 답변·inline card·도구 재발견은 Claude 화면 확인 필요 |

## Public health snapshot

```json
{
  "status": "ok",
  "service": "masil-mcp",
  "documents": 538,
  "captures": 38,
  "authorities": {
    "deck": 64,
    "canonical": 235,
    "evidence": 82,
    "supporting": 157
  },
  "fingerprint": "b6d22561dc3aec107bf810fc3d5e321cfa9610fc49bb1f3ffc7dc1d6f967cfb8"
}
```

## OAuth and tool smoke test

```json
{
  "authorization_code_flow": "PASS",
  "confidential_client_secret": "PASS",
  "pkce_s256": "PASS",
  "mcp_tool_count": 17,
  "authenticated_tool_call": "PASS",
  "connector_guide_call": "PASS",
  "topic_brief_call": "PASS",
  "product_logic_call": "PASS",
  "slide_context_call": "PASS",
  "answer_context_call": "PASS",
  "inline_evidence_call": "PASS",
  "mcp_app_resource": "PASS",
  "mcp_app_tool_metadata": "PASS",
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
  "same_token_after_server_restart": "PASS"
}
```

## Cloudflare isolation

기존 `summit1123` 공유 터널은 Mac Studio 커넥터 2개와 부하 분산되어 MASIL 요청 일부가 502를 반환했다. `masil-mcp` 전용 터널을 생성하고 이 호스트의 경로와 DNS를 전용 터널로 이전했다. 다른 공개 애플리케이션 경로와 Mac Studio 커넥터는 변경하지 않았다.

## Retrieval regression checks

- 기본 `search_knowledge`는 덱과 현재 상품 계약의 답변 가능한 사실만 반환하며 historical·forbidden·conflict 기록을 섞지 않는다.
- `prepare_topic_brief`는 현재 입장·근거·주장 경계·미검증 범위만 반환하고 예상 질문을 생성하지 않는다.
- `forbidden_claims`와 `must_not_say`는 주장 경계로만 사용하며 자동 질문 목록으로 바꾸지 않는다.
- `list_open_items` 기본 호출은 unresolved 16개를 16/16으로 반환하고, 후보·파일럿 가설까지 명시적으로 열면 29개를 상태별로 구분한다.
- 과거 설계, Master Q&A, 폐기 규칙, 변경 이력은 Git에만 보존하고 공개 런타임에서는 검색·반환하지 않는다.
- 일반 MASIL 질문은 `prepare_answer_context`를 기본 진입점으로 사용하고, 도구명·내부 ID·YAML 필드를 최종 답변에 노출하지 않는다.
- `prepare_answer_context`는 별도 AI 호출 없이 질문 의도에 따라 덱·상품·문헌·미확정·가치·초안 재료의 우선순위만 조정한다.
- 텔레메트리 SQLite 스키마와 실제 파일에는 질문, 도구 인자, 답변, 근거 본문 필드가 없으며 도구명·라우트·상태·지연시간·결과·캡처 개수와 익명 세션 해시만 남는다.
- OAuth access/refresh token은 권한 600 SQLite에 저장된다. 공개 서버에서 발급한 동일 access token으로 재시작 전·후 17개 도구 목록과 실제 호출을 확인했다.
- 검색은 제목·태그·메타데이터·본문 가중치와 한국어 n-gram을 사용하되, 주장-문헌 근거 연결은 명시적인 `evidence_links`만 인정한다.
- 생활권 밖 위험 맥락에는 Ehsani만 연결한다. 위치만으로 감점하지 않는 원칙은 MASIL 상품 결정이며 Hirsch나 페르소나 장표를 직접 근거로 제시하지 않는다.
- 이미지 도구는 MCP ImageContent, `text/html;profile=mcp-app` inline 뷰, 공개 대체 URL·Markdown을 함께 반환한다. 실제 Claude Web 카드 렌더링은 커넥터 재연결 후 화면 재확인 대상이다.
- source 모드는 실제 원문 캡처만 반환한다. Ehsani·Vivoda·Chen처럼 로컬 원문 캡처가 없는 문헌은 덱 발췌로 자동 대체하지 않는다.
- Candrive 등 Q&A·References 전용 자료는 공개 런타임에서 접근할 수 없다.

## Known non-blocking warnings

- FastMCP 2.14.7의 `authlib.jose` 사용 중단 예정 경고
- Starlette `TestClient`의 httpx 사용 중단 예정 경고

둘 다 현재 테스트나 공개 MCP 호출 실패는 아니며, FastMCP 3 전환 전에 의존성 호환성을 별도로 점검한다.

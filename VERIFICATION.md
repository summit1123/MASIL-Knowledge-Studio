# MASIL MCP verification report

검증 시각: 2026-08-10 14:09 KST

## Result

| Layer | Result | Evidence |
|---|---|---|
| Knowledge model | PASS | YAML 15개 파싱, 중복 ID 0, 덱 claim 64개 51/6/7 일치, P0 15개, 누락 파일 0 |
| Evidence assets | PASS | 로컬 캡처 44개, active 22그룹·38이미지, Q&A 2그룹, References 3그룹, 공개 비밀값 노출 0 |
| Unit and MCP tests | PASS | pytest 68개 통과, 라우팅 8종·입력 비수집·OAuth 재시작 회귀, 로컬 HTTP 17개 도구 호출 통과 |
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
  "documents": 1312,
  "captures": 44,
  "authorities": {
    "deck": 64,
    "canonical": 235,
    "evidence": 82,
    "historical": 732,
    "supporting": 199
  },
  "fingerprint": "94fd8af3fef788a9b592dd1b1d1b88dff861ff23a864dbbe72769bbf91e231e1"
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
  "qa_only_mapping": "PASS",
  "reference_only_mapping": "PASS",
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
- 과거 설계와 Master Q&A는 변경·충돌 의도가 있는 질문에서만 `historical_material`로 반환한다.
- 일반 MASIL 질문은 `prepare_answer_context`를 기본 진입점으로 사용하고, 도구명·내부 ID·YAML 필드를 최종 답변에 노출하지 않는다.
- `prepare_answer_context`는 별도 AI 호출 없이 8개 준비 유형 중 하나를 선택한다. 라우트는 답을 고정하지 않고 덱·상품·문헌·변경 이력·미확정·가치·초안 재료의 우선순위만 조정한다.
- 텔레메트리 SQLite 스키마와 실제 파일에는 질문, 도구 인자, 답변, 근거 본문 필드가 없으며 도구명·라우트·상태·지연시간·결과·캡처 개수와 익명 세션 해시만 남는다.
- OAuth access/refresh token은 권한 600 SQLite에 저장된다. 공개 서버에서 발급한 동일 access token으로 재시작 전·후 17개 도구 목록과 실제 호출을 확인했다.
- 검색은 제목·태그·메타데이터·본문 가중치와 한국어 n-gram을 사용하며, `source_refs`·`material_refs`·`evidence_links`를 통한 정확한 문헌 연결을 유사 키워드보다 우선한다.
- 생활권 밖 위험 맥락은 Ehsani `capture-006`, 위치만으로 감점하지 않는 경계는 Hirsch `capture-037`로 함께 연결되며, 별도 캡처 요청 없이 답변 근거로 반환된다.
- 이미지 도구는 MCP ImageContent, `text/html;profile=mcp-app` inline 뷰, 공개 대체 URL·Markdown을 함께 반환한다. 실제 Claude Web 카드 렌더링은 커넥터 재연결 후 화면 재확인 대상이다.
- Cicchino, ERSO, Ehsani, Vivoda, Chen, LongROAD의 이름 기반 검색은 각 문헌의 정확한 대표 캡처로 연결된다.
- Candrive는 `qa_only`, References 자료는 `listed_only`를 명시해야 접근할 수 있다.

## Known non-blocking warnings

- FastMCP 2.14.7의 `authlib.jose` 사용 중단 예정 경고
- Starlette `TestClient`의 httpx 사용 중단 예정 경고

둘 다 현재 테스트나 공개 MCP 호출 실패는 아니며, FastMCP 3 전환 전에 의존성 호환성을 별도로 점검한다.

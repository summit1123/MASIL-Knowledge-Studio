# MASIL MCP verification report

검증 시각: 2026-08-10 06:59 KST

## Result

| Layer | Result | Evidence |
|---|---|---|
| Knowledge model | PASS | YAML 15개 파싱, 중복 ID 0, 덱 claim 64개 51/6/7 일치, P0 15개, 누락 파일 0 |
| Evidence assets | PASS | 로컬 캡처 44개, 연결 문헌 11개, 공개 비밀값 노출 0 |
| Unit and MCP tests | PASS | pytest 10개 통과 |
| Local service | PASS | LaunchAgent 실행, `/healthz` 200 |
| Public tunnel | PASS | 전용 `masil-mcp` 터널, 공개 `/healthz` 20회 연속 200 |
| OAuth | PASS | authorization code, confidential client secret, PKCE S256 |
| Public MCP | PASS | 도구 11개 목록, 검색, 답변 재료, 캡처 이미지 반환 |
| Claude Web connector | PASS | `MASIL Knowledge Studio` 등록·OAuth 연결, 11개 읽기 도구 표시, 항상 허용 설정 |
| Claude answer generation | ACCOUNT BLOCKED | 연결 후 실제 프롬프트 전송 단계에서 Claude 계정 사용 크레딧 소진 알림. 서버 오류 아님 |

## Public health snapshot

```json
{
  "status": "ok",
  "service": "masil-mcp",
  "documents": 722,
  "captures": 44,
  "authorities": {
    "canonical": 441,
    "evidence": 56,
    "historical": 28,
    "supporting": 197
  }
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
  "answer_context_call": "PASS",
  "capture_image_call": "PASS"
}
```

## Cloudflare isolation

기존 `summit1123` 공유 터널은 Mac Studio 커넥터 2개와 부하 분산되어 MASIL 요청 일부가 502를 반환했다. `masil-mcp` 전용 터널을 생성하고 이 호스트의 경로와 DNS를 전용 터널로 이전했다. 다른 공개 애플리케이션 경로와 Mac Studio 커넥터는 변경하지 않았다.

## Remaining manual check

Claude 사용량이 초기화되면 새 채팅에서 다음 문장으로 실제 답변 렌더만 확인한다.

> MASIL Knowledge Studio 커넥터만 사용해서 knowledge_status를 확인하고, 평소 점수가 계속 낮지만 최근 변화가 크지 않은 운전자의 월 판정을 확인한 뒤, capture-015 이미지를 불러와 보여주세요.

정상 기대 결과는 `knowledge_status`, `search_knowledge` 또는 `explain_product_logic`, `get_capture_image` 호출과 이미지 표시다.

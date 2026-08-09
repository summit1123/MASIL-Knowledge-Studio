# MASIL Evidence Studio

팀이 확정한 지식만을 근거로 Q&A·대본 작성, 내용 검수, 발표 연습을 지원하는 워크스페이스.

- `knowledge/` — 승인 스냅샷 (상품 계약은 V20, 시뮬레이션 수치는 확정수치카드)
- `knowledge/mcp_manifest.yaml` — 최종 덱·직접 Q&A만 넣는 기본 검색 범위
- `knowledge/claims/deck_claims.yaml` — 최종 제출 덱(9장)의 장표별 인쇄 사실 원장. 지식 충돌 시 덱-우선(deck-first)이 최상위다.
- `knowledge/history/decision_log.yaml` — 바뀐 규칙의 이전·이후와 변경 이유
- `sources/11_V20_결정_기록_0810.md` — 2026-08-10 현재 상품·문헌·사업 결정 정본

충돌 시 `sources/11_V20_결정_기록_0810.md`와 `status: active` 항목이 우선한다.
`historical_demo`와 `deprecated`는 과거 화면·결과를 설명할 때만 사용한다.
기존 8/4 전체 추출물은 `legacy_reference`이며 MCP 기본 검색에서 제외한다.
발표 대본 초안은 V20 문안으로 갱신된 뒤 별도 버전으로 연결한다.

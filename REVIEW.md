# V20 활성 지식 검토 가이드 — 2026-08-10

이 저장소는 최종 덱 전체를 다시 설명하는 백과사전이 아니다. Summary·Appendix에서 실제로
말하는 내용과 그 직접 Q&A만 MCP 기본 검색에 넣는다. 현재 대본 초안은 V20 반영 전이라
정본에서 제외한다.

## 기본 검색 범위

`knowledge/mcp_manifest.yaml`을 따른다.

- `official_positions.yaml`: `status: active`
- `qa/cards.yaml`: `status: active`
- `key_numbers.yaml`: `status: active`
- `glossary.yaml`: `status: active`
- `forbidden_claims.yaml`: `status: active`
- `evidence/registry.yaml`: `presentation_entries` 중 `stage_citable`·`qa_only`

기존 8/4 항목은 `legacy_reference`다. 과거 화면을 설명하라는 명시 요청이 없으면 검색하지 않는다.
`history/decision_log.yaml`도 기본 검색에서 제외한다.

## 검토 순서

1. 최종 덱과 V20이 같은 말을 하는지 확인한다.
2. 활성 Q&A의 첫 문장이 결론인지 확인한다.
3. 숫자는 `claim_type`이 `team_decision`, `simulation_result`, `target`,
   `candidate_parameter` 중 무엇인지 확인한다.
4. 문헌은 허용 주장과 덱 위치가 원문 캡처에 연결되는지 확인한다.
5. 구 데모 수치가 현재 답변에 섞이지 않는지 확인한다.

## 승인 상태

- 스냅샷: `draft_pending_review`
- 덱·대본·대시보드 수정: 이번 브랜치 범위 밖
- 원격 push·main 병합: 이번 브랜치 범위 밖

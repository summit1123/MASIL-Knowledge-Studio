# 덱 우선 활성 지식 검토 가이드 — 2026-08-10

이 저장소는 최종 덱 9장을 중심으로 발표와 Q&A에 필요한 사실·해석·근거를 관리한다. 질문 카드가 없는 새로운 질문도 deck claims, active positions와 evidence를 조합해 답할 수 있어야 한다.

## 기본 검색 범위

`knowledge/mcp_manifest.yaml`을 따른다.

- `claims/deck_claims.yaml`: 항상, 최우선
- `official_positions.yaml`: `status: active`
- `glossary.yaml`: `status: active`
- `forbidden_claims.yaml`: `status: active`
- `evidence/registry.yaml`: `presentation_entries` 중 `stage_citable`·`qa_only`
- `qa/cards.yaml`: `status: active`, 질문 시나리오와 표현 예시로만 사용

과거 결정과 구 데모는 `history` 또는 `legacy_reference`다. 명시 요청이 없으면 검색하지 않는다. 발표 대본 초안은 팀 승인 전까지 정본에서 제외한다.

## 검토 순서

1. 최종 덱의 인쇄 사실과 장표 번호를 확인한다.
2. 팀 확정 해석이 덱을 부정하지 않고 필요한 맥락만 보완하는지 확인한다.
3. 고정 용어와 쉬운 spoken English 규칙을 확인한다.
4. 숫자가 `team_decision`, `simulation_result`, `target`, `candidate_parameter` 중 무엇인지 확인한다.
5. 문헌의 허용 주장·덱 위치·원문 캡처 연결을 확인한다.
6. Q&A 카드는 사실 정본이 아니라 표현 예시로 사용되는지 확인한다.
7. 구 데모·내부 버전명·과거 계약이 현재 공개 답변에 섞이지 않는지 확인한다.

## 자동 검증

```bash
ruby knowledge/scripts/verify_knowledge.rb
```

## 승인 상태

- 스냅샷: `draft_pending_review`
- 덱·대본·대시보드 수정: 이번 브랜치 범위 밖
- 이미지 자산화·FastMCP 구현: 아직 시작하지 않음
- 원격 push·main 병합: 이번 브랜치 범위 밖

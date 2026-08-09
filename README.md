# MASIL Evidence Studio

최종 제출 덱을 기준으로 MASIL의 장표 사실, 팀 확정 해석, 용어, 수치, 문헌 근거와 변경 이력을 관리하는 워크스페이스.

## 정본 우선순위

1. 최종 제출 덱 9장 — `knowledge/claims/deck_claims.yaml`
2. 팀 최신 확정 설명 — `knowledge/official_positions.yaml`의 `status: active`
3. 승인된 발표 대본 최종본
4. 검증 문헌과 캡처 — `knowledge/evidence/registry.yaml`
5. 시뮬레이션·대시보드 산출물
6. 과거 결정 이력 — 기본 검색 제외

내부 회의 기록과 과거 Q&A는 최종 덱을 덮어쓸 수 없다. 충돌이 해소되지 않으면 과거 문장으로 빈칸을 채우지 말고 사람 검토로 보낸다.

## 주요 파일

- `knowledge/mcp_manifest.yaml` — MCP 기본 검색 범위와 검색 순서
- `knowledge/claims/deck_claims.yaml` — 최종 덱 9장의 인쇄 사실·구두 보완·수정 예정 원장
- `knowledge/official_positions.yaml` — 팀 확정 해석. `status: active`만 현재 정본
- `knowledge/qa/cards.yaml` — P0 질문 시나리오와 쉬운 표현 예시. 사실 정본이 아님
- `knowledge/glossary.yaml` — 고정 영문, 쉬운 뜻, 검색 별칭
- `knowledge/forbidden_claims.yaml` — 과장·충돌 방지 경계
- `knowledge/evidence/registry.yaml` — 문헌의 허용 주장·주의사항·덱 사용 위치
- `knowledge/history/decision_log.yaml` — 변경 이력. 기본 검색 제외
- `sources/11_V20_결정_기록_0810.md` — 파일명은 유지하는 과거 결정 기록. 현재 공개 정본이 아님

발표 대본 초안은 팀 승인 전까지 기본 검색에서 제외한다. 문헌 캡처 원본은 아직 자산화되지 않았으며 MCP 구현 단계에서 별도 연결한다.

## 검증

```bash
ruby knowledge/scripts/verify_knowledge.rb
```

검증기는 YAML 파싱, 중복 ID, deck claim 집계와 9개 장표 coverage, P0-01~15, 파일 참조, 정본·이력 격리와 공개 답변의 폐기 표현 누출을 확인한다.

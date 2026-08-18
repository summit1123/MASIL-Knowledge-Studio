# MASIL Knowledge Studio — 전체 구조

## 핵심 지도

| 파일 | 역할 | 현재 지위 |
|---|---|---|
| `IMPLEMENTATION.md` | 현재 GaipStudio 작업 checkout의 실제 점수·Care·할인 계산 감사 | 2026-08-10 관측, dirty working tree 주의 |
| `knowledge/presentation_story.yaml` | 문제정의→해결책→신뢰→검증→사회적 가치→실행의 발표 서사 | 검토 대기 |
| `knowledge/product_model.yaml` | 전체 상품 설계와 current·candidate·unresolved·historical 경계 | 검토 대기 |
| `knowledge/conflict_map.yaml` | 현재와 과거 설명의 충돌 및 해소 상태 | 검토 대기 |
| `knowledge/coverage_matrix.yaml` | 영역별 완성도와 MCP 구현 차단 조건 | 검토 대기 |
| `knowledge/claims/deck_claims.yaml` | 최종 덱 9장의 인쇄 사실·구두 맥락·수정 예정 | 64건 구조화 |
| `knowledge/official_positions.yaml` | 최신 설명과 과거 세부 자료 | active만 현재 설명 |
| `knowledge/key_numbers.yaml` | 팀 결정·시뮬레이션·후보값·목표 수치 | active만 현재 사용 |
| `knowledge/evidence/registry.yaml` | 문헌의 허용 주장·주의사항·덱 위치 | 16개 발표 카드 |
| `knowledge/glossary.yaml` | 고정 영어와 쉬운 뜻 | active만 사용 |
| `knowledge/qa/cards.yaml` | 핵심 질문 시나리오와 표현 예시 | 사실 정본 아님 |
| `knowledge/history/decision_log.yaml` | 변경 이유와 과거 계약 | 보조 재료 |
| `sources/` 승인 목록 | 계산 설명·근거 지도·과거 답변 | 보조 재료 |

## 전체 발표 영역

1. 문제정의와 왜 지금인가
2. 왜 고령자부터 시작하는가
3. 기존 규제·마일리지·UBI의 간격
4. MASIL의 상품 정의와 이름
5. 개인 생활권 형성
6. 월별 측정·판정·Care
7. 현재 연간 할인 구조와 후보 요율의 검증 경계
8. AI·사람·프라이버시
9. 합성 시뮬레이션과 검증 한계
10. 직원 대시보드와 고객 지원 흐름
11. 보험사·고령자·가족·사회의 가치
12. 파일럿·실현 가능성·로드맵
13. 시장·경쟁·채널·팀·파트너와 아직 없는 근거
14. 문헌·수치·캡처 근거와 주장하지 않는 것

## 자료 조합 원칙

- 덱은 발표 범위와 인쇄 사실을 제공하지만 모든 질문의 답을 단독 결정하지 않는다.
- 현재 상품 논리는 `product_model`, 문헌은 `registry`, 수치는 `key_numbers`가 각각 권한을 가진다.
- 과거 자료는 질문 의도, 설명 후보, 후속 질문, 변경 이유와 충돌 탐지에 사용한다.
- 미확정 항목은 과거 산식으로 채우지 않고 그대로 미확정으로 반환한다.
- Master Q&A URL을 런타임에 조회하지 않는다. 텍스트와 캡처를 로컬 자산으로 내보낸 뒤 사용한다.
- 미확정 질문은 `현재 검증 수준 → 논리에 맞는 권고 표현 → 필요한 검증` 세 부분으로 답한다.

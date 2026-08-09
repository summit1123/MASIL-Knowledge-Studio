# MASIL Knowledge Studio — 덱 우선 구조

## 기본 원칙

MKS의 기본 검색은 최종 덱의 사실과 현재 팀 확정 해석에서 시작한다. Q&A 카드는 고정 정답집이 아니라 질문 시나리오와 쉬운 표현 예시다. 과거 회의 기록, 구 데모와 미정합 대본은 명시 요청이 없으면 검색하지 않는다.

## 파일 지도

| 파일 | 역할 | MCP 기본 검색 |
|---|---|---|
| `knowledge/claims/deck_claims.yaml` | 최종 덱 9장 인쇄 사실·주의 표기 | 항상, 최우선 |
| `knowledge/official_positions.yaml` | 팀 최신 확정 해석 | `status: active`만 |
| `knowledge/snapshot.yaml` | 현재 정본·구현 차이 요약 | 현재 항목만, history 제외 |
| `knowledge/glossary.yaml` | 고정 영어·쉬운 뜻 | `status: active`만 |
| `knowledge/forbidden_claims.yaml` | 실제 충돌 방지 경계 | `status: active`만 |
| `knowledge/evidence/registry.yaml` | 발표·Q&A 문헌 카드 | `stage_citable`·`qa_only`만 |
| `knowledge/qa/cards.yaml` | P0 시나리오·표현 예시 | `status: active`, 사실 정본 아님 |
| `knowledge/key_numbers.yaml` | 발표 수치와 지위 | `status: active`만 |
| `knowledge/history/decision_log.yaml` | 변경 이력 | 기본 제외 |
| `sources/` | 원문·과거 승인 문서 | 기본 제외, 명시 요청 시 |

## 현재 공개 상품 계약

- 월별 결과는 Favorable, Standard, Care의 세 등급으로 설명한다.
- Hold는 네 번째 위험 등급이 아니라 데이터 부족 시 판정을 보류하는 no-penalty 상태다.
- Care는 도움이 필요할 수 있는 달을 표시하며 직원 검토와 지원 제안으로 이어진다.
- Care 자체가 자동 할증·자동 차감을 만들지는 않는다.
- 연간 할인율 계산은 월별 등급 표시와 구분한다.
- 대시보드의 13%p 차이는 Edward 사례의 연간 시뮬레이션 결과이며 한 달 Care의 고정 차감값이 아니다.
- 생활권 밖은 위험 맥락이 될 수 있지만 위치만으로 감점하지 않는다.
- 내부 점수 판정과 Care 신호의 분리 구조는 `layer: deep` 기술 설명으로만 사용한다.

## 문헌 검색 규칙

- `stage_citable`: 덱의 해당 문장을 위해 무대에서 사용 가능
- `qa_only`: 질문이 들어왔을 때만 사용
- `listed_only`: 참고문헌에는 있지만 선제 인용하지 않음
- `banned`: 덱에 남아 있어도 해당 주장을 방어하지 않음

각 문헌은 `allowed_claim`, `caveat`, `deck_location`, `capture_available`을 함께 반환한다. 문헌 제목만 반환하거나 허용 범위보다 강한 문장을 만들지 않는다.

## 검색 우선순위

1. `deck_claims`
2. `official_positions`의 active 항목
3. `glossary`와 `forbidden_claims`의 언어·해석 경계
4. `evidence/registry`의 발표·Q&A 근거
5. `qa/cards`의 표현 예시
6. 명시 요청 시에만 history·legacy

활성 근거가 없으면 과거 문서로 빈칸을 채우지 말고 근거 부족으로 답한다.

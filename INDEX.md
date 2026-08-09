# MASIL Knowledge Studio — V20 구조

## 기본 원칙

MKS의 기본 검색 범위는 최종 덱의 Summary·Appendix와 거기서 바로 파생되는 Q&A다.
현재 대본은 V20 반영 전 초안이므로 정본으로 넣지 않는다. 과거 검토 문서도 전부 모델에
넣지 않는다.

## 파일 지도

| 파일 | 역할 | MCP 기본 검색 |
|---|---|---|
| `knowledge/mcp_manifest.yaml` | 포함·제외 규칙 | 항상 |
| `knowledge/snapshot.yaml` | 현재 버전·정본·구현 차이 | 항상 |
| `knowledge/official_positions.yaml` | V20 공식 스탠스 | `status: active`만 |
| `knowledge/qa/cards.yaml` | 최종 덱 직접 Q&A | `status: active`만 |
| `knowledge/key_numbers.yaml` | 발표 수치와 지위 | `status: active`만 |
| `knowledge/glossary.yaml` | 고정 영어·쉬운 뜻 | `status: active`만 |
| `knowledge/forbidden_claims.yaml` | 실제 충돌 방지 규칙 | `status: active`만 |
| `knowledge/evidence/registry.yaml` | V20 문헌 카드 | `presentation_entries`만 |
| `knowledge/history/decision_log.yaml` | 현재 데모와 V20의 변경 이력 | 기본 제외 |
| `sources/` | 원문·과거 승인 문서 | 기본 제외, 명시 요청 시 |

## 현재 상품 계약

- 월 통합점수: 30/30/20/20 네 축
- 월 판정: Favorable 또는 Standard, 데이터 부족 시 Hold
- Care review: 같은 달 이동 +25%p AND 위험행동 +20%p의 별도 사람 검토 신호
- 연간 점수: 12개월 월 통합점수의 단순 평균
- Favorable 9/12: 추가 할인 자격
- Care review: 직접 가격 영향 없음
- 환경 간 실질 일치: 59/60
- 500명·15–20%·+2%p: 실측이 아닌 파일럿 목표

## 문헌 검색 규칙

- `stage_citable`: 덱의 해당 문장을 위해 무대에서 사용 가능
- `qa_only`: 질문이 들어왔을 때만 사용
- `listed_only`: 참고문헌에는 있지만 선제 인용하지 않음
- `banned`: 덱에 남아 있어도 해당 주장을 방어하지 않음

각 문헌은 `allowed_claim`, `caveat`, `deck_location`, `capture_available`을 함께 반환한다.
문헌 제목만 반환하거나 허용 범위보다 강한 문장을 만들지 않는다.

## 충돌 우선순위

1. `sources/11_V20_결정_기록_0810.md`
2. 각 파일의 `status: active`
3. V20 문헌 카드의 허용 주장
4. `historical_demo`·`legacy_reference`

활성 근거가 없으면 과거 문서로 빈칸을 채우지 말고 근거 부족으로 답한다.

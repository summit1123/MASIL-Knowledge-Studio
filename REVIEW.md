# Knowledge Core 초안 — 검토 가이드 (2026-08-04)

`final/` 승인 문서 11종 → 병렬 추출(8 에이전트) → 중복 병합 → 확정수치카드(`e2d2e49`) 대조 검증을 거친 **DRAFT**입니다. 사람 검토 전이며, 검토 완료 시 `snapshot.yaml`의 `status`를 `active`로 바꾸면 됩니다.

## 파일 구성

| 파일 | 항목 수 | 내용 |
|---|---|---|
| `knowledge/snapshot.yaml` | — | 승인 소스 11종 + 일괄 deprecated(사유 포함) + 수치 앵커(카드 SHA) |
| `knowledge/official_positions.yaml` | **161** | 주제별 공식 스탠스 (claim_type·must_include·must_not_say·근거) |
| `knowledge/qa/cards.yaml` | **53** | Q&A 카드 (직답 + 발표답변 전문 + 후속질문 + 금지 표현) |
| `knowledge/evidence/registry.yaml` | **268** | 출처 원장 (지지하는 것/하지 않는 것 + verified/unverified/banned) |
| `knowledge/forbidden_claims.yaml` | **129** | 금지 표현 + 사유 + 대체 문구 |
| `knowledge/glossary.yaml` | **97** | 용어 (공식 영어·쉬운 영어·금지 변형) |
| `knowledge/key_numbers.yaml` | **252** | 수치 전수 (카드 행 단위 + 문서별 핵심 수치) |

## 자동 검증 결과

- **정본 수치 누락 0**: 118 / 기본 56 / 54/60 / 113건 / 969 / 30·30·20·20 / 260m / 80,032 전부 존재
- **구수치 오염 0**: 자동 스캔 경고 9건은 전수 확인 결과 모두 정당한 맥락 — "구: 56/60" 같은 이력 표기, 금지 목록 안의 금지 표현 자체, 레거시 격자 "랭킹 114건"(요율 114건과 무관)
- **'확인 필요' 플래그 32건**: 대부분 기존 팩트체크 미결 목록과 일치 (Zheng/Montoliu, MDPI 12278, 일본 ~3,500km, 2023 노인실태조사 등) — 출처부록의 미확인 등급이 그대로 이관된 것. `grep "확인 필요"` 로 전체 조회 가능

## 저장 구조 — 2층 (8/4 보강)

- **`sources/`** — 승인 원문 11종 전문 사본. AI에 knowledge/와 **함께** 넣어야 함(색인만 넣으면 답이 얕아짐)
- **`knowledge/`** — 색인·규칙층. positions는 스탠스 + `detail_ko`(무엇을·왜·어떻게) + `source`(원문 앵커)
- 얇았던 포지션 11건(케어 월수 비례·k-거리 실측 절차 등)에 detail_ko·source 보강 완료

## 검토 우선순위 (권장 순서)

1. **`official_positions.yaml`** — 이게 시스템의 심장. 특히 `claim_type` 분류(team_decision vs simulation_result vs external_fact)가 맞는지. 잘못 분류되면 AI가 팀 결정을 외부 사실처럼 말함
2. **`forbidden_claims.yaml`** — 여기 없는 금지 표현이 생각나면 추가 (시스템의 검수 규칙이 됨)
3. **`qa/cards.yaml`** — 발표답변 전문이 마스터답변안 최신본(어제 rolling 정합본)에서 왔는지 몇 개 표본 대조
4. `glossary.yaml` — 15초면 됨. 단, 아래 미결 1번 먼저
5. `evidence/`·`key_numbers`는 조회용이라 훑기만

## 검토 전 결정 필요 (미결 2건)

1. ~~"MASIL Zone" 공식화~~ — **확정(8/4)**: 공식 영어 MASIL Zone, 대시보드 EN 49곳 스윕 완료. 잔여: — glossary에 후보로 들어 있으나, 현 대시보드·덱 EN은 전부 "living zone". 공식화하면 대시보드 EN 스윕 필요(내가 함). 결정 전까지 glossary에 `pending` 표시해 둠
2. ~~레포 public~~ — **private 전환 완료(8/4)**. (구) — 여기 내용물이 사실상 Q&A 전략 전체라 private 전환 후 푸시 권장:
   ```
   gh repo edit summit1123/MASIL-Knowledge-Studio --visibility private --accept-visibility-change-consequences
   ```

## 다음 단계

검토 OK → 커밋·푸시(사후에 내가) → 0.5단계: 이 폴더를 GPT 프로젝트/Claude Project 지식으로 넣고 시스템 프롬프트에 "수치·스탠스는 knowledge/ 밖에서 가져오지 마"를 박으면 오늘부터 검수기로 사용 가능.

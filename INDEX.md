# MASIL Knowledge Studio — 구조 지도

한 장으로 보는 "뭐가 어디 있나". 헷갈리면 여기부터.

## 전체 그림

```
sources/          원문층 — 승인 문서 11종 전문 (사람이 읽는 원본)
   │  ↑ 여기서만 근거를 가져온다. 여기 없으면 "근거 없음"
   ▼
knowledge/        색인·규칙층 — AI가 먹는 구조화 지식
   ├─ snapshot.yaml            무엇이 유효/폐기인가 + 수치 앵커(카드 커밋 SHA)
   ├─ official_positions.yaml  주제별 공식 스탠스 161개  ← 시스템의 심장
   ├─ qa/cards.yaml            Q&A 53장 (직답·발표답변 전문·후속질문·금지)
   ├─ evidence/registry.yaml   문헌 원장 176건 (URL·검증상태·주제)
   ├─ forbidden_claims.yaml    금지 표현 129개 (+ 대체 문구)
   ├─ glossary.yaml            용어 (공식 영어·쉬운 영어·금지 변형)
   └─ key_numbers.yaml         수치 252개 (카드 행 단위)

OPEN_ITEMS.md     사람 판단 대기 (문헌 지위 11 · 내용 상충 4 · 용어 1 · 분류 5)
REVIEW.md         검토 가이드 (우선순위·검증 결과)
```

## 각 파일을 언제 보나

| 질문 | 볼 곳 |
|---|---|
| "이 주제 우리 입장이 뭐지?" | `official_positions.yaml` — topic으로 찾기 |
| "심사위원이 이렇게 물으면?" | `qa/cards.yaml` — question_ko |
| "이 숫자 맞나?" | `key_numbers.yaml` → 원본은 `sources/00_확정수치카드.md` |
| "이거 말해도 되나?" | `forbidden_claims.yaml` |
| "이 문헌 써도 되나? 링크는?" | `evidence/registry.yaml` — status·url |
| "영어로 뭐라고?" | `glossary.yaml` |
| "왜 그렇게 정했지?" (전체 맥락) | `sources/` 원문 |

## 문헌은 이렇게 정리돼 있다

`evidence/registry.yaml` 176건, 각 항목의 필드:

```yaml
- source: Ehsani & Tefft 2021 (CHANCE 34(1))   # 대표 이름
  citation_full: ...                            # 완전한 서지
  url: https://...                              # 실제 링크 (55건 보유)
  status: verified                              # ← 이게 핵심
  status_reason: 출처부록 ◎ 원문 대조 확인
  topics: [생활권-안-사고통계, 친숙도]           # 어디에 쓰이는 근거인가
  aliases: [...]                                # 병합된 다른 표기들
  status_conflict: ...                          # 지위가 갈렸던 이력 (있으면 사람 확인 대상)
```

**status 4단계 — 이것만 기억하면 됩니다:**

| status | 개수 | 의미 | 사용 |
|---|---|---|---|
| `verified` | 58 | 원문 대조 확인 | 무대에서 인용 가능 |
| `internal` | 63 | 우리 실측·코드 | 인용 가능 (합성·시뮬 단서 필수) |
| `unverified` | 41 | 팩트체크 미결 | **확보 전 발표 인용 금지** |
| `banned` | 14 | 인용 금지 확정 | 절대 금지 |

URL이 없는 건 원문에 링크가 없었던 것(내부 실측·법령·비공개 자료). `sources/`에서 마크다운 링크로 찾을 수 있는 건 전부 붙였습니다.

## 정본 앵커 — 숫자가 헷갈릴 때

**모든 수치의 최종 기준은 `sources/00_확정수치카드.md`** (커밋 `e2d2e49`, 2026-08-02 rolling 확정). knowledge의 수치가 카드와 다르면 카드가 이깁니다.

기억할 최신값: 우대 118 / 기본 56 / 보류 6 · 케어 30 · 3지형 케어 60/60·우대 54/60 · 요율 150/113 · 민감도 ±5 중앙 3·최대 9 · 케어 월수 전원 1개월 · eps 260m 단일 · 로그 80,032.

## AI에 넣는 법 (0.5단계 — 오늘 가능)

GPT 프로젝트 / Claude Project 지식에 **`knowledge/` + `sources/` 둘 다** 넣습니다(색인만 넣으면 답이 얕아짐). 시스템 프롬프트 핵심:

```
1. 수치·스탠스는 knowledge/ 와 sources/ 밖에서 가져오지 마라.
2. forbidden_claims.yaml의 표현은 어떤 이유로도 쓰지 마라.
3. 근거가 없으면 "현재 승인된 자료로는 뒷받침할 수 없습니다"라고 답하고 빈칸을 채우지 마라.
4. 답변마다 근거 상태를 밝혀라: VERIFIED / TEAM DECISION / SIMULATION / UNVERIFIED / UNSUPPORTED
5. 수치가 카드(00_확정수치카드)와 다르면 카드를 따라라.
```

## 갱신 규칙

- 원문(`final/`)이 바뀌면 → `sources/` 동기화 → 해당 항목만 수정
- 새 결정이 나면 → `official_positions.yaml`에 topic 추가 + 구 스탠스는 삭제가 아니라 `status: deprecated`
- 팩트체크 결과가 오면 → `registry.yaml`의 status 승급 + `OPEN_ITEMS.md`에서 제거
- **공식 스탠스 수정은 사람만** (AI가 자동 수정하지 않는다)

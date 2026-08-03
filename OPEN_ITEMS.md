# 사람 확인 대기 목록 (2026-08-04 교차검사 산출)

자동 교차검사 57건 중 **기계적으로 고친 것은 반영 완료**(eps 0/180 단서, 케어 '여러 달' 삭제, 위치 창 4개월→상시 2개월, 1/7→1/8, Ehsani 연루/유발, 85%→86.0%, MASIL Zone 정리 등).
아래는 **팀 판단이 필요해 남긴 것**입니다. 결정하면 즉시 반영합니다.

## A. 문헌 지위 상충 11건 (registry.yaml의 `status_conflict` 필드에 이력 보존)

보수적 원칙(banned > unverified > verified)으로 임시 통일했으나, 원래 등급이 갈렸던 건들:

| 출처 | 임시 지위 | 쟁점 |
|---|---|---|
| Burdett 2017 | banned | 한쪽은 ◎(자택 11km 62% 근거), 한쪽은 ✕. **우리 핵심 논거(노출의 지도)에 쓰이므로 확인 우선순위 최상** |
| Intini 2019 | banned | ◎(초록 확인) vs ✕(결론 불확실) |
| KTDB 2013 (트립당 14.0km) | banned | 원문 링크 미확보 |
| KIRI리포트 2024.7 | banned | 동명 리포트 2건이 섞임 — 리포트 번호로 분리 필요 |
| 업계 UBI 3~6개월 | banned | 세 규칙이 서로 다름(완화 인용 / 발표 금지 / 비교 생략) — **하나로 확정 필요** |
| 2023 노인실태조사 | unverified | 경로당 주 2.9회는 ◎ 확인분이라 분해 필요 |
| Langford 2013 (Candrive) | unverified | △(초록만) 등급을 verified로 볼지 규약 필요 |
| Charlton 2018 | unverified | 동일 |
| DEGURBA | unverified | 표준 자체는 실재 / 구현은 공백 — 분리 표기 |
| 위치정보법 23조 | unverified | 조문(사실) vs 자체 해석(법무 미검토) 분리 필요 |
| TAAS 2024 | verified | verified vs internal — 우리 산출인지 공식 통계인지 |

**결정 방식 제안**: △(초록만)은 "verified + '초록 기준' 명시 조건"으로 규약화하면 5건이 한 번에 정리됩니다.

## B. 내용 상충 — 원문층까지 고쳐야 하는 것 4건

1. **데이터 확보 3경로 정의가 두 버전** — "① 기존 UBI 채널 ② 특약 신규 수집 ③ 공공·제휴" vs "자체 앱 → OEM → 제휴". 어느 쪽이 팀 확정인지 확인 필요
2. **개인당 방문점 수** — "100개 수준" vs "수십 개" (원문층도 불일치). `gaip_visit_events.csv` 실측으로 확정 가능 — 원하면 계산해 드립니다
3. **TAAS 구성비 유도 근거** — "2024년 246개 시군구" vs "2010–2024 원천 CSV 전수", 정밀도도 44.6/42.4/13.0 vs 44.55/42.43/13.02
4. **'사고 70% 자택 8km'** — 원문 미확인인데 일부 항목에서 플래그 없이 인용됨. Burdett(11km 62%)로 대체 권장

## C. 용어 결정 1건

- **Safe Zone 유지 여부** — 현재 '생활권 원(circle)'에 Safe Zone이 남아 있음. MASIL Zone(생활권 전체)과 계열이 갈려 혼동 위험. 유지하려면 "Safe Zone = 원 한정" 구분 note, 폐기하려면 MASIL Zone circle 등으로 교체

## D. claim_type 재분류 제안 5건

- Candrive 표기 규칙 → external_fact **→ team_decision** (내용이 우리 표기 결정)
- 위치정보법 해석 → external_fact **→ team_decision** (자체 해석, 법무 미검토)
- 배포·검증 상태 / Safe Zone 방어선 / DBSCAN 3중 → simulation_result **→ team_decision** (설계·운영 서사)

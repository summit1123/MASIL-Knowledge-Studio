# V20 이후 사람 확인 대기

MCP 기본 검색은 `knowledge/mcp_manifest.yaml`의 활성 항목만 사용한다. 아래 항목은
최종 덱·현재 데모와 V20 계약 사이에 실제로 남은 차이만 기록한다.

## 1. 덱·데모 표기 충돌 — 팀 장표 작업 범위

- Summary 1의 `Favorable · Standard · Care Tier`는 V20의 두 축 계약과 다르다.
- Summary 1의 `more than 3 visitings`는 `3+ distinct visit days`로 고쳐야 한다.
- Summary 1의 KCA `2.28s (+90%)`는 시야 제한 돌발 상황의 `2.28s vs 1.20s`라는 조건을 붙여야 한다.
- Summary 2의 `Favorable / Standard / Care` 단일 분류 표기도 두 축 표현이 필요하다.
- Dashboard Appendix의 `MASIL proposal 3%`와 13%p 차이는 이전 데모 요율이다.
- Appendix A의 Sumagaysay·LexisNexis 문장은 V20 문헌 검토에서 방어 근거가 철회됐다.
- Appendix D의 Care 단일 등급과 일부 legacy persona references는 V20 설명과 맞지 않는다.
- 영어·한국어 발표 대본 초안도 위 충돌을 포함하므로 V20 문안으로 갱신한 뒤 정본에 연결한다.

이 저장소는 장표를 수정하지 않는다. Q&A에서는 활성 카드로 현재 계약을 답하고, 구 화면은
`historical_demo`라고 설명한다.

## 2. 구현 차이 — 다음 버전 범위

- 연간 점수 = 12개월 월 통합점수 평균 규칙을 기본 할인율에 연결하는 산식은 미구현이다.
- Care review와 가격을 분리한 V20 계약이 기존 대시보드 데모에는 아직 반영되지 않았다.

## 3. 문헌 캡처 자산화 — MCP 구현 단계

V20 문헌 카드의 원문 캡처는 검토 완료 상태다. 현재 MKS에는 `allowed_claim`,
`deck_location`, `citation_tier`, `capture_available`만 기록했다. Claude 답변 안에서 이미지를
직접 보여주려면 다음 단계에서 캡처 원본을 저장소 또는 접근 가능한 객체 저장소로 내보내고,
각 evidence key에 안정적인 asset URL과 페이지 좌표를 연결해야 한다.

## 4. 사업 수치

500명, 자발 가입률 15–20%, 유지율 +2%p는 모두 파일럿 목표다. 측정 결과가 생길 때까지
`target` 상태를 유지한다.

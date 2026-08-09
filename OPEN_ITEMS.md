# 덱 우선 교정 이후 남은 작업

MCP 기본 검색은 `knowledge/mcp_manifest.yaml`을 따른다. 아래 항목은 최종 덱을 부정하는 계약 변경이 아니라, 인쇄 문안 보완·근거 자산화·미구현 기능을 기록한다.

## 1. 최종 덱 인쇄 문안 수정 예정 7건

정확한 항목과 구두 대응은 `knowledge/claims/deck_claims.yaml`의 `printed_correction_planned`를 정본으로 사용한다.

- Summary 1: `more than 3 visitings` → `3 or more distinct visit days`
- Summary 2: 86% 이동권 문구에 출처를 붙이거나 표현 조정
- Appendix A: Sumagaysay로 방어할 수 없는 UBI 한계 문장 제거·대체
- Appendix A: LexisNexis 45% fleet 문맥 제거, 0.5% 수치만 정확한 맥락으로 사용
- Appendix D: `ScienceDirect` 플랫폼명을 실제 저자·논문명으로 교정
- References: Sumagaysay 항목 제거 예정
- References: LexisNexis fleet telematics 항목 제거 예정

## 2. 인쇄는 유지하되 구두 맥락이 필요한 6건

- KCA 2.28초는 시야 제한 돌발 상황의 조건부 결과로 설명
- `2M/12M`은 2개월 기준선·12개월 평가로 풀어 말함
- 500명·15–20%·+2%p는 실측이 아니라 파일럿 목표
- 대시보드 13%p는 Edward 사례의 연간 시뮬레이션 결과
- OECD 1 in 4는 drivers가 아니라 persons 기준으로 보정
- Appendix D persona row 2는 인쇄 결과와 실제 시뮬레이션 결과를 대조 확인 후 답변

## 3. 구현 차이

- 연간 점수에서 기본 할인율로 연결되는 최종 요율 산식은 데모 엔진에 아직 구현되지 않았다.
- 최종 산식은 파일럿과 계리 검증 대상이다.
- Q&A용 하이브리드 검색 인덱스와 서버 측 답변 생성기는 아직 구현되지 않았다.

## 4. 문헌 캡처 자산화

현재 MKS에는 `allowed_claim`, `deck_location`, `citation_tier`, `capture_available`이 기록돼 있지만 이미지 원본 파일은 없다. Claude 답변 안에서 원문을 보여주려면 다음이 필요하다.

- 캡처 원본 내보내기
- evidence ID·문헌 페이지·덱 사용 위치 연결
- 안정적인 asset path 또는 URL
- 캡처가 없는 근거를 이미지가 있는 것처럼 반환하지 않는 검증

## 5. FastMCP 구현 전 승인 게이트

- 현재 브랜치 diff 사람 검토
- 검색 우선순위와 P0-01~15 확인
- 문헌 캡처 저장 위치 결정
- 서버 측 OpenAI API 사용 정책·키 관리 결정
- 승인 후에만 로컬 HTTP MCP와 검색 인덱스 구현

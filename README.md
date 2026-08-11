# MASIL Knowledge Studio

MASIL의 8분 Q&A 준비를 위해 문제정의, 상품 설계, 기술, 근거, 사회적 가치와 실행 가능성을 관리하는 워크스페이스다. 발표 대본 작성은 별도 작업이며 MCP의 기본 목적이 아니다.

지식 정합성 검토를 통과한 현재 정본을 FastMCP 서버로 제공한다. 서버는 답변을 고정해 대신 말하는 도구가 아니라, Claude가 심사 질문에 맞는 현재 사실·덱 문구·근거·구현 상태·주의점을 짧게 가져오도록 돕는 Q&A 재료 계층이다. 팀원은 도구 이름을 외우지 않고 평소처럼 질문하거나 Q&A 초안을 붙여 넣으면 된다.

## 네 개의 지식층

1. `knowledge/presentation_story.yaml` — 문제정의부터 마무리까지 발표 전체 논리
2. `knowledge/product_model.yaml` — 생활권·점수·Care·할인·AI·프라이버시·검증·사업을 포함한 전체 상품 모델
3. `knowledge/evidence/registry.yaml`과 `knowledge/claims/deck_claims.yaml` — 문헌 근거와 최종 덱 인쇄 사실
4. `knowledge/conflict_map.yaml`과 `knowledge/history/decision_log.yaml` — 현재 설명과 과거 설계의 충돌·변경 이유

`knowledge/coverage_matrix.yaml`은 영역별 완성도와 미확정 항목을 기록한다.
`IMPLEMENTATION.md`는 2026-08-10 현재 실행 화면에서 실제로 확인한 월 점수·Care·연간 표시점수·할인 계산을 사람이 읽기 쉽게 설명한다.

## 질문 유형별 정본

하나의 전역 우선순위를 두지 않는다.

- 장표에 무엇이 적혔는가 → `deck_claims.yaml`
- 현재 상품 논리는 무엇인가 → `product_model.yaml`
- 수치와 시뮬레이션 결과는 무엇인가 → `key_numbers.yaml`
- 문헌이 무엇을 지지하는가 → `evidence/registry.yaml`
- 왜 설계가 바뀌었는가 → `conflict_map.yaml`과 `decision_log.yaml`
- 발표에서 어떻게 쉽게 말하는가 → `glossary.yaml`과 active Q&A 표현 예시
- 현재 화면이 실제로 어떻게 계산하는가 → `IMPLEMENTATION.md`

과거 Q&A와 승인 정리문서는 자동 보조 검색 재료지만 현재 사실을 단독 확정하지 않는다. 충돌은 삭제하지 않고 현재 결론, 과거 표현, 변경 이유와 피해야 할 문장으로 나눈다.

## MCP 서버

공개 엔드포인트는 `https://masil-mcp.summit1123.co.kr/mcp`다. 팀 커넥터는 OAuth 2.0 Authorization Code + PKCE와 고정 confidential client를 사용한다. 로컬 개발에서는 인증 없음 또는 정적 Bearer 토큰 모드를 선택할 수 있다.

Claude가 내부적으로 사용하는 도구:

- `connector_guide` — 팀원에게 명령어가 아니라 평범한 질문 예시로 사용법 안내
- `search_knowledge` — 제목·태그·메타데이터·본문을 따로 가중한 BM25F형 검색, 한국어 문자 n-gram, 한영 고정 용어 별칭
- `prepare_topic_brief` — 한 주제의 현재 입장·근거·주장 경계·미검증 범위·쉬운 표현 재료. 예상 질문은 만들지 않음
- `prepare_answer_context` — 일반 MASIL 질문과 붙여 넣은 초안의 기본 진입점. 별도 AI 호출 없이 질문을 8개 준비 유형으로 가볍게 라우팅하고, 현재 사실에서 정확한 문헌·캡처 링크를 순회해 짧은 답변 재료를 만듦
- `show_answer_evidence` — 답변 재료에 정확히 연결된 캡처가 있을 때 별도 요청 없이 최대 2개를 대화 안의 증거 카드로 표시
- `explain_product_logic` — 생활권, 점수, Care, 할인 등 상품 논리
- `get_slide_context` — 9장 덱의 인쇄 사실과 구두 보완점
- `get_evidence` — Summary·Appendix에서 실제 사용하는 문헌의 주장, 한계, 원문/덱 캡처 연결
- `get_implementation` — 현재 외부 데모와 목표 상품 규칙의 차이
- `compare_claims` — 붙여 넣은 주장과 현재 덱·상품 계약의 정합성 확인
- `list_open_items` — 미확정·파일럿 가설·후보 파라미터를 상태별 정확한 총계와 함께 조회
- `list_captures`, `show_evidence_capture`, `get_capture_image` — active Summary·Appendix 캡처의 정확한 연결 조회와 이미지 반환. 실제 원문 캡처가 없으면 덱 이미지로 대체하지 않으며, 이미지 도구는 MCP Apps `ui://` 뷰와 공개 Markdown 대체 경로를 함께 제공
- `knowledge_status` — 코퍼스·자산·권한 상태
- `usage_telemetry` — 질문·답변 원문 없이 도구별 호출·성공률·지연시간·선택된 준비 유형·캡처 표시량을 집계
- `record_usage_feedback` — 팀원이 명시적으로 평가했을 때만 고정 태그로 도움 여부를 기록

서버는 최종 덱, 현재 상품 계약, 현재 용어·미확정 항목, Summary·Appendix에서 실제 사용하는 문헌과 active 캡처만 팀 런타임에 제공한다. 주장과 문헌은 명시적인 `evidence_links`로만 연결하며, provenance용 `source_refs`, `material_refs`, `evidence_ref`를 직접 근거로 오인하지 않는다. 과거 Q&A, Master Q&A 원문, 폐기된 규칙과 변경 이력은 Git에 보존되지만 공개 검색·답변·이미지 도구에서는 반환하지 않는다.

텔레메트리는 도구명, 라우트, 성공 여부, 지연시간, 결과·캡처 개수와 익명 세션 해시만 로컬 SQLite에 저장한다. 질문, 도구 인자, Claude 답변, 근거 본문, 사용자 신원, OAuth 비밀값은 저장하지 않는다. OAuth access/refresh token은 권한 600의 별도 SQLite 파일에 보존하므로 일반 코드·지식 업데이트 뒤 서버가 재시작되어도 팀원이 커넥터를 다시 등록할 필요가 없다. 도구 목록이 바뀐 배포 직후 현재 대화가 예전 목록을 캐시했다면 새 대화만 열면 된다.

`forbidden_claims`와 `must_not_say`는 예상 질문 목록이 아니라 과장을 막는 주장 경계다. 서버는 이를 자동으로 질문으로 바꾸지 않는다. 예상 질문은 팀원이 명시적으로 요청할 때만 Claude가 별도로 만들며, 저장된 사실과 구분한다.

## 실행

```bash
uv sync
cp .env.example .env
.venv/bin/masil-mcp
```

로컬 상태 확인은 `http://127.0.0.1:8000/healthz`, MCP 경로는 `/mcp`다. 실제 운영 환경 변수와 OAuth 비밀값은 Git에서 제외된 `.env`에만 둔다.

## 아직 완료되지 않은 상품 검증

- 문제정의와 사회적 가치 중 현재 사실·파일럿 가설·장기 기대효과의 최종 구분
- 공정성·디지털 접근성·가입 선택편의 검증 계획
- 개인정보 보관·철회·가족 공유와 싱가포르·EU 이식 법무 설계
- Care 담당자·인력·비용·통보·거부권·이의제기·책임의 실제 운영 절차
- 시장 규모·채널·경쟁·차별성·팀·파트너·파일럿 측정 설계
- 계절성·다중거주·드리프트·재보정과 실제 코드 기반 검증
- 현재 구현 checkout을 재현 가능한 커밋·배포 산출물로 고정
- Favorable 후보 `+3%p`와 전체 `45%` 상한의 계리·파일럿 검증
- 발표 직전 대본 수정본과 수정 예정 PPT/PDF의 최종 버전 동기화

남은 항목 15개와 각 항목에서 지금 말할 수 있는 범위는 `OPEN_ITEMS.md`에 표로 정리했다.

이 항목들은 서버 구현을 막는 게이트가 아니라, 답변에서 확정 사실과 계획·가설을 분리하기 위한 공개 미확정 목록이다. 서버 자체는 OpenAI API를 호출하지 않는다. 답변 문장 생성과 다듬기는 커넥터를 호출한 Claude가 담당한다.

## 검증

```bash
ruby knowledge/scripts/verify_knowledge.rb
.venv/bin/pytest
.venv/bin/python scripts/check_mcp.py http://127.0.0.1:8000/mcp
.venv/bin/python scripts/check_oauth.py https://masil-mcp.summit1123.co.kr
```

지식 검증기는 YAML, ID, 덱 64개 claim, P0 15개, 전체 상품 영역, 발표 서사, 충돌 지도, 권한 라우팅과 이미지 자산을 확인한다. MCP 검사는 실제 초기화, 도구 목록, 한영 검색 회귀, 답변 재료, OAuth, 다중 이미지 반환, `text/html;profile=mcp-app` 증거 뷰까지 수행한다. 배포 운영 정보는 `DEPLOYMENT.md`를 참고한다.

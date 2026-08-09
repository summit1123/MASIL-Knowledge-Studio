# MASIL 지식 커버리지 — 현재 검토판

이 문서는 서버 구현 전, 발표 전체를 설명할 재료가 준비됐는지 보는 진입점입니다.
산식과 월별 등급만 확인하지 않고 문제정의·사회적 가치·운영·사업·규제·근거·한계를 함께 봅니다.

## 현재 구조

- `knowledge/product_model.yaml`: 15개 영역의 현재 사실·가설·미확정 사항
- `knowledge/presentation_story.yaml`: 문제정의부터 마무리까지 14개 설명 흐름
- `knowledge/conflict_map.yaml`: 자료끼리 충돌하는 지점과 현재 해석
- `knowledge/coverage_matrix.yaml`: 영역별 준비도와 남은 빈칸
- `IMPLEMENTATION.md`: 현재 GaipStudio 작업 파일에서 확인한 점수·Care·할인 계산
- `OPEN_ITEMS.md`: 남은 18개 항목의 검증 수준·권고 표현·필요한 검증
- `knowledge/history/coverage_probe_2026-08-04.md`: 과거 72문항 진단 원문. 현재 사실의 정본은 아니지만 빠진 질문을 찾는 보조 자료

## 현재 판단

- 서버 구현: **보류**
- 이유: 전체 상품 모델과 미확정 경계를 사람이 먼저 검토해야 함
- 현재 구현은 확인했지만 외부 dirty working tree이므로 재현 가능한 커밋 고정이 필요함
- 특히 비어 있는 축: 현지 규제, 공정성 검증, 시장·경쟁·채널, Care 운영 인력·비용·책임, 파일럿 설계, 팀·파트너, 문헌 캡처·Master Q&A의 로컬 자산화

과거 진단은 버리지 않습니다. 검색 시 질문을 넓히고 누락을 찾는 재료로 사용하되, 현재 결론은 `knowledge/product_model.yaml`과 질문 유형별 권한 자료가 정합니다.

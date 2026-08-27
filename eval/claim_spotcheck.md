# Claim 추출 정확도 스팟체크 절차 (부록 A 작업 5)

목표: 정확도 90% 이상 (기획서 Phase 1 exit criteria)

1. `make enrich` 완료 후, 무작위 문서 10건 선정:
   `sqlite3 data/pipeline.db "SELECT id,title FROM documents WHERE status='enriched' ORDER BY RANDOM() LIMIT 10"`
2. 각 문서의 원문(data/raw/...)과 추출 claim을 대조:
   `sqlite3 data/pipeline.db "SELECT claim_text, stance, metric FROM claims WHERE document_id='<ID>'"`
3. 판정 기준 (claim당 O/X):
   - 원문에 실제로 있는 주장인가 (날조 아님)
   - 자체 문장으로 재작성되었는가 (원문 복사 아님)
   - metric 수치가 원문과 정확히 일치하는가
   - stance/evidence_type 분류가 타당한가
4. 기록: `eval/spotcheck-YYYY-MM-DD.md`에 문서별 O/X와 실패 유형
5. 90% 미만 시: 실패 유형별로 prompts/claim_extraction.md 규칙 보강 → 동일 10건 재실행 비교

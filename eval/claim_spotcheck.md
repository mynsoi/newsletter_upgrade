# Claim 추출 정확도 스팟체크 절차 (부록 A 작업 5)

목표: 정확도 90% 이상 (기획서 Phase 1 exit criteria)

DB 접속: 운영은 PostgreSQL(`psql "$DATABASE_URL"`), 로컬 테스트는 `sqlite3 data/pipeline.db`.
아래 예시는 PostgreSQL 기준. `RANDOM()` 은 SQLite도 동일, PostgreSQL은 `RANDOM()` 그대로 사용 가능.

1. `make enrich` 완료 후, 무작위 문서 10건 선정:
   `psql "$DATABASE_URL" -c "SELECT id,title FROM documents WHERE status='enriched' ORDER BY RANDOM() LIMIT 10"`
2. 각 문서의 원문(`documents.body` 컬럼)과 추출 claim을 대조:
   `psql "$DATABASE_URL" -c "SELECT body FROM documents WHERE id='<ID>'"`
   `psql "$DATABASE_URL" -c "SELECT claim_text, stance, metric FROM claims WHERE document_id='<ID>'"`
3. 판정 기준 (claim당 O/X):
   - 원문에 실제로 있는 주장인가 (날조 아님)
   - 자체 문장으로 재작성되었는가 (원문 복사 아님)
   - metric 수치가 원문과 정확히 일치하는가
   - stance/evidence_type 분류가 타당한가
4. 기록: `eval/spotcheck-YYYY-MM-DD.md`에 문서별 O/X와 실패 유형
5. 90% 미만 시: 실패 유형별로 prompts/claim_extraction.md 규칙 보강 → 동일 10건 재실행 비교

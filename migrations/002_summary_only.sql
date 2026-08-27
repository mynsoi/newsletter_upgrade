-- 002_summary_only.sql — A3 수집 게이트: 본문 800자 미만 문서 표시
-- summary_only=1 문서는 claim 추출(enrich) 대상에서 제외된다 (docs/phase1-plan.md β4·β5).
ALTER TABLE documents ADD COLUMN summary_only INTEGER DEFAULT 0;

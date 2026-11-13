-- 007_drop_documents_trgm.sql — documents의 트라이그램 GIN 인덱스 2개 제거 (−84MB)
--
-- 배경: Supabase 무료 등급 500MB 중 326MB를 쓰고 있고 일 증가가 12.6MB다.
-- 사용량을 뜯어보니 idx_documents_body_trgm(72MB)은 21일간 scan 9회, tup_fetch 0이었고
-- 그 9회조차 앱 코드가 아니라 임시 질의였다.
--
-- 근본 원인: documents 전문검색의 유일한 경로인 search_documents(q)가
--   WHERE COALESCE(title,'') ILIKE … OR COALESCE(body,'') ILIKE …
-- 형태라, 맨 컬럼에 걸린 트라이그램 인덱스와 표현식이 달라 플래너가 후보로 올리지 못한다.
-- 실행 계획은 항상 Seq Scan이고, 인덱스를 끄고 재봐도 868ms → 860ms로 차이가 없었다.
-- 게다가 search_documents 자체가 src/ 운영 코드·슬래시 커맨드·워크플로 어디서도
-- 호출되지 않는다(유일한 호출부인 tests/test_pipeline.py는 SQLite 모드라 이 인덱스를
-- 건드리지 않는다).
--
-- 유지: idx_claims_text_trgm — search_claims와 semantic.py keyword_search가 맨
-- claim_text ILIKE를 쓰므로 실제로 Bitmap Index Scan을 탄다(/draft 증거 수집 경로).
-- 유지: idx_internal_*_trgm — 합계 2.6MB로 절감 대상이 아니다.
--
-- 되돌리기: 문서 전문검색이 실제로 필요해지면 아래 두 줄을 새 마이그레이션으로 다시 만들고,
-- 그때는 search_documents의 COALESCE를 함께 걷어내야 인덱스가 실제로 쓰인다.
--   CREATE INDEX idx_documents_title_trgm ON documents USING gin (title gin_trgm_ops);
--   CREATE INDEX idx_documents_body_trgm  ON documents USING gin (body  gin_trgm_ops);
--
-- PostgreSQL 전용. SQLite 모드에는 이 인덱스가 없다(001의 트라이그램 블록도 +postgres).

-- +postgres
DROP INDEX IF EXISTS idx_documents_body_trgm;
DROP INDEX IF EXISTS idx_documents_title_trgm;
-- +end

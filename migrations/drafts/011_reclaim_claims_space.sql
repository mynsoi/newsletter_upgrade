-- 011_reclaim_claims_space.sql — claims 표 용량 회수 (초안 · 사람이 직접 실행)
--
-- ⚠ 이 파일은 자동 적용되지 않는다. db.migrate()는 migrations/*.sql만 읽고(하위 폴더 제외),
--   일일 워크플로(collect.yml의 make init)가 그것을 매일 운영 DB에 적용한다. 이 초안을
--   migrations/ 바로 아래로 옮기면 다음 날 06:00 KST에 운영 DB에서 실행된다 — 옮기지 말 것.
--   실행 순서·확인 쿼리·되돌리기는 같은 폴더의 README.md를 따른다.
--
-- 배경: 2026-11-10 claim 추출·claim 임베딩을 없앴다(src/enrich/relevance.py, src/search/embed.py).
-- 칼럼 작업실은 claims를 읽지 않는다. 11/10 실측 DB 391MB 중 claims가 174MB
-- (표 77MB · idx_claims_embedding_hnsw 72MB · idx_claims_text_trgm 21MB · 기타 인덱스 4MB).
--
-- PostgreSQL(Supabase) 전용. SQL Editor에서 단계별로 나눠 실행한다.

-- ── 1단계: 벡터·검색 인덱스 제거 (되돌리기 쉬움 · 즉시 약 93MB 회수) ─────────────────
-- 인덱스는 DROP 즉시 파일이 지워진다. 열 삭제분(벡터 약 55MB)은 3단계 VACUUM FULL 뒤에 돌아온다.
BEGIN;
DROP INDEX IF EXISTS idx_claims_embedding_hnsw;
DROP INDEX IF EXISTS idx_claims_text_trgm;
DROP FUNCTION IF EXISTS search_claims(text);
ALTER TABLE claims DROP COLUMN IF EXISTS embedding;
COMMIT;

-- ── 2단계 (선택): 인용 원장이 가리키지 않는 claim 행 삭제 ─────────────────────────────
-- article_sources.claim_id → claims(id) FK가 있어 원장이 가리키는 행(11/10 기준 23행이
-- 가리키는 18건, 「ai-productivity-paradox」)은 남긴다. 발행본 2편이 인용한 claim의 문장은
-- content/evidence/{slug}.json에 사본이 있다(README.md "발행본 인용" 참고).
-- 이론 카드 claim(source_id='theory-canon', 629건)도 같이 지워진다 — 카드 원본은
-- knowledge/theories/ 파일이고 색인 스크립트(load_theories.py)는 지웠다.
-- BEGIN;
-- DELETE FROM claims c
--  WHERE NOT EXISTS (SELECT 1 FROM article_sources s WHERE s.claim_id = c.id);
-- COMMIT;

-- ── 3단계: 표 다시 쓰기 (트랜잭션 밖에서 단독 실행) ─────────────────────────────────
-- DROP COLUMN과 DELETE는 공간을 표 안의 빈자리로만 돌려준다. 파일 크기를 줄이려면
-- VACUUM FULL로 표를 새로 써야 한다. 실행 중 claims에 ACCESS EXCLUSIVE 잠금이 걸린다
-- (11/10 이후 claims를 읽거나 쓰는 코드는 없다).
-- VACUUM (FULL, ANALYZE) claims;

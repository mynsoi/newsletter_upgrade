-- 005_claims_embedding.sql — A6 의미 기반 검색: claims.embedding을 pgvector로 전환
-- 001_init.sql의 embedding BYTEA 컬럼은 "Phase 1에서 채움" 예정이었으나 미사용으로
-- 남아 있었다(Phase 1 종료 시점 실사용 데이터 0건) — 안전하게 vector(1536)으로 교체한다.
-- PostgreSQL 전용. SQLite 모드는 이 컬럼과 의미 검색을 건너뛰고 키워드 검색만 지원한다
-- (src/search/semantic.py의 폴백 — make test는 네트워크·pgvector 없이 통과해야 함).

-- +postgres
CREATE EXTENSION IF NOT EXISTS vector;

ALTER TABLE claims DROP COLUMN IF EXISTS embedding;
ALTER TABLE claims ADD COLUMN embedding vector(1536);

-- HNSW + 코사인 거리(<=>) — text-embedding-3-small은 코사인 유사도 기준으로 학습된 모델.
CREATE INDEX IF NOT EXISTS idx_claims_embedding_hnsw
  ON claims USING hnsw (embedding vector_cosine_ops);
-- +end

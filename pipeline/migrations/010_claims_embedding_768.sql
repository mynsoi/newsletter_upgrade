-- 010_claims_embedding_768.sql — claims.embedding을 halfvec(768)로 줄인다
-- 배경: 2026-10-28 DB 461MB(무료 한도 500MB의 92%). claims가 275MB(임베딩 30,368개, HNSW 포함)로 가장 크다.
-- text-embedding-3-small의 dimensions 요청은 앞부분 절단 + 재정규화와 같고 코사인은 배율에
-- 무관하므로, 저장된 1536차원 값의 앞 768차원(subvector)은 768차원으로 새로 받은 값과 순위가 같다
-- — API 재호출 없이 제자리 전환한다. 품질: 2026-09-10 leave-one-out 측정에서 상위 10건 일치율
-- 0.82(무작위 25질의) / 0.89(핵심 근거 claim 8건). 전환 전후 동의어 리콜 3질의(scripts/semantic_recall_check.py)로 확인.
-- 토픽 군집(discover.py)은 앞 256차원만 쓰므로 영향 없다. 카드(document_card_embeddings)는 1536 그대로.
-- 운영 DB에는 세션 풀러(5432)로 직접 적용하고 schema_migrations에 기록했다 — 트랜잭션 풀러(6543)는
-- statement_timeout 2분이라 HNSW 재생성이 끊길 수 있다.

-- +postgres
-- 006과 같은 순서 — 인덱스를 먼저 내려 테이블 재작성 동안 순간 용량을 낮춘다.
DROP INDEX IF EXISTS idx_claims_embedding_hnsw;

ALTER TABLE claims
  ALTER COLUMN embedding TYPE halfvec(768) USING subvector(embedding, 1, 768)::halfvec(768);

CREATE INDEX IF NOT EXISTS idx_claims_embedding_hnsw
  ON claims USING hnsw (embedding halfvec_cosine_ops);
-- +end

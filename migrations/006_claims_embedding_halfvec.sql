-- 006_claims_embedding_halfvec.sql — claims.embedding을 halfvec(1536)으로 전환
-- 배경: A6(005) 이후 claims 테이블이 315MB로 불어 DB 총 용량이 478MB가 됐다.
-- 내역은 embedding 값 TOAST 150MB + HNSW 인덱스 148MB — 둘 다 4바이트 float 기준이다.
-- halfvec은 2바이트 반정밀도로 같은 1536차원을 담아 저장·인덱스를 각각 절반으로 줄인다.
-- text-embedding-3-small의 값 범위(대략 -1~1)에서 fp16의 유효 정밀도는 약 3자리로,
-- 코사인 상위 k 정렬에는 영향이 없다(전환 후 동의어 리콜 3질의 재실행으로 확인 —
-- eval/semantic-search-synonym-recall-2026-09.md).
-- PostgreSQL 전용. SQLite 모드는 이 컬럼과 의미 검색을 건너뛴다(005와 동일).
-- pgvector 0.7.0+ 필요 (halfvec 도입 버전, 운영 DB는 0.8.2).

-- +postgres
-- 인덱스를 먼저 떨어뜨린다 — vector_cosine_ops는 halfvec을 받지 못해
-- ALTER TYPE이 인덱스 재작성 단계에서 실패한다. 또 살아 있는 인덱스를 끌고
-- 테이블을 다시 쓰는 것보다 지우고 새로 만드는 편이 빠르다.
DROP INDEX IF EXISTS idx_claims_embedding_hnsw;

ALTER TABLE claims
  ALTER COLUMN embedding TYPE halfvec(1536) USING embedding::halfvec(1536);

CREATE INDEX IF NOT EXISTS idx_claims_embedding_hnsw
  ON claims USING hnsw (embedding halfvec_cosine_ops);
-- +end

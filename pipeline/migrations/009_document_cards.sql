-- 009_document_cards.sql — 문서 카드 (2026-10-21 카드 비교 시험 → main 자동 생성)
--
-- 배경: 칼럼 작업실이 주제를 뽑고 원문을 찾을 때 claim보다 문서 단위 '카드'가 낫다는 시험 결과
-- (게이트 통과 원문 40편, 방식을 가린 평가 — Sonnet 5.5 카드 1위, 숫자·영문 이름 원문 일치 94~100%).
-- claim 추출은 그대로 두고 카드를 덧붙인다. 카드 = 글쓴이가 하는 말(thesis) + 있었던 일 0~4개
-- (episodes) + 재료 유형. 생성은 src/enrich/doc_cards.py, 프롬프트는 prompts/doc_card.md.
-- 작업실은 이 표를 읽기만 한다(주제 묶기는 작업실 쪽).
--
-- document_card_embeddings: 핵심 주장 1개 + 사례별 각각을 claims와 같은 모델·차원
-- (text-embedding-3-small, 1536, halfvec — migrations/006)으로 저장. PostgreSQL 전용 —
-- SQLite 모드는 벡터 표를 만들지 않는다(005와 같은 이유: make test는 pgvector 없이 통과해야 함).

-- +postgres
CREATE TABLE IF NOT EXISTS document_cards (
  document_id    TEXT PRIMARY KEY REFERENCES documents(id),
  thesis         TEXT NOT NULL,
  episodes       JSONB NOT NULL DEFAULT '[]'::jsonb,   -- 문자열 배열 0~4개
  material_type  TEXT CHECK (material_type IN ('사례형','데이터형','의견형','재료 없음')),
  model          TEXT,
  prompt_version TEXT,                                 -- prompts/doc_card.md 본문 해시 앞 12자
  created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS document_card_embeddings (
  document_id TEXT NOT NULL REFERENCES document_cards(document_id),
  part        TEXT NOT NULL,                           -- 'thesis' | 'episode:1' ~ 'episode:4'
  embedding   halfvec(1536) NOT NULL,
  PRIMARY KEY (document_id, part)
);

CREATE INDEX IF NOT EXISTS idx_document_card_embeddings_hnsw
  ON document_card_embeddings USING hnsw (embedding halfvec_cosine_ops);
-- +end

-- +sqlite
CREATE TABLE IF NOT EXISTS document_cards (
  document_id    TEXT PRIMARY KEY REFERENCES documents(id),
  thesis         TEXT NOT NULL,
  episodes       TEXT NOT NULL DEFAULT '[]',           -- JSON 문자열
  material_type  TEXT CHECK (material_type IN ('사례형','데이터형','의견형','재료 없음')),
  model          TEXT,
  prompt_version TEXT,
  created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- +end

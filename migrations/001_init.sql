-- 001_init.sql — 기획서 5장 스키마
-- 실행: make init (이미 적용된 마이그레이션은 건너뜀)

CREATE TABLE IF NOT EXISTS schema_migrations (
  filename    TEXT PRIMARY KEY,
  applied_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 원본 문서
CREATE TABLE IF NOT EXISTS documents (
  id            TEXT PRIMARY KEY,
  source_id     TEXT NOT NULL,
  tier          TEXT NOT NULL CHECK (tier IN ('T1','T2','T3','T4','T5')),
  url           TEXT UNIQUE,
  canonical_url TEXT,
  title         TEXT,
  author        TEXT,
  published_at  DATE,
  collected_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
  lang          TEXT,
  raw_path      TEXT,
  content_hash  TEXT,
  quality_score REAL,
  status        TEXT DEFAULT 'new'
                CHECK (status IN ('new','enriched','rejected','used'))
);
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
CREATE INDEX IF NOT EXISTS idx_documents_hash   ON documents(content_hash);

-- 전문 검색 (제목 + 본문 요지)
CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
  id UNINDEXED, title, body
);

-- 문서에서 추출한 개별 주장 (인사이트 생성의 재료)
CREATE TABLE IF NOT EXISTS claims (
  id            TEXT PRIMARY KEY,
  document_id   TEXT NOT NULL REFERENCES documents(id),
  claim_text    TEXT NOT NULL,          -- 자체 문장으로 재작성된 주장
  evidence_type TEXT CHECK (evidence_type IN
                  ('survey','experiment','case','opinion','theory','data')),
  stance        TEXT CHECK (stance IN
                  ('optimistic','cautious','conditional','neutral')),
  metric        TEXT,                   -- 수치 근거 원문 표기 (있으면)
  confidence    REAL,
  embedding     BLOB                    -- Phase 1에서 채움
);
CREATE INDEX IF NOT EXISTS idx_claims_doc    ON claims(document_id);
CREATE INDEX IF NOT EXISTS idx_claims_stance ON claims(stance);

CREATE VIRTUAL TABLE IF NOT EXISTS claims_fts USING fts5(
  id UNINDEXED, claim_text
);

-- 다축 태깅
CREATE TABLE IF NOT EXISTS tags (
  document_id TEXT NOT NULL REFERENCES documents(id),
  axis        TEXT NOT NULL,            -- topic|content_type|stance|maturity|layer|region|tier
  value       TEXT NOT NULL,
  PRIMARY KEY (document_id, axis, value)
);

-- 내부 자료 (SKMS·경영층 메시지 등)
CREATE TABLE IF NOT EXISTS internal_docs (
  id             TEXT PRIMARY KEY,      -- 파일 상대경로
  path           TEXT NOT NULL,
  title          TEXT,
  type           TEXT,                  -- skms|leadership-message|policy
  speaker        TEXT,                  -- 실명·직책 (확정 사항)
  security       TEXT NOT NULL CHECK (security IN ('A','B')),  -- C는 색인 자체 거부
  effective_date DATE,
  superseded_by  TEXT,
  content_hash   TEXT,
  api_eligible   INTEGER DEFAULT 0,     -- 1이면 외부 LLM API 전송 가능 (A등급 또는 B승인 후)
  indexed_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
  embedding      BLOB
);

CREATE VIRTUAL TABLE IF NOT EXISTS internal_fts USING fts5(
  id UNINDEXED, title, body
);

-- 생성 아티클
CREATE TABLE IF NOT EXISTS articles (
  id           TEXT PRIMARY KEY,
  slug         TEXT UNIQUE,
  title        TEXT,
  angle        TEXT,
  status       TEXT DEFAULT 'draft'
               CHECK (status IN ('draft','review','approved','published','rejected')),
  created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
  published_at DATETIME,
  rubric_score REAL,
  reject_code  TEXT                     -- 부록 B 코드 (R-01 ~ R-08)
);

-- 아티클-근거 추적 (검증 게이트가 검사하는 테이블)
CREATE TABLE IF NOT EXISTS article_sources (
  article_id    TEXT NOT NULL REFERENCES articles(id),
  claim_id      TEXT NOT NULL REFERENCES claims(id),
  paragraph_ref TEXT,
  role          TEXT CHECK (role IN ('support','counter','context')),
  PRIMARY KEY (article_id, claim_id, paragraph_ref)
);

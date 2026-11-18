-- 012_reference_files.sql — 작업실 참고 원문 보관 (2026-11-18)
--
-- 배경: 「유정식의 경영일기」 본문(문체·제목 참고)만 git에 올라가 있었다. 저장소가 Public이라 다른 원문처럼
-- git 밖으로 옮긴다 — 원천을 이 표에 두고, 작업실이 받아 sources/ 아래 파일로 내려 둔다(scripts/style_refs.py).
-- 문서(documents)와 섞지 않는다: 주제 재료가 아니라 문체 참고라 관련성 판별·카드·임베딩 대상이 아니다.
-- path는 저장소의 sources/ 기준 상대 경로(예: originals/infuture/p497.md), body는 파일 내용 그대로.
--
-- Supabase는 public 스키마의 새 표에 anon·authenticated 권한을 기본으로 준다(REST로 읽힌다).
-- 이 표는 직접 연결(DATABASE_URL)로만 쓰므로 그 권한을 걷고 RLS를 켠다(정책 없음 = REST로는 아무것도 안 보임).
-- 표 주인(postgres)은 RLS를 받지 않아 수집 묶음·작업실의 직접 연결은 그대로 읽고 쓴다.

-- +postgres
CREATE TABLE IF NOT EXISTS reference_files (
  path        TEXT PRIMARY KEY,
  collection  TEXT NOT NULL,                 -- 묶음 이름(예: 'infuture')
  body        TEXT NOT NULL,
  sha256      TEXT NOT NULL,
  updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_reference_files_collection ON reference_files (collection);
ALTER TABLE reference_files ENABLE ROW LEVEL SECURITY;
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
    REVOKE ALL ON TABLE reference_files FROM anon;
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
    REVOKE ALL ON TABLE reference_files FROM authenticated;
  END IF;
END $$;
-- +end

-- +sqlite
CREATE TABLE IF NOT EXISTS reference_files (
  path        TEXT PRIMARY KEY,
  collection  TEXT NOT NULL,
  body        TEXT NOT NULL,
  sha256      TEXT NOT NULL,
  updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_reference_files_collection ON reference_files (collection);
-- +end

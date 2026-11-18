-- 013_lock_public_tables.sql — 웹 주소(REST)로는 표가 보이지 않게 (2026-11-19)
--
-- 배경: Supabase는 public 스키마의 표에 anon·authenticated 역할의 모든 권한을 기본으로 주고, 행 단위 보안(RLS)은
-- 꺼 둔다. 그래서 프로젝트 주소와 익명 키를 아는 사람은 로그인 없이 원문(documents)·사내 자료(internal_docs)·카드를
-- 읽고 고치고 지울 수 있었다(2026-11-19 확인: 익명 역할로 사내 자료 31건·원문 41,442건이 보였다).
-- 수집 묶음과 작업실은 직접 연결(DATABASE_URL, 표 주인 postgres)만 쓴다 — 웹 주소를 쓰는 곳이 없다.
--
-- 하는 일(public 스키마의 모든 표):
--   1. RLS를 켠다. 정책을 하나도 두지 않으므로 anon·authenticated에게는 아무 행도 보이지 않는다.
--   2. anon·authenticated의 표·시퀀스 권한을 걷는다(이중으로 막음).
--   3. 앞으로 만드는 표·시퀀스에도 그 권한이 자동으로 붙지 않게 기본 권한을 걷는다.
-- 표 주인(postgres)과 service_role은 RLS를 받지 않아 직접 연결·대시보드는 그대로다. 데이터는 건드리지 않는다.
-- 새 표를 만드는 마이그레이션은 앞으로도 ENABLE ROW LEVEL SECURITY를 함께 적는다(012처럼) — RLS는 표마다 켜야 한다.
--
-- 되돌리기(웹 주소로 다시 열어야 할 때, 표마다):
--   ALTER TABLE <표> DISABLE ROW LEVEL SECURITY;  GRANT ALL ON TABLE <표> TO anon, authenticated;
-- SQLite(테스트용 로컬 모드)에는 역할·RLS가 없어 할 일이 없다.

-- +postgres
DO $$
DECLARE
  t record;
  r text;
BEGIN
  FOR t IN SELECT c.oid::regclass AS name, c.relkind
           FROM pg_class c
           WHERE c.relnamespace = 'public'::regnamespace AND c.relkind IN ('r', 'p', 'S')
  LOOP
    IF t.relkind IN ('r', 'p') THEN
      EXECUTE format('ALTER TABLE %s ENABLE ROW LEVEL SECURITY', t.name);
    END IF;
    FOREACH r IN ARRAY ARRAY['anon', 'authenticated'] LOOP
      IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
        EXECUTE format('REVOKE ALL ON %s FROM %I', t.name, r);
      END IF;
    END LOOP;
  END LOOP;

  FOREACH r IN ARRAY ARRAY['anon', 'authenticated'] LOOP
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
      EXECUTE format('ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM %I', r);
      EXECUTE format('ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON SEQUENCES FROM %I', r);
    END IF;
  END LOOP;
END $$;
-- +end

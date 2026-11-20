-- 014_site_reader.sql — 발행 사이트의 조회수·좋아요 (2026-11-20)
--
-- 배경: 발행 사이트(site/, Vercel 정적 페이지)에 조회수와 좋아요를 붙인다. 독자는 로그인하지 않으므로
-- '같은 사람'이 아니라 '같은 브라우저' 기준이다(브라우저에 둔 무작위 방문자 값) — 수치는 근사치다.
-- IP·이름은 저장하지 않는다.
--
-- 길: 발행 페이지(web/reader.js) → Vercel 함수(api/reader.py) → 아래 함수 3개(웹 주소 /rest/v1/rpc/…).
-- 표는 013처럼 잠근 채 두고(RLS 켬·정책 없음·anon 권한 없음), 익명 역할에는 함수 3개의 실행 권한만 준다.
-- 함수는 SECURITY DEFINER라 표 주인 권한으로 돌지만, 하는 일이 '조회 +1 · 좋아요 켜고 끄기 · 수치 읽기'뿐이고
-- site_articles에 live로 올라 있는 글만 받는다. 익명 키가 새어도 할 수 있는 일은 그 셋이다.
--
--   site_articles     발행된 글 목록 — 작업실이 발행·내리기 때 site/와 맞춘다(scripts/reader_stats.py sync).
--                     내린 글은 지우지 않고 live=false(수치는 남는다 — 다시 발행하면 이어진다).
--   site_views_daily  글·날짜(KST)별 조회수. 합계 = 총 조회수.
--   site_likes        글·방문자별 한 줄 = 좋아요 1(다시 누르면 줄을 지운다).
--
-- 작업실은 직접 연결(DATABASE_URL, 표 주인)로 표를 바로 읽는다.
-- SQLite(테스트용 로컬 모드)에는 역할·RPC가 없어 만들지 않는다.

-- +postgres
CREATE TABLE IF NOT EXISTS site_articles (
  article_id   TEXT PRIMARY KEY,
  title        TEXT NOT NULL DEFAULT '',
  published_at DATE,
  live         BOOLEAN NOT NULL DEFAULT TRUE,
  updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS site_views_daily (
  article_id TEXT NOT NULL REFERENCES site_articles(article_id),
  day        DATE NOT NULL,
  views      INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (article_id, day)
);

CREATE TABLE IF NOT EXISTS site_likes (
  article_id TEXT NOT NULL REFERENCES site_articles(article_id),
  visitor    TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (article_id, visitor)
);

ALTER TABLE site_articles    ENABLE ROW LEVEL SECURITY;
ALTER TABLE site_views_daily ENABLE ROW LEVEL SECURITY;
ALTER TABLE site_likes       ENABLE ROW LEVEL SECURITY;

-- 글 하나의 수치(안에서만 쓴다)
CREATE OR REPLACE FUNCTION site_reader_counts(p_article TEXT, p_visitor TEXT)
RETURNS JSON
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
  SELECT json_build_object(
    'views', (SELECT COALESCE(SUM(views), 0) FROM site_views_daily WHERE article_id = p_article),
    'likes', (SELECT COUNT(*) FROM site_likes WHERE article_id = p_article),
    'liked', EXISTS (SELECT 1 FROM site_likes WHERE article_id = p_article AND visitor = p_visitor)
  );
$$;

-- 글을 열었다 — p_view가 참이면 오늘(KST) 조회수 +1. 수치와 이 방문자의 좋아요 여부를 돌려준다.
-- 발행 목록에 없는 글·모양이 다른 방문자 값은 아무것도 하지 않고 NULL.
CREATE OR REPLACE FUNCTION site_reader_hit(p_article TEXT, p_visitor TEXT, p_view BOOLEAN)
RETURNS JSON
LANGUAGE plpgsql SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
BEGIN
  IF p_visitor IS NULL OR p_visitor !~ '^[A-Za-z0-9-]{8,64}$'
     OR NOT EXISTS (SELECT 1 FROM site_articles WHERE article_id = p_article AND live) THEN
    RETURN NULL;
  END IF;
  IF p_view THEN
    INSERT INTO site_views_daily (article_id, day, views)
    VALUES (p_article, (now() AT TIME ZONE 'Asia/Seoul')::date, 1)
    ON CONFLICT (article_id, day) DO UPDATE SET views = site_views_daily.views + 1;
  END IF;
  RETURN site_reader_counts(p_article, p_visitor);
END $$;

-- 좋아요 켜기(p_on 참)·끄기(거짓) — 같은 값을 여러 번 보내도 결과가 같다.
CREATE OR REPLACE FUNCTION site_reader_like(p_article TEXT, p_visitor TEXT, p_on BOOLEAN)
RETURNS JSON
LANGUAGE plpgsql SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
BEGIN
  IF p_visitor IS NULL OR p_visitor !~ '^[A-Za-z0-9-]{8,64}$'
     OR NOT EXISTS (SELECT 1 FROM site_articles WHERE article_id = p_article AND live) THEN
    RETURN NULL;
  END IF;
  IF p_on THEN
    INSERT INTO site_likes (article_id, visitor) VALUES (p_article, p_visitor) ON CONFLICT DO NOTHING;
  ELSE
    DELETE FROM site_likes WHERE article_id = p_article AND visitor = p_visitor;
  END IF;
  RETURN site_reader_counts(p_article, p_visitor);
END $$;

-- 목록 페이지용 — 발행 중인 글 전체의 수치 {"<글>": {"views": n, "likes": n}, …}
CREATE OR REPLACE FUNCTION site_reader_stats()
RETURNS JSON
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
  SELECT COALESCE(json_object_agg(a.article_id, json_build_object(
    'views', (SELECT COALESCE(SUM(v.views), 0) FROM site_views_daily v WHERE v.article_id = a.article_id),
    'likes', (SELECT COUNT(*) FROM site_likes l WHERE l.article_id = a.article_id))), '{}'::json)
  FROM site_articles a WHERE a.live;
$$;

-- 권한: 표는 013과 같이 걷고, 함수는 PUBLIC(기본)에서 걷은 뒤 anon에만 셋을 준다.
DO $$
DECLARE
  r text;
BEGIN
  REVOKE ALL ON FUNCTION site_reader_counts(TEXT, TEXT) FROM PUBLIC;
  REVOKE ALL ON FUNCTION site_reader_hit(TEXT, TEXT, BOOLEAN) FROM PUBLIC;
  REVOKE ALL ON FUNCTION site_reader_like(TEXT, TEXT, BOOLEAN) FROM PUBLIC;
  REVOKE ALL ON FUNCTION site_reader_stats() FROM PUBLIC;
  FOREACH r IN ARRAY ARRAY['anon', 'authenticated'] LOOP
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
      EXECUTE format('REVOKE ALL ON TABLE site_articles, site_views_daily, site_likes FROM %I', r);
      EXECUTE format('REVOKE ALL ON FUNCTION site_reader_counts(TEXT, TEXT) FROM %I', r);
      EXECUTE format('REVOKE ALL ON FUNCTION site_reader_hit(TEXT, TEXT, BOOLEAN) FROM %I', r);
      EXECUTE format('REVOKE ALL ON FUNCTION site_reader_like(TEXT, TEXT, BOOLEAN) FROM %I', r);
      EXECUTE format('REVOKE ALL ON FUNCTION site_reader_stats() FROM %I', r);
    END IF;
  END LOOP;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
    GRANT EXECUTE ON FUNCTION site_reader_hit(TEXT, TEXT, BOOLEAN) TO anon;
    GRANT EXECUTE ON FUNCTION site_reader_like(TEXT, TEXT, BOOLEAN) TO anon;
    GRANT EXECUTE ON FUNCTION site_reader_stats() TO anon;
  END IF;
END $$;

-- 웹 주소(PostgREST)가 새 함수를 바로 알게
NOTIFY pgrst, 'reload schema';
-- +end

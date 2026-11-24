-- 015_site_comments.sql — 발행 사이트의 댓글 (2026-11-24)
--
-- 014(조회수·좋아요)와 같은 길: 발행 페이지(web/reader.js) → Vercel 함수(api/reader.py) → 아래 함수.
-- 표는 잠근 채 두고(RLS 켬·정책 없음·anon 권한 없음) 익명 역할에는 함수 실행 권한만 준다.
-- 독자는 로그인하지 않는다 — 이름은 자유 입력(비우면 '익명'), '내 댓글'은 브라우저의 방문자 값으로만 가린다.
--
--   site_comments   댓글 한 줄. status: visible(보임) · pending(승인 기다림) · hidden(작업실이 숨김) · deleted(쓴 사람이 지움).
--                   숨기거나 지워도 줄은 남긴다. ip_hash는 도배 제한에만 쓰는 값(그날만 쓰는 해시 — IP 자체는 저장하지 않는다).
--   site_settings   사이트 설정. comments = open(바로 공개 · 기본) | moderated(승인 뒤 공개) | closed(새 댓글 받지 않음, 있던 댓글은 보임).
--                   작업실 발행 탭에서 바꾼다(scripts/reader_stats.py).
--
-- 도배 제한(site_comment_add 안): 같은 방문자 30초에 1개 · 글 하나에 1시간 60개 · 같은 ip_hash 1시간 30개
-- (사내망은 모두 같은 IP로 나가므로 IP 제한은 느슨하게). 내용 1~500자, 이름 20자까지, 링크 3개부터 거절.
-- 방문자 값·ip_hash는 부르는 쪽이 주는 값이라 마음먹으면 피해 갈 수 있다 — 막는 장치가 아니라 늦추는 장치다.
--
-- 014의 수치 함수 둘(site_reader_counts · site_reader_stats)은 댓글 수(comments)를 함께 돌려주도록 다시 만든다.
-- SQLite(테스트용 로컬 모드)에는 역할·RPC가 없어 만들지 않는다.

-- +postgres
CREATE TABLE IF NOT EXISTS site_comments (
  id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  article_id TEXT NOT NULL REFERENCES site_articles(article_id),
  visitor    TEXT NOT NULL,
  name       TEXT NOT NULL DEFAULT '익명',
  body       TEXT NOT NULL,
  status     TEXT NOT NULL DEFAULT 'visible' CHECK (status IN ('visible', 'pending', 'hidden', 'deleted')),
  ip_hash    TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_site_comments_article ON site_comments (article_id, id DESC);
CREATE INDEX IF NOT EXISTS idx_site_comments_created ON site_comments (created_at);

CREATE TABLE IF NOT EXISTS site_settings (
  key        TEXT PRIMARY KEY,
  value      TEXT NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE site_comments ENABLE ROW LEVEL SECURITY;
ALTER TABLE site_settings ENABLE ROW LEVEL SECURITY;

-- 댓글 받는 방식(안에서만 쓴다)
CREATE OR REPLACE FUNCTION site_comment_mode()
RETURNS TEXT
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
  SELECT COALESCE((SELECT value FROM site_settings WHERE key = 'comments' AND value IN ('open', 'moderated', 'closed')), 'open');
$$;

-- 댓글 한 줄을 페이지에 줄 모양으로(안에서만 쓴다) — 방문자 값·ip_hash는 내보내지 않는다
CREATE OR REPLACE FUNCTION site_comment_json(c site_comments, p_visitor TEXT)
RETURNS JSON
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
  SELECT json_build_object('id', c.id, 'name', c.name, 'body', c.body, 'at', c.created_at,
                           'mine', c.visitor = p_visitor, 'pending', c.status = 'pending');
$$;

-- 글의 댓글 — 새 것부터 p_limit개(1~50). p_before가 있으면 그 번호보다 앞선 것(더 보기).
-- 보이는 댓글 + 이 방문자가 쓴 승인 대기 댓글. 발행 목록에 없는 글은 NULL.
CREATE OR REPLACE FUNCTION site_comment_list(p_article TEXT, p_visitor TEXT, p_before BIGINT DEFAULT NULL, p_limit INTEGER DEFAULT 20)
RETURNS JSON
LANGUAGE plpgsql STABLE SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  n INTEGER := LEAST(GREATEST(COALESCE(p_limit, 20), 1), 50);
  rows JSON;
  last_id BIGINT;
BEGIN
  IF NOT EXISTS (SELECT 1 FROM site_articles WHERE article_id = p_article AND live) THEN
    RETURN NULL;
  END IF;
  SELECT COALESCE(json_agg(site_comment_json(c, p_visitor) ORDER BY c.id DESC), '[]'::json), MIN(c.id)
    INTO rows, last_id
  FROM (SELECT * FROM site_comments
        WHERE article_id = p_article AND (status = 'visible' OR (status = 'pending' AND visitor = p_visitor))
          AND (p_before IS NULL OR id < p_before)
        ORDER BY id DESC LIMIT n) c;
  RETURN json_build_object(
    'comments', rows,
    'total', (SELECT COUNT(*) FROM site_comments WHERE article_id = p_article AND status = 'visible'),
    'more', last_id IS NOT NULL AND EXISTS (
      SELECT 1 FROM site_comments WHERE article_id = p_article AND id < last_id
        AND (status = 'visible' OR (status = 'pending' AND visitor = p_visitor))),
    'mode', site_comment_mode());
END $$;

-- 댓글 쓰기 — {"comment": {…}, "total": n} 또는 {"error": "closed"|"invalid"|"links"|"rate"|"busy"}. 발행 목록에 없는 글은 NULL.
CREATE OR REPLACE FUNCTION site_comment_add(p_article TEXT, p_visitor TEXT, p_name TEXT, p_body TEXT, p_ip TEXT)
RETURNS JSON
LANGUAGE plpgsql SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_mode TEXT := site_comment_mode();
  v_name TEXT := left(btrim(regexp_replace(COALESCE(p_name, ''), '\s+', ' ', 'g')), 20);
  v_body TEXT := btrim(regexp_replace(COALESCE(p_body, ''), E'\\n{3,}', E'\n\n', 'g'));
  v_ip   TEXT := NULLIF(left(COALESCE(p_ip, ''), 64), '');
  c site_comments;
BEGIN
  IF p_visitor IS NULL OR p_visitor !~ '^[A-Za-z0-9-]{8,64}$'
     OR NOT EXISTS (SELECT 1 FROM site_articles WHERE article_id = p_article AND live) THEN
    RETURN NULL;
  END IF;
  IF v_mode = 'closed' THEN
    RETURN json_build_object('error', 'closed');
  END IF;
  IF char_length(v_body) < 1 OR char_length(v_body) > 500 THEN
    RETURN json_build_object('error', 'invalid');
  END IF;
  IF (SELECT COUNT(*) FROM regexp_matches(v_body, 'https?://|www\.', 'gi')) >= 3 THEN
    RETURN json_build_object('error', 'links');
  END IF;
  IF EXISTS (SELECT 1 FROM site_comments WHERE visitor = p_visitor AND created_at > now() - interval '30 seconds') THEN
    RETURN json_build_object('error', 'rate');
  END IF;
  IF (SELECT COUNT(*) FROM site_comments WHERE article_id = p_article AND created_at > now() - interval '1 hour') >= 60
     OR (v_ip IS NOT NULL AND (SELECT COUNT(*) FROM site_comments WHERE ip_hash = v_ip AND created_at > now() - interval '1 hour') >= 30) THEN
    RETURN json_build_object('error', 'busy');
  END IF;
  INSERT INTO site_comments (article_id, visitor, name, body, status, ip_hash)
  VALUES (p_article, p_visitor, CASE WHEN v_name = '' THEN '익명' ELSE v_name END, v_body,
          CASE WHEN v_mode = 'moderated' THEN 'pending' ELSE 'visible' END, v_ip)
  RETURNING * INTO c;
  RETURN json_build_object('comment', site_comment_json(c, p_visitor),
                           'total', (SELECT COUNT(*) FROM site_comments WHERE article_id = p_article AND status = 'visible'));
END $$;

-- 내 댓글 지우기 — 같은 방문자 값으로 쓴 것만. {"ok": true|false, "total": n}
CREATE OR REPLACE FUNCTION site_comment_delete(p_id BIGINT, p_visitor TEXT)
RETURNS JSON
LANGUAGE plpgsql SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_article TEXT;
BEGIN
  UPDATE site_comments SET status = 'deleted'
  WHERE id = p_id AND visitor = p_visitor AND status IN ('visible', 'pending')
  RETURNING article_id INTO v_article;
  RETURN json_build_object('ok', v_article IS NOT NULL,
                           'total', (SELECT COUNT(*) FROM site_comments WHERE article_id = v_article AND status = 'visible'));
END $$;

-- 014의 수치 함수 — 댓글 수를 함께
CREATE OR REPLACE FUNCTION site_reader_counts(p_article TEXT, p_visitor TEXT)
RETURNS JSON
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
  SELECT json_build_object(
    'views', (SELECT COALESCE(SUM(views), 0) FROM site_views_daily WHERE article_id = p_article),
    'likes', (SELECT COUNT(*) FROM site_likes WHERE article_id = p_article),
    'liked', EXISTS (SELECT 1 FROM site_likes WHERE article_id = p_article AND visitor = p_visitor),
    'comments', (SELECT COUNT(*) FROM site_comments WHERE article_id = p_article AND status = 'visible')
  );
$$;

CREATE OR REPLACE FUNCTION site_reader_stats()
RETURNS JSON
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
  SELECT COALESCE(json_object_agg(a.article_id, json_build_object(
    'views', (SELECT COALESCE(SUM(v.views), 0) FROM site_views_daily v WHERE v.article_id = a.article_id),
    'likes', (SELECT COUNT(*) FROM site_likes l WHERE l.article_id = a.article_id),
    'comments', (SELECT COUNT(*) FROM site_comments c WHERE c.article_id = a.article_id AND c.status = 'visible'))), '{}'::json)
  FROM site_articles a WHERE a.live;
$$;

-- 권한: 표와 안에서만 쓰는 함수는 걷고, anon에는 댓글 함수 셋만 준다(014의 권한은 CREATE OR REPLACE로 그대로 남는다).
DO $$
DECLARE
  r text;
  f text;
BEGIN
  FOREACH f IN ARRAY ARRAY[
    'site_comment_mode()', 'site_comment_json(site_comments, TEXT)',
    'site_comment_list(TEXT, TEXT, BIGINT, INTEGER)', 'site_comment_add(TEXT, TEXT, TEXT, TEXT, TEXT)', 'site_comment_delete(BIGINT, TEXT)']
  LOOP
    EXECUTE format('REVOKE ALL ON FUNCTION %s FROM PUBLIC', f);
    FOREACH r IN ARRAY ARRAY['anon', 'authenticated'] LOOP
      IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
        EXECUTE format('REVOKE ALL ON FUNCTION %s FROM %I', f, r);
      END IF;
    END LOOP;
  END LOOP;
  FOREACH r IN ARRAY ARRAY['anon', 'authenticated'] LOOP
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
      EXECUTE format('REVOKE ALL ON TABLE site_comments, site_settings FROM %I', r);
      EXECUTE format('REVOKE ALL ON SEQUENCE site_comments_id_seq FROM %I', r);
    END IF;
  END LOOP;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
    GRANT EXECUTE ON FUNCTION site_comment_list(TEXT, TEXT, BIGINT, INTEGER) TO anon;
    GRANT EXECUTE ON FUNCTION site_comment_add(TEXT, TEXT, TEXT, TEXT, TEXT) TO anon;
    GRANT EXECUTE ON FUNCTION site_comment_delete(BIGINT, TEXT) TO anon;
  END IF;
END $$;

NOTIFY pgrst, 'reload schema';
-- +end

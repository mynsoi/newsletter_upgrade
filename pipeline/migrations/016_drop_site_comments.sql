-- 016_drop_site_comments.sql — 발행 사이트의 댓글을 걷어낸다 (2026-11-26)
--
-- 2026-11-24에 넣은 댓글(015)을 사용자 결정으로 없앤다. 화면·API·작업실 쪽 코드는 같은 날 되돌렸다.
-- 적용 시점의 데이터: site_comments 1줄(배포 확인용 시험 댓글, 쓴 쪽에서 지운 상태) · site_settings 0줄 — 독자가 쓴 댓글은 없었다.
--
-- 하는 일:
--   1. 수치 함수 둘(site_reader_counts · site_reader_stats)을 014의 모양(댓글 수 없음)으로 되돌린다 — 표를 지우기 전에 먼저.
--   2. 댓글 함수 다섯과 표 둘(site_comments · site_settings)을 지운다.
-- 조회수·좋아요(014의 표 셋과 함수)는 그대로다. 015 파일은 적용 기록이라 남겨 둔다.
-- SQLite(테스트용 로컬 모드)에는 처음부터 만들지 않았다.

-- +postgres
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

DROP FUNCTION IF EXISTS site_comment_list(TEXT, TEXT, BIGINT, INTEGER);
DROP FUNCTION IF EXISTS site_comment_add(TEXT, TEXT, TEXT, TEXT, TEXT);
DROP FUNCTION IF EXISTS site_comment_delete(BIGINT, TEXT);
DROP FUNCTION IF EXISTS site_comment_json(site_comments, TEXT);
DROP FUNCTION IF EXISTS site_comment_mode();
DROP TABLE IF EXISTS site_comments;
DROP TABLE IF EXISTS site_settings;

NOTIFY pgrst, 'reload schema';
-- +end

-- 017_site_chat.sql — 발행 사이트의 챗봇 1단계 (2026-11-26)
--
-- 독자가 글 페이지에서 '이 글'에 대해 묻고 답을 받는다. 답의 근거는 그 글 본문과 그 글이 참고자료로 밝힌 원문의 전문이다.
-- 길: 글 페이지(web/reader.js) → Vercel 함수(api/chat.py) → 아래 함수 둘 → Claude API(claude-haiku-5-5).
--
-- 조회수·좋아요(014)와 다른 점: 원문 전문이 오가므로 익명 키만으로는 부를 수 없게 한다.
--   함수 둘은 Vercel에만 두는 비밀값(CHAT_SECRET)을 함께 받아, site_settings에 적어 둔 그 해시와 맞을 때만 일한다.
--   비밀값이 새어도 나가는 것은 '발행 중인 글이 참고자료로 밝힌 원문'까지다(서재 전체가 아니다).
--
--   site_settings      사이트 설정. chat = off(기본) | test(주소에 ?chat=1을 붙인 사람에게만 버튼) | on. chat_secret_hash = 비밀값의 sha256.
--                      (015에서 만들었다 016에서 지운 표를 챗봇용으로 다시 만든다.)
--   site_chat_context  글마다 근거 자료 한 줄 — {"title", "body", "sources": [{"label", "url", "text"}]}.
--                      발행·refresh 때 작업실이 넣는다(scripts/reader_stats.py). 원문 전문이 들어 있으므로 git에는 올리지 않는다.
--   site_chat_log      질문·답변 기록. 하루 상한을 세는 데도 쓴다. 방문자는 브라우저의 무작위 값뿐이다(이름·IP 없음).
--
-- 상한(site_chat_begin 안, 날짜는 KST): 한 브라우저 하루 10건 · 사이트 전체 하루 300건 · 같은 브라우저 5초에 1건 · 질문 1~300자.
-- 사이트 전체 상한이 곧 하루 비용 상한이다.
-- SQLite(테스트용 로컬 모드)에는 역할·RPC가 없어 만들지 않는다.

-- +postgres
CREATE TABLE IF NOT EXISTS site_settings (
  key        TEXT PRIMARY KEY,
  value      TEXT NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS site_chat_context (
  article_id TEXT PRIMARY KEY REFERENCES site_articles(article_id),
  context    JSONB NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS site_chat_log (
  id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  article_id    TEXT NOT NULL REFERENCES site_articles(article_id),
  visitor       TEXT NOT NULL,
  question      TEXT NOT NULL,
  answer        TEXT,
  status        TEXT NOT NULL DEFAULT 'started',   -- started(답하는 중·끊김) · done · refused(모델이 거절) · error
  model         TEXT,
  input_tokens  INTEGER,                            -- 캐시에서 읽은 것·새로 쓴 것 포함
  cached_tokens INTEGER,
  output_tokens INTEGER,
  ms            INTEGER,                            -- 질문을 받고 답을 끝낼 때까지
  dropped       INTEGER,                            -- 원문과 길게 겹쳐 뺀 문장 수
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_site_chat_log_created ON site_chat_log (created_at);
CREATE INDEX IF NOT EXISTS idx_site_chat_log_article ON site_chat_log (article_id, id DESC);

ALTER TABLE site_settings     ENABLE ROW LEVEL SECURITY;
ALTER TABLE site_chat_context ENABLE ROW LEVEL SECURITY;
ALTER TABLE site_chat_log     ENABLE ROW LEVEL SECURITY;

-- 비밀값이 맞는가(안에서만 쓴다) — 해시가 아직 없으면 언제나 거짓
CREATE OR REPLACE FUNCTION site_chat_auth(p_secret TEXT)
RETURNS BOOLEAN
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
  SELECT COALESCE(length(p_secret) >= 24 AND encode(sha256(convert_to(p_secret, 'UTF8')), 'hex')
                  = (SELECT value FROM site_settings WHERE key = 'chat_secret_hash'), FALSE);
$$;

-- 이 글에서 챗봇이 켜져 있는가(안에서만 쓴다) — 'on' · 'test' · NULL(꺼짐이거나 근거 자료가 없음)
CREATE OR REPLACE FUNCTION site_chat_state(p_article TEXT)
RETURNS TEXT
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
  SELECT s.value FROM site_settings s
  WHERE s.key = 'chat' AND s.value IN ('on', 'test')
    AND EXISTS (SELECT 1 FROM site_chat_context c JOIN site_articles a USING (article_id)
                WHERE c.article_id = p_article AND a.live);
$$;

-- 질문을 받는다 — 상한을 확인하고 기록 한 줄을 만든 뒤 근거 자료를 돌려준다.
-- {"id": 기록 번호, "context": {…}} 또는 {"error": "auth"|"off"|"invalid"|"rate"|"visitor_limit"|"daily_limit"}
CREATE OR REPLACE FUNCTION site_chat_begin(p_secret TEXT, p_article TEXT, p_visitor TEXT, p_question TEXT)
RETURNS JSON
LANGUAGE plpgsql SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_q   TEXT := btrim(COALESCE(p_question, ''));
  v_day TIMESTAMPTZ := date_trunc('day', now() AT TIME ZONE 'Asia/Seoul') AT TIME ZONE 'Asia/Seoul';  -- 오늘(KST) 0시
  v_id  BIGINT;
BEGIN
  IF NOT site_chat_auth(p_secret) THEN
    RETURN json_build_object('error', 'auth');
  END IF;
  IF site_chat_state(p_article) IS NULL THEN
    RETURN json_build_object('error', 'off');
  END IF;
  IF p_visitor IS NULL OR p_visitor !~ '^[A-Za-z0-9-]{8,64}$' OR char_length(v_q) < 1 OR char_length(v_q) > 300 THEN
    RETURN json_build_object('error', 'invalid');
  END IF;
  IF EXISTS (SELECT 1 FROM site_chat_log WHERE visitor = p_visitor AND created_at > now() - interval '5 seconds') THEN
    RETURN json_build_object('error', 'rate');
  END IF;
  IF (SELECT COUNT(*) FROM site_chat_log WHERE visitor = p_visitor AND created_at >= v_day) >= 10 THEN
    RETURN json_build_object('error', 'visitor_limit');
  END IF;
  IF (SELECT COUNT(*) FROM site_chat_log WHERE created_at >= v_day) >= 300 THEN
    RETURN json_build_object('error', 'daily_limit');
  END IF;
  INSERT INTO site_chat_log (article_id, visitor, question) VALUES (p_article, p_visitor, v_q) RETURNING id INTO v_id;
  RETURN json_build_object('id', v_id, 'context', (SELECT context FROM site_chat_context WHERE article_id = p_article));
END $$;

-- 답을 끝냈다 — 기록을 채운다. 아직 'started'인 줄만(같은 줄을 두 번 쓰지 못하게).
CREATE OR REPLACE FUNCTION site_chat_end(p_secret TEXT, p_id BIGINT, p_answer TEXT, p_status TEXT, p_model TEXT,
                                         p_input INTEGER, p_cached INTEGER, p_output INTEGER, p_ms INTEGER, p_dropped INTEGER)
RETURNS BOOLEAN
LANGUAGE plpgsql SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
BEGIN
  IF NOT site_chat_auth(p_secret) OR p_status NOT IN ('done', 'refused', 'error') THEN
    RETURN FALSE;
  END IF;
  UPDATE site_chat_log
  SET answer = left(p_answer, 8000), status = p_status, model = left(p_model, 60), input_tokens = p_input,
      cached_tokens = p_cached, output_tokens = p_output, ms = p_ms, dropped = p_dropped
  WHERE id = p_id AND status = 'started';
  RETURN FOUND;
END $$;

-- 014의 수치 함수 — 이 글에서 챗봇 버튼을 보일지('on' · 'test' · null)를 함께 돌려준다
CREATE OR REPLACE FUNCTION site_reader_counts(p_article TEXT, p_visitor TEXT)
RETURNS JSON
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
  SELECT json_build_object(
    'views', (SELECT COALESCE(SUM(views), 0) FROM site_views_daily WHERE article_id = p_article),
    'likes', (SELECT COUNT(*) FROM site_likes WHERE article_id = p_article),
    'liked', EXISTS (SELECT 1 FROM site_likes WHERE article_id = p_article AND visitor = p_visitor),
    'chat', site_chat_state(p_article)
  );
$$;

-- 권한: 표와 안에서만 쓰는 함수는 걷고, anon에는 begin·end만 준다(비밀값 없이는 아무 일도 하지 않는다).
DO $$
DECLARE
  r text;
  f text;
BEGIN
  FOREACH f IN ARRAY ARRAY[
    'site_chat_auth(TEXT)', 'site_chat_state(TEXT)', 'site_chat_begin(TEXT, TEXT, TEXT, TEXT)',
    'site_chat_end(TEXT, BIGINT, TEXT, TEXT, TEXT, INTEGER, INTEGER, INTEGER, INTEGER, INTEGER)']
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
      EXECUTE format('REVOKE ALL ON TABLE site_settings, site_chat_context, site_chat_log FROM %I', r);
      EXECUTE format('REVOKE ALL ON SEQUENCE site_chat_log_id_seq FROM %I', r);
    END IF;
  END LOOP;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
    GRANT EXECUTE ON FUNCTION site_chat_begin(TEXT, TEXT, TEXT, TEXT) TO anon;
    GRANT EXECUTE ON FUNCTION site_chat_end(TEXT, BIGINT, TEXT, TEXT, TEXT, INTEGER, INTEGER, INTEGER, INTEGER, INTEGER) TO anon;
  END IF;
END $$;

NOTIFY pgrst, 'reload schema';
-- +end

"""발행 사이트의 조회수·좋아요·챗봇 — 작업실 쪽(직접 연결).

표와 함수는 pipeline/migrations/014_site_reader.sql · 017_site_chat.sql, 독자 쪽 길은 api/reader.py · api/chat.py(Vercel) → web/reader.js.
  sync()   site/<토큰>/*/article.json을 site_articles 표에 맞춘다 — 발행·내리기 때 scripts/publish.py가 부른다.
           표에 live로 올라 있는 글만 조회·좋아요를 받는다. 내린 글은 live=false로만 바꾼다(수치는 남는다).
           챗봇(017)이 있으면 글마다 근거 자료(글 본문 + 참고 원문 전문)도 site_chat_context에 넣는다 — 이 PC에 확정 원고와
           원문 파일(sources/originals/…, git 밖)이 있는 글만. 원문 전문은 DB에만 두고 git·site/에는 올리지 않는다.
  stats()  글별 합계와 최근 날짜별 조회수 — 작업실 발행 탭이 읽는다.
  chat(글) · set_chat_mode(방식) · new_chat_secret()  독자 질문 보기, 챗봇 켜기·시험·끄기, Vercel에 넣을 비밀값 만들기.
DB 연결 문자열은 환경변수 DATABASE_URL에서만 읽는다(card_search와 같이 Windows 사용자 환경변수도 본다).
DB에 닿지 못해도 발행은 막지 않는다 — sync는 사유를 돌려주고, stats는 빈 값.

사용: python -I scripts/reader_stats.py sync | stats | chat-secret
"""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DAYS = 14  # 발행 탭에 보여 줄 날짜별 조회수의 기간


def _url():
    v = os.environ.get("DATABASE_URL")
    if not v and os.name == "nt":
        v = subprocess.run(["powershell", "-NoProfile", "-Command", "[Environment]::GetEnvironmentVariable('DATABASE_URL','User')"],
                           capture_output=True, text=True).stdout.strip()
    return v


def connect():
    url = _url()
    if not url:
        raise RuntimeError("DATABASE_URL이 없습니다")
    import psycopg
    return psycopg.connect(url, prepare_threshold=None, connect_timeout=10)  # Supabase 풀러(트랜잭션 모드)는 prepared statement를 못 씀


def site_articles():
    """site/에 올라 있는 글 [(id, 제목, 발행일)]"""
    token = json.loads((ROOT / "config" / "publish.json").read_text(encoding="utf-8"))["web_path_token"]
    out = []
    for f in sorted((ROOT / "site" / token).glob("*/article.json")):
        x = json.loads(f.read_text(encoding="utf-8"))
        out.append((f.parent.name, x.get("title", ""), x.get("pub_date") or None))
    return out


def sync():
    """site/의 글 목록을 표에 맞춘다. 돌려주는 값: (성공 여부, 한 줄 설명)"""
    rows = site_articles()
    try:
        with connect() as c:
            if not c.execute("SELECT to_regclass('public.site_articles')").fetchone()[0]:
                return False, "site_articles 표가 아직 없습니다(migrations/014가 적용되기 전)"
            for k, title, day in rows:
                c.execute("INSERT INTO site_articles (article_id, title, published_at, live) VALUES (%s, %s, %s, TRUE) "
                          "ON CONFLICT (article_id) DO UPDATE SET title = EXCLUDED.title, published_at = EXCLUDED.published_at, "
                          "live = TRUE, updated_at = CURRENT_TIMESTAMP", (k, title, day))
            c.execute("UPDATE site_articles SET live = FALSE, updated_at = CURRENT_TIMESTAMP WHERE live AND NOT (article_id = ANY(%s))",
                      ([k for k, _, _ in rows],))
            note = _sync_chat(c, [k for k, _, _ in rows])
        return True, f"발행 목록 {len(rows)}편을 DB에 맞췄습니다" + note
    except Exception as e:  # noqa: BLE001 — 발행을 막지 않는다
        return False, f"{type(e).__name__}: {str(e).splitlines()[0][:160] if str(e) else ''}"


# ---------- 챗봇 근거 자료 ----------
BIG_SOURCE = 60_000  # 자 — 이보다 긴 원문은 줄이지 않고 그대로 넣되 알린다(질문마다 읽는 양이 커진다)


def chat_context(k):
    """글 k의 챗봇 근거 자료 {"title", "body", "sources": [{"label", "url", "text"}]} — 확정 원고와 원문 파일에서.
    본문은 발행본과 같은 글(굵게·강조 표시와 그림은 뺀다), 원문은 머리말을 뗀 전문 그대로. 사내 자료는 넣지 않는다(발행본 참고자료와 같은 기준)."""
    sys.path.insert(0, str(ROOT / "scripts"))
    import re
    import publish as P
    a = P.load(k)
    body = "\n\n".join(re.sub(r"\*\*|==", "", b["text"]) for b in a["blocks"] if b["type"] in ("p", "h2", "quote"))
    meta, sources = json.loads(a["meta"].read_text(encoding="utf-8")), []
    for (path, _label), ref in zip(meta.get("sources", []), a["references"]):
        f = ROOT / "sources" / path
        if not f.is_file():
            raise FileNotFoundError(f"원문 없음: sources/{path}")
        text = re.sub(r"^---\n.*?\n---\n", "", f.read_text(encoding="utf-8"), count=1, flags=re.S).strip()
        sources.append({"label": ref["label"], "url": ref["url"], "text": text})
    return {"title": a["title"], "body": body, "sources": sources}


def _sync_chat(c, ids):
    """발행 중인 글들의 근거 자료를 넣는다(같은 연결로). 돌려주는 값: sync 설명 뒤에 붙일 말. 표가 없으면(017 전) 아무것도 안 한다."""
    if not c.execute("SELECT to_regclass('public.site_chat_context')").fetchone()[0]:
        return ""
    ok, skipped, big = 0, [], []
    for k in ids:
        try:
            ctx = chat_context(k)
        except (Exception, SystemExit) as e:  # noqa: BLE001 — 이 PC에 원고·원문이 없는 글은 건너뛴다(있던 근거 자료는 그대로)
            skipped.append(f"{k}({str(e)[:50]})")
            continue
        big += [f"{k} {len(s['text']):,}자" for s in ctx["sources"] if len(s["text"]) > BIG_SOURCE]
        c.execute("INSERT INTO site_chat_context (article_id, context) VALUES (%s, %s) "
                  "ON CONFLICT (article_id) DO UPDATE SET context = EXCLUDED.context, updated_at = now()", (k, json.dumps(ctx, ensure_ascii=False)))
        ok += 1
    return (f" · 챗봇 근거 자료 {ok}편" + (f" · 건너뜀 {len(skipped)}편: {', '.join(skipped)}" if skipped else "")
            + (f" · 긴 원문: {', '.join(big)}" if big else ""))


def stats():
    """{"<글>": {"views", "likes", "days": [["YYYY-MM-DD", n], …]}} — 표가 없거나 닿지 못하면 {}."""
    try:
        with connect() as c:
            c.read_only = True
            if not c.execute("SELECT to_regclass('public.site_articles')").fetchone()[0]:
                return {}
            out = {k: {"views": int(v), "likes": int(l), "days": []} for k, v, l in c.execute(
                "SELECT a.article_id, (SELECT COALESCE(SUM(views), 0) FROM site_views_daily v WHERE v.article_id = a.article_id), "
                "(SELECT COUNT(*) FROM site_likes l WHERE l.article_id = a.article_id) FROM site_articles a")}
            for k, day, n in c.execute(
                    "SELECT article_id, day, views FROM site_views_daily "
                    "WHERE day > (now() AT TIME ZONE 'Asia/Seoul')::date - %s ORDER BY day", (DAYS,)):
                if k in out:
                    out[k]["days"].append([day.isoformat(), int(n)])
            return out
    except Exception as e:  # noqa: BLE001
        print(f"독자 수치 읽기 실패: {type(e).__name__}", flush=True)
        return {}


CHAT_MODES = ("off", "test", "on")  # 꺼짐 · 시험(주소에 ?chat=1을 붙인 사람에게만 버튼) · 켜짐
SECRET_FILE = ROOT / "publish" / "chat_secret.txt"  # publish/는 git 밖 — 비밀값은 여기 한 번 적히고, 사람이 Vercel에 옮긴 뒤 지운다


def chat(article):
    """발행 탭용 — {"ready", "mode", "secret"(비밀값 해시가 DB에 있는가), "context"(이 글의 근거 자료가 있는가), "today"(오늘 사이트 전체 질문 수),
    "questions": [{"id", "question", "answer", "status", "at", "ms", "dropped"}]} 새 것부터 100개. 017 전이거나 닿지 못하면 ready 거짓."""
    empty = {"ready": False, "mode": "off", "secret": False, "context": False, "today": 0, "questions": []}
    try:
        with connect() as c:
            c.read_only = True
            if not c.execute("SELECT to_regclass('public.site_chat_log')").fetchone()[0]:
                return empty
            st = dict(c.execute("SELECT key, value FROM site_settings WHERE key IN ('chat', 'chat_secret_hash')").fetchall())
            rows = c.execute("SELECT id, question, answer, status, created_at, ms, dropped FROM site_chat_log "
                             "WHERE article_id = %s ORDER BY id DESC LIMIT 100", (article,)).fetchall()
            return {"ready": True, "mode": st.get("chat") if st.get("chat") in CHAT_MODES else "off", "secret": bool(st.get("chat_secret_hash")),
                    "context": bool(c.execute("SELECT 1 FROM site_chat_context WHERE article_id = %s", (article,)).fetchone()),
                    "today": c.execute("SELECT COUNT(*) FROM site_chat_log WHERE created_at >= "
                                       "date_trunc('day', now() AT TIME ZONE 'Asia/Seoul') AT TIME ZONE 'Asia/Seoul'").fetchone()[0],
                    "questions": [{"id": i, "question": q, "answer": a or "", "status": s, "at": at.isoformat(), "ms": ms, "dropped": d or 0}
                                  for i, q, a, s, at, ms, d in rows]}
    except Exception as e:  # noqa: BLE001
        print(f"독자 질문 읽기 실패: {type(e).__name__}", flush=True)
        return empty


def set_chat_mode(mode):
    """챗봇 켜기(on)·시험(test)·끄기(off) — 사이트 전체에 바로 적용된다."""
    if mode not in CHAT_MODES:
        raise ValueError("잘못된 방식: " + str(mode))
    with connect() as c:
        c.execute("INSERT INTO site_settings (key, value) VALUES ('chat', %s) "
                  "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = now()", (mode,))
    return mode


def new_chat_secret():
    """Vercel 함수(api/chat.py)와 DB가 나눠 갖는 비밀값을 새로 만든다 — 해시는 DB에, 값은 SECRET_FILE에 적는다(화면·로그에는 찍지 않는다).
    다시 만들면 예전 값은 바로 못 쓰게 된다 — Vercel의 CHAT_SECRET도 새 값으로 바꾸고 다시 배포해야 한다."""
    import hashlib
    import secrets
    value = secrets.token_urlsafe(36)
    with connect() as c:
        c.execute("INSERT INTO site_settings (key, value) VALUES ('chat_secret_hash', %s) "
                  "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = now()", (hashlib.sha256(value.encode("utf-8")).hexdigest(),))
    SECRET_FILE.parent.mkdir(parents=True, exist_ok=True)
    SECRET_FILE.write_text(value, encoding="utf-8")
    return SECRET_FILE


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "stats"
    if cmd == "chat-secret":
        f = new_chat_secret()
        print(f"비밀값을 새로 만들었습니다 — {f.relative_to(ROOT).as_posix()} 의 내용을 Vercel 환경변수 CHAT_SECRET에 넣고, 넣은 뒤 이 파일은 지우세요.", flush=True)
        sys.exit(0)
    if cmd == "sync":
        ok, msg = sync()
        print(msg, flush=True)
        sys.exit(0 if ok else 1)
    print(json.dumps(stats(), ensure_ascii=False, indent=1))

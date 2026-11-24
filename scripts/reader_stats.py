"""발행 사이트의 조회수·좋아요·댓글 — 작업실 쪽(직접 연결).

표와 함수는 pipeline/migrations/014_site_reader.sql · 015_site_comments.sql, 독자 쪽 길은 api/reader.py(Vercel) → web/reader.js.
  sync()   site/<토큰>/*/article.json을 site_articles 표에 맞춘다 — 발행·내리기 때 scripts/publish.py가 부른다.
           표에 live로 올라 있는 글만 조회·좋아요를 받는다. 내린 글은 live=false로만 바꾼다(수치는 남는다).
  stats()  글별 합계와 최근 날짜별 조회수 — 작업실 발행 탭이 읽는다.
  comments(글) · set_comment(번호, 상태) · set_mode(방식)  댓글 보기·숨기기·승인, 받는 방식(바로 공개·승인 뒤 공개·닫힘) — 발행 탭.
           쓴 사람이 지운 댓글(deleted)은 보여 주지 않는다. 방문자 값·ip_hash는 화면에 내보내지 않는다.
DB 연결 문자열은 환경변수 DATABASE_URL에서만 읽는다(card_search와 같이 Windows 사용자 환경변수도 본다).
DB에 닿지 못해도 발행은 막지 않는다 — sync는 사유를 돌려주고, stats는 빈 값.

사용: python -I scripts/reader_stats.py sync | stats
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
        return True, f"발행 목록 {len(rows)}편을 DB에 맞췄습니다"
    except Exception as e:  # noqa: BLE001 — 발행을 막지 않는다
        return False, f"{type(e).__name__}: {str(e).splitlines()[0][:160] if str(e) else ''}"


def stats():
    """{"<글>": {"views", "likes", "days": [["YYYY-MM-DD", n], …]}} — 표가 없거나 닿지 못하면 {}."""
    try:
        with connect() as c:
            c.read_only = True
            if not c.execute("SELECT to_regclass('public.site_articles')").fetchone()[0]:
                return {}
            out = {k: {"views": int(v), "likes": int(l), "comments": 0, "pending": 0, "days": []} for k, v, l in c.execute(
                "SELECT a.article_id, (SELECT COALESCE(SUM(views), 0) FROM site_views_daily v WHERE v.article_id = a.article_id), "
                "(SELECT COUNT(*) FROM site_likes l WHERE l.article_id = a.article_id) FROM site_articles a")}
            if c.execute("SELECT to_regclass('public.site_comments')").fetchone()[0]:  # 015가 적용되기 전에는 댓글 없이
                for k, n, pend in c.execute(
                        "SELECT article_id, COUNT(*) FILTER (WHERE status = 'visible'), COUNT(*) FILTER (WHERE status = 'pending') "
                        "FROM site_comments GROUP BY article_id"):
                    if k in out:
                        out[k]["comments"], out[k]["pending"] = int(n), int(pend)
            for k, day, n in c.execute(
                    "SELECT article_id, day, views FROM site_views_daily "
                    "WHERE day > (now() AT TIME ZONE 'Asia/Seoul')::date - %s ORDER BY day", (DAYS,)):
                if k in out:
                    out[k]["days"].append([day.isoformat(), int(n)])
            return out
    except Exception as e:  # noqa: BLE001
        print(f"독자 수치 읽기 실패: {type(e).__name__}", flush=True)
        return {}


MODES = ("open", "moderated", "closed")       # 바로 공개 · 승인 뒤 공개 · 새 댓글 받지 않음
STATUSES = ("visible", "hidden")             # 작업실이 바꿀 수 있는 상태(승인 = visible, 숨기기 = hidden)


def comments(article):
    """{"ready", "mode", "comments": [{"id", "name", "body", "at", "status"}]} — 새 것부터 200개까지. 015 전이거나 닿지 못하면 ready 거짓."""
    try:
        with connect() as c:
            c.read_only = True
            if not c.execute("SELECT to_regclass('public.site_comments')").fetchone()[0]:
                return {"ready": False, "mode": "open", "comments": []}
            mode = c.execute("SELECT value FROM site_settings WHERE key = 'comments'").fetchone()
            rows = c.execute("SELECT id, name, body, created_at, status FROM site_comments "
                             "WHERE article_id = %s AND status <> 'deleted' ORDER BY id DESC LIMIT 200", (article,)).fetchall()
            return {"ready": True, "mode": mode[0] if mode and mode[0] in MODES else "open",
                    "comments": [{"id": i, "name": n, "body": b, "at": at.isoformat(), "status": st} for i, n, b, at, st in rows]}
    except Exception as e:  # noqa: BLE001
        print(f"댓글 읽기 실패: {type(e).__name__}", flush=True)
        return {"ready": False, "mode": "open", "comments": []}


def set_comment(comment_id, status):
    """댓글을 보이게(visible — 승인·되살리기)·숨기게(hidden). 쓴 사람이 지운 댓글은 건드리지 않는다. 바뀌었으면 참."""
    if status not in STATUSES:
        raise ValueError("잘못된 상태: " + str(status))
    with connect() as c:
        return c.execute("UPDATE site_comments SET status = %s WHERE id = %s AND status <> 'deleted'", (status, int(comment_id))).rowcount == 1


def set_mode(mode):
    """댓글 받는 방식 — 사이트 전체에 바로 적용된다."""
    if mode not in MODES:
        raise ValueError("잘못된 방식: " + str(mode))
    with connect() as c:
        c.execute("INSERT INTO site_settings (key, value) VALUES ('comments', %s) "
                  "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = now()", (mode,))
    return mode


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "stats"
    if cmd == "sync":
        ok, msg = sync()
        print(msg, flush=True)
        sys.exit(0 if ok else 1)
    print(json.dumps(stats(), ensure_ascii=False, indent=1))

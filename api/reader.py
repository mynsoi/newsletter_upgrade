"""발행 사이트의 조회수·좋아요 창구 (Vercel 함수 — /api/reader).

발행 페이지(web/reader.js)가 부르고, Supabase의 함수 3개만 부른다(pipeline/migrations/014_site_reader.sql).
표에는 닿지 못한다 — 익명 키로 할 수 있는 일은 '조회 +1 · 좋아요 켜고 끄기 · 수치 읽기'뿐이다.

  GET  /api/reader                                    → {"<글>": {"views": n, "likes": n}, …}   (목록 페이지)
  POST /api/reader  {"article", "visitor", "view"}    → {"views", "likes", "liked"}             (글을 열 때 — view가 참이면 조회 +1)
  POST /api/reader  {"article", "visitor", "like"}    → 같은 모양                               (좋아요 켜기 true · 끄기 false)

환경변수(Vercel 프로젝트 설정): SUPABASE_URL(https://<프로젝트>.supabase.co) · SUPABASE_ANON_KEY(익명 키 — anon 또는 publishable).
표준 라이브러리만 쓴다 — vercel.json이 설치 단계를 건너뛰므로 패키지를 더하지 않는다.
이 PC에서 띄워 볼 때: python api/reader.py 8790 (같은 환경변수 필요)
"""
import json
import os
import re
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse

ARTICLE = re.compile(r"^[0-9A-Za-z가-힣][0-9A-Za-z가-힣_.-]{0,80}$")  # scripts/publish.py의 ID와 같은 모양
VISITOR = re.compile(r"^[A-Za-z0-9-]{8,64}$")
MAX_BODY = 1024


def rpc(fn, args):
    """Supabase 함수 호출 — 결과(JSON)를 돌려준다. 설정이 없거나 실패하면 예외."""
    base, key = os.environ.get("SUPABASE_URL", "").rstrip("/"), os.environ.get("SUPABASE_ANON_KEY", "")
    if not base or not key:
        raise RuntimeError("SUPABASE_URL · SUPABASE_ANON_KEY가 없습니다")
    headers = {"apikey": key, "Content-Type": "application/json", "Accept": "application/json"}
    if key.startswith("eyJ"):  # 예전 방식의 anon 키(JWT)는 Authorization에도 넣는다. 새 publishable 키는 apikey만
        headers["Authorization"] = "Bearer " + key
    req = urllib.request.Request(f"{base}/rest/v1/rpc/{fn}", data=json.dumps(args).encode("utf-8"), headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=8) as r:
        return json.loads(r.read().decode("utf-8") or "null")


class handler(BaseHTTPRequestHandler):
    def reply(self, code, obj):
        b = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(b)

    def same_site(self):
        """다른 사이트의 페이지가 독자 브라우저로 대신 부르지 못하게 — Origin이 있으면 이 사이트여야 한다."""
        o = self.headers.get("Origin")
        return not o or urlparse(o).netloc == (self.headers.get("X-Forwarded-Host") or self.headers.get("Host") or "")

    def call(self, fn, args):
        try:
            out = rpc(fn, args)
        except (urllib.error.URLError, RuntimeError, ValueError, TimeoutError) as e:
            print("reader:", fn, type(e).__name__, getattr(e, "code", ""), flush=True)  # 키·주소는 찍지 않는다
            return self.reply(502, {"error": "지금은 수치를 불러올 수 없습니다"})
        if out is None:
            return self.reply(404, {"error": "발행된 글이 아닙니다"})
        return self.reply(200, out)

    def do_GET(self):
        return self.call("site_reader_stats", {})

    def do_POST(self):
        if not self.same_site():
            return self.reply(403, {"error": "허용되지 않은 요청입니다"})
        try:
            n = int(self.headers.get("Content-Length") or 0)
            if not 0 < n <= MAX_BODY:
                raise ValueError
            a = json.loads(self.rfile.read(n).decode("utf-8"))
            article, visitor = a["article"], a["visitor"]
            if not (isinstance(article, str) and ARTICLE.match(article) and isinstance(visitor, str) and VISITOR.match(visitor)):
                raise ValueError
        except (ValueError, KeyError, TypeError):
            return self.reply(400, {"error": "잘못된 요청입니다"})
        if "like" in a:
            return self.call("site_reader_like", {"p_article": article, "p_visitor": visitor, "p_on": a["like"] is True})
        return self.call("site_reader_hit", {"p_article": article, "p_visitor": visitor, "p_view": a.get("view") is True})

    def log_message(self, *args):  # 기본 접근 로그는 남기지 않는다
        pass


if __name__ == "__main__":
    import sys
    from http.server import ThreadingHTTPServer
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8790
    print(f"http://127.0.0.1:{port}/api/reader", flush=True)
    ThreadingHTTPServer(("127.0.0.1", port), handler).serve_forever()

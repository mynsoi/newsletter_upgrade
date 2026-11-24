"""발행 사이트의 조회수·좋아요·댓글 창구 (Vercel 함수 — /api/reader).

발행 페이지(web/reader.js)가 부르고, Supabase의 함수만 부른다(pipeline/migrations/014_site_reader.sql · 015_site_comments.sql).
표에는 닿지 못한다 — 익명 키로 할 수 있는 일은 '조회 +1 · 좋아요 켜고 끄기 · 수치 읽기 · 댓글 읽기·쓰기·내 것 지우기'뿐이다.

  GET  /api/reader                                       → {"<글>": {"views", "likes", "comments"}, …}  (목록 페이지)
  GET  /api/reader?article=&visitor=[&before=<번호>]     → {"comments": […], "total", "more", "mode"}   (댓글 — 새 것부터 20개, before로 더 보기)
  POST /api/reader  {"article", "visitor", "view"}       → {"views", "likes", "liked", "comments"}      (글을 열 때 — view가 참이면 조회 +1)
  POST /api/reader  {"article", "visitor", "like"}       → 같은 모양                                    (좋아요 켜기 true · 끄기 false)
  POST /api/reader  {"article", "visitor", "comment": {"name", "body"}} → {"comment", "total"} 또는 400 {"error", "code"}
  POST /api/reader  {"article", "visitor", "uncomment": <번호>}         → {"ok", "total"}               (같은 브라우저에서 쓴 댓글만)

댓글 도배 제한은 DB 함수가 한다(015). 여기서는 요청자 IP를 그날만 쓰는 해시로 바꿔 넘긴다 — IP는 어디에도 저장하지 않는다.

환경변수(Vercel 프로젝트 설정): SUPABASE_URL(https://<프로젝트>.supabase.co) · SUPABASE_ANON_KEY(익명 키 — anon 또는 publishable).
환경변수는 다음 배포부터 적용된다. 대시보드의 Redeploy는 vercel.json의 ignoreCommand(site/·api/·vercel.json 변경 없음 → 건너뜀)에
막혀 취소되니, 값을 바꾼 뒤에는 이 폴더나 site/를 바꾼 커밋을 올리거나 다음 발행을 기다린다(2026-11-20).
표준 라이브러리만 쓴다 — vercel.json이 설치 단계를 건너뛰므로 패키지를 더하지 않는다.
이 PC에서 띄워 볼 때: python api/reader.py 8790 (같은 환경변수 필요)
"""
import hashlib
import json
import os
import re
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlparse

ARTICLE = re.compile(r"^[0-9A-Za-z가-힣][0-9A-Za-z가-힣_.-]{0,80}$")  # scripts/publish.py의 ID와 같은 모양
VISITOR = re.compile(r"^[A-Za-z0-9-]{8,64}$")
MAX_BODY = 4096  # 댓글 500자(한글 1,500바이트)에 이름·따옴표 처리 여유
COMMENT_ERRORS = {  # DB 함수(site_comment_add)가 돌려주는 사유 → 독자에게 보일 말
    "closed": "지금은 댓글을 받지 않습니다.",
    "invalid": "댓글은 1자에서 500자까지 쓸 수 있습니다.",
    "links": "링크가 너무 많습니다. 줄여서 다시 등록해 주세요.",
    "rate": "방금 댓글을 등록했습니다. 잠시 뒤에 다시 써 주세요.",
    "busy": "지금 댓글이 많이 등록되고 있습니다. 잠시 뒤에 다시 써 주세요.",
}


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

    def ip_hash(self):
        """요청자 IP를 그날(UTC)만 쓰는 해시로 — 도배 제한에만 쓴다. 날짜와 이 배포만 아는 값(익명 키)을 섞어 되짚지 못하게."""
        ip = (self.headers.get("X-Real-Ip") or (self.headers.get("X-Forwarded-For") or "").split(",")[0]).strip()
        if not ip:
            return None
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return hashlib.sha256(f"{ip}|{day}|{os.environ.get('SUPABASE_ANON_KEY', '')}".encode("utf-8")).hexdigest()[:32]

    def call(self, fn, args):
        try:
            out = rpc(fn, args)
        except (urllib.error.URLError, RuntimeError, ValueError, TimeoutError) as e:
            print("reader:", fn, type(e).__name__, getattr(e, "code", ""), flush=True)  # 키·주소는 찍지 않는다
            return self.reply(502, {"error": "지금은 수치를 불러올 수 없습니다"})
        if out is None:
            return self.reply(404, {"error": "발행된 글이 아닙니다"})
        if isinstance(out, dict) and out.get("error") in COMMENT_ERRORS:
            return self.reply(400, {"error": COMMENT_ERRORS[out["error"]], "code": out["error"]})
        return self.reply(200, out)

    def do_GET(self):
        q = parse_qs(urlparse(self.path).query)
        article, visitor, before = (q.get(k, [""])[0] for k in ("article", "visitor", "before"))
        if not article:
            return self.call("site_reader_stats", {})
        if not (ARTICLE.match(article) and VISITOR.match(visitor) and (not before or (before.isdigit() and len(before) < 16))):
            return self.reply(400, {"error": "잘못된 요청입니다"})
        return self.call("site_comment_list", {"p_article": article, "p_visitor": visitor, "p_before": int(before) if before else None})

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
        if "comment" in a:
            c = a["comment"]
            if not (isinstance(c, dict) and isinstance(c.get("body"), str) and isinstance(c.get("name", ""), str)):
                return self.reply(400, {"error": "잘못된 요청입니다"})
            return self.call("site_comment_add", {"p_article": article, "p_visitor": visitor, "p_name": c.get("name", ""),
                                                  "p_body": c["body"], "p_ip": self.ip_hash()})
        if "uncomment" in a:
            if not (isinstance(a["uncomment"], int) and not isinstance(a["uncomment"], bool) and 0 < a["uncomment"] < 10 ** 15):
                return self.reply(400, {"error": "잘못된 요청입니다"})
            return self.call("site_comment_delete", {"p_id": a["uncomment"], "p_visitor": visitor})
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

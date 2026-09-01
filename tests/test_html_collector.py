"""HTML 목록 수집기·무유입 경보 테스트 (네트워크 불필요 — 가짜 클라이언트 사용)."""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))


@pytest.fixture()
def test_db(tmp_path, monkeypatch):
    monkeypatch.setenv("PIPELINE_DB", str(tmp_path / "test.db"))
    monkeypatch.delenv("DATABASE_URL", raising=False)
    for mod in list(sys.modules):
        if mod in ("db", "handoff") or mod.startswith(("collectors", "enrich")):
            del sys.modules[mod]
    import db
    import handoff
    monkeypatch.setattr(handoff, "ensure_active", lambda *a, **k: None)
    conn = db.connect()
    db.migrate(conn)
    yield conn, db
    conn.close()


class FakeResponse:
    def __init__(self, status_code=200, text="", content=None, content_type="text/html"):
        self.status_code = status_code
        self.text = text
        self.content = content if content is not None else text.encode("utf-8")
        self.headers = {"content-type": content_type}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPError(f"HTTP {self.status_code}")


class FakeClient:
    def __init__(self, responses=None, default=None):
        self.responses = responses or {}
        self.default = default if default is not None else FakeResponse(404, "")
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append(url)
        r = self.responses.get(url, self.default)
        if isinstance(r, Exception):
            raise r
        return r


LONG_BODY = "<p>" + "AI 도입이 일하는 방식에 미치는 영향 분석. " * 40 + "</p>"

LIST_HTML = """<html><body>
<a href="/news/first-article">글1</a>
<a href="/news/second-article">글2</a>
<a href="/news/first-article">중복</a>
<a href="/news">허브</a>
<a href="/about/team">무관</a>
</body></html>"""

ARTICLE_HTML = f"""<html><head><title>테스트 기사 제목 | HAI</title>
<meta property="article:published_time" content="2026-08-30T10:00:00Z"/></head>
<body><article>{LONG_BODY}</article></body></html>"""

SOURCE = {
    "id": "test-html", "tier": "T1", "type": "html", "lang": "en",
    "list_url": "https://ex.com/news",
    "link_pattern": r'href="(/news/[a-z0-9\-]+)"',
}


@pytest.fixture()
def hcol(monkeypatch):
    import collectors.html_list as h
    monkeypatch.setattr(h.time, "sleep", lambda s: None)
    h._robots_cache.clear()
    return h


def test_extract_links_pattern_dedup_exclude(hcol):
    links = hcol.extract_links(LIST_HTML, "https://ex.com/news", r'href="(/news/[a-z0-9\-]+)"')
    assert links == ["https://ex.com/news/first-article", "https://ex.com/news/second-article"]
    links2 = hcol.extract_links(LIST_HTML, "https://ex.com/news",
                                r'href="(/news/[a-z0-9\-]+)"', exclude=r"second")
    assert links2 == ["https://ex.com/news/first-article"]


def test_collect_source_two_stage_and_dedup(test_db, hcol):
    conn, db = test_db
    client = FakeClient({
        "https://ex.com/robots.txt": FakeResponse(200, "User-agent: *\nAllow: /"),
        "https://ex.com/news": FakeResponse(200, LIST_HTML),
        "https://ex.com/news/first-article": FakeResponse(200, ARTICLE_HTML),
        "https://ex.com/news/second-article": FakeResponse(
            200, ARTICLE_HTML.replace("영향 분석", "다른 내용 분석").replace("테스트 기사", "두번째 기사")),
    })
    stats = hcol.collect_source(SOURCE, conn, client)
    assert stats["new"] == 2 and stats["failed"] == 0

    row = conn.execute("SELECT * FROM documents WHERE url LIKE '%first%'").fetchone()
    assert row["title"] == "테스트 기사 제목 | HAI"
    assert row["published_at"] == "2026-08-30"
    assert row["summary_only"] == 0  # 본문 800자 이상
    assert "일하는 방식" in row["body"]

    # 재수집 시 전량 중복 — 본문 재요청 없음 (2단계 구조)
    calls_before = len(client.calls)
    stats2 = hcol.collect_source(SOURCE, conn, client)
    assert stats2["new"] == 0 and stats2["dup"] == 2
    assert not any("first-article" in c for c in client.calls[calls_before:])


def test_collect_respects_robots(test_db, hcol):
    conn, db = test_db
    client = FakeClient({
        "https://ex.com/robots.txt": FakeResponse(
            200, "User-agent: *\nDisallow: /news/second-article"),
        "https://ex.com/news": FakeResponse(200, LIST_HTML),
        "https://ex.com/news/first-article": FakeResponse(200, ARTICLE_HTML),
    })
    stats = hcol.collect_source(SOURCE, conn, client)
    assert stats["new"] == 1 and stats["robots"] == 1  # 금지 경로는 수집하지 않음


def test_collect_pdf_body(test_db, hcol, monkeypatch):
    conn, db = test_db
    pdf_source = dict(SOURCE, id="test-pdf",
                      link_pattern=r'href="(/news/[a-z0-9\-]+\.pdf)"')
    list_pdf = '<a href="/news/report-a.pdf">r</a>'
    client = FakeClient({
        "https://ex.com/robots.txt": FakeResponse(200, "User-agent: *\nAllow: /"),
        "https://ex.com/news": FakeResponse(200, list_pdf),
        "https://ex.com/news/report-a.pdf": FakeResponse(
            200, content=b"%PDF-fake", content_type="application/pdf"),
    })
    monkeypatch.setattr(hcol, "pdf_to_text", lambda data: "PDF에서 추출한 본문. " * 60)
    stats = hcol.collect_source(pdf_source, conn, client)
    assert stats["new"] == 1
    row = conn.execute("SELECT body, summary_only FROM documents").fetchone()
    assert row["body"].startswith("PDF에서 추출한 본문")


def test_follow_pdf_replaces_intro_page_body(test_db, hcol, monkeypatch):
    """follow_pdf: 소개 페이지의 PDF 링크를 따라가 더 긴 PDF 텍스트를 본문으로 쓴다."""
    conn, db = test_db
    src = dict(SOURCE, id="test-follow", follow_pdf=True)
    intro = ('<html><head><title>리포트 소개</title></head><body>'
             '<p>본 보고서는 소개 요약입니다.</p>'
             '<a href="/files/report.pdf">PDF 다운로드</a></body></html>')
    client = FakeClient({
        "https://ex.com/robots.txt": FakeResponse(200, "User-agent: *\nAllow: /"),
        "https://ex.com/news": FakeResponse(200, '<a href="/news/report-intro">r</a>'),
        "https://ex.com/news/report-intro": FakeResponse(200, intro),
        "https://ex.com/files/report.pdf": FakeResponse(
            200, content=b"%PDF-fake", content_type="application/pdf"),
    })
    monkeypatch.setattr(hcol, "pdf_to_text", lambda data: "PDF 전문 본문. " * 100)
    stats = hcol.collect_source(src, conn, client)
    assert stats["new"] == 1
    row = conn.execute("SELECT body, title FROM documents").fetchone()
    assert row["body"].startswith("PDF 전문 본문")   # PDF 텍스트로 대체
    assert row["title"] == "리포트 소개"              # 제목은 소개 페이지에서


def test_pdf_to_text_parses_real_pdf(hcol):
    from io import BytesIO
    from pypdf import PdfWriter
    buf = BytesIO()
    w = PdfWriter()
    w.add_blank_page(width=200, height=200)
    w.write(buf)
    assert isinstance(hcol.pdf_to_text(buf.getvalue()), str)  # 파싱 자체가 성공


def test_list_failure_marks_source_failed(test_db, hcol):
    conn, db = test_db
    client = FakeClient(default=httpx.ConnectError("down"))
    stats = hcol.collect_source(SOURCE, conn, client)
    assert stats["failed"] == -1


def test_run_returns_stats_and_respects_lock(test_db, hcol, monkeypatch):
    conn, db = test_db
    monkeypatch.setattr(hcol, "SOURCES_PATH", None)  # 호출되면 안 됨
    db.begin_collection(conn, "h")
    db.finish_collection(conn, ok=True)
    assert hcol.run() == {"targets": 0, "failed": 0}  # 오늘 완료 → 조기 종료


# ---------- 무유입 경보 ----------

def _mk_sources():
    return [
        {"id": "fresh-rss", "type": "rss", "status": "active"},
        {"id": "stale-html", "type": "html", "status": "active"},
        {"id": "never-html", "type": "html", "status": "active"},
        {"id": "slow-ok", "type": "rss", "status": "active", "inflow_alert_days": 35},
        {"id": "optout", "type": "html", "status": "active", "inflow_alert": False},
        {"id": "newsletter-src", "type": "newsletter", "status": "active"},
        {"id": "excluded-src", "type": "rss", "status": "excluded"},
    ]


def test_inflow_alerts(test_db):
    conn, db = test_db
    import collectors.collect as collect

    now = datetime.now(timezone.utc)
    rows = [("D1", "fresh-rss", now - timedelta(days=1)),
            ("D2", "stale-html", now - timedelta(days=10)),
            ("D4", "slow-ok", now - timedelta(days=20)),
            ("D5", "optout", now - timedelta(days=100))]
    for did, sid, ts in rows:
        conn.execute(
            "INSERT INTO documents (id, source_id, tier, url, collected_at) VALUES (?,?,?,?,?)",
            (did, sid, "T3", f"http://x/{did}", ts.strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()

    alerts = collect.inflow_alerts(conn, _mk_sources())
    text = "\n".join(alerts)
    assert "stale-html — 10일째" in text
    assert "never-html — 유입 기록 없음" in text
    assert "fresh-rss" not in text          # 어제 유입 → 정상
    assert "slow-ok" not in text            # 기준 35일 완화 → 정상
    assert "optout" not in text             # 경보 제외
    assert "newsletter-src" not in text     # 자동 수집 유형 아님
    assert "excluded-src" not in text

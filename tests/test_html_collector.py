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


# ---------- /ingest-file (브라우저 경로 진입점) ----------

def test_ingest_file_new_dup_and_missing_fields(test_db, tmp_path, monkeypatch):
    conn, db = test_db
    import collectors.ingest_file as ing
    monkeypatch.setattr(ing, "load_source",
                        lambda sid: {"id": sid, "tier": "T2", "type": "browse", "lang": "en"}
                        if sid == "knowledge-wharton" else None)

    doc = tmp_path / "knowledge-wharton_2026-08-24_test.md"
    doc.write_text("---\nsource_id: knowledge-wharton\nurl: http://x/a\n"
                   "title: 테스트\npublished: 2026-08-24\nfetched_by: browse\n---\n"
                   + "본문 원문 그대로. " * 100, encoding="utf-8")
    assert ing.ingest(doc, conn) == "new"
    assert (tmp_path / "ingested" / doc.name).exists()  # 처리 후 이동
    row = conn.execute("SELECT * FROM documents WHERE url='http://x/a'").fetchone()
    assert row["source_id"] == "knowledge-wharton" and row["published_at"] == "2026-08-24"

    dup = tmp_path / "dup.md"
    dup.write_text("---\nsource_id: knowledge-wharton\nurl: http://x/a\ntitle: 테스트\n---\n다른 본문",
                   encoding="utf-8")
    assert ing.ingest(dup, conn) == "dup"  # URL 중복 — 자동 수집과 동일 규칙

    bad = tmp_path / "bad.md"
    bad.write_text("---\nsource_id: knowledge-wharton\n---\n본문", encoding="utf-8")
    assert ing.ingest(bad, conn) == "error"  # url/title 누락
    assert bad.exists()  # 오류 파일은 이동하지 않음


def test_ingest_pdf_pair(test_db, tmp_path, monkeypatch):
    """PDF + 동명 .yaml 머리말 쌍: pypdf 추출로 등재, 두 파일 모두 ingested/ 이동."""
    conn, db = test_db
    import collectors.ingest_file as ing
    src = {"id": "samjong-kpmg", "tier": "T2", "type": "browse", "lang": "ko"}
    monkeypatch.setattr(ing, "load_source",
                        lambda sid: src if sid == "samjong-kpmg" else None)
    monkeypatch.setattr(ing, "pdf_to_text", lambda data: "PDF에서 추출한 리포트 본문. " * 60)

    pdf = tmp_path / "report-a.pdf"
    pdf.write_bytes(b"%PDF-fake")
    (tmp_path / "report-a.yaml").write_text(
        "source_id: samjong-kpmg\nurl: http://x/report-a\ntitle: 리포트A\n"
        "published: 2026-08-30\nfetched_by: browse\n", encoding="utf-8")
    assert ing.ingest(pdf, conn) == "new"
    assert (tmp_path / "ingested" / "report-a.pdf").exists()
    assert (tmp_path / "ingested" / "report-a.yaml").exists()
    row = conn.execute("SELECT * FROM documents WHERE url='http://x/report-a'").fetchone()
    assert row["body"].startswith("PDF에서 추출한 리포트 본문")
    assert row["summary_only"] == 0 and row["fetched_by"] == "browse"

    # .yaml 짝 없는 PDF는 오류 — 파일은 이동하지 않음
    orphan = tmp_path / "orphan.pdf"
    orphan.write_bytes(b"%PDF-fake")
    assert ing.ingest(orphan, conn) == "error"
    assert orphan.exists()


def test_ingest_file_upgrades_summary_only_doc(test_db, tmp_path, monkeypatch):
    """격상: RSS가 요약만 준 문서(summary_only=1)를 브라우저 전문으로 교체하고
    추출 대기(status=new)로 되돌린다. 임계 미달이면 격상하지 않는다."""
    conn, db = test_db
    import collectors.ingest_file as ing
    from collectors.store import store_document
    src = {"id": "knowledge-wharton", "tier": "T2", "type": "html", "lang": "en"}
    monkeypatch.setattr(ing, "load_source",
                        lambda sid: src if sid == "knowledge-wharton" else None)

    # RSS 요약만 등재된 상태 (800자 미만 → summary_only=1)
    assert store_document(conn, src, url="http://x/up", title="요약",
                          text="피드가 제공한 짧은 요약. " * 15) == "new"
    conn.execute("UPDATE documents SET status='enriched' WHERE url='http://x/up'")
    row = conn.execute("SELECT summary_only FROM documents WHERE url='http://x/up'").fetchone()
    assert row["summary_only"] == 1

    # 더 길지만 여전히 800자 미만 → 격상하지 않고 중복 유지
    short = tmp_path / "short.md"
    short.write_text("---\nsource_id: knowledge-wharton\nurl: http://x/up\ntitle: 조금 긴 요약\n---\n"
                     + "여전히 요약 수준. " * 30, encoding="utf-8")
    assert ing.ingest(short, conn) == "dup"

    # 브라우저 전문(임계 통과·기존보다 김) → 격상
    full = tmp_path / "full.md"
    full.write_text("---\nsource_id: knowledge-wharton\nurl: http://x/up\n"
                    "title: 전문\nfetched_by: browse\n---\n"
                    + "브라우저로 확보한 전문 본문. " * 100, encoding="utf-8")
    assert ing.ingest(full, conn) == "upgraded"
    row = conn.execute("SELECT * FROM documents WHERE url='http://x/up'").fetchone()
    assert row["summary_only"] == 0
    assert row["status"] == "new"                      # 추출 대기로 복귀
    assert row["fetched_by"] == "browse"
    assert row["body"].startswith("브라우저로 확보한 전문 본문")
    assert (tmp_path / "ingested" / "full.md").exists()

    # 이미 전문인 문서에 재등재 → 현행 중복 규칙 유지
    again = tmp_path / "again.md"
    again.write_text("---\nsource_id: knowledge-wharton\nurl: http://x/up\ntitle: 재등재\n---\n"
                     + "또 다른 전문 텍스트. " * 200, encoding="utf-8")
    assert ing.ingest(again, conn) == "dup"


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

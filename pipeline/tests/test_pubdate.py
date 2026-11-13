"""발행일 추출(collectors/pubdate.py)·수집기 연결·소급 도구 테스트 — 네트워크 불필요.

2026-09-30: 발행일이 비어 토픽 발굴에서 빠지던 claim 약 386건(NBER·Stanford HAI·AI랩·WorkLab) 대응.
"""
import sys
from datetime import date, timedelta
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
        if mod in ("db", "handoff") or mod.startswith("collectors"):
            del sys.modules[mod]
    import db
    import handoff
    monkeypatch.setattr(handoff, "ensure_active", lambda *a, **k: None)
    conn = db.connect()
    db.migrate(conn)
    yield conn, db
    conn.close()


class FakeResponse:
    def __init__(self, status_code=200, text=""):
        self.status_code = status_code
        self.text = text
        self.content = text.encode("utf-8")
        self.headers = {"content-type": "text/html"}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPError(f"HTTP {self.status_code}")


class FakeClient:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append(url)
        return self.responses.get(url, FakeResponse(404, ""))


BODY = "<p>" + "AI 도입이 일하는 방식에 미치는 영향 분석. " * 40 + "</p>"


# --------------------------------------------------------------------------- #
# 추출기                                                                       #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("html,expected", [
    ('<meta property="article:published_time" content="2026-09-25T16:58:00.000Z"/>', "2026-09-25"),
    ('<meta content="2026-09-25T16:58:00Z" property="article:published_time">', "2026-09-25"),  # 속성 순서
    ('{"@type":"Article","datePublished":"2026-07-08T09:00:00Z"}', "2026-07-08"),
    ('<meta name="citation_publication_date" content="2026/09/28" />', "2026-09-28"),        # NBER
    ('<meta name="citation_date" content="2026-9-3">', "2026-09-03"),
    ('<meta name="DC.date.issued" content="2025-12-01">', "2025-12-01"),
    ('<time dateTime="2026-09-25T16:58:00.000Z">Sep 25, 2026</time>', "2026-09-25"),         # 대문자 T
])
def test_extracts_standard_markup(html, expected):
    from collectors.pubdate import extract_published
    assert extract_published(html) == expected


def test_ignores_modified_dates():
    """수정일은 발행일이 아니다 — 옛 글이 최근 글로 둔갑하면 토픽 급증도가 오염된다."""
    from collectors.pubdate import extract_published
    html = ('<meta property="article:modified_time" content="2026-09-25"/>'
            '"dateModified":"2026-09-25"')
    assert extract_published(html) is None


def test_text_dates_only_when_enabled():
    """본문 글자 날짜는 오인 위험이 있어 소스가 켠 경우만(date_from_text) — Stanford HAI."""
    from collectors.pubdate import extract_published
    html = "<div class='date'>September 25, 2026</div><p>Founded on March 3, 2019</p>"
    assert extract_published(html) is None
    assert extract_published(html, text_dates=True) == "2026-09-25"   # 첫 번째 것


def test_rejects_future_and_impossible_dates():
    from collectors.pubdate import extract_published
    future = (date.today() + timedelta(days=30)).isoformat()
    assert extract_published(f'"datePublished":"{future}"') is None
    assert extract_published('<meta name="citation_date" content="2026/02/30">') is None
    # 잘못된 첫 후보를 건너뛰고 다음 표기로 넘어간다
    html = f'"datePublished":"{future}" <time datetime="2026-01-05">'
    assert extract_published(html) == "2026-01-05"


# --------------------------------------------------------------------------- #
# 수집기 연결                                                                   #
# --------------------------------------------------------------------------- #
FEED_NO_DATES = """<?xml version="1.0"?><rss version="2.0"><channel><title>t</title>
<link>https://ex.org/new.html</link>
<item><title>Paper A</title><link>https://ex.org/papers/w1#fromrss</link><description>abs</description></item>
</channel></rss>"""


def test_rss_falls_back_to_page_date_when_feed_has_none(test_db, monkeypatch):
    """NBER처럼 피드에 날짜가 없으면 본문 페이지의 표준 메타에서 찾는다."""
    conn, _ = test_db
    import collectors.rss as rss
    monkeypatch.setattr(rss.time, "sleep", lambda s: None)
    page = f'<html><head><meta name="citation_publication_date" content="2026/09/28"/></head><body>{BODY}</body></html>'
    client = FakeClient({
        "https://ex.org/feed.xml": FakeResponse(200, FEED_NO_DATES),
        "https://ex.org/papers/w1#fromrss": FakeResponse(200, page),
    })
    src = {"id": "t-rss", "tier": "T1", "type": "rss", "lang": "en", "feed_url": "https://ex.org/feed.xml"}
    rss.collect_source(src, conn, client)
    assert conn.execute("SELECT published_at FROM documents").fetchone()["published_at"] == "2026-09-28"


def test_html_list_text_dates_follow_source_flag(test_db, monkeypatch):
    conn, _ = test_db
    import collectors.html_list as h
    monkeypatch.setattr(h.time, "sleep", lambda s: None)
    h._robots_cache.clear()
    page = f"<html><head><title>기사</title></head><body><div>September 25, 2026</div>{BODY}</body></html>"
    responses = {
        "https://ex.com/robots.txt": FakeResponse(200, "User-agent: *\nAllow: /"),
        "https://ex.com/news": FakeResponse(200, '<a href="/news/first-article">1</a>'),
        "https://ex.com/news/first-article": FakeResponse(200, page),
    }
    src = {"id": "t-html", "tier": "T1", "type": "html", "lang": "en",
           "list_url": "https://ex.com/news", "link_pattern": r'href="(/news/[a-z0-9\-]+)"'}
    h.collect_source({**src, "date_from_text": True}, conn, FakeClient(responses))
    assert conn.execute("SELECT published_at FROM documents").fetchone()["published_at"] == "2026-09-25"


# --------------------------------------------------------------------------- #
# 소급 도구                                                                     #
# --------------------------------------------------------------------------- #
def _doc(conn, doc_id, source_id, url, published=None):
    conn.execute(
        "INSERT INTO documents (id, source_id, tier, url, title, body, status, published_at) "
        "VALUES (?,?,?,?,?,?, 'enriched', ?)", (doc_id, source_id, "T1", url, doc_id, "b", published))
    conn.commit()


def test_eligible_sources_skip_no_pubdate_inactive_and_api():
    import collectors.backfill_pubdate as bf
    sources = [
        {"id": "a", "status": "active", "type": "rss"},
        {"id": "b", "status": "active", "type": "html", "no_pubdate": True},   # WorkLab
        {"id": "c", "status": "excluded", "type": "rss"},
        {"id": "d", "status": "active", "type": "api"},                        # arXiv — 날짜 있음
    ]
    assert set(bf.eligible_sources(sources)) == {"a"}
    assert set(bf.eligible_sources(sources, only=["a", "b"])) == {"a"}


def test_backfill_fills_only_missing_and_strips_fragment(test_db, monkeypatch):
    conn, _ = test_db
    import collectors.backfill_pubdate as bf
    _doc(conn, "N1", "nber", "https://ex.org/papers/w1#fromrss")
    _doc(conn, "N2", "nber", "https://ex.org/papers/w2#fromrss")           # 페이지에 날짜 없음
    _doc(conn, "N3", "nber", "https://ex.org/papers/w3", published="2020-01-01")  # 이미 있음
    client = FakeClient({
        "https://ex.org/papers/w1": FakeResponse(200, '<meta name="citation_publication_date" content="2026/09/28"/>'),
        "https://ex.org/papers/w2": FakeResponse(200, "<p>no date</p>"),
    })
    sources = {"nber": {"id": "nber", "status": "active", "type": "rss"}}
    targets = bf.select_targets(conn, ["nber"], None)
    assert {r["id"] for r in targets} == {"N1", "N2"}
    stats = bf.backfill(conn, targets, sources, client, sleep=0)
    got = {r["id"]: r["published_at"] for r in conn.execute("SELECT id, published_at FROM documents")}
    assert got == {"N1": "2026-09-28", "N2": None, "N3": "2020-01-01"}
    assert stats[("nber", "filled")] == 1 and stats[("nber", "no_date")] == 1
    assert "#" not in "".join(client.calls)                                  # 조각 제거 후 요청


def test_backfill_dry_run_changes_nothing(test_db):
    conn, _ = test_db
    import collectors.backfill_pubdate as bf
    _doc(conn, "N1", "nber", "https://ex.org/papers/w1")
    client = FakeClient({"https://ex.org/papers/w1": FakeResponse(200, '"datePublished":"2026-09-01"')})
    bf.backfill(conn, bf.select_targets(conn, ["nber"], None),
                {"nber": {"id": "nber", "type": "rss"}}, client, dry_run=True, sleep=0)
    assert conn.execute("SELECT published_at FROM documents").fetchone()["published_at"] is None

"""API 수집기·수집 게이트 테스트 (네트워크 불필요 — 가짜 클라이언트·픽스처 사용)."""
import sys
from pathlib import Path

import httpx
import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))


@pytest.fixture()
def test_db(tmp_path, monkeypatch):
    monkeypatch.setenv("PIPELINE_DB", str(tmp_path / "test.db"))
    monkeypatch.delenv("DATABASE_URL", raising=False)  # 로컬 테스트는 SQLite 모드 강제
    for mod in ["db"]:
        if mod in sys.modules:
            del sys.modules[mod]
    import db
    conn = db.connect()
    db.migrate(conn)
    yield conn, db
    conn.close()


LONG_ABSTRACT = "AI 도입이 조직의 협업 방식과 인재 운용에 미치는 영향을 분석한다. " * 30  # > 800자
SHORT_ABSTRACT = "짧은 요약."  # < 800자 → summary_only

ARXIV_ATOM = f"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>arXiv Query Results</title>
  <entry>
    <title>AI and the Future of Work</title>
    <link href="http://arxiv.org/abs/2601.00001"/>
    <summary>{LONG_ABSTRACT}</summary>
    <author><name>Kim Researcher</name></author>
    <published>2026-08-20T00:00:00Z</published>
  </entry>
  <entry>
    <title>Short Note</title>
    <link href="http://arxiv.org/abs/2601.00002"/>
    <summary>{SHORT_ABSTRACT}</summary>
    <published>2026-08-21T00:00:00Z</published>
  </entry>
</feed>"""

OSF_JSON = """{
  "data": [
    {"attributes": {"title": "Team Psychological Safety Preprint",
                    "description": "%s",
                    "date_created": "2026-08-19T10:00:00"},
     "links": {"html": "https://osf.io/abc12"}},
    {"attributes": {"title": "Empty One", "description": "",
                    "date_created": "2026-08-18T10:00:00"},
     "links": {"html": "https://osf.io/def34"}}
  ],
  "links": {"next": null}
}""" % ("조직 학습과 심리적 안전감에 관한 프리프린트 요약. " * 40)


class FakeResponse:
    def __init__(self, status_code=200, text=""):
        self.status_code = status_code
        self.text = text

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


@pytest.fixture()
def api(tmp_path, monkeypatch):
    import collectors.api as api_mod
    monkeypatch.setattr(api_mod.time, "sleep", lambda s: None)
    return api_mod


ARXIV_SOURCE = {
    "id": "arxiv-econ-gn", "tier": "T1", "type": "api", "lang": "en",
    "endpoint": "https://export.arxiv.org/api/query",
    "test_query": ("https://export.arxiv.org/api/query?search_query=cat:econ.GN"
                   "&sortBy=submittedDate&sortOrder=descending&max_results=3"),
}
OSF_SOURCE = {
    "id": "psyarxiv", "tier": "T1", "type": "api", "lang": "en",
    "endpoint": "https://api.osf.io/v2/preprints/",
    "test_query": "https://api.osf.io/v2/preprints/?filter[provider]=psyarxiv&page[size]=3",
}


def test_arxiv_collect_dedup_and_summary_only(test_db, api):
    conn, db = test_db
    client = FakeClient({api.arxiv_url(ARXIV_SOURCE): FakeResponse(200, ARXIV_ATOM)})
    stats = api.collect_source(ARXIV_SOURCE, conn, client)
    assert stats == {"seen": 2, "new": 2, "dup": 0, "failed": 0}

    # 재수집 시 전량 중복 (rss와 동일 규칙)
    stats2 = api.collect_source(ARXIV_SOURCE, conn, client)
    assert stats2["new"] == 0 and stats2["dup"] == 2

    rows = {r["url"]: r for r in conn.execute("SELECT * FROM documents")}
    long_doc = rows["http://arxiv.org/abs/2601.00001"]
    short_doc = rows["http://arxiv.org/abs/2601.00002"]
    assert long_doc["summary_only"] == 0
    assert short_doc["summary_only"] == 0          # api 소스(초록형)는 A3 임계 면제
    assert long_doc["tier"] == "T1" and long_doc["status"] == "new"
    assert long_doc["published_at"] == "2026-08-20"


def test_summary_only_threshold_applies_to_rss_but_not_api(test_db):
    """A3 임계: rss는 800자 미만이면 summary_only=1, api(초록형)는 면제."""
    conn, db = test_db
    from collectors.store import store_document
    short = "짧은 본문."
    store_document(conn, {"id": "r", "tier": "T3", "type": "rss"},
                   url="http://x/rss-short", title="t", text=short)
    store_document(conn, {"id": "a", "tier": "T1", "type": "api"},
                   url="http://x/api-short", title="t", text=short + " 다른 내용")
    rows = {r["url"]: r["summary_only"] for r in
            conn.execute("SELECT url, summary_only FROM documents")}
    assert rows["http://x/rss-short"] == 1
    assert rows["http://x/api-short"] == 0
    # 빈 본문은 유형과 무관하게 저장 자체를 거부
    assert store_document(conn, {"id": "a", "tier": "T1", "type": "api"},
                          url="http://x/api-empty", title="t", text="  ") == "empty"


def test_osf_collect_json(test_db, api):
    conn, db = test_db
    client = FakeClient({api.osf_url(OSF_SOURCE): FakeResponse(200, OSF_JSON)})
    stats = api.collect_source(OSF_SOURCE, conn, client)
    # 설명이 빈 항목은 empty → failed로 집계
    assert stats == {"seen": 2, "new": 1, "dup": 0, "failed": 1}
    row = conn.execute("SELECT * FROM documents").fetchone()
    assert row["url"] == "https://osf.io/abc12"
    assert row["published_at"] == "2026-08-19"


def test_arxiv_backfill_builds_range_and_paginates(test_db, api, monkeypatch):
    conn, db = test_db
    monkeypatch.setattr(api, "PAGE_SIZE", 2)
    bf = ("2026-01-01", "2026-06-30")
    url0 = api.arxiv_url(ARXIV_SOURCE, 0, bf)
    url1 = api.arxiv_url(ARXIV_SOURCE, 2, bf)
    assert "submittedDate%3A%5B202601010000+TO+202606302359%5D" in url0
    assert "start=2" in url1

    one_entry = ARXIV_ATOM.replace(
        '<link href="http://arxiv.org/abs/2601.00001"/>',
        '<link href="http://arxiv.org/abs/2601.00003"/>').replace(
        LONG_ABSTRACT, "세 번째 논문의 고유한 요약 — 원격 협업과 성과 측정. " * 30).split("<entry>")
    page1 = one_entry[0] + "<entry>" + one_entry[1] + "</feed>"  # 항목 1건 → 마지막 페이지
    client = FakeClient({url0: FakeResponse(200, ARXIV_ATOM),   # 2건 (가득) → 다음 페이지
                         url1: FakeResponse(200, page1)})
    stats = api.collect_source(ARXIV_SOURCE, conn, client, backfill=bf)
    assert client.calls == [url0, url1]
    assert stats["seen"] == 3 and stats["new"] == 3


def test_unsupported_api_source_marked_failed(test_db, api):
    conn, db = test_db
    s = {"id": "x", "tier": "T3", "type": "api", "test_query": "https://unknown.com/api"}
    stats = api.collect_source(s, conn, FakeClient())
    assert stats["failed"] == -1


def test_backfill_arg_validation(api):
    with pytest.raises(SystemExit):
        api._parse_args(["--backfill", "2026-01-01", "bad-date"])
    with pytest.raises(SystemExit):
        api._parse_args(["--backfill", "2026-06-30", "2026-01-01"])  # 순서 역전
    a = api._parse_args(["--backfill", "2026-01-01", "2026-06-30", "arxiv-econ-gn"])
    assert a.backfill == ["2026-01-01", "2026-06-30"] and a.ids == ["arxiv-econ-gn"]


def test_cross_collector_dedup(test_db, api, tmp_path):
    """rss가 먼저 저장한 URL은 api 수집에서 중복 처리 — 공용 store 규칙."""
    conn, db = test_db
    from collectors.store import store_document
    store_document(conn, {"id": "rss-src", "tier": "T3"}, url="http://arxiv.org/abs/2601.00001",
                   title="이미 수집됨", text="x" * 900)
    client = FakeClient({api.arxiv_url(ARXIV_SOURCE): FakeResponse(200, ARXIV_ATOM)})
    stats = api.collect_source(ARXIV_SOURCE, conn, client)
    assert stats["dup"] == 1 and stats["new"] == 1


# ---------- enrich 게이트 (A1·A3) ----------

def test_select_target_docs_excludes_summary_only(test_db):
    conn, db = test_db
    import enrich.extract_claims as ec
    for i, so in enumerate([0, 1]):
        conn.execute(
            "INSERT INTO documents (id, source_id, tier, url, body, status, summary_only) "
            "VALUES (?,?,?,?,?,'new',?)",
            (f"D{i}", "s", "T1", f"http://x/{i}", "본문 텍스트", so))
    conn.commit()
    docs = ec.select_target_docs(conn, 10)
    assert [d["id"] for d in docs] == ["D0"]  # summary_only=1 제외


def test_check_relevance_parses_verdict(monkeypatch):
    import enrich.extract_claims as ec
    monkeypatch.setattr(ec, "call_model", lambda prompt, model: "IRRELEVANT")
    assert ec.check_relevance("제목", "본문", "m") is False
    monkeypatch.setattr(ec, "call_model", lambda prompt, model: "relevant — 관련 문서")
    assert ec.check_relevance("제목", "본문", "m") is True

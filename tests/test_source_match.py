"""수기 등록 소스 자동 판별 테스트 (/ingest-url · /ingest-file — 네트워크 불필요)."""
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from collectors.source_match import (  # noqa: E402
    SourceResolveError, detect_source, load_sources, resolve_source)

# 판별 규칙 단위 테스트용 소스 목록 (실제 sources.yaml과 무관한 가상 주소)
FAKE = [
    {"id": "corp-a", "tier": "T2", "status": "active", "type": "browse",
     "homepage": "https://www2.corp-a.test/us/en/insights.html"},
    {"id": "corp-b-lab", "tier": "T4", "status": "active", "type": "html",
     "list_url": "https://www.corp-b.test/en-us/lab", "homepage": "https://www.corp-b.test/en-us/lab"},
    {"id": "blog-c", "tier": "T5", "status": "active", "type": "rss",
     "feed_url": "https://blog-c.test/feed/"},
    {"id": "pre-x", "tier": "T1", "status": "active", "type": "api", "feed_url": "https://rss.pre.test/x"},
    {"id": "pre-y", "tier": "T1", "status": "active", "type": "api", "feed_url": "https://rss.pre.test/y"},
    {"id": "gone", "tier": "T3", "status": "excluded", "type": "rss", "feed_url": "https://gone.test/feed"},
]


@pytest.mark.parametrize("url,expected", [
    ("https://www.corp-a.test/us/en/insights/topics/talent/x.html", "corp-a"),  # www2↔www
    ("https://corp-a.test/us/en/insights", "corp-a"),
    ("https://www.corp-a.test/us/en/insightsfoo/x", None),     # 경로 구간 경계에서만 일치
    ("https://www.corp-a.test/kr/ko/other", None),              # 경로 접두 밖
    ("https://www.corp-b.test/en-us/lab/report-2026", "corp-b-lab"),
    ("https://www.corp-b.test/en-us/research/x", None),
    ("https://blog-c.test/2026/10/post/", "blog-c"),            # feed_url은 호스트만
    ("https://pre.test/abs/1234", None),                        # 여러 소스 겹침 → 실패
    ("https://gone.test/a", None),                              # excluded는 후보 아님
    ("https://unknown.test/a", None),
])
def test_detect_rules(url, expected):
    source, note = detect_source(url, FAKE)
    assert (source["id"] if source else None) == expected
    assert note  # 판별 결과 설명은 항상 있음


@pytest.mark.parametrize("url,expected", [
    ("https://joshbersin.com/2026/03/the-ai-transformation-of-hr/", "josh-bersin"),
    ("https://www.deloitte.com/us/en/insights/topics/talent/human-capital-trends.html",
     "deloitte-insights"),
    ("https://www.microsoft.com/en-us/worklab/work-trend-index", "ms-worklab"),
    ("https://www.anthropic.com/research/economic-index", "ai-lab-enterprise-reports"),
])
def test_detect_real_sources_yaml(url, expected):
    """실제 sources.yaml 기준 — 2026-10-20 manual 재매핑 대상 발행처가 자동 판별되는지."""
    source, _ = detect_source(url, load_sources())
    assert source is not None and source["id"] == expected


def test_resolve_fallback_manual_and_tier():
    src, note = resolve_source("https://unknown.test/a", sources=FAKE)
    assert src == {"id": "manual", "tier": "T5"} and "manual" in note
    src, _ = resolve_source("https://unknown.test/a", tier="T3", sources=FAKE)
    assert src["id"] == "manual" and src["tier"] == "T3"
    # 판별되는 URL도 --source manual이면 수기
    src, _ = resolve_source("https://blog-c.test/p", "manual", "T2", sources=FAKE)
    assert src == {"id": "manual", "tier": "T2"}


def test_resolve_explicit_source_and_tier_mismatch():
    src, _ = resolve_source("https://anything.test/x", "corp-a", sources=FAKE)
    assert src["id"] == "corp-a" and src["tier"] == "T2"
    assert resolve_source("https://anything.test/x", "corp-a", "T2", sources=FAKE)[0]["id"] == "corp-a"
    with pytest.raises(SourceResolveError, match="tier 불일치"):
        resolve_source("https://anything.test/x", "corp-a", "T3", sources=FAKE)
    with pytest.raises(SourceResolveError, match="tier 불일치"):   # 자동 판별 + tier 불일치
        resolve_source("https://blog-c.test/p", tier="T1", sources=FAKE)
    with pytest.raises(SourceResolveError, match="없는 소스"):
        resolve_source("https://x.test", "no-such", sources=FAKE)
    with pytest.raises(SourceResolveError, match="excluded"):
        resolve_source("https://x.test", "gone", sources=FAKE)


# ---------- CLI·등재 경로 ----------

@pytest.fixture()
def test_db(tmp_path, monkeypatch):
    monkeypatch.setenv("PIPELINE_DB", str(tmp_path / "test.db"))
    monkeypatch.delenv("DATABASE_URL", raising=False)  # SQLite 로컬 모드 강제
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


def test_ingest_url_tier_mismatch_stops_before_fetch(test_db, monkeypatch, capsys):
    import collectors.ingest_url as iu

    def no_network(*a, **k):
        raise AssertionError("tier 불일치면 접속 전에 멈춰야 함")
    monkeypatch.setattr(iu.httpx, "Client", no_network)
    assert iu.main(["https://joshbersin.com/x/", "--tier", "T3"]) == 2
    assert iu.main(["https://x.test/a", "--source", "josh-bersin", "--tier", "T5"]) == 2
    assert "tier 불일치" in capsys.readouterr().out


def test_ingest_url_stores_detected_source(test_db, monkeypatch, capsys):
    conn, _ = test_db
    import collectors.ingest_url as iu

    class FakeResp:
        text = "<html><head><title>T</title></head><body><article><p>" + "본문 " * 300 \
               + "</p></article></body></html>"

        def raise_for_status(self):
            pass

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get(self, *a, **k):
            return FakeResp()

    monkeypatch.setattr(iu.httpx, "Client", FakeClient)
    monkeypatch.setattr(iu.trafilatura, "extract", lambda html, **k: "본문 원문. " * 200)
    assert iu.main(["https://joshbersin.com/2026/10/a/"]) == 0
    assert "자동 판별: josh-bersin" in capsys.readouterr().out
    row = conn.execute("SELECT source_id, tier FROM documents").fetchone()
    assert (row["source_id"], row["tier"]) == ("josh-bersin", "T2")

    monkeypatch.setattr(iu.trafilatura, "extract", lambda html, **k: "다른 본문. " * 200)
    assert iu.main(["https://unknown.test/b", "--tier", "T3"]) == 0
    row = conn.execute("SELECT source_id, tier FROM documents WHERE url='https://unknown.test/b'").fetchone()
    assert (row["source_id"], row["tier"]) == ("manual", "T3")


def test_ingest_file_blank_source_id_auto_detects(test_db, tmp_path):
    conn, _ = test_db
    import collectors.ingest_file as ing

    hit = tmp_path / "hit.md"
    hit.write_text("---\nsource_id:\nurl: https://joshbersin.com/2026/10/b/\ntitle: 판별\n---\n"
                   + "본문 원문 그대로. " * 100, encoding="utf-8")
    assert ing.ingest(hit, conn) == "new"
    miss = tmp_path / "miss.md"
    miss.write_text("---\nurl: https://unknown.test/c\ntitle: 실패\ntier: T4\n---\n"
                    + "다른 본문 원문. " * 100, encoding="utf-8")
    assert ing.ingest(miss, conn) == "new"
    rows = {r["url"]: (r["source_id"], r["tier"]) for r in
            conn.execute("SELECT url, source_id, tier FROM documents").fetchall()}
    assert rows["https://joshbersin.com/2026/10/b/"] == ("josh-bersin", "T2")
    assert rows["https://unknown.test/c"] == ("manual", "T4")

    bad = tmp_path / "bad.md"
    bad.write_text("---\nurl: https://joshbersin.com/2026/10/d/\ntitle: 불일치\ntier: T1\n---\n"
                   + "또 다른 본문. " * 100, encoding="utf-8")
    assert ing.ingest(bad, conn) == "error" and bad.exists()

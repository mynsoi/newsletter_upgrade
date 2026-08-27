"""validate_sources 경로 배정·유형별 검증 테스트 (네트워크 불필요 — 가짜 클라이언트 사용)."""
import sys
from pathlib import Path

import httpx
import pytest
import yaml

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

import collectors.validate_sources as vs  # noqa: E402

FEED_XML = (Path(__file__).parent / "fixtures" / "sample_feed.xml").read_text(encoding="utf-8")

ATOM_XML = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>arXiv Query Results</title>
  <entry><title>Paper One</title><id>http://arxiv.org/abs/1</id></entry>
  <entry><title>Paper Two</title><id>http://arxiv.org/abs/2</id></entry>
  <entry><title>Paper Three</title><id>http://arxiv.org/abs/3</id></entry>
</feed>"""

ARXIV_CSCY_QUERY = ("https://export.arxiv.org/api/query?search_query=cat:cs.CY"
                    "&sortBy=submittedDate&sortOrder=descending&max_results=3")
OSF_QUERY = "https://api.osf.io/v2/preprints/?filter[provider]=psyarxiv&page[size]=3"


class FakeResponse:
    def __init__(self, status_code=200, text=""):
        self.status_code = status_code
        self.text = text


class FakeClient:
    """URL별로 지정된 응답(또는 예외)을 돌려주는 httpx.Client 대역. 미지정 URL은 default."""

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

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


# ---------- 유형별 검사 함수 ----------

def test_check_rss_four_steps():
    client = FakeClient({
        "http://ok/feed": FakeResponse(200, FEED_XML),
        "http://404/feed": FakeResponse(404, ""),
        "http://html/feed": FakeResponse(200, "<html><body>not a feed</body></html>"),
        "http://down/feed": httpx.ConnectError("boom"),
    })
    ok, msg = vs.check_rss({"feed_url": "http://ok/feed"}, client)
    assert ok and "항목 2건" in msg
    assert vs.check_rss({}, client) == (False, "feed_url 없음")
    assert vs.check_rss({"feed_url": "http://404/feed"}, client)[1] == "HTTP 404"
    assert not vs.check_rss({"feed_url": "http://html/feed"}, client)[0]
    assert "접속 실패" in vs.check_rss({"feed_url": "http://down/feed"}, client)[1]


def test_check_api_atom_json_and_failures():
    client = FakeClient({
        "http://api/atom": FakeResponse(200, ATOM_XML),
        "http://api/json": FakeResponse(200, '{"items": [{"a": 1}, {"a": 2}]}'),
        "http://api/json-nested": FakeResponse(200, '{"feed": {"entry": [1, 2, 3]}}'),
        "http://api/json-empty": FakeResponse(200, '{"items": []}'),
        "http://api/garbage": FakeResponse(200, "%%% not parseable %%%"),
        "http://api/500": FakeResponse(500, ""),
    })
    ok, msg = vs.check_api({"test_query": "http://api/atom"}, client)
    assert ok and "항목 3건" in msg
    ok, msg = vs.check_api({"test_query": "http://api/json"}, client)
    assert ok and "항목 2건" in msg
    ok, msg = vs.check_api({"test_query": "http://api/json-nested"}, client)
    assert ok and "항목 3건" in msg
    assert not vs.check_api({"test_query": "http://api/json-empty"}, client)[0]
    assert "파싱 실패" in vs.check_api({"test_query": "http://api/garbage"}, client)[1]
    assert vs.check_api({"test_query": "http://api/500"}, client)[1] == "HTTP 500"
    ok, msg = vs.check_api({}, client)
    assert not ok and "test_query 없음" in msg


def test_check_newsletter_status_management():
    s = {}
    status, msg = vs.check_newsletter(s)
    assert status == "구독 대기" and s["subscription_status"] == "구독 대기"
    assert "자동 검증 불가" in msg and "A4 인박스" in msg

    s = {"subscription_status": "수신 확인됨"}
    assert vs.check_newsletter(s)[0] == "수신 확인됨"

    s = {"subscription_status": "이상한값"}
    status, msg = vs.check_newsletter(s)
    assert status == "구독 대기" and "알 수 없는 상태" in msg


def test_set_auto_note_preserves_human_note():
    s = {"note": "사람이 적은 메모"}
    vs.set_auto_note(s, "실패 사유 X")
    assert s["note"].startswith("사람이 적은 메모 / [자동검증 ")
    assert "실패 사유 X" in s["note"]
    vs.set_auto_note(s, "실패 사유 Y")  # 갱신 시 이전 자동 세그먼트 교체
    assert s["note"].count("[자동검증") == 1 and "실패 사유 Y" in s["note"]
    vs.set_auto_note(s, None)  # 성공 시 자동 세그먼트 제거, 사람 메모 보존
    assert s["note"] == "사람이 적은 메모"
    s2 = {}
    vs.set_auto_note(s2, "사유")
    vs.set_auto_note(s2, None)
    assert "note" not in s2


# ---------- 경로 배정 (1순위 API → 2순위 RSS → 3순위 기타) ----------

def test_assign_known_api_arxiv_from_rss_source():
    """arXiv rss 소스는 내장 목록에 의해 api로 승격되고 카테고리를 물려받는다."""
    client = FakeClient({ARXIV_CSCY_QUERY: FakeResponse(200, ATOM_XML)})
    s = {"id": "arxiv-cs-cy", "type": "rss",
         "feed_url": "https://rss.arxiv.org/rss/cs.CY", "verified": True}
    mark, msg = vs.validate_source(s, client)
    assert mark == "OK" and "arXiv API 배정" in msg
    assert s["type"] == "api"
    assert s["endpoint"] == "https://export.arxiv.org/api/query"
    assert "cat:cs.CY" in s["test_query"]
    assert s["verified"] is True


def test_assign_known_api_psyarxiv_json():
    client = FakeClient({OSF_QUERY: FakeResponse(200, '{"data": [1, 2, 3]}')})
    s = {"id": "psyarxiv", "homepage": "https://psyarxiv.com"}
    mark, msg = vs.validate_source(s, client)
    assert mark == "OK" and "OSF" in msg and "항목 3건" in msg
    assert s["type"] == "api" and s["endpoint"] == "https://api.osf.io/v2/preprints/"


def test_existing_test_query_not_overwritten():
    client = FakeClient({"http://custom/q": FakeResponse(200, ATOM_XML)})
    s = {"id": "arxiv-econ", "type": "api",
         "feed_url": "https://rss.arxiv.org/rss/econ.GN", "test_query": "http://custom/q"}
    mark, _ = vs.validate_source(s, client)
    assert mark == "OK" and s["test_query"] == "http://custom/q"


def test_probe_rss_conventional_paths():
    """기존 feed_url 실패 시 관례 경로(/feed 등)를 탐지해 feed_url을 갱신한다."""
    client = FakeClient({"http://site.com/feed": FakeResponse(200, FEED_XML)})  # 그 외 404
    s = {"id": "some-blog", "feed_url": "http://site.com/broken.xml"}
    mark, msg = vs.validate_source(s, client)
    assert mark == "OK"
    assert s["type"] == "rss" and s["feed_url"] == "http://site.com/feed"
    assert s["verified"] is True


def test_fallback_to_newsletter_when_nothing_found():
    client = FakeClient()  # 모든 요청 404 (응답은 받음 → 확정적 실패)
    s = {"id": "no-feed", "type": "rss", "feed_url": "http://nofeed.com/x", "verified": True}
    mark, msg = vs.validate_source(s, client)
    assert mark == "NEWS" and "newsletter 분류" in msg
    assert s["type"] == "newsletter"
    assert s["subscription_status"] == "구독 대기"
    assert "verified" not in s
    assert "[자동검증" in s["note"] and "API·RSS 미발견" in s["note"]


def test_4xx_with_passed_history_not_demoted():
    """실측 통과 이력(note)이 있는 소스가 4xx를 받으면 강등 대신 '환경 차단 의심' 분류."""
    client = FakeClient(default=FakeResponse(403, "Forbidden"))
    s = {"id": "wharton", "type": "rss", "feed_url": "http://w.edu/feed",
         "verified": True, "note": "편입 권고. 2026-08-27 피드 실측 통과"}
    mark, msg = vs.validate_source(s, client)
    assert mark == "FAIL" and "환경 차단 의심" in msg
    assert s["type"] == "rss"            # 강등 금지
    assert s["verified"] is False
    assert "환경 차단 의심(4xx)" in s["note"]
    assert s["note"].startswith("편입 권고")  # 사람 note 보존


def test_4xx_without_passed_history_still_demoted():
    """실측 통과 이력이 없으면 기존대로 newsletter 강등."""
    client = FakeClient(default=FakeResponse(403, "Forbidden"))
    s = {"id": "unknown-src", "type": "rss", "feed_url": "http://x.com/feed"}
    mark, msg = vs.validate_source(s, client)
    assert mark == "NEWS" and s["type"] == "newsletter"


def test_non4xx_definitive_failure_still_demoted_despite_history():
    """4xx가 아닌 확정 실패(파싱 실패 등)는 실측 이력이 있어도 정상 강등."""
    client = FakeClient(default=FakeResponse(200, "<html>not a feed</html>"))
    s = {"id": "gone-src", "type": "rss", "feed_url": "http://x.com/feed",
         "note": "2026-08-20 피드 실측 통과"}
    mark, msg = vs.validate_source(s, client)
    assert mark == "NEWS" and s["type"] == "newsletter"


def test_network_failure_keeps_type():
    """전 후보 접속 실패면 네트워크 문제로 보고 유형을 강등하지 않는다."""
    client = FakeClient(default=httpx.ConnectError("net down"))
    s = {"id": "rss-src", "type": "rss", "feed_url": "https://x.com/feed", "verified": True}
    mark, msg = vs.validate_source(s, client)
    assert mark == "FAIL" and "네트워크 확인 필요" in msg
    assert s["type"] == "rss"  # 강등 금지
    assert s["verified"] is False
    assert "네트워크 확인 필요" in s["note"]


def test_allow_feed_discovery_false_checks_registered_url_only():
    """섹션 한정 소스는 등재된 URL만 검사하고 관례 경로를 탐지하지 않는다."""
    client = FakeClient({"http://news.com/feed": FakeResponse(200, FEED_XML)})  # 관례 경로는 살아 있음
    s = {"id": "chosun-section", "type": "rss",
         "feed_url": "http://news.com/section/it.xml", "allow_feed_discovery": False}
    mark, _ = vs.validate_source(s, client)
    assert client.calls == ["http://news.com/section/it.xml"]  # 탐지 시도 없음
    assert s["feed_url"] == "http://news.com/section/it.xml"   # URL 불변

    # 플래그가 없으면(기본) 탐지가 동작해 /feed를 찾는다
    client2 = FakeClient({"http://news.com/feed": FakeResponse(200, FEED_XML)})
    s2 = {"id": "open-src", "type": "rss", "feed_url": "http://news.com/section/it.xml"}
    mark2, _ = vs.validate_source(s2, client2)
    assert mark2 == "OK" and s2["feed_url"] == "http://news.com/feed"
    assert "확인 필요" in s2["note"]  # URL 변경은 note에 기록


def test_manual_skipped_untouched():
    s = {"id": "leadership-msg", "type": "manual"}
    mark, msg = vs.validate_source(s, FakeClient())
    assert mark == "SKIP" and s == {"id": "leadership-msg", "type": "manual"}


# ---------- main: 표 보고·유형별 집계·파일 갱신·종료 코드 ----------

@pytest.fixture()
def sources_file(tmp_path, monkeypatch):
    path = tmp_path / "sources.yaml"
    monkeypatch.setattr(vs, "SOURCES_PATH", path)
    return path


def write_sources(path, sources):
    path.write_text(yaml.dump({"sources": sources}, allow_unicode=True, sort_keys=False),
                    encoding="utf-8")


def test_main_table_summary_and_updates(sources_file, monkeypatch, capsys):
    write_sources(sources_file, [
        {"id": "arxiv-cs-cy", "type": "rss",
         "feed_url": "https://rss.arxiv.org/rss/cs.CY", "verified": True},
        {"id": "rss-ok", "type": "rss", "feed_url": "http://ok.com/feed", "verified": False},
        {"id": "rss-dead", "type": "rss", "feed_url": "http://dead.com/feed", "verified": True},
        {"id": "news-1", "type": "newsletter"},
        {"id": "man-1", "type": "manual"},
    ])
    client = FakeClient({
        ARXIV_CSCY_QUERY: FakeResponse(200, ATOM_XML),
        "http://ok.com/feed": FakeResponse(200, FEED_XML),
    })  # 그 외 404 → rss-dead는 newsletter로 분류
    monkeypatch.setattr(vs.httpx, "Client", lambda **kw: client)

    rc = vs.main()
    out = capsys.readouterr().out

    assert rc == 0  # FAIL 없음 (NEWS·SKIP은 실패가 아님)
    assert "rss→api" in out          # 표에 유형 전환 표시
    assert "api        : 1/1 통과" in out
    assert "rss        : 1/1 통과" in out
    assert "수신 확인됨 0 / 구독 대기 2" in out
    assert "manual     : 1건 SKIP" in out
    assert "검증 결과: 2/2 통과" in out

    saved = {s["id"]: s for s in
             yaml.safe_load(sources_file.read_text(encoding="utf-8"))["sources"]}
    assert saved["arxiv-cs-cy"]["type"] == "api" and saved["arxiv-cs-cy"]["verified"] is True
    assert saved["rss-ok"]["verified"] is True
    assert saved["rss-dead"]["type"] == "newsletter"
    assert saved["rss-dead"]["subscription_status"] == "구독 대기"
    assert "[자동검증" in saved["rss-dead"]["note"]
    assert saved["news-1"]["subscription_status"] == "구독 대기"
    assert saved["man-1"] == {"id": "man-1", "type": "manual"}


def test_main_reports_url_changes_separately(sources_file, monkeypatch, capsys):
    write_sources(sources_file, [
        {"id": "moved-feed", "type": "rss", "feed_url": "http://site.com/broken.xml"},
        {"id": "stable-feed", "type": "rss", "feed_url": "http://ok.com/feed"},
    ])
    client = FakeClient({
        "http://site.com/feed": FakeResponse(200, FEED_XML),
        "http://ok.com/feed": FakeResponse(200, FEED_XML.replace("productivity", "workforce")),
    })
    monkeypatch.setattr(vs.httpx, "Client", lambda **kw: client)
    vs.main()
    out = capsys.readouterr().out
    assert "URL 변경 — 확인 필요:" in out
    assert "moved-feed: http://site.com/broken.xml → http://site.com/feed" in out
    assert "stable-feed" not in out.split("URL 변경 — 확인 필요:")[1].split("유형별 집계")[0]

    saved = {s["id"]: s for s in
             yaml.safe_load(sources_file.read_text(encoding="utf-8"))["sources"]}
    assert "확인 필요" in saved["moved-feed"]["note"]
    assert "note" not in saved["stable-feed"]


def test_main_network_failure_exit_code(sources_file, monkeypatch):
    write_sources(sources_file, [
        {"id": "rss-src", "type": "rss", "feed_url": "https://x.com/feed", "verified": True},
    ])
    client = FakeClient(default=httpx.ConnectError("net down"))
    monkeypatch.setattr(vs.httpx, "Client", lambda **kw: client)
    assert vs.main() == 1
    saved = yaml.safe_load(sources_file.read_text(encoding="utf-8"))["sources"][0]
    assert saved["type"] == "rss" and saved["verified"] is False

"""sources.yaml의 모든 소스에 수집 경로를 배정하고 유형별로 검증한다.

사용: make validate  (또는 python src/collectors/validate_sources.py)

경로 배정 원칙 (소스마다 1순위 → 3순위 순서로 시도):
1. API   — 공식 API가 알려진 도메인(arXiv, PsyArXiv/OSF 등 KNOWN_APIS 내장 목록)이면
           type: api + endpoint 기록, test_query 자동 생성(없을 때만).
2. RSS   — 기존 feed_url과 관례 경로(/feed, /rss, /feed.xml 등)를 탐지해
           통과하는 URL이 있으면 type: rss + feed_url 기록.
3. 기타  — 둘 다 없으면 type: newsletter로 분류(자동 검증 불가 —
           subscription_status로 관리). type: manual은 사람의 결정이므로
           배정·검사 없이 SKIP 유지.

유형별 검사:
- api:        test_query 1건 실행 → 응답 파싱(Atom/RSS 또는 JSON)·항목 수 확인 → verified
- rss:        4단계 검사(feed_url 존재 → 접속 → HTTP 200 → 파싱·항목 수) → verified
- newsletter: "구독 대기"/"수신 확인됨" 상태만 관리. 수신 확인은 A4 인박스 구축 후
              실제 도착 메일 존재로만 판정한다.
- manual:     검증 대상 아님(SKIP).

안전장치: 모든 시도가 접속 실패(응답 자체를 못 받음)인 소스는 네트워크 문제로 보고
유형을 바꾸지 않는다(verified만 false + note). 사내망처럼 외부 https가 막힌 환경에서
정상 소스가 newsletter로 강등되는 것을 막기 위함이다.

검증 결과는 verified·type·실패 사유(note의 "[자동검증 날짜]" 세그먼트)로
sources.yaml에 기록되며, 사람이 적은 note 본문은 보존된다.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

import feedparser
import httpx
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db import ROOT  # noqa: E402

# Windows 콘솔(cp949)에서 한글·특수문자 출력 깨짐 방지
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SOURCES_PATH = ROOT / "config" / "sources.yaml"
USER_AGENT = "SK-CultureInsights-Pipeline/0.1 (feed validation)"
NEWSLETTER_STATUSES = ("구독 대기", "수신 확인됨")
RSS_PROBE_PATHS = ("/feed", "/rss", "/feed.xml", "/rss.xml", "/atom.xml", "/index.xml")
AUTO_NOTE = "[자동검증 "
CONN_FAIL = "접속 실패"


# ---------- 1순위: 알려진 공식 API ----------

def _arxiv_test_query(source: dict) -> str:
    """feed_url의 카테고리(예: /rss/cs.CY)를 재사용해 arXiv API 질의를 만든다."""
    m = re.search(r"/rss/([\w.\-]+)", source.get("feed_url") or "")
    cat = m.group(1) if m else "cs.CY"
    return (f"https://export.arxiv.org/api/query?search_query=cat:{cat}"
            "&sortBy=submittedDate&sortOrder=descending&max_results=3")


KNOWN_APIS = [
    {
        "name": "arXiv API",
        "domains": ("arxiv.org",),
        "endpoint": "https://export.arxiv.org/api/query",
        "test_query": _arxiv_test_query,
    },
    {
        "name": "OSF Preprints API (PsyArXiv)",
        "domains": ("psyarxiv.com", "osf.io"),
        "endpoint": "https://api.osf.io/v2/preprints/",
        "test_query": lambda s: "https://api.osf.io/v2/preprints/?filter[provider]=psyarxiv&page[size]=3",
    },
]


def source_domain(source: dict) -> str | None:
    for key in ("endpoint", "feed_url", "test_query", "homepage"):
        url = source.get(key)
        if url:
            return urlparse(url).netloc.lower()
    return None


def find_known_api(source: dict) -> dict | None:
    dom = source_domain(source)
    if not dom:
        return None
    for rule in KNOWN_APIS:
        if any(dom == d or dom.endswith("." + d) for d in rule["domains"]):
            return rule
    return None


# ---------- 유형별 검사 ----------

def check_rss_url(url: str, client: httpx.Client) -> tuple[bool, str]:
    """4단계 검사: 접속 → HTTP 200 → 파싱 → 항목 수."""
    try:
        r = client.get(url, follow_redirects=True, timeout=15)
    except httpx.HTTPError as e:
        return False, f"{CONN_FAIL}: {type(e).__name__}"
    if r.status_code != 200:
        return False, f"HTTP {r.status_code}"
    feed = feedparser.parse(r.text)
    if feed.bozo and not feed.entries:
        return False, "RSS/Atom 파싱 실패 (피드 형식 아님)"
    if not feed.entries:
        return False, "파싱은 되나 항목 0건"
    return True, f"OK — 항목 {len(feed.entries)}건, 제목 예시: {feed.entries[0].get('title','?')[:50]}"


def check_rss(source: dict, client: httpx.Client) -> tuple[bool, str]:
    url = source.get("feed_url")
    if not url:
        return False, "feed_url 없음"
    return check_rss_url(url, client)


def _count_json_items(payload) -> int | None:
    """JSON 응답에서 항목 리스트를 찾아 개수를 반환. 리스트가 없으면 None."""
    if isinstance(payload, list):
        return len(payload)
    if isinstance(payload, dict):
        for v in payload.values():
            if isinstance(v, list):
                return len(v)
        for v in payload.values():  # 한 단계 안쪽까지 탐색 (예: {"feed": {"entry": [...]}})
            if isinstance(v, dict):
                n = _count_json_items(v)
                if n is not None:
                    return n
    return None


def check_api(source: dict, client: httpx.Client) -> tuple[bool, str]:
    url = source.get("test_query")
    if not url:
        return False, "test_query 없음 — api 소스는 테스트 질의 URL을 정의해야 함"
    try:
        r = client.get(url, follow_redirects=True, timeout=15)
    except httpx.HTTPError as e:
        return False, f"{CONN_FAIL}: {type(e).__name__}"
    if r.status_code != 200:
        return False, f"HTTP {r.status_code}"
    feed = feedparser.parse(r.text)
    if feed.entries:
        return True, (f"OK — Atom/RSS 응답, 항목 {len(feed.entries)}건, "
                      f"제목 예시: {feed.entries[0].get('title','?')[:50]}")
    try:
        n = _count_json_items(json.loads(r.text))
    except ValueError:
        return False, "응답 파싱 실패 (Atom/RSS·JSON 모두 아님)"
    if n is None:
        return False, "JSON 파싱은 되나 항목 리스트를 찾지 못함"
    if n == 0:
        return False, "파싱은 되나 항목 0건"
    return True, f"OK — JSON 응답, 항목 {n}건"


def check_newsletter(source: dict) -> tuple[str, str]:
    """자동 검증 불가 — subscription_status만 정규화·보고한다."""
    status = source.get("subscription_status") or "구독 대기"
    note = "자동 검증 불가 — 수신 확인은 A4 인박스의 실제 도착 메일로만 판정"
    if status not in NEWSLETTER_STATUSES:
        source["subscription_status"] = "구독 대기"
        return "구독 대기", f"알 수 없는 상태 '{status}' → '구독 대기'로 재설정 ({note})"
    source["subscription_status"] = status
    return status, f"{status} ({note})"


# ---------- 2순위: RSS 관례 경로 탐지 ----------

def probe_rss(source: dict, client: httpx.Client) -> tuple[str | None, str, bool, bool]:
    """기존 feed_url → 관례 경로 순으로 시도.

    반환: (통과한 URL 또는 None, 메시지, 서버 응답 수신 여부, 4xx 수신 여부).
    세 번째 값이 False면 전부 접속 실패 — 네트워크 문제로 취급한다.
    네 번째 값이 True면 4xx 차단 응답이 있었다 — 실측 통과 이력이 있는 소스는
    강등하지 않고 "환경 차단 의심"으로 분류하는 데 쓴다.
    """
    candidates: list[str] = []
    if source.get("feed_url"):
        candidates.append(source["feed_url"])
    # allow_feed_discovery: false — 섹션 한정 소스 등은 등재된 URL만 검사 (관례 경로 탐지 금지)
    if source.get("allow_feed_discovery", True) is not False:
        base = None
        for key in ("homepage", "feed_url"):
            url = source.get(key)
            if url:
                p = urlparse(url)
                base = f"{p.scheme}://{p.netloc}"
                break
        if base:
            for path in RSS_PROBE_PATHS:
                u = base + path
                if u not in candidates:
                    candidates.append(u)
    if not candidates:
        return None, "feed_url·homepage 없음 — 탐지 후보를 만들 수 없음", True, False

    got_response = False
    saw_4xx = False
    last = ""
    for u in candidates:
        ok, msg = check_rss_url(u, client)
        if ok:
            return u, msg, True, False
        if not msg.startswith(CONN_FAIL):
            got_response = True
        if re.match(r"HTTP 4\d\d", msg):
            saw_4xx = True
        last = f"{u} → {msg}"
    return None, f"RSS 미발견 (시도 {len(candidates)}건, 마지막: {last})", got_response, saw_4xx


# ---------- note 관리 ----------

def set_auto_note(source: dict, reason: str | None) -> None:
    """note의 '[자동검증 …]' 세그먼트만 갱신·제거하고 사람이 적은 본문은 보존한다."""
    note = source.get("note") or ""
    if AUTO_NOTE in note:
        note = note.split(AUTO_NOTE)[0].rstrip().rstrip("/").rstrip()
    if reason:
        stamp = f"{AUTO_NOTE}{date.today().isoformat()}] {reason}"
        note = f"{note} / {stamp}" if note else stamp
    if note:
        source["note"] = note
    else:
        source.pop("note", None)


# ---------- 배정 + 검사 ----------

def validate_source(source: dict, client: httpx.Client) -> tuple[str, str]:
    """우선순위(API→RSS→기타)로 유형을 배정하고 검사한다. source를 제자리 갱신.

    반환: (결과 마크 OK/FAIL/NEWS/SKIP, 상세 메시지)
    """
    old_type = source.get("type")
    if old_type == "manual":
        return "SKIP", "manual — 검증 대상 아님 (배정·검사 생략)"

    # 1순위: 공식 API (내장 목록 매칭, 또는 이미 api로 정의된 소스)
    rule = find_known_api(source)
    if rule or old_type == "api":
        source["type"] = "api"
        if rule:
            source["endpoint"] = rule["endpoint"]
            if not source.get("test_query"):
                source["test_query"] = rule["test_query"](source)
        ok, msg = check_api(source, client)
        source["verified"] = bool(ok)
        set_auto_note(source, None if ok else f"api 검사 실패: {msg}")
        assigned = (rule["name"] + " 배정 — ") if rule and old_type != "api" else ""
        return ("OK" if ok else "FAIL"), assigned + msg

    # 2순위: RSS (기존 feed_url + 관례 경로 탐지)
    orig_feed = source.get("feed_url")
    url, msg, got_response, saw_4xx = probe_rss(source, client)
    if url:
        source["type"] = "rss"
        source["feed_url"] = url
        source["verified"] = True
        if orig_feed and url != orig_feed:
            # 탐지가 URL을 바꿨다 — 섹션이 달라졌을 수 있으므로 사람 확인 필요
            set_auto_note(source, f"탐지로 feed_url 변경(구: {orig_feed}) — 확인 필요")
        else:
            set_auto_note(source, None)
        return "OK", msg

    if not got_response:
        # 전부 접속 실패 — 네트워크 문제로 보고 유형을 유지한다 (강등 금지)
        if old_type in ("rss", "api"):
            source["verified"] = False
        set_auto_note(source, f"전 후보 {CONN_FAIL} — 네트워크 확인 필요, 유형 유지")
        if old_type == "newsletter":
            status, nmsg = check_newsletter(source)
            return "NEWS", nmsg
        return "FAIL", f"전 후보 {CONN_FAIL} — 네트워크 확인 필요, 유형 유지(type={old_type})"

    # 실측 통과 이력이 있는 소스가 4xx를 받으면 강등하지 않는다 —
    # 실행 환경(클라우드 IP·클라이언트 지문) 차단일 가능성이 높으므로 사람 확인으로 넘긴다
    if saw_4xx and old_type in ("rss", "api") and "실측 통과" in (source.get("note") or ""):
        source["verified"] = False
        set_auto_note(source, "환경 차단 의심(4xx) — 확인 필요 (실측 통과 이력 있음, 강등 보류)")
        return "FAIL", f"환경 차단 의심(4xx) — 확인 필요, 유형 유지(type={old_type}) — {msg}"

    # 3순위: 기타 — newsletter로 분류
    source["type"] = "newsletter"
    source.pop("verified", None)  # 자동 검증 불가 유형에는 verified를 남기지 않는다
    status, nmsg = check_newsletter(source)
    set_auto_note(source, f"API·RSS 미발견: {msg}")
    return "NEWS", f"newsletter 분류 — {nmsg}"


# ---------- 실행 ----------

def main() -> int:
    data = yaml.safe_load(SOURCES_PATH.read_text(encoding="utf-8"))
    sources = data.get("sources", [])
    rows: list[tuple[str, str, str, str]] = []
    net = {"rss": [0, 0], "api": [0, 0]}  # type → [통과, 전체]
    news = {s: 0 for s in NEWSLETTER_STATUSES}
    skipped = 0
    fail = 0

    url_changed: list[tuple[str, str, str]] = []

    with httpx.Client(headers={"User-Agent": USER_AGENT}) as client:
        for s in sources:
            old_type = s.get("type") or "미지정"
            old_feed = s.get("feed_url")
            mark, msg = validate_source(s, client)
            if old_feed and s.get("feed_url") and s["feed_url"] != old_feed:
                url_changed.append((s["id"], old_feed, s["feed_url"]))
            new_type = s.get("type") or "미지정"
            type_disp = new_type if new_type == old_type else f"{old_type}→{new_type}"
            rows.append((s["id"], type_disp, mark, msg))

            if new_type in net:
                net[new_type][1] += 1
                net[new_type][0] += int(mark == "OK")
            if new_type == "newsletter":
                news[s.get("subscription_status", "구독 대기")] += 1
            if mark == "SKIP":
                skipped += 1
            if mark == "FAIL":
                fail += 1

    SOURCES_PATH.write_text(
        yaml.dump(data, allow_unicode=True, sort_keys=False, default_flow_style=False),
        encoding="utf-8",
    )

    print("소스 검증 결과:")
    print(f"  {'ID':<22} {'유형':<16} {'결과':<5} 상세")
    print(f"  {'-'*22} {'-'*16} {'-'*5} {'-'*44}")
    for sid, tdisp, mark, msg in rows:
        print(f"  {sid:<22} {tdisp:<16} {mark:<5} {msg}")

    if url_changed:
        print("\nURL 변경 — 확인 필요:")
        for sid, old, new in url_changed:
            print(f"  {sid}: {old} → {new}")

    print("\n유형별 집계:")
    for stype in ("api", "rss"):
        if net[stype][1]:
            print(f"  {stype:<10} : {net[stype][0]}/{net[stype][1]} 통과")
    if sum(news.values()):
        print(f"  newsletter : 수신 확인됨 {news['수신 확인됨']} / 구독 대기 {news['구독 대기']} (자동 검증 불가)")
    if skipped:
        print(f"  manual     : {skipped}건 SKIP")

    ok_count = net["rss"][0] + net["api"][0]
    total = net["rss"][1] + net["api"][1]
    print(f"\n검증 결과: {ok_count}/{total} 통과 (rss+api) — sources.yaml에 type·verified·note 기록 완료")
    if fail:
        print("실패 소스는 note의 [자동검증] 사유를 확인해 수정 후 재실행하거나 뉴스레터 경로로 전환하세요.")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

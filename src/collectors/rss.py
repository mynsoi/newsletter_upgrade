"""RSS/Atom 수집기.

sources.yaml의 type=rss 소스를 순회하며:
  피드 파싱 → 신규 항목 판별(URL/해시 중복 제거) → 본문 추출 → raw 저장 → DB 등록

정책 (CLAUDE.md 절대 규칙):
  - robots/ToS 준수: 요청 간 REQUEST_INTERVAL 대기, User-Agent 명시
  - 페이월 우회 시도 없음 — 본문 추출 실패 시 피드 요약만 저장하고 넘어감
"""
from __future__ import annotations

import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import feedparser
import httpx
import trafilatura
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db import ROOT, collection_done_today, connect, migrate  # noqa: E402
from collectors.store import store_document  # noqa: E402

# Windows 콘솔(cp949)에서 한글·특수문자 출력 깨짐 방지
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SOURCES_PATH = ROOT / "config" / "sources.yaml"
USER_AGENT = "SK-CultureInsights-Pipeline/0.1 (internal research; contact: pipeline-admin)"
REQUEST_INTERVAL = 3.0  # 초 — 같은 도메인 연속 요청 간격
MAX_ITEMS_PER_FEED = 50


def load_sources() -> list[dict]:
    data = yaml.safe_load(SOURCES_PATH.read_text(encoding="utf-8"))
    return data.get("sources", [])


def fetch_url(url: str, client: httpx.Client) -> str | None:
    try:
        r = client.get(url, follow_redirects=True, timeout=20)
        r.raise_for_status()
        return r.text
    except httpx.HTTPError as e:
        print(f"    ! fetch 실패 {url}: {type(e).__name__}")
        return None


def extract_body(html: str) -> str | None:
    return trafilatura.extract(html, include_comments=False, include_tables=False)


def parse_date(entry) -> str | None:
    for key in ("published_parsed", "updated_parsed"):
        t = entry.get(key)
        if t:
            return time.strftime("%Y-%m-%d", t)
    return None


def collect_source(source: dict, conn, client: httpx.Client, fetch_full: bool = True) -> dict:
    stats = {"seen": 0, "new": 0, "dup": 0, "failed": 0}
    feed_xml = fetch_url(source["feed_url"], client)
    if feed_xml is None:
        stats["failed"] = -1  # 피드 자체 실패
        return stats

    feed = feedparser.parse(feed_xml)
    # 일부 피드(HBR 등)는 항목 링크가 상대 경로 — 사이트 링크 기준으로 절대 URL화
    link_base = feed.feed.get("link") or source["feed_url"]
    for entry in feed.entries[:MAX_ITEMS_PER_FEED]:
        stats["seen"] += 1
        url = entry.get("link")
        if not url:
            continue
        url = urljoin(link_base, url)
        if conn.execute("SELECT 1 FROM documents WHERE url = ?", (url,)).fetchone():
            stats["dup"] += 1
            continue

        summary = entry.get("summary", "") or ""
        body = None
        if fetch_full:
            time.sleep(REQUEST_INTERVAL)
            html = fetch_url(url, client)
            if html:
                body = extract_body(html)
        text = body or summary

        # 저장은 공용 로직으로 — 중복 제거·summary_only 규칙을 api 수집기와 동일 적용
        result = store_document(
            conn, source, url=url, title=entry.get("title", "(무제)"), text=text,
            author=entry.get("author"), published=parse_date(entry))
        stats[{"new": "new", "dup": "dup", "empty": "failed"}[result]] += 1
    conn.commit()
    return stats


def run(source_ids: list[str] | None = None, fetch_full: bool = True, *,
        force: bool = False) -> dict:
    """반환: {"targets": 대상 소스 수, "failed": 소스 단위 실패 수} — 오케스트레이터가
    전량 실패를 판정하는 데 쓴다."""
    from handoff import ensure_active
    ensure_active("수집")
    conn = connect()
    migrate(conn)

    # 하루 1회 잠금 확인. force=True 는 오케스트레이터(collect.py)가 이미 daily
    # lock 을 선점했다는 내부 신호이며, 이때는 재확인을 생략한다.
    if not force and collection_done_today(conn):
        print("오늘 수집이 이미 완료됨 — 우회하려면 --force")
        conn.close()
        return {"targets": 0, "failed": 0}

    sources = load_sources()
    if source_ids:
        sources = [s for s in sources if s["id"] in source_ids]
    targets = [s for s in sources if s.get("type") == "rss"]
    print(f"수집 대상 {len(targets)}개 소스 (전문 추출: {fetch_full})")

    headers = {"User-Agent": USER_AGENT}
    failed_feeds = []
    with httpx.Client(headers=headers) as client:
        for s in targets:
            print(f"  {s['id']} [{s['tier']}] {s['name']}")
            st = collect_source(s, conn, client, fetch_full)
            if st["failed"] == -1:
                failed_feeds.append(s["id"])
                print("    → 피드 접속 실패")
            else:
                print(f"    → 신규 {st['new']} / 중복 {st['dup']} / 본문실패 {st['failed']} (피드 {st['seen']}건)")
            time.sleep(REQUEST_INTERVAL)

    if failed_feeds:
        print(f"\n[경고] 피드 실패 소스: {', '.join(failed_feeds)}")
        print("      `make validate`로 URL을 점검하고 sources.yaml을 수정하세요.")
    conn.close()
    return {"targets": len(targets), "failed": len(failed_feeds)}


if __name__ == "__main__":
    args = sys.argv[1:]
    fast = "--no-body" in args
    force = "--force" in args
    ids = [a for a in args if not a.startswith("--")] or None
    run(ids, fetch_full=not fast, force=force)

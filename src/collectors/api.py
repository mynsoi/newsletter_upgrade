"""API 수집기 — sources.yaml의 type=api 소스를 수집한다.

지원 어댑터:
  - arXiv Atom API (export.arxiv.org): 카테고리는 test_query 또는 feed_url에서 추출
  - OSF Preprints JSON API (api.osf.io / psyarxiv): provider는 test_query에서 추출

사용:
  python src/collectors/api.py                                   # 일상 수집 — 최근 PAGE_SIZE건
  python src/collectors/api.py --backfill 2026-01-01 2026-06-30  # 기간 지정 과거분 소급(페이지네이션)
  python src/collectors/api.py <source_id> ...                   # 특정 소스만

중복 제거·summary_only 규칙은 collectors.store.store_document로 RSS 수집기와 동일 적용.
관련성 게이트(A1)는 enrich 단계(extract_claims)에서 rss/api 문서 공통으로 적용된다.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import date
from pathlib import Path
from urllib.parse import quote_plus, urlparse

import feedparser
import httpx
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db import ROOT, connect, migrate  # noqa: E402
from collectors.store import store_document  # noqa: E402

# Windows 콘솔(cp949)에서 한글·특수문자 출력 깨짐 방지
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SOURCES_PATH = ROOT / "config" / "sources.yaml"
RAW_DIR = ROOT / "data" / "raw"
USER_AGENT = "SK-CultureInsights-Pipeline/0.1 (internal research; contact: pipeline-admin)"
REQUEST_INTERVAL = 3.0      # 초 — API 예절 (arXiv 권고 준수)
PAGE_SIZE = 50
MAX_BACKFILL_PAGES = 20     # 소급 수집 시 소스당 최대 페이지 (폭주 방지)


def fetch_text(url: str, client: httpx.Client) -> str | None:
    try:
        r = client.get(url, follow_redirects=True, timeout=30)
        r.raise_for_status()
        return r.text
    except httpx.HTTPError as e:
        print(f"    ! fetch 실패 {url}: {type(e).__name__}")
        return None


# ---------- arXiv (Atom) ----------

def arxiv_category(source: dict) -> str | None:
    for pattern, field in ((r"search_query=cat:([\w.\-]+)", "test_query"),
                           (r"/rss/([\w.\-]+)", "feed_url")):
        m = re.search(pattern, source.get(field) or "")
        if m:
            return m.group(1)
    return None


def arxiv_url(source: dict, start: int = 0,
              backfill: tuple[str, str] | None = None) -> str:
    q = f"cat:{arxiv_category(source)}"
    if backfill:
        frm, to = (d.replace("-", "") for d in backfill)
        q += f" AND submittedDate:[{frm}0000 TO {to}2359]"
    endpoint = source.get("endpoint") or "https://export.arxiv.org/api/query"
    return (f"{endpoint}?search_query={quote_plus(q)}&start={start}"
            f"&max_results={PAGE_SIZE}&sortBy=submittedDate&sortOrder=descending")


def parse_arxiv(text: str) -> tuple[list[dict], str | None]:
    feed = feedparser.parse(text)
    items = []
    for e in feed.entries:
        published = None
        if e.get("published_parsed"):
            published = time.strftime("%Y-%m-%d", e.published_parsed)
        items.append({
            "url": e.get("link"),
            "title": e.get("title", "(무제)"),
            "text": e.get("summary", "") or "",
            "author": e.get("author"),
            "published": published,
        })
    return items, None  # arXiv는 start 파라미터로 다음 페이지를 만든다


# ---------- OSF Preprints (JSON) ----------

def osf_provider(source: dict) -> str:
    m = re.search(r"filter\[provider\]=([\w\-]+)", source.get("test_query") or "")
    return m.group(1) if m else "psyarxiv"


def osf_url(source: dict, backfill: tuple[str, str] | None = None) -> str:
    endpoint = (source.get("endpoint") or "https://api.osf.io/v2/preprints/").rstrip("?")
    url = (f"{endpoint}?filter[provider]={osf_provider(source)}"
           f"&sort=-date_created&page[size]={PAGE_SIZE}")
    if backfill:
        url += (f"&filter[date_created][gte]={backfill[0]}"
                f"&filter[date_created][lte]={backfill[1]}")
    return url


def parse_osf(text: str) -> tuple[list[dict], str | None]:
    payload = json.loads(text)
    items = []
    for d in payload.get("data", []):
        attr = d.get("attributes") or {}
        items.append({
            "url": (d.get("links") or {}).get("html"),
            "title": attr.get("title", "(무제)"),
            "text": attr.get("description", "") or "",
            "author": None,
            "published": (attr.get("date_created") or "")[:10] or None,
        })
    return items, (payload.get("links") or {}).get("next")


# ---------- 공통 수집 루프 ----------

def pick_adapter(source: dict) -> str | None:
    for key in ("endpoint", "test_query", "feed_url"):
        if source.get(key):
            dom = urlparse(source[key]).netloc.lower()
            if "arxiv.org" in dom:
                return "arxiv"
            if "osf.io" in dom or "psyarxiv" in dom:
                return "osf"
            return None
    return None


def collect_source(source: dict, conn, client: httpx.Client,
                   backfill: tuple[str, str] | None = None) -> dict:
    stats = {"seen": 0, "new": 0, "dup": 0, "failed": 0}
    kind = pick_adapter(source)
    if kind is None:
        print(f"    ! 지원하지 않는 api 소스 (arXiv/OSF 아님)")
        stats["failed"] = -1
        return stats
    if kind == "arxiv" and not arxiv_category(source):
        print(f"    ! arXiv 카테고리를 test_query/feed_url에서 찾을 수 없음")
        stats["failed"] = -1
        return stats

    max_pages = MAX_BACKFILL_PAGES if backfill else 1
    url = arxiv_url(source, 0, backfill) if kind == "arxiv" else osf_url(source, backfill)
    for page in range(max_pages):
        text = fetch_text(url, client)
        if text is None:
            if page == 0:
                stats["failed"] = -1
            break
        items, next_url = (parse_arxiv if kind == "arxiv" else parse_osf)(text)
        if not items:
            break
        for it in items:
            stats["seen"] += 1
            if not it["url"]:
                continue
            result = store_document(
                conn, source, url=it["url"], title=it["title"], text=it["text"],
                author=it["author"], published=it["published"], raw_dir=RAW_DIR)
            stats[{"new": "new", "dup": "dup", "empty": "failed"}[result]] += 1
        conn.commit()

        if kind == "arxiv":
            if len(items) < PAGE_SIZE:
                break
            url = arxiv_url(source, (page + 1) * PAGE_SIZE, backfill)
        else:
            if not next_url:
                break
            url = next_url
        time.sleep(REQUEST_INTERVAL)
    return stats


def run(source_ids: list[str] | None = None,
        backfill: tuple[str, str] | None = None) -> None:
    from handoff import ensure_active
    ensure_active("수집")
    conn = connect()
    migrate(conn)
    sources = yaml.safe_load(SOURCES_PATH.read_text(encoding="utf-8")).get("sources", [])
    if source_ids:
        sources = [s for s in sources if s["id"] in source_ids]
    targets = [s for s in sources if s.get("type") == "api"]
    mode = f"소급 {backfill[0]}~{backfill[1]}" if backfill else "일상(최근분)"
    print(f"API 수집 대상 {len(targets)}개 소스 — {mode}")

    failed = []
    with httpx.Client(headers={"User-Agent": USER_AGENT}) as client:
        for s in targets:
            print(f"  {s['id']} [{s['tier']}] {s['name']}")
            st = collect_source(s, conn, client, backfill)
            if st["failed"] == -1:
                failed.append(s["id"])
                print("    → 수집 실패")
            else:
                print(f"    → 신규 {st['new']} / 중복 {st['dup']} / 본문없음 {st['failed']} (응답 {st['seen']}건)")
            time.sleep(REQUEST_INTERVAL)

    if failed:
        print(f"\n[경고] 실패 소스: {', '.join(failed)} — `make validate`로 점검하세요.")
    conn.close()


def _parse_args(argv: list[str]):
    p = argparse.ArgumentParser(description="type=api 소스 수집기")
    p.add_argument("ids", nargs="*", help="특정 소스 id만 수집 (생략 시 전체)")
    p.add_argument("--backfill", nargs=2, metavar=("FROM", "TO"),
                   help="기간 지정 과거분 소급 수집 (YYYY-MM-DD YYYY-MM-DD)")
    args = p.parse_args(argv)
    if args.backfill:
        try:
            frm, to = (date.fromisoformat(d) for d in args.backfill)
        except ValueError:
            p.error("--backfill 날짜는 YYYY-MM-DD 형식이어야 합니다")
        if frm > to:
            p.error("--backfill FROM은 TO보다 이전이어야 합니다")
    return args


if __name__ == "__main__":
    a = _parse_args(sys.argv[1:])
    run(a.ids or None, tuple(a.backfill) if a.backfill else None)

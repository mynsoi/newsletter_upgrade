"""HTML 목록 수집기 — sources.yaml의 type=html 소스 (기획서 4.2 4순위 경로).

rss.py와 동일한 2단계 구조: 목록 페이지 → 신규 링크만 → 본문 추출.
저장은 반드시 collectors.store를 거쳐 중복 제거·summary_only 규칙을 동일 적용한다.

sources.yaml 설정 (type: html):
  list_url:      목록 페이지 URL (문자열 또는 URL 목록)
  link_pattern:  글 링크 추출 정규식 — CSS 선택자 대신 URL 패턴을 쓴다
                 (사이트 디자인 변경에 덜 깨진다). 캡처 그룹 1 = 링크
  link_exclude:  (선택) 제외 정규식 — 허브/목록 페이지 걸러내기
  min_links:     (선택) validate 통과 기준 링크 수 (기본 3)
  request_headers: (선택) 있으면 httpx 실패 시 curl 폴백 (rss.py와 동일 —
                 WAF의 파이썬 클라이언트 지문 차단 대응: OECD·OpenAI 등)

본문: content-type이 PDF(또는 .pdf URL)면 pypdf로 텍스트 추출 후 저장, 그 외 HTML 추출.
robots.txt 준수(호스트별 캐시, Disallow 경로는 건너뜀) · 요청 간격 3초 · 수집 주체 UA 명시.
"""
from __future__ import annotations

import re
import sys
import time
import urllib.robotparser
from io import BytesIO
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db import ROOT, collection_done_today, connect, migrate  # noqa: E402
from collectors.store import store_document  # noqa: E402
from collectors.rss import USER_AGENT, extract_body, fetch_url, fetch_via_curl  # noqa: E402

# Windows 콘솔(cp949)에서 한글·특수문자 출력 깨짐 방지
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SOURCES_PATH = ROOT / "config" / "sources.yaml"
REQUEST_INTERVAL = 3.0
MAX_ITEMS_PER_LIST = 50

_robots_cache: dict[str, urllib.robotparser.RobotFileParser | None] = {}


def robots_allows(url: str, client: httpx.Client) -> bool:
    """robots.txt 준수 — 호스트별 캐시. robots가 없거나 읽기 실패면 허용으로 본다."""
    host = urlparse(url).netloc
    if host not in _robots_cache:
        rp = urllib.robotparser.RobotFileParser()
        try:
            r = client.get(f"{urlparse(url).scheme}://{host}/robots.txt",
                           follow_redirects=True, timeout=15)
            if r.status_code == 200:
                rp.parse(r.text.splitlines())
            else:
                rp = None
        except httpx.HTTPError:
            rp = None
        _robots_cache[host] = rp
    rp = _robots_cache[host]
    return True if rp is None else rp.can_fetch(USER_AGENT, url)


def list_entries(source: dict) -> list[str]:
    lu = source.get("list_url")
    if isinstance(lu, str):
        return [lu]
    return list(lu or [])


def extract_links(html: str, base_url: str, pattern: str,
                  exclude: str | None = None) -> list[str]:
    """정규식(URL 패턴)으로 글 링크 추출 → 절대 URL·중복 제거·제외 필터."""
    rx = re.compile(pattern)
    out: list[str] = []
    seen: set[str] = set()
    for m in rx.finditer(html):
        raw = m.group(1) if m.groups() else m.group(0)
        u = urljoin(base_url, raw).split("#")[0].rstrip("/")
        if exclude and re.search(exclude, u):
            continue
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def pdf_to_text(data: bytes) -> str:
    from pypdf import PdfReader
    reader = PdfReader(BytesIO(data))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def fetch_document(url: str, client: httpx.Client,
                   curl_headers: dict | None = None) -> tuple[str, bytes] | None:
    """본문 페이지를 (content_type, bytes)로 가져온다. httpx 실패 시 curl 폴백."""
    try:
        r = client.get(url, follow_redirects=True, timeout=30)
        r.raise_for_status()
        return r.headers.get("content-type", ""), r.content
    except httpx.HTTPError as e:
        if curl_headers is not None:
            print(f"    ! httpx 실패({type(e).__name__}) → curl 폴백: {url}")
            text = fetch_via_curl(url, curl_headers)
            if text is not None:
                ct = "application/pdf" if url.lower().endswith(".pdf") else "text/html"
                return ct, text.encode("utf-8", errors="replace")
        else:
            print(f"    ! fetch 실패 {url}: {type(e).__name__}")
        return None


def extract_title(html: str) -> str | None:
    m = re.search(r'<meta[^>]+property="og:title"[^>]+content="([^"]+)"', html)
    if not m:
        m = re.search(r"<title[^>]*>(.*?)</title>", html, re.S)
    if m:
        title = re.sub(r"\s+", " ", m.group(1)).strip()
        return title or None
    return None


def extract_published(html: str) -> str | None:
    for pat in (r'property="article:published_time"[^>]+content="(\d{4}-\d{2}-\d{2})',
                r'"datePublished"\s*:\s*"(\d{4}-\d{2}-\d{2})',
                r'<time[^>]+datetime="(\d{4}-\d{2}-\d{2})'):
        m = re.search(pat, html)
        if m:
            return m.group(1)
    return None


def collect_source(source: dict, conn, client: httpx.Client) -> dict:
    stats = {"seen": 0, "new": 0, "dup": 0, "failed": 0, "robots": 0}
    curl_headers = source.get("request_headers")
    pattern = source.get("link_pattern")
    if not pattern or not list_entries(source):
        print("    ! list_url/link_pattern 미설정")
        stats["failed"] = -1
        return stats

    links: list[str] = []
    list_failed = 0
    for list_url in list_entries(source):
        if not robots_allows(list_url, client):
            print(f"    ! robots 금지 — 목록 건너뜀: {list_url}")
            stats["robots"] += 1
            continue
        page = fetch_url(list_url, client, curl_headers)
        if page is None:
            list_failed += 1
            continue
        links += extract_links(page, list_url, pattern, source.get("link_exclude"))
        time.sleep(REQUEST_INTERVAL)
    if not links:
        if list_failed == len(list_entries(source)) or stats["robots"] == len(list_entries(source)):
            stats["failed"] = -1  # 목록 자체 실패
        return stats

    for url in dict.fromkeys(links[:MAX_ITEMS_PER_LIST]):
        stats["seen"] += 1
        if conn.execute("SELECT 1 FROM documents WHERE url = ?", (url,)).fetchone():
            stats["dup"] += 1
            continue
        if not robots_allows(url, client):
            stats["robots"] += 1
            continue
        time.sleep(REQUEST_INTERVAL)
        fetched = fetch_document(url, client, curl_headers)
        if fetched is None:
            stats["failed"] += 1
            continue
        ctype, data = fetched
        if "pdf" in ctype.lower() or url.lower().endswith(".pdf"):
            try:
                text = pdf_to_text(data)
            except Exception as e:  # noqa: BLE001 — 깨진 PDF가 배치를 중단시키지 않도록
                print(f"    ! PDF 추출 실패 {url}: {type(e).__name__}")
                stats["failed"] += 1
                continue
            title = url.rsplit("/", 1)[-1]
            published = None
        else:
            page_html = data.decode("utf-8", errors="replace")
            text = extract_body(page_html) or ""
            title = extract_title(page_html) or url.rsplit("/", 1)[-1]
            published = extract_published(page_html)
            # follow_pdf: 본문이 리포트 '소개 페이지'인 소스(삼일PwC 등)는 페이지 내
            # PDF 링크를 따라가 PDF 텍스트를 본문으로 쓴다 (더 길 때만 대체)
            if source.get("follow_pdf"):
                m = re.search(r'href="([^"]+\.pdf)"', page_html)
                if m:
                    pdf_url = urljoin(url, m.group(1))
                    if robots_allows(pdf_url, client):
                        time.sleep(REQUEST_INTERVAL)
                        f2 = fetch_document(pdf_url, client, curl_headers)
                        if f2 is not None:
                            try:
                                pdf_text = pdf_to_text(f2[1])
                                if len(pdf_text.strip()) > len(text.strip()):
                                    text = pdf_text
                            except Exception as e:  # noqa: BLE001 — PDF 실패 시 소개 페이지 본문 유지
                                print(f"    ! PDF 추출 실패(소개 페이지 본문 유지) {pdf_url}: {type(e).__name__}")

        result = store_document(conn, source, url=url, title=title, text=text,
                                published=published)
        stats[{"new": "new", "dup": "dup", "empty": "failed"}[result]] += 1
    conn.commit()
    return stats


def run(source_ids: list[str] | None = None, *, force: bool = False) -> dict:
    """반환: {"targets": 대상 소스 수, "failed": 소스 단위 실패 수}."""
    from handoff import ensure_active
    ensure_active("수집")
    conn = connect()
    migrate(conn)

    if not force and collection_done_today(conn):
        print("오늘 수집이 이미 완료됨 — 우회하려면 --force")
        conn.close()
        return {"targets": 0, "failed": 0}

    sources = yaml.safe_load(SOURCES_PATH.read_text(encoding="utf-8")).get("sources", [])
    if source_ids:
        sources = [s for s in sources if s["id"] in source_ids]
    targets = [s for s in sources if s.get("type") == "html"]
    print(f"HTML 목록 수집 대상 {len(targets)}개 소스")

    failed = []
    with httpx.Client(headers={"User-Agent": USER_AGENT}) as client:
        for s in targets:
            print(f"  {s['id']} [{s['tier']}] {s['name']}")
            st = collect_source(s, conn, client)
            if st["failed"] == -1:
                failed.append(s["id"])
                print("    → 목록 수집 실패")
            else:
                extra = f" / robots 제외 {st['robots']}" if st["robots"] else ""
                print(f"    → 신규 {st['new']} / 중복 {st['dup']} / 본문실패 {st['failed']}"
                      f" (링크 {st['seen']}건{extra})")
            time.sleep(REQUEST_INTERVAL)

    if failed:
        print(f"\n[경고] 실패 소스: {', '.join(failed)} — `make validate`로 점검하세요.")
    conn.close()
    return {"targets": len(targets), "failed": len(failed)}


if __name__ == "__main__":
    args = sys.argv[1:]
    force = "--force" in args
    ids = [a for a in args if not a.startswith("--")] or None
    run(ids, force=force)

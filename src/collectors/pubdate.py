"""본문 페이지에서 발행일(YYYY-MM-DD)을 찾는다 — rss·html_list 수집기 공용.

발행일이 비면 그 문서의 claim은 토픽 발굴(src/topics/discover.py — 발행일 기준 창)에 잡히지 않고,
증거 수집의 발행일 필터에서도 빠진다. 2026-09-30 월간 소스 리뷰에서 약 386건을 확인했다
(content/reports/source-review-2026-09.md 4장 ②).

찾는 순서 — 기계가 읽으라고 넣어 둔 표준 표기부터:
  1. <meta property="article:published_time">   (Open Graph — 속성 순서 무관)
  2. JSON-LD "datePublished"
  3. <meta name="citation_publication_date|citation_date">  (학술 사이트 — NBER 등. 2026/09/28 형식)
  4. <meta name="dc.date|DC.date.issued">
  5. <time datetime=...>   (대소문자 무관 — dateTime)
  6. (소스가 켠 경우만) 본문 글자 "September 25, 2026" — 첫 번째 것
     본문의 다른 날짜(인용 연도·행사일)를 발행일로 오인할 수 있어 기본은 끈다.
     sources.yaml의 소스에 `date_from_text: true`로 켠다(Stanford HAI 등 메타가 없는 곳).

수정일(article:modified_time, dateModified, 사이트맵 lastmod)은 쓰지 않는다 — 옛 글이 최근 글로
둔갑하면 토픽 급증도가 오염된다(기획서 Phase 2 설계 메모 2).
"""
from __future__ import annotations

import re
from datetime import date

_SEP = r"[-/.]"
_YMD = rf"((?:19|20)\d{{2}}){_SEP}(\d{{1,2}}){_SEP}(\d{{1,2}})"

_META_PATTERNS = [
    # Open Graph — property가 content 앞이든 뒤든
    rf'<meta[^>]+property=["\']article:published_time["\'][^>]+content=["\']{_YMD}',
    rf'<meta[^>]+content=["\']{_YMD}[^"\']*["\'][^>]+property=["\']article:published_time["\']',
    rf'"datePublished"\s*:\s*"{_YMD}',
    rf'<meta[^>]+name=["\']citation_(?:publication_)?date["\'][^>]+content=["\']{_YMD}',
    rf'<meta[^>]+content=["\']{_YMD}[^"\']*["\'][^>]+name=["\']citation_(?:publication_)?date["\']',
    rf'<meta[^>]+name=["\'](?:dc|DC)\.date(?:\.issued)?["\'][^>]+content=["\']{_YMD}',
    rf'<time[^>]+datetime=["\']{_YMD}',
]
_META_RES = [re.compile(p, re.I) for p in _META_PATTERNS]

_MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august",
     "september", "october", "november", "december"], 1)}
_TEXT_RE = re.compile(
    r"\b(January|February|March|April|May|June|July|August|September|October|November|December)"
    r"\s+(\d{1,2}),\s+((?:19|20)\d{2})\b")


def _valid(y: int, m: int, d: int) -> str | None:
    """실존 날짜이고 미래가 아니면 YYYY-MM-DD. 아니면 None(오인 방지)."""
    try:
        dt = date(y, m, d)
    except ValueError:
        return None
    if dt.year < 1990 or dt > date.today():
        return None
    return dt.isoformat()


def extract_published(html: str, *, text_dates: bool = False) -> str | None:
    """페이지 HTML에서 발행일. 못 찾으면 None."""
    if not html:
        return None
    for rx in _META_RES:
        m = rx.search(html)
        if m:
            got = _valid(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            if got:
                return got
    if text_dates:
        for m in _TEXT_RE.finditer(html):
            got = _valid(int(m.group(3)), _MONTHS[m.group(1).lower()], int(m.group(2)))
            if got:
                return got
    return None

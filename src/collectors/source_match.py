"""수기 등록 URL → sources.yaml 소스 자동 판별 (/ingest-url, /ingest-file 공용).

수기 등록 문서가 전부 source_id='manual'로 들어가면 참고자료에 기관명이 붙지 않고
(verify_article REF_NAME_SKIP) 월간 소스 리뷰의 인용 수도 발행처로 잡히지 않는다.
그래서 등록 시 URL의 도메인·경로로 정식 소스를 찾는다. 판별 기준은 코드가 아니라
sources.yaml의 주소 필드(homepage·list_url·browse_list_urls·feed_url)에서만 읽는다.

판별 규칙:
- 호스트 비교는 www·www2·feeds·rss 같은 일반 접두를 떼고 한다
  (www2.deloitte.com 과 www.deloitte.com 은 같은 발행처).
- homepage·list_url·browse_list_urls 는 경로까지 접두로 쓴다
  (microsoft.com/en-us/worklab → 마이크로소프트 전체가 아니라 WorkLab만).
  경로 끝의 .html 은 떼고, 경로 구간 경계에서만 일치로 본다.
- feed_url 은 호스트만 쓴다 (/feed/·/rss 경로는 글 주소와 무관).
- 가장 긴 경로 접두가 일치한 소스가 이긴다. 같은 길이로 서로 다른 소스가 겹치면
  (arXiv 여러 분류처럼) 하나로 정할 수 없으므로 판별 실패 → 호출 측이 'manual'로 등록.
- 제외(excluded) 소스와 type=manual 소스는 후보에서 뺀다.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import urlparse

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db import ROOT  # noqa: E402

SOURCES_PATH = ROOT / "config" / "sources.yaml"
MANUAL_ID = "manual"

PATH_FIELDS = ("homepage", "list_url", "browse_list_urls")
HOST_ONLY_FIELDS = ("feed_url",)
_HOST_PREFIX = re.compile(r"^(?:www\d*|feeds?|rss)\.")


def load_sources(path: Path = SOURCES_PATH) -> list[dict]:
    return yaml.safe_load(path.read_text(encoding="utf-8")).get("sources", [])


def find_source(source_id: str, sources: list[dict] | None = None) -> dict | None:
    for s in sources if sources is not None else load_sources():
        if s["id"] == source_id:
            return s
    return None


def _norm_host(host: str) -> str:
    host = (host or "").lower().split(":")[0]
    return _HOST_PREFIX.sub("", host)


def _norm_path(path: str) -> str:
    path = (path or "").lower()
    if path.endswith(".html"):
        path = path[: -len(".html")]
    return path.rstrip("/")


def _urls(value) -> list[str]:
    if not value:
        return []
    return [value] if isinstance(value, str) else [v for v in value if v]


def _patterns(source: dict) -> list[tuple[str, str]]:
    """소스 1건의 (호스트, 경로 접두) 목록."""
    pats = []
    for field in PATH_FIELDS:
        for u in _urls(source.get(field)):
            p = urlparse(u)
            pats.append((_norm_host(p.netloc), _norm_path(p.path)))
    for field in HOST_ONLY_FIELDS:
        for u in _urls(source.get(field)):
            pats.append((_norm_host(urlparse(u).netloc), ""))
    return [(h, p) for h, p in pats if h]


def _path_match(path: str, prefix: str) -> bool:
    return not prefix or path == prefix or path.startswith(prefix + "/")


def detect_source(url: str, sources: list[dict] | None = None) -> tuple[dict | None, str]:
    """URL로 소스를 판별한다. 반환: (소스 또는 None, 판별 설명 한 줄)."""
    sources = sources if sources is not None else load_sources()
    p = urlparse(url)
    host, path = _norm_host(p.netloc), _norm_path(p.path)
    best: dict[str, int] = {}  # source_id → 일치한 가장 긴 경로 접두 길이
    for s in sources:
        if s.get("status") == "excluded" or s.get("type") == MANUAL_ID:
            continue
        for h, prefix in _patterns(s):
            if h == host and _path_match(path, prefix):
                best[s["id"]] = max(best.get(s["id"], -1), len(prefix))
    if not best:
        return None, f"판별 실패 — sources.yaml에 {host} 와 일치하는 소스 없음"
    top = max(best.values())
    winners = sorted(sid for sid, n in best.items() if n == top)
    if len(winners) > 1:
        return None, f"판별 실패 — 여러 소스가 겹침: {', '.join(winners)}"
    source = find_source(winners[0], sources)
    return source, f"자동 판별: {source['id']} ({source.get('name', '')}, {source['tier']})"


class SourceResolveError(ValueError):
    """--source/--tier 지정이 sources.yaml과 맞지 않을 때."""


def resolve_source(url: str, source_id: str | None = None, tier: str | None = None,
                   sources: list[dict] | None = None,
                   default_tier: str = "T5") -> tuple[dict, str]:
    """등록할 소스를 정한다. 반환: (소스 dict — 최소 id·tier, 판별 설명 한 줄).

    - source_id='manual' → 판별 없이 수기 등록 (tier 미지정 시 default_tier)
    - source_id 지정 → 그 소스의 id·tier. tier를 따로 줬는데 다르면 오류
    - 미지정 → URL로 자동 판별. 판별되면 그 소스(tier 불일치 시 오류), 아니면 manual
    """
    sources = sources if sources is not None else load_sources()
    if source_id == MANUAL_ID:
        return {"id": MANUAL_ID, "tier": tier or default_tier}, "수기(manual) 지정 — 판별 생략"
    if source_id:
        source = find_source(source_id, sources)
        if source is None:
            raise SourceResolveError(f"sources.yaml에 없는 소스: {source_id}")
        if source.get("status") == "excluded":
            raise SourceResolveError(f"제외(excluded)된 소스: {source_id}")
        note = f"지정 소스: {source['id']} ({source.get('name', '')}, {source['tier']})"
    else:
        source, note = detect_source(url, sources)
        if source is None:
            return {"id": MANUAL_ID, "tier": tier or default_tier}, f"{note} → manual"
    if tier and tier != source["tier"]:
        hint = "" if source_id else " — 수기로 넣으려면 --source manual"
        raise SourceResolveError(
            f"tier 불일치: {source['id']}의 tier는 {source['tier']}인데 {tier}가 지정됨{hint}")
    return source, note

"""sources.yaml의 모든 피드 URL을 접속 검증하고 verified 필드를 갱신한다.

사용: make validate  (또는 python src/collectors/validate_sources.py)
실패 소스는 사유와 함께 보고하며, 사람이 URL을 수정 후 재실행한다.
"""
from __future__ import annotations

import sys
from pathlib import Path

import feedparser
import httpx
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db import ROOT  # noqa: E402

SOURCES_PATH = ROOT / "config" / "sources.yaml"
USER_AGENT = "SK-CultureInsights-Pipeline/0.1 (feed validation)"


def check(source: dict, client: httpx.Client) -> tuple[bool, str]:
    url = source.get("feed_url")
    if not url:
        return False, "feed_url 없음"
    try:
        r = client.get(url, follow_redirects=True, timeout=15)
    except httpx.HTTPError as e:
        return False, f"접속 실패: {type(e).__name__}"
    if r.status_code != 200:
        return False, f"HTTP {r.status_code}"
    feed = feedparser.parse(r.text)
    if feed.bozo and not feed.entries:
        return False, "RSS/Atom 파싱 실패 (피드 형식 아님)"
    if not feed.entries:
        return False, "파싱은 되나 항목 0건"
    return True, f"OK — 항목 {len(feed.entries)}건, 제목 예시: {feed.entries[0].get('title','?')[:50]}"


def main() -> int:
    data = yaml.safe_load(SOURCES_PATH.read_text(encoding="utf-8"))
    sources = data.get("sources", [])
    ok_count = 0
    with httpx.Client(headers={"User-Agent": USER_AGENT}) as client:
        for s in sources:
            if s.get("type") != "rss":
                print(f"  SKIP  {s['id']} (type={s.get('type')})")
                continue
            ok, msg = check(s, client)
            s["verified"] = bool(ok)
            mark = "OK  " if ok else "FAIL"
            print(f"  {mark}  {s['id']:<20} {msg}")
            ok_count += int(ok)

    SOURCES_PATH.write_text(
        yaml.dump(data, allow_unicode=True, sort_keys=False, default_flow_style=False),
        encoding="utf-8",
    )
    total = sum(1 for s in sources if s.get("type") == "rss")
    print(f"\n검증 결과: {ok_count}/{total} 통과 — sources.yaml의 verified 필드 갱신 완료")
    if ok_count < total:
        print("실패 소스는 feed_url 수정 후 재실행하거나, note에 따라 뉴스레터 경로(Phase 1)로 전환하세요.")
    return 0 if ok_count == total else 1


if __name__ == "__main__":
    raise SystemExit(main())

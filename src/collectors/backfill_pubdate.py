"""발행일(published_at)이 비어 있는 문서의 본문 페이지를 다시 받아 발행일을 채운다 — 1회성 소급 도구.

배경: 2026-09-30 월간 소스 리뷰에서 발행일이 비어 토픽 발굴에 잡히지 않는 claim 약 386건을 확인했다.
수집기(rss·html_list)는 collectors/pubdate.py로 고쳐 신규분은 채워지고, 이 도구는 이미 쌓인 분을 채운다.

- 대상: status active 이고 type rss/html 인 소스의 발행일 없는 문서. `no_pubdate: true` 소스는 건너뛴다
  (페이지에 발행일이 아예 없는 곳 — ms-worklab. 헛되이 다시 받지 않도록).
- 발행일만 채운다(`published_at IS NULL`인 행만 갱신). 본문·상태는 건드리지 않는다.
- 요청 간격은 수집기와 같다. 차단(403 등)된 문서는 건너뛰고 집계에 남긴다.
- 요청은 수집기와 같은 경로(fetch_document): httpx가 막히면 소스에 request_headers가 있을 때만 curl로
  다시 시도한다. NBER은 httpx 접속 지문을 막아(IP 무관) request_headers에 파이프라인 UA를 그대로
  등재해 curl 경로를 켰다(2026-10-01). 브라우저로 위장하지 않는다.

사용:
  python src/collectors/backfill_pubdate.py --dry-run                 # 대상만 센다
  python src/collectors/backfill_pubdate.py --source stanford-hai,ai-lab-enterprise-reports
  python src/collectors/backfill_pubdate.py --source nber-working-papers --limit 200
"""
from __future__ import annotations

import argparse
import sys
import time
from collections import Counter
from pathlib import Path

import httpx
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db import ROOT, connect, migrate  # noqa: E402
from collectors.html_list import fetch_document  # noqa: E402
from collectors.pubdate import extract_published  # noqa: E402
from collectors.rss import REQUEST_INTERVAL, USER_AGENT  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SOURCES_PATH = ROOT / "config" / "sources.yaml"
TYPES = ("rss", "html")


def eligible_sources(sources: list[dict], only: list[str] | None = None) -> dict[str, dict]:
    """소급 대상 소스 {id: 설정}. only가 있으면 그 안에서만."""
    out = {}
    for s in sources:
        if s.get("status") != "active" or s.get("type") not in TYPES or s.get("no_pubdate"):
            continue
        if only and s["id"] not in only:
            continue
        out[s["id"]] = s
    return out


def select_targets(conn, source_ids: list[str], limit: int | None) -> list:
    if not source_ids:
        return []
    ph = ",".join("?" for _ in source_ids)
    sql = (f"SELECT id, source_id, url FROM documents WHERE published_at IS NULL "
           f"AND source_id IN ({ph}) ORDER BY collected_at DESC")
    params: list = list(source_ids)
    if limit is not None:
        sql += " LIMIT ?"
        params.append(limit)
    return conn.execute(sql, tuple(params)).fetchall()


def backfill(conn, targets, sources: dict[str, dict], client, *, dry_run: bool = False,
             sleep: float = REQUEST_INTERVAL) -> Counter:
    """반환: Counter — (source_id, 'filled'|'no_date'|'fetch_failed'|'pdf') 별 건수."""
    stats: Counter = Counter()
    for i, row in enumerate(targets):
        src = sources[row["source_id"]]
        url = row["url"].split("#")[0]           # NBER '#fromrss' 같은 조각 제거
        if row["url"].lower().endswith(".pdf"):
            stats[(src["id"], "pdf")] += 1      # PDF에는 발행일 메타가 없다
            continue
        if i:
            time.sleep(sleep)
        fetched = fetch_document(url, client, src.get("request_headers"))
        if fetched is None:
            stats[(src["id"], "fetch_failed")] += 1
            continue
        got = extract_published(fetched[1].decode("utf-8", errors="replace"),
                                text_dates=bool(src.get("date_from_text")))
        if got is None:
            stats[(src["id"], "no_date")] += 1
            continue
        if not dry_run:
            conn.execute("UPDATE documents SET published_at = ? WHERE id = ? AND published_at IS NULL",
                         (got, row["id"]))
            if stats[(src["id"], "filled")] % 20 == 0:
                conn.commit()
        stats[(src["id"], "filled")] += 1
    if not dry_run:
        conn.commit()
    return stats


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="발행일 없는 문서의 발행일 소급")
    p.add_argument("--source", help="쉼표 구분 source_id (미지정 시 대상 소스 전부)")
    p.add_argument("--limit", type=int, default=None, help="처리할 문서 수 상한")
    p.add_argument("--dry-run", action="store_true", help="요청·갱신 없이 대상 건수만")
    args = p.parse_args(argv)

    only = [s.strip() for s in (args.source or "").split(",") if s.strip()] or None
    all_sources = yaml.safe_load(SOURCES_PATH.read_text(encoding="utf-8"))["sources"]
    sources = eligible_sources(all_sources, only)
    if only:
        skipped = sorted(set(only) - set(sources))
        if skipped:
            print(f"대상 아님(비활성·유형·no_pubdate): {', '.join(skipped)}")

    conn = connect()
    migrate(conn)
    targets = select_targets(conn, list(sources), args.limit)
    by_src = Counter(r["source_id"] for r in targets)
    print(f"대상 {len(targets)}건 — " + (", ".join(f"{k} {v}" for k, v in by_src.most_common()) or "없음"))
    if args.dry_run or not targets:
        conn.close()
        return 0

    with httpx.Client(headers={"User-Agent": USER_AGENT}) as client:
        stats = backfill(conn, targets, sources, client)
    conn.close()

    for sid in by_src:
        parts = {k: stats[(sid, k)] for k in ("filled", "no_date", "fetch_failed", "pdf")}
        print(f"  {sid:28s} 채움 {parts['filled']:>4} · 날짜 없음 {parts['no_date']:>3} · "
              f"받기 실패 {parts['fetch_failed']:>3}" + (f" · PDF {parts['pdf']}" if parts["pdf"] else ""))
    filled = sum(v for (s, k), v in stats.items() if k == "filled")
    print(f"총 {filled}/{len(targets)}건 채움")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

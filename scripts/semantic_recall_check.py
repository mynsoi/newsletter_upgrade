"""A6 동의어 리콜 검수 자료 — 키워드-단독 결과와 하이브리드 결과를 나란히 비교한다.

일회성 검수 스크립트(docs/phase2-plan.md A6). claim 임베딩 백필(make embed-backfill)
완료 후 실행한다. 출력은 마크다운 표 — 사람이 "키워드가 놓치고 의미 검색이 찾아낸 claim"을
확인할 수 있게 한다.

사용: python scripts/semantic_recall_check.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from db import connect, migrate  # noqa: E402
from search.semantic import hybrid_search, keyword_search  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

QUERIES = ["심리적 안전감", "아낀 시간의 사용처", "관리자 역할 변화"]
LIMIT = 10


def _fmt(rows: list[dict]) -> str:
    if not rows:
        return "(결과 없음)"
    return "<br>".join(f"`{r['id'][:8]}` {r['claim_text'][:60]}" for r in rows)


def main() -> int:
    conn = connect()
    migrate(conn)
    if not conn.is_postgres:
        print("SQLite 모드 — 의미 검색을 지원하지 않아 리콜 비교를 수행할 수 없습니다.")
        conn.close()
        return 0

    lines = ["# A6 동의어 리콜 실험 — 키워드 vs 하이브리드", "", f"limit={LIMIT}건", ""]
    for q in QUERIES:
        kw = keyword_search(conn, q, limit=LIMIT)
        hy = hybrid_search(q, limit=LIMIT, conn=conn)
        kw_ids = {r["id"] for r in kw}
        semantic_only = [r for r in hy if r["id"] not in kw_ids]

        lines.append(f'## "{q}"')
        lines.append("")
        lines.append("| 구분 | 결과 |")
        lines.append("|---|---|")
        lines.append(f"| 키워드 단독 ({len(kw)}건) | {_fmt(kw)} |")
        lines.append(f"| 하이브리드 ({len(hy)}건) | {_fmt(hy)} |")
        lines.append(f"| **키워드가 놓치고 의미가 찾은 claim** ({len(semantic_only)}건) | "
                      f"{_fmt(semantic_only)} |")
        lines.append("")

    conn.close()
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

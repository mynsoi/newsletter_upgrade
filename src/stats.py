"""파이프라인 현황 요약 — 교대 인수인계용 (/status 커맨드가 호출).

사용: make stats
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from db import ROOT, connect, migrate  # noqa: E402


def section(title: str) -> None:
    print(f"\n## {title}")


def main() -> int:
    conn = connect()
    migrate(conn)

    section("문서 (외부)")
    rows = conn.execute(
        "SELECT tier, status, COUNT(*) n FROM documents GROUP BY tier, status ORDER BY tier"
    ).fetchall()
    if not rows:
        print("  (없음 — make collect 를 실행하세요)")
    for r in rows:
        print(f"  {r['tier']}  {r['status']:<9} {r['n']:>5}건")

    section("Claims")
    rows = conn.execute(
        "SELECT stance, COUNT(*) n FROM claims GROUP BY stance ORDER BY n DESC"
    ).fetchall()
    total = sum(r["n"] for r in rows)
    print(f"  총 {total}건" if rows else "  (없음)")
    for r in rows:
        print(f"    {r['stance']:<12} {r['n']:>5}건")
    if total:
        stances = {r["stance"] for r in rows}
        if not ({"optimistic", "cautious"} & stances == {"optimistic", "cautious"}):
            print("  [주의] 낙관/신중 양쪽 stance가 모두 확보되지 않음 — 상반 관점 규칙(기획서 6.3) 충족 불가")

    section("내부 자료")
    rows = conn.execute(
        "SELECT security, api_eligible, COUNT(*) n FROM internal_docs "
        "GROUP BY security, api_eligible"
    ).fetchall()
    if not rows:
        print("  (없음 — internal/에 파일 등록 후 make sync)")
    for r in rows:
        api = "API가능" if r["api_eligible"] else "API제외(이행기)"
        print(f"  {r['security']}등급 {api}: {r['n']}건")

    section("아티클")
    rows = conn.execute(
        "SELECT status, COUNT(*) n FROM articles GROUP BY status"
    ).fetchall()
    if not rows:
        print("  (없음)")
    for r in rows:
        print(f"  {r['status']:<10} {r['n']}건")

    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

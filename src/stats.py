"""파이프라인 현황 요약 — 교대 인수인계용 (/status 커맨드가 호출).

사용: make stats
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from db import ROOT, connect, migrate  # noqa: E402

# Windows 콘솔(cp949)에서 '—' 같은 글자로 UnicodeEncodeError가 나며 죽지 않도록(rss.py 등과 동일, 2026-11-10)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


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

    section("문서 카드 (document_cards)")
    n = conn.execute("SELECT COUNT(*) n FROM document_cards").fetchone()["n"]
    print(f"  총 {n}장" if n else "  (없음)")
    for r in conn.execute(
            "SELECT material_type, COUNT(*) n FROM document_cards GROUP BY material_type "
            "ORDER BY n DESC").fetchall():
        print(f"    {r['material_type']:<8} {r['n']:>5}장")

    section("내부 자료")
    rows = conn.execute(
        "SELECT type, COUNT(*) n FROM internal_docs GROUP BY type"
    ).fetchall()
    if not rows:
        print("  (없음 — internal/에 파일 등록 후 make sync)")
    for r in rows:
        print(f"  {r['type'] or '(유형 미기재)'}: {r['n']}건")

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

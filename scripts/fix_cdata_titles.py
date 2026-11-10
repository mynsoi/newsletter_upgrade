"""documents.title의 CDATA 래퍼 일괄 정리 — 1회성 데이터 보정 (2026-11-10).

bain-insights 피드가 제목을 이스케이프된 CDATA로 보내 154편 전부 `<![CDATA[…]]>`가 남았다.
수집기는 collectors/store.py의 clean_title로 고쳤고, 이 스크립트는 이미 들어온 행을 고친다.

  python scripts/fix_cdata_titles.py           # 미리보기 — 바뀔 제목만 출력(DB 쓰기 없음)
  python scripts/fix_cdata_titles.py --write   # 실제 UPDATE

소스를 가리지 않고 제목에 'CDATA'가 든 행만 대상으로 한다. 같은 함수(clean_title)를 써서
수집기와 결과가 같다. 작업실 원문 파일의 제목은 다음 'Supabase 받기'가 다시 쓴다.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from db import connect  # noqa: E402
from collectors.store import clean_title  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--write", action="store_true", help="실제로 UPDATE (없으면 미리보기)")
    args = p.parse_args(argv)
    conn = connect()
    rows = conn.execute(
        "SELECT id, source_id, title FROM documents WHERE title LIKE ?", ("%CDATA%",)).fetchall()
    fixes = [(r["id"], r["source_id"], r["title"], clean_title(r["title"])) for r in rows]
    fixes = [f for f in fixes if f[2] != f[3]]
    by_src: dict[str, int] = {}
    for _, sid, _, _ in fixes:
        by_src[sid] = by_src.get(sid, 0) + 1
    print(f"대상 {len(fixes)}편 — " + ", ".join(f"{k} {v}" for k, v in sorted(by_src.items())))
    for _, sid, old, new in fixes[:5]:
        print(f"  [{sid}] {old[:70]}\n      → {new[:70]}")
    if not args.write:
        print("미리보기 — 고치려면 --write")
        conn.close()
        return 0
    for doc_id, _, _, new in fixes:
        conn.execute("UPDATE documents SET title = ? WHERE id = ?", (new, doc_id))
    conn.commit()
    left = conn.execute("SELECT COUNT(*) c FROM documents WHERE title LIKE ?", ("%CDATA%",)).fetchone()["c"]
    print(f"고침 {len(fixes)}편 · 남은 CDATA 제목 {left}편")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

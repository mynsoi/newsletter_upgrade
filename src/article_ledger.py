"""인용 원장(article_sources) — 발행본이 실제로 인용한 claim을 문단 단위로 기록한다.

원장이 있어야 돌아가는 것(기획서 90행): 검증 게이트의 실사용 근거 재계산 · 발행 후 근거 역추적
(문단→claim→원문→출처) · 과거 글과의 논지 중복 검사 · **"6개월 무인용 소스 퇴출" 집계(4.2)**.
2026-09-30 월간 소스 리뷰 때 이 원장이 0행이어서(발행 절차에 기록 단계가 없었다) 파일의 claim ID를
역추적하는 대리 지표를 써야 했다 — content/reports/source-review-2026-09.md 2장.

원본은 발행본 본문의 `<!-- claims: ID, ID -->` 주석이다(verify_article.parse_article로 읽는다 —
검증 게이트와 같은 파서라 "검증한 인용"과 "기록한 인용"이 어긋나지 않는다).

- paragraph_ref: "소제목 ¶n" — 그 소제목 아래 n번째 문단. 발행본은 고정본이라 안정적이다.
- role: 증거 파일(content/evidence/{slug}.json)의 자유 서술 role을 세 값으로 보수적으로 대응시킨다.
  경계 조건·상반·반론·한계 → counter / 관찰된 신호·내부 맥락 → context / 그 밖 → support.
  증거 파일에 없는 claim은 NULL. 인용 횟수 집계는 role과 무관하다.
- 재실행 안전: 기록 전에 그 아티클의 원장 행을 지우고 다시 쓴다.

사용:
  python src/article_ledger.py record ai-productivity-paradox   # 발행본 → 원장
  python src/article_ledger.py sources                          # 소스별 인용 횟수(월간 리뷰용)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from db import ROOT, connect, migrate  # noqa: E402
from verify_article import parse_article  # noqa: E402

PUBLISHED_DIR = ROOT / "content" / "published"
EVIDENCE_DIR = ROOT / "content" / "evidence"

COUNTER_HINTS = ("경계 조건", "상반", "반론", "한계")
CONTEXT_HINTS = ("관찰된 신호", "내부 맥락", "내부 자료", "맥락")


def map_role(role_text: str | None) -> str | None:
    """증거 파일의 자유 서술 role → support / counter / context. 없으면 None."""
    if not role_text:
        return None
    if any(h in role_text for h in COUNTER_HINTS):
        return "counter"
    if any(role_text.startswith(h) for h in CONTEXT_HINTS):
        return "context"
    return "support"


def ledger_rows(md: str, evidence: dict | None = None) -> list[tuple[str, str, str | None]]:
    """발행본 본문 → [(claim_id, paragraph_ref, role)]. 같은 문단의 같은 claim은 한 번만."""
    roles = {c["id"]: map_role(c.get("role")) for c in (evidence or {}).get("claims", [])}
    segments, _ = parse_article(md)
    rows: list[tuple[str, str, str | None]] = []
    seen: set[tuple[str, str]] = set()
    counter: dict[str, int] = {}
    for seg in segments:
        heading = seg.heading or "(머리)"
        counter[heading] = counter.get(heading, 0) + 1
        ref = f"{heading} ¶{counter[heading]}"
        for cid in seg.claim_ids:
            if (cid, ref) in seen:
                continue
            seen.add((cid, ref))
            rows.append((cid, ref, roles.get(cid)))
    return rows


def record(conn, article_id: str, md: str, evidence: dict | None = None) -> int:
    """원장을 다시 쓴다(재실행 안전). 반환: 기록한 행 수.

    DB에 없는 claim ID가 있으면 아무것도 쓰지 않고 실패한다 — 조용히 건너뛰면 원장이 발행본과
    어긋난 채 남는다.
    """
    rows = ledger_rows(md, evidence)
    ids = sorted({cid for cid, _, _ in rows})
    if ids:
        ph = ",".join("?" for _ in ids)
        found = {r["id"] for r in conn.execute(f"SELECT id FROM claims WHERE id IN ({ph})", tuple(ids))}
        missing = [i for i in ids if i not in found]
        if missing:
            raise ValueError(f"DB에 없는 claim {len(missing)}건 — 원장을 쓰지 않았다: {', '.join(missing)}")
    conn.execute("DELETE FROM article_sources WHERE article_id = ?", (article_id,))
    for cid, ref, role in rows:
        conn.execute(
            "INSERT INTO article_sources (article_id, claim_id, paragraph_ref, role) VALUES (?,?,?,?)",
            (article_id, cid, ref, role))
    conn.commit()
    return len(rows)


def citations_by_source(conn) -> list[dict]:
    """소스별 인용 집계 — 서로 다른 claim 수, 인용한 아티클 수, 마지막 인용일."""
    return [dict(r) for r in conn.execute(
        "SELECT d.source_id, COUNT(DISTINCT s.claim_id) AS claims, "
        "COUNT(DISTINCT s.article_id) AS articles, "
        "MAX(COALESCE(a.published_at, a.created_at)) AS last_cited "
        "FROM article_sources s "
        "JOIN claims c ON c.id = s.claim_id "
        "JOIN documents d ON d.id = c.document_id "
        "JOIN articles a ON a.id = s.article_id "
        "GROUP BY d.source_id ORDER BY claims DESC, d.source_id")]


def _record_slug(slug: str) -> int:
    md_path = PUBLISHED_DIR / f"{slug}.md"
    if not md_path.exists():
        print(f"오류: 발행본이 없다 — {md_path.relative_to(ROOT)}")
        return 2
    ev_path = EVIDENCE_DIR / f"{slug}.json"
    evidence = json.loads(ev_path.read_text(encoding="utf-8")) if ev_path.exists() else None
    conn = connect()
    migrate(conn)
    art = conn.execute("SELECT id, status FROM articles WHERE slug = ?", (slug,)).fetchone()
    if art is None:
        print(f"오류: articles에 slug '{slug}' 행이 없다 — 승인 기록(/publish ②)부터")
        conn.close()
        return 2
    n = record(conn, art["id"], md_path.read_text(encoding="utf-8"), evidence)
    roles = {r["role"]: r["n"] for r in conn.execute(
        "SELECT role, COUNT(*) n FROM article_sources WHERE article_id = ? GROUP BY role", (art["id"],))}
    claims = conn.execute("SELECT COUNT(DISTINCT claim_id) n FROM article_sources WHERE article_id = ?",
                          (art["id"],)).fetchone()["n"]
    role_note = ", ".join(f"{k or '미분류'} {v}" for k, v in sorted(roles.items(), key=lambda x: str(x[0])))
    print(f"원장 기록: {slug} — {n}행(문단×claim) · 서로 다른 claim {claims}건 · 역할 {role_note}"
          + ("" if evidence else " (증거 파일 없음 — 역할 전부 미분류)"))
    conn.close()
    return 0


def _print_sources() -> int:
    conn = connect()
    migrate(conn)
    rows = citations_by_source(conn)
    conn.close()
    if not rows:
        print("(원장 비어 있음 — python src/article_ledger.py record <slug>)")
        return 0
    print(f"{'소스':28s} {'claim':>5} {'아티클':>5}  마지막 인용")
    for r in rows:
        print(f"{r['source_id']:28s} {r['claims']:>5} {r['articles']:>5}  {str(r['last_cited'])[:10]}")
    return 0


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description="인용 원장(article_sources) 기록·조회")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("record", help="발행본의 claims 주석 → 원장(재실행 안전)")
    r.add_argument("slug")
    sub.add_parser("sources", help="소스별 인용 횟수 (월간 소스 리뷰용)")
    args = p.parse_args(argv)
    return _record_slug(args.slug) if args.cmd == "record" else _print_sources()


if __name__ == "__main__":
    raise SystemExit(main())

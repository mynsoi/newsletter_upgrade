"""claim 하이브리드 검색 — 키워드(트라이그램/LIKE) + 의미(pgvector halfvec 코사인) 결합.

/draft ② 증거 수집이 이 모듈의 hybrid_search()를 쓴다. 티어·stance·기간 필터는
기존 claim 추출 필터(src/enrich/extract_claims.py build_doc_filters)와 같은 값 형식을 쓴다
(tiers/stances는 목록, published_after/before는 YYYY-MM-DD).

의미 검색은 SQLite 모드이거나 OpenAI 키가 없으면 자동으로 건너뛰고 키워드 검색만
반환한다(오류가 아니라 정상 폴백). 결과마다 match_type을 표기해 사람이 확인할 수 있게
한다: 'keyword' | 'semantic' | 'both'.

사용(CLI 확인용):
  python src/search/semantic.py "심리적 안전감" --tiers T1,T2 --stances optimistic,cautious
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db import connect, migrate  # noqa: E402
from search.embed import VECTOR_TYPE, embed_one, to_vector_literal  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DEFAULT_LIMIT = 20

_SELECT_COLS = (
    "c.id, c.document_id, c.claim_text, c.evidence_type, c.stance, c.metric, c.confidence, "
    "d.title AS document_title, d.source_id, d.tier, d.url, d.published_at"
)


def _claim_filters(tiers: list[str] | None = None, stances: list[str] | None = None,
                   published_after: str | None = None,
                   published_before: str | None = None) -> tuple[str, list]:
    """claims/documents 조인 대상 필터. 반환: (WHERE 조각, 파라미터 목록)."""
    clauses, params = [], []
    if tiers:
        clauses.append(f"d.tier IN ({', '.join('?' for _ in tiers)})")
        params.extend(tiers)
    if stances:
        clauses.append(f"c.stance IN ({', '.join('?' for _ in stances)})")
        params.extend(stances)
    if published_after:
        clauses.append("d.published_at >= ?")
        params.append(published_after)
    if published_before:
        clauses.append("d.published_at < ?")
        params.append(published_before)
    return ("".join(f" AND {c}" for c in clauses), params)


def keyword_search(conn, query: str, *, tiers=None, stances=None, published_after=None,
                   published_before=None, limit: int = DEFAULT_LIMIT) -> list[dict]:
    """트라이그램 유사도(PostgreSQL) / LIKE(SQLite) 기반 claim_text 검색."""
    where, params = _claim_filters(tiers, stances, published_after, published_before)
    if conn.is_postgres:
        sql = (f"SELECT {_SELECT_COLS}, similarity(c.claim_text, ?) AS score "
               "FROM claims c JOIN documents d ON d.id = c.document_id "
               f"WHERE c.claim_text ILIKE ?{where} ORDER BY score DESC LIMIT ?")
        params_all = [query, f"%{query}%", *params, limit]
    else:
        sql = (f"SELECT {_SELECT_COLS} "
               "FROM claims c JOIN documents d ON d.id = c.document_id "
               f"WHERE c.claim_text LIKE ?{where} ORDER BY c.id DESC LIMIT ?")
        params_all = [f"%{query}%", *params, limit]
    rows = conn.execute(sql, tuple(params_all)).fetchall()
    out = [dict(r) for r in rows]
    for r in out:
        r["match_type"] = "keyword"
    return out


def semantic_search(conn, query_vector: list[float], *, tiers=None, stances=None,
                    published_after=None, published_before=None,
                    limit: int = DEFAULT_LIMIT) -> list[dict]:
    """코사인 거리(<=>) 기반 claim 임베딩 검색. PostgreSQL 전용 — 그 외는 빈 목록."""
    if not conn.is_postgres:
        return []
    where, params = _claim_filters(tiers, stances, published_after, published_before)
    vec = to_vector_literal(query_vector)
    sql = (f"SELECT {_SELECT_COLS}, 1 - (c.embedding <=> ?::{VECTOR_TYPE}) AS score "
           "FROM claims c JOIN documents d ON d.id = c.document_id "
           f"WHERE c.embedding IS NOT NULL{where} "
           f"ORDER BY c.embedding <=> ?::{VECTOR_TYPE} LIMIT ?")
    rows = conn.execute(sql, tuple([vec, *params, vec, limit])).fetchall()
    out = [dict(r) for r in rows]
    for r in out:
        r["match_type"] = "semantic"
    return out


def hybrid_search(query: str, *, tiers: list[str] | None = None,
                  stances: list[str] | None = None, published_after: str | None = None,
                  published_before: str | None = None, limit: int = DEFAULT_LIMIT,
                  conn=None) -> list[dict]:
    """키워드 + 의미 검색 결과를 합쳐 반환한다 (score 내림차순, 최대 limit건).

    두 검색 모두에 걸린 claim은 match_type='both'로 표시되고 semantic_score도 함께 남는다.
    SQLite 모드이거나 OpenAI 키가 없으면 키워드 검색 결과만 반환한다(자동 폴백, 오류 아님).
    conn을 넘기면 그 연결을 재사용(테스트용) — 생략 시 이 함수가 열고 닫는다.
    """
    owns_conn = conn is None
    if owns_conn:
        conn = connect()
        migrate(conn)
    try:
        keyword_hits = keyword_search(conn, query, tiers=tiers, stances=stances,
                                      published_after=published_after,
                                      published_before=published_before, limit=limit)
        vec = embed_one(query) if conn.is_postgres else None
        semantic_hits = (
            semantic_search(conn, vec, tiers=tiers, stances=stances,
                            published_after=published_after,
                            published_before=published_before, limit=limit)
            if vec is not None else []
        )

        merged: dict[str, dict] = {r["id"]: r for r in keyword_hits}
        for r in semantic_hits:
            if r["id"] in merged:
                merged[r["id"]]["match_type"] = "both"
                merged[r["id"]]["semantic_score"] = r.get("score")
            else:
                merged[r["id"]] = r
        results = list(merged.values())
        results.sort(key=lambda r: r.get("score") or r.get("semantic_score") or 0, reverse=True)
        return results[:limit]
    finally:
        if owns_conn:
            conn.close()


def _print_cli(rows: list[dict]) -> None:
    if not rows:
        print("(결과 없음)")
        return
    for r in rows:
        tag = {"keyword": "[키워드]", "semantic": "[의미]", "both": "[키워드+의미]"}[r["match_type"]]
        print(f"{tag} {r['tier']:<3} {r['stance']:<11} {r['claim_text'][:70]}")
        print(f"        source={r['source_id']} doc={(r['document_title'] or '')[:40]!r} id={r['id']}")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="claim 하이브리드 검색 (키워드+의미)")
    p.add_argument("query")
    p.add_argument("--tiers", help="쉼표 구분. 예: T1,T2")
    p.add_argument("--stances", help="쉼표 구분. 예: optimistic,cautious")
    p.add_argument("--published-after", help="YYYY-MM-DD")
    p.add_argument("--published-before", help="YYYY-MM-DD")
    p.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    args = p.parse_args(argv)

    tiers = [t.strip().upper() for t in (args.tiers or "").split(",") if t.strip()]
    stances = [s.strip() for s in (args.stances or "").split(",") if s.strip()]

    rows = hybrid_search(args.query, tiers=tiers or None, stances=stances or None,
                         published_after=args.published_after,
                         published_before=args.published_before, limit=args.limit)
    _print_cli(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""A6 의미 기반 검색(pgvector) 테스트.

- SQLite 모드(기본, test_db 픽스처): 네트워크·OpenAI 키 불필요 — 키워드 폴백 경로만 검증.
- PostgreSQL 모드(DATABASE_URL 설정 시에만): pgvector SQL 자체를 검증하되, 임베딩은
  raw SQL로 직접 삽입해 OpenAI API 호출 없이 돈다(test_run_locks.py의 기존 관행과 동일 —
  고유 source_id 마커로 삽입 후 finally에서 정리).
"""
import os
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))


@pytest.fixture()
def test_db(tmp_path, monkeypatch):
    monkeypatch.setenv("PIPELINE_DB", str(tmp_path / "test.db"))
    monkeypatch.delenv("DATABASE_URL", raising=False)  # 로컬 테스트는 SQLite 모드 강제
    monkeypatch.delenv("OPENAI_API_KEY_EMBED", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    for mod in list(sys.modules):
        if mod in ("db", "handoff") or mod.startswith(("collectors", "enrich", "search")):
            del sys.modules[mod]
    import db
    conn = db.connect()
    db.migrate(conn)
    yield conn, db
    conn.close()


def _seed(conn, db):
    doc_a, doc_b = db.new_id(), db.new_id()
    conn.execute(
        "INSERT INTO documents (id, source_id, tier, url, title, body, status, published_at) "
        "VALUES (?,?,?,?,?,?, 'enriched', ?)",
        (doc_a, "src-a", "T1", f"http://x/{doc_a}", "문서 A", "본문 A", "2026-01-01"))
    conn.execute(
        "INSERT INTO documents (id, source_id, tier, url, title, body, status, published_at) "
        "VALUES (?,?,?,?,?,?, 'enriched', ?)",
        (doc_b, "src-b", "T3", f"http://x/{doc_b}", "문서 B", "본문 B", "2026-06-01"))
    c1, c2 = db.new_id(), db.new_id()
    conn.execute(
        "INSERT INTO claims (id, document_id, claim_text, evidence_type, stance) "
        "VALUES (?,?,?,?,?)",
        (c1, doc_a, "심리적 안전감은 학습 행동을 매개로 성과에 기여한다", "theory", "neutral"))
    conn.execute(
        "INSERT INTO claims (id, document_id, claim_text, evidence_type, stance) "
        "VALUES (?,?,?,?,?)",
        (c2, doc_b, "관리자는 감시자에서 코치로 역할을 바꾼다", "opinion", "optimistic"))
    conn.commit()
    return doc_a, doc_b, c1, c2


# --------------------------------------------------------------------------- #
# src/search/embed.py — 순수 로직 (네트워크 불필요)                            #
# --------------------------------------------------------------------------- #
def test_to_vector_literal_formats_as_pgvector_text():
    from search.embed import to_vector_literal
    assert to_vector_literal([0.1, -0.2, 3.0]) == "[0.1,-0.2,3.0]"


def test_api_key_prefers_embed_specific_var(monkeypatch):
    from search.embed import api_key
    monkeypatch.delenv("OPENAI_API_KEY_EMBED", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "generic-key")
    assert api_key() == "generic-key"
    monkeypatch.setenv("OPENAI_API_KEY_EMBED", "embed-specific-key")
    assert api_key() == "embed-specific-key"


def test_get_client_returns_none_without_any_key(monkeypatch):
    from search.embed import get_client
    monkeypatch.delenv("OPENAI_API_KEY_EMBED", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert get_client() is None


def test_embed_one_returns_none_without_key(monkeypatch):
    import search.embed as embed
    monkeypatch.setattr(embed, "get_client", lambda: None)
    assert embed.embed_one("아무 텍스트") is None


def test_run_skips_on_sqlite_without_touching_db(test_db, monkeypatch):
    """SQLite 모드는 vector 컬럼이 없으므로 connect()조차 호출하지 않고 즉시 종료해야 한다."""
    import search.embed as embed

    def _boom():
        raise AssertionError("SQLite 모드에서 connect()가 호출되면 안 됨")
    monkeypatch.setattr(embed, "connect", _boom)
    assert embed.run(100) == 0


def test_run_skips_when_no_key_even_in_postgres_mode(monkeypatch):
    import search.embed as embed
    monkeypatch.setattr(embed, "IS_POSTGRES", True)
    monkeypatch.setattr(embed, "get_client", lambda: None)

    def _boom():
        raise AssertionError("키 없이는 connect()가 호출되면 안 됨")
    monkeypatch.setattr(embed, "connect", _boom)
    assert embed.run(100) == 0


# --------------------------------------------------------------------------- #
# src/search/embed.py — arXiv 보존 기간 (2026-09-22)                           #
# --------------------------------------------------------------------------- #
def test_months_ago_clamps_to_month_end():
    from datetime import date
    import search.embed as embed
    assert embed.months_ago(date(2026, 9, 22), 6) == date(2026, 3, 22)
    assert embed.months_ago(date(2026, 8, 31), 6) == date(2026, 2, 28)   # 2월 말일로 보정
    assert embed.months_ago(date(2026, 3, 15), 6) == date(2025, 9, 15)   # 해 넘김


def test_arxiv_cutoff_disabled_by_zero_or_none():
    from datetime import date
    import search.embed as embed
    assert embed.arxiv_cutoff(0) is None
    assert embed.arxiv_cutoff(None) is None
    assert embed.arxiv_cutoff(6, today=date(2026, 9, 22)) == "2026-03-22"


def _add_doc(conn, db, source_id, published_at, fetched_by=None):
    doc_id = db.new_id()
    conn.execute(
        "INSERT INTO documents (id, source_id, tier, url, title, body, status, published_at, "
        "fetched_by) VALUES (?,?,?,?,?,?, 'enriched', ?, ?)",
        (doc_id, source_id, "T1", f"http://x/{doc_id}", doc_id, "본문", published_at, fetched_by))
    conn.commit()
    return doc_id


def test_stale_arxiv_selects_only_old_bulk_arxiv(test_db):
    """경계 이전 발행 arXiv만 고른다 — 최근 arXiv·사람이 고른 문서·발행일 없는 문서·
    arXiv 아닌 소스는 유지(벡터를 비우지 않는다)."""
    conn, db = test_db
    import search.embed as embed
    old = _add_doc(conn, db, "arxiv-cs-hc", "2025-06-10")
    _add_doc(conn, db, "arxiv-cs-cy", "2026-06-10")                        # 최근 — 유지
    _add_doc(conn, db, "arxiv-econ-gn", "2023-03-17", fetched_by="browse")  # 핵심 논문 — 유지
    _add_doc(conn, db, "arxiv-cs-si", None)                                # 발행일 모름 — 유지
    _add_doc(conn, db, "hbr-korea", "2025-01-01")                          # arXiv 아님 — 유지
    sub, params = embed.stale_arxiv_docs_sql("2026-03-22")
    assert {r["id"] for r in conn.execute(sub, tuple(params))} == {old}
    assert "%" not in sub   # LIKE 패턴은 파라미터로 — psycopg 자리표시자 오인 방지


def test_prune_is_noop_when_disabled(test_db):
    conn, db = test_db
    import search.embed as embed
    assert embed.prune_stale_arxiv(conn, None) == 0


def test_run_prune_only_needs_no_key(monkeypatch):
    """--prune-only는 API를 쓰지 않으므로 키 없이도 DB 비우기를 수행한다."""
    import search.embed as embed
    calls = []

    class _Conn:
        def close(self):
            calls.append("close")
    monkeypatch.setattr(embed, "IS_POSTGRES", True)
    monkeypatch.setattr(embed, "get_client", lambda: None)
    monkeypatch.setattr(embed, "connect", lambda: _Conn())
    monkeypatch.setattr(embed, "migrate", lambda conn: None)
    monkeypatch.setattr(embed, "prune_stale_arxiv", lambda conn, cutoff: calls.append(cutoff) or 3)
    assert embed.run(100, retention_months=6, prune_only=True) == 0
    assert calls[0] is not None and calls[-1] == "close"


@pytest.mark.skipif(not os.environ.get("DATABASE_URL"),
                    reason="DATABASE_URL 미설정 — PostgreSQL 보존 기간 테스트 생략")
def test_pruned_arxiv_is_not_reselected_on_postgres(monkeypatch):
    """핵심 보장: 비운 arXiv claim이 'embedding IS NULL'로 다음 실행에 다시 선정되지 않는다.
    운영 DB에서 돌므로 고유 source_id 마커로 삽입하고 finally에서 정리한다.
    대상 패턴을 마커로 좁힌다 — 그대로 두면 실제 arXiv claim의 벡터까지 테스트가 지운다."""
    for mod in list(sys.modules):
        if mod == "db" or mod.startswith("search"):
            del sys.modules[mod]
    import db
    import search.embed as embed
    conn = db.connect()
    marker = f"zztest-arxiv-{db.new_id()[:8].lower()}"   # LIKE 와일드카드('_'·'%') 없음
    monkeypatch.setattr(embed, "ARXIV_SOURCE_PATTERN", marker)
    old_doc, new_doc = db.new_id(), db.new_id()
    old_claim, new_claim = db.new_id(), db.new_id()
    try:
        for doc_id, pub in ((old_doc, "2020-01-01"), (new_doc, "2099-01-01")):
            conn.execute(
                "INSERT INTO documents (id, source_id, tier, url, title, body, status, published_at) "
                "VALUES (?,?,?,?,?,?, 'enriched', ?)",
                (doc_id, marker, "T1", f"http://x/{doc_id}", "t", "b", pub))
        vec = embed.to_vector_literal([0.1] * embed.DIMENSIONS)
        for claim_id, doc_id in ((old_claim, old_doc), (new_claim, new_doc)):
            conn.execute(
                "INSERT INTO claims (id, document_id, claim_text, evidence_type, stance, embedding) "
                f"VALUES (?,?,?,?,?, ?::{embed.VECTOR_TYPE})",
                (claim_id, doc_id, "보존 기간 테스트", "theory", "neutral", vec))
        conn.commit()

        cutoff = "2026-03-22"
        assert embed.prune_stale_arxiv(conn, cutoff) == 1   # 마커 문서의 옛 claim 1건만
        rows = {r["id"]: r["e"] for r in conn.execute(
            "SELECT id, embedding IS NOT NULL AS e FROM claims WHERE id IN (?, ?)",
            (old_claim, new_claim))}
        assert rows == {old_claim: False, new_claim: True}
        pending_ids = {r["id"] for r in embed.select_pending(conn, None, cutoff)}
        assert old_claim not in pending_ids   # 비운 claim을 다시 채우지 않는다
    finally:
        conn.execute("DELETE FROM claims WHERE id IN (?, ?)", (old_claim, new_claim))
        conn.execute("DELETE FROM documents WHERE source_id = ?", (marker,))
        conn.commit()
        conn.close()


# --------------------------------------------------------------------------- #
# src/search/semantic.py — 필터 SQL 조립                                      #
# --------------------------------------------------------------------------- #
def test_claim_filters_build_where_and_params():
    from search.semantic import _claim_filters
    where, params = _claim_filters(tiers=["T1", "T2"], stances=["optimistic"],
                                   published_after="2026-01-01", published_before="2026-07-01")
    assert "d.tier IN (?, ?)" in where
    assert "c.stance IN (?)" in where
    assert "d.published_at >= ?" in where
    assert "d.published_at < ?" in where
    assert params == ["T1", "T2", "optimistic", "2026-01-01", "2026-07-01"]


def test_claim_filters_excludes_from_summary_by_default():
    """인자를 주지 않아도 요약뿐 문서의 claim은 빠진다 — 증거로 쓸 수 없기 때문 (migrations/008)."""
    from search.semantic import _claim_filters
    where, params = _claim_filters()
    assert where.strip() == "AND COALESCE(c.from_summary, 0) = 0" and params == []


def test_claim_filters_can_include_from_summary_explicitly():
    from search.semantic import _claim_filters
    where, params = _claim_filters(include_from_summary=True)
    assert where == "" and params == []


# --------------------------------------------------------------------------- #
# semantic.py — SQLite 폴백 (키워드 검색만, 의미 검색은 자동 생략)             #
# --------------------------------------------------------------------------- #
def test_keyword_search_sqlite_fallback(test_db):
    conn, db = test_db
    _seed(conn, db)
    from search.semantic import keyword_search

    rows = keyword_search(conn, "심리적")
    assert len(rows) == 1
    assert rows[0]["match_type"] == "keyword"
    assert rows[0]["claim_text"].startswith("심리적")


def test_keyword_search_applies_tier_and_stance_filters(test_db):
    conn, db = test_db
    _seed(conn, db)
    from search.semantic import keyword_search

    assert keyword_search(conn, "역할", tiers=["T1"]) == []  # 해당 claim은 T3 문서 소속
    rows = keyword_search(conn, "역할", tiers=["T3"], stances=["optimistic"])
    assert len(rows) == 1


def test_semantic_search_returns_empty_on_sqlite(test_db):
    conn, db = test_db
    _seed(conn, db)
    from search.semantic import semantic_search
    assert semantic_search(conn, [0.1] * 1536) == []


def test_hybrid_search_falls_back_to_keyword_only_on_sqlite(test_db):
    conn, db = test_db
    _seed(conn, db)
    from search.semantic import hybrid_search, keyword_search

    kw = keyword_search(conn, "코치")
    hy = hybrid_search("코치", conn=conn)
    assert {r["id"] for r in hy} == {r["id"] for r in kw}
    assert hy and all(r["match_type"] == "keyword" for r in hy)


# --------------------------------------------------------------------------- #
# PostgreSQL 모드 (DATABASE_URL 설정 시에만) — pgvector SQL 자체를 검증한다.   #
# 임베딩은 raw SQL로 직접 삽입해 OpenAI API 키 없이 돈다.                      #
# --------------------------------------------------------------------------- #
@pytest.mark.skipif(not os.environ.get("DATABASE_URL"),
                    reason="DATABASE_URL 미설정 — pgvector 검색 테스트 생략")
def test_semantic_search_ranks_by_cosine_distance_on_postgres():
    for mod in list(sys.modules):
        if mod == "db" or mod.startswith("search"):
            del sys.modules[mod]
    import db
    assert db.IS_POSTGRES
    from search.embed import VECTOR_TYPE, to_vector_literal
    from search.semantic import hybrid_search, semantic_search

    conn = db.connect()
    db.migrate(conn)
    marker = "pg-search-test"
    try:
        doc_id = db.new_id()
        conn.execute(
            "INSERT INTO documents (id, source_id, tier, url, title, body, status) "
            "VALUES (?,?,?,?,?,?, 'enriched')",
            (doc_id, marker, "T2", f"http://{marker}/{doc_id}", "테스트 문서", "본문"))
        near_id, far_id = db.new_id(), db.new_id()
        conn.execute(
            "INSERT INTO claims (id, document_id, claim_text, stance) VALUES (?,?,?,?)",
            (near_id, doc_id, "가까운 벡터 claim", "neutral"))
        conn.execute(
            "INSERT INTO claims (id, document_id, claim_text, stance) VALUES (?,?,?,?)",
            (far_id, doc_id, "먼 벡터 claim", "neutral"))
        conn.commit()

        near_vec = [1.0] + [0.0] * 1535
        far_vec = [0.0] * 1535 + [1.0]
        conn.execute(f"UPDATE claims SET embedding = ?::{VECTOR_TYPE} WHERE id = ?",
                    (to_vector_literal(near_vec), near_id))
        conn.execute(f"UPDATE claims SET embedding = ?::{VECTOR_TYPE} WHERE id = ?",
                    (to_vector_literal(far_vec), far_id))
        conn.commit()

        query_vec = [0.99] + [0.01] * 1535
        rows = semantic_search(conn, query_vec, limit=5)
        mine = [r for r in rows if r["document_id"] == doc_id]
        assert mine and mine[0]["id"] == near_id  # 코사인 거리상 가까운 claim이 먼저 나온다
        assert all(r["match_type"] == "semantic" for r in rows)

        # 이 환경에는 OpenAI 키가 없다 — hybrid_search는 postgres 모드에서도 키가
        # 없으면 의미 검색 없이 키워드만 반환해야 한다(자동 폴백, 오류 아님).
        os.environ.pop("OPENAI_API_KEY_EMBED", None)
        os.environ.pop("OPENAI_API_KEY", None)
        hy = hybrid_search("가까운 벡터", conn=conn)
        assert any(r["id"] == near_id for r in hy)
        assert all(r["match_type"] == "keyword" for r in hy)
    finally:
        conn.execute(
            "DELETE FROM claims WHERE document_id IN "
            "(SELECT id FROM documents WHERE source_id = ?)", (marker,))
        conn.execute("DELETE FROM documents WHERE source_id = ?", (marker,))
        conn.commit()
        conn.close()

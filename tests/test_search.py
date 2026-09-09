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


def test_claim_filters_empty_when_no_args():
    from search.semantic import _claim_filters
    where, params = _claim_filters()
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
    from search.embed import to_vector_literal
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
        conn.execute("UPDATE claims SET embedding = ?::vector WHERE id = ?",
                    (to_vector_literal(near_vec), near_id))
        conn.execute("UPDATE claims SET embedding = ?::vector WHERE id = ?",
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

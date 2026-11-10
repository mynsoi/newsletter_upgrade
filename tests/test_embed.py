"""카드 임베딩(src/search/embed.py) 테스트 — SQLite 모드, 네트워크·OpenAI 키 불필요.

2026-11-10 claim 임베딩·arXiv 벡터 비우기·claim 하이브리드 검색(semantic.py)을 지우면서
그 테스트도 지웠다. 카드 조각 나누기는 test_doc_cards.py에 있다.
"""
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

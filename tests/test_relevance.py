"""관련성 판별 대상 선정 — 요약뿐인 T5 문서의 흐름 (migrations/008).

claim 추출을 없앤 뒤에도(2026-11-10) T5 요약분은 예전처럼 판별을 거친다. T2~T4의 요약분은
브라우저 격상을 기다리는 문서라 계속 제외한다. 예전 tests/test_topics.py에 있던 선정 테스트를
옮겨 왔다(그 파일은 토픽 발굴과 함께 지웠다).
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
    for mod in list(sys.modules):
        if mod in ("db", "handoff") or mod.startswith(("collectors", "enrich")):
            del sys.modules[mod]
    import db
    conn = db.connect()
    db.migrate(conn)
    yield conn, db
    conn.close()


def _doc(conn, doc_id, tier, *, summary_only, status="new"):
    conn.execute(
        "INSERT INTO documents (id, source_id, tier, url, title, body, status, summary_only) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (doc_id, f"src-{doc_id}", tier, f"http://x/{doc_id}", f"제목 {doc_id}",
         "본문", status, summary_only))


def test_select_target_docs_includes_t5_summary_only_but_not_other_tiers(test_db):
    conn, _ = test_db
    from enrich.relevance import select_target_docs
    _doc(conn, "full", "T3", summary_only=0)
    _doc(conn, "t5sum", "T5", summary_only=1)
    _doc(conn, "t2sum", "T2", summary_only=1)   # 브라우저 격상 대기 — 계속 제외
    conn.commit()
    assert sorted(d["id"] for d in select_target_docs(conn, 10)) == ["full", "t5sum"]


def test_select_target_docs_round_robin_applies_same_summary_gate(test_db):
    conn, _ = test_db
    from enrich.relevance import select_target_docs_round_robin
    _doc(conn, "t5sum", "T5", summary_only=1)
    _doc(conn, "t2sum", "T2", summary_only=1)
    conn.commit()
    assert [d["id"] for d in select_target_docs_round_robin(conn, 10)] == ["t5sum"]


def test_only_summary_filter_selects_retroactive_targets_only(test_db):
    conn, _ = test_db
    from enrich.relevance import select_target_docs
    _doc(conn, "full", "T5", summary_only=0)
    _doc(conn, "t5sum", "T5", summary_only=1)
    conn.commit()
    assert [d["id"] for d in select_target_docs(conn, 10, only_summary=True)] == ["t5sum"]


def test_summary_gate_sql_lists_only_allowed_tiers():
    from enrich.relevance import SUMMARY_GATE_TIERS, summary_gate_sql
    sql = summary_gate_sql()
    assert "'T5'" in sql and "'T2'" not in sql
    assert SUMMARY_GATE_TIERS == ("T5",)


def test_t5_summary_doc_is_judged_and_enriched(test_db, monkeypatch):
    """요약뿐인 T5 문서도 판별을 거쳐 enriched/rejected로 나뉜다(claim은 없다)."""
    conn, _ = test_db
    import enrich.relevance as rel
    _doc(conn, "t5ok", "T5", summary_only=1)
    _doc(conn, "t5off", "T5", summary_only=1)
    conn.commit()
    verdicts = {"제목 t5ok": "RELEVANT", "제목 t5off": "IRRELEVANT"}
    monkeypatch.setattr(rel, "call_model", lambda prompt, model, max_tokens: rel.ModelReply(
        next(v for k, v in verdicts.items() if k in prompt)))
    cost, stats = rel.CostState(), rel.RunStats()
    rel.process_batch(conn, rel.select_target_docs(conn, 10), "m", cost, stats, dry_run=False)
    status = {r["id"]: r["status"] for r in conn.execute("SELECT id, status FROM documents")}
    assert status == {"t5ok": "enriched", "t5off": "rejected"}
    assert stats.passed == 1 and stats.gated == 1 and cost.calls == 2

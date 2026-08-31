"""하루 1회 수집 보장 잠금 + claim 추출 문서 단위 동시성 제어 테스트.

- SQLite 모드: 기본 (test_db 픽스처가 PIPELINE_DB 설정 + DATABASE_URL 해제 + 모듈 리로드)
- PostgreSQL 모드: DATABASE_URL 이 설정돼 있을 때만 실행 (test_locks_on_postgres)
"""
import os
import sys
from datetime import datetime, timezone
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
    import handoff
    monkeypatch.setattr(handoff, "ensure_active", lambda *a, **k: None)  # 핸드오프 가드 우회
    conn = db.connect()
    db.migrate(conn)
    yield conn, db
    conn.close()


def _add_new_doc(conn, doc_id, body="본문 " * 300):
    conn.execute(
        "INSERT INTO documents (id, source_id, tier, url, title, body, status) "
        "VALUES (?,?,?,?,?,?,'new')",
        (doc_id, "s", "T3", f"http://x/{doc_id}", f"문서 {doc_id}", body))
    conn.commit()


# --------------------------------------------------------------------------- #
# 마이그레이션 003                                                             #
# --------------------------------------------------------------------------- #
def test_migration_003_creates_lock_schema(test_db):
    conn, _ = test_db
    cols = {r[1] for r in conn.execute("PRAGMA table_info(collection_runs)")}
    assert {"run_date", "host", "status", "started_at", "finished_at"} <= cols
    doc_cols = {r[1] for r in conn.execute("PRAGMA table_info(documents)")}
    assert "enrich_locked_at" in doc_cols


# --------------------------------------------------------------------------- #
# 하루 1회 수집 잠금                                                           #
# --------------------------------------------------------------------------- #
def test_begin_collection_first_wins_second_sees_running(test_db):
    conn, db = test_db
    assert db.begin_collection(conn, "host-a") == "acquired"
    assert db.begin_collection(conn, "host-b") == "running"  # 방금 시작 → 회수 불가
    row = conn.execute("SELECT host, status FROM collection_runs").fetchone()
    assert row["host"] == "host-a" and row["status"] == "running"


def test_begin_collection_done_after_completed(test_db):
    conn, db = test_db
    assert db.begin_collection(conn, "h") == "acquired"
    db.finish_collection(conn, ok=True)
    assert db.begin_collection(conn, "h") == "done"
    assert db.collection_done_today(conn) is True


def test_begin_collection_retries_after_failed(test_db):
    conn, db = test_db
    db.begin_collection(conn, "h")
    db.finish_collection(conn, ok=False)  # 도중 실패 → 그날은 잠기지 않음
    assert db.collection_done_today(conn) is False
    assert db.begin_collection(conn, "h2") == "acquired"
    assert conn.execute("SELECT status FROM collection_runs").fetchone()["status"] == "running"


def test_begin_collection_force_bypasses_completed(test_db):
    conn, db = test_db
    db.begin_collection(conn, "h")
    db.finish_collection(conn, ok=True)
    assert db.begin_collection(conn, "h", force=True) == "acquired"
    row = conn.execute("SELECT status, finished_at FROM collection_runs").fetchone()
    assert row["status"] == "running" and row["finished_at"] is None


def test_begin_collection_reclaims_stale_running(test_db):
    conn, db = test_db
    db.begin_collection(conn, "dead-host")
    # 크래시로 4시간 전 started_at 인 running 기록을 시뮬레이션
    conn.execute("UPDATE collection_runs SET started_at=?",
                 (db._hours_ago_str(4),))
    conn.commit()
    assert db.begin_collection(conn, "new-host", stale_running_hours=3) == "acquired"
    assert conn.execute("SELECT host FROM collection_runs").fetchone()["host"] == "new-host"


def test_collection_done_today_is_readonly(test_db):
    conn, db = test_db
    assert db.collection_done_today(conn) is False
    assert conn.execute("SELECT COUNT(*) n FROM collection_runs").fetchone()["n"] == 0


def test_collection_date_uses_kst_not_runner_timezone(test_db, monkeypatch):
    """21:30 UTC = 익일 06:30 KST — Actions(UTC 러너)와 국내 PC가 같은 날짜 키를 써야 한다."""
    conn, db = test_db

    class FakeDateTime:
        @staticmethod
        def now(tz=None):
            base = datetime(2026, 8, 31, 21, 30, tzinfo=timezone.utc)
            return base.astimezone(tz) if tz is not None else base

    monkeypatch.setattr(db, "datetime", FakeDateTime)
    assert db._collection_date() == "2026-09-01"

    db.begin_collection(conn, "actions-runner-utc")
    assert conn.execute("SELECT run_date FROM collection_runs").fetchone()["run_date"] \
        in ("2026-09-01", "2026-09-01T00:00:00")  # sqlite: 문자열 그대로


# --------------------------------------------------------------------------- #
# 오케스트레이터 (collect.py)                                                  #
# --------------------------------------------------------------------------- #
@pytest.fixture()
def spy_workers(monkeypatch):
    import collectors.collect as collect
    calls = {"rss": [], "api": []}
    # 실제 워커와 동일하게 {"targets", "failed"} 집계를 반환한다
    monkeypatch.setattr(collect.rss, "run",
                        lambda *a, **k: (calls["rss"].append(k),
                                         {"targets": 1, "failed": 0})[1])
    monkeypatch.setattr(collect.api, "run",
                        lambda *a, **k: (calls["api"].append(k),
                                         {"targets": 1, "failed": 0})[1])
    return collect, calls


def test_orchestrator_runs_both_once_then_noop(test_db, spy_workers):
    collect, calls = spy_workers
    assert collect.run() == 0
    assert len(calls["rss"]) == 1 and len(calls["api"]) == 1
    assert calls["rss"][0].get("force") is True  # 워커에 내부 신호 전달
    assert calls["api"][0].get("force") is True

    conn, db = test_db
    assert conn.execute("SELECT status FROM collection_runs").fetchone()["status"] == "completed"

    assert collect.run() == 0  # 두 번째 호출은 아무 것도 하지 않음
    assert len(calls["rss"]) == 1 and len(calls["api"]) == 1


def test_orchestrator_force_reruns(test_db, spy_workers):
    collect, calls = spy_workers
    collect.run()
    collect.run(force=True)
    assert len(calls["rss"]) == 2 and len(calls["api"]) == 2


def test_orchestrator_marks_failed_on_worker_error(test_db, spy_workers):
    collect, calls = spy_workers

    def boom(*a, **k):
        raise RuntimeError("피드 서버 다운")

    collect.rss.run = boom
    assert collect.run() == 1
    conn, db = test_db
    assert conn.execute("SELECT status FROM collection_runs").fetchone()["status"] == "failed"

    # 실패한 날은 다음 실행이 자동 재시도
    collect.rss.run = lambda *a, **k: calls["rss"].append(k)
    assert collect.run() == 0
    assert len(calls["rss"]) == 1


def test_orchestrator_marks_failed_when_all_sources_fail(test_db, spy_workers, monkeypatch):
    """전 소스 실패는 인프라 문제 가능성 — completed 가 아니라 failed 로 남겨 재시도한다."""
    collect, calls = spy_workers
    monkeypatch.setattr(collect.rss, "run",
                        lambda *a, **k: {"targets": 2, "failed": 2})
    monkeypatch.setattr(collect.api, "run",
                        lambda *a, **k: {"targets": 1, "failed": 1})
    assert collect.run() == 1
    conn, db = test_db
    assert conn.execute("SELECT status FROM collection_runs").fetchone()["status"] == "failed"
    # 다음 실행이 자동 재시도 가능
    assert db.begin_collection(conn, "retry-host") == "acquired"


def test_orchestrator_marks_failed_on_majority_failure(test_db, spy_workers, monkeypatch):
    """과반 실패(예: 18/25)는 인프라 문제로 보고 failed — 첫 관문 31/32 completed 사례 방지."""
    collect, calls = spy_workers
    monkeypatch.setattr(collect.rss, "run", lambda *a, **k: {"targets": 20, "failed": 18})
    monkeypatch.setattr(collect.api, "run", lambda *a, **k: {"targets": 5, "failed": 0})
    assert collect.run() == 1
    conn, db = test_db
    assert conn.execute("SELECT status FROM collection_runs").fetchone()["status"] == "failed"


def test_orchestrator_exactly_half_failure_completed(test_db, spy_workers, monkeypatch):
    """정확히 절반 실패는 completed (과반 기준 경계)."""
    collect, calls = spy_workers
    monkeypatch.setattr(collect.rss, "run", lambda *a, **k: {"targets": 4, "failed": 2})
    monkeypatch.setattr(collect.api, "run", lambda *a, **k: {"targets": 0, "failed": 0})
    assert collect.run() == 0
    conn, db = test_db
    assert conn.execute("SELECT status FROM collection_runs").fetchone()["status"] == "completed"


def test_orchestrator_partial_failure_still_completed(test_db, spy_workers, monkeypatch):
    """일부 소스 실패는 소스 개별 문제로 보고 completed (validate 로 점검)."""
    collect, calls = spy_workers
    monkeypatch.setattr(collect.rss, "run",
                        lambda *a, **k: {"targets": 3, "failed": 1})
    assert collect.run() == 0
    conn, db = test_db
    assert conn.execute("SELECT status FROM collection_runs").fetchone()["status"] == "completed"


def test_worker_run_returns_failure_stats(test_db, monkeypatch):
    """워커 run() 이 {"targets","failed"} 집계를 반환한다 (오케스트레이터 판정 근거)."""
    import collectors.rss as rss
    monkeypatch.setattr(rss, "fetch_url", lambda url, client, curl_headers=None: None)  # 전 피드 접속 실패
    monkeypatch.setattr(rss, "load_sources", lambda: [
        {"id": "s1", "type": "rss", "tier": "T3", "name": "S1", "feed_url": "http://x/1"},
        {"id": "s2", "type": "rss", "tier": "T3", "name": "S2", "feed_url": "http://x/2"},
    ])
    monkeypatch.setattr(rss.time, "sleep", lambda s: None)
    assert rss.run(force=True) == {"targets": 2, "failed": 2}

    conn, db = test_db
    db.begin_collection(conn, "h")
    db.finish_collection(conn, ok=True)
    assert rss.run() == {"targets": 0, "failed": 0}  # 오늘 완료 → 조기 종료도 집계 반환


def test_begin_collection_failed_race_loser_sees_running(test_db):
    """failed 회수 경쟁에서 진 프로세스는 acquired 가 아니라 running 을 받아야 한다."""
    conn, db = test_db
    db.begin_collection(conn, "winner")  # 실제 행은 running(방금 시작 — 회수 불가)

    class RaceConn:
        """SELECT status 만 'failed' 로 속여, 판독 직후 경쟁자가 회수한 상황을 재현."""

        def __init__(self, real):
            self._real = real

        def execute(self, sql, params=()):
            if sql.startswith("SELECT status FROM collection_runs"):
                class _C:
                    def fetchone(self):
                        return {"status": "failed"}
                return _C()
            return self._real.execute(sql, params)

        def commit(self):
            self._real.commit()

    assert db.begin_collection(RaceConn(conn), "loser") == "running"
    assert conn.execute("SELECT host FROM collection_runs").fetchone()["host"] == "winner"


# --------------------------------------------------------------------------- #
# 커넥션 래퍼 — % 리터럴 안전성                                                 #
# --------------------------------------------------------------------------- #
def test_execute_without_params_keeps_percent_literals(test_db):
    """파라미터가 없으면 SQL 을 원문 그대로 실행 — psycopg 의 % 오인 방지."""
    conn, db = test_db

    class RecCursor:
        def __init__(self, log):
            self._log = log

        def execute(self, sql, *args):
            self._log.append((sql, args))

    class RecRaw:
        def __init__(self):
            self.log = []

        def cursor(self):
            return RecCursor(self.log)

    raw = RecRaw()
    pg = db.Connection(raw, is_postgres=True)
    pg.execute("SELECT proname FROM pg_proc WHERE proname LIKE 'search_%'")
    sql, args = raw.log[0]
    assert "LIKE 'search_%'" in sql and args == ()  # 치환·파라미터 전달 없음

    pg.execute("SELECT ?", (1,))
    sql2, args2 = raw.log[1]
    assert sql2 == "SELECT %s" and args2 == ((1,),)  # 파라미터 있으면 기존과 동일

    # 실제 SQLite 커넥션에서도 % 리터럴 무파라미터 쿼리 정상 동작
    row = conn.execute("SELECT 1 AS ok WHERE 'search_documents' LIKE 'search_%'").fetchone()
    assert row["ok"] == 1


def test_worker_direct_run_blocked_after_completed(test_db, monkeypatch):
    conn, db = test_db
    db.begin_collection(conn, "orch")
    db.finish_collection(conn, ok=True)

    import collectors.rss as rss
    monkeypatch.setattr(rss, "fetch_url", lambda url, client, curl_headers=None: None)
    called = []
    monkeypatch.setattr(rss, "load_sources", lambda: called.append(1) or [])
    rss.run()  # collection_done_today → True → 즉시 반환
    assert called == []

    rss.run(force=True)  # 우회
    assert called == [1]


# --------------------------------------------------------------------------- #
# claim 추출 문서 단위 원자적 선점                                             #
# --------------------------------------------------------------------------- #
def test_claim_document_is_atomic(test_db):
    conn, db = test_db
    _add_new_doc(conn, "D1")
    assert db.claim_document_for_enrich(conn, "D1") is True
    assert db.claim_document_for_enrich(conn, "D1") is False  # 이미 선점됨


def test_claim_document_reclaims_after_window(test_db):
    conn, db = test_db
    _add_new_doc(conn, "D1")
    db.claim_document_for_enrich(conn, "D1")
    conn.execute("UPDATE documents SET enrich_locked_at=? WHERE id='D1'",
                 (db._hours_ago_str(7),))
    conn.commit()
    assert db.claim_document_for_enrich(conn, "D1", reclaim_hours=6) is True


def test_claim_document_rejects_non_new(test_db):
    conn, db = test_db
    _add_new_doc(conn, "D1")
    conn.execute("UPDATE documents SET status='enriched' WHERE id='D1'")
    conn.commit()
    assert db.claim_document_for_enrich(conn, "D1") is False


def test_release_enrich_lock(test_db):
    conn, db = test_db
    _add_new_doc(conn, "D1")
    db.claim_document_for_enrich(conn, "D1")
    db.release_enrich_lock(conn, "D1")
    assert db.claim_document_for_enrich(conn, "D1") is True


def _run_enrich(monkeypatch, model_output="[]"):
    """model_output: 문자열(고정 응답) | Exception(항상 raise) | list(호출 순서별 응답/예외)."""
    import enrich.extract_claims as ec
    monkeypatch.setattr(sys, "argv", ["extract_claims"])
    monkeypatch.setattr(ec, "check_relevance", lambda *a, **k: True)
    if isinstance(model_output, Exception):
        def call(*a, **k):
            raise model_output
    elif isinstance(model_output, list):
        seq = iter(model_output)

        def call(*a, **k):
            item = next(seq)
            if isinstance(item, Exception):
                raise item
            return item
    else:
        def call(*a, **k):
            return model_output
    monkeypatch.setattr(ec, "call_model", call)
    return ec


CLAIM_JSON = """[{"claim_text": "AI 도입이 협업 방식을 바꾼다", "stance": "optimistic",
                 "evidence_type": "case", "confidence": 0.7}]"""


def test_enrich_main_skips_locked_doc_and_cleans_lock(test_db, monkeypatch):
    conn, db = test_db
    _add_new_doc(conn, "D0")
    _add_new_doc(conn, "D1")
    assert db.claim_document_for_enrich(conn, "D0") is True  # 다른 프로세스가 선점한 상태

    ec = _run_enrich(monkeypatch, CLAIM_JSON)
    assert ec.main() == 0  # 잠금 건너뜀은 실패가 아님

    d0 = conn.execute("SELECT status, enrich_locked_at FROM documents WHERE id='D0'").fetchone()
    d1 = conn.execute("SELECT status, enrich_locked_at FROM documents WHERE id='D1'").fetchone()
    assert d0["status"] == "new" and d0["enrich_locked_at"] is not None  # 건드리지 않음
    assert d1["status"] == "enriched" and d1["enrich_locked_at"] is None  # 완료 + 잠금 정리
    assert conn.execute("SELECT COUNT(*) n FROM claims WHERE document_id='D1'").fetchone()["n"] == 1


def test_enrich_main_releases_lock_on_model_failure(test_db, monkeypatch):
    conn, db = test_db
    _add_new_doc(conn, "D1")
    ec = _run_enrich(monkeypatch, RuntimeError("API 오류"))
    assert ec.main() == 1  # 기술적 처리 실패 → non-zero
    row = conn.execute("SELECT status, enrich_locked_at FROM documents WHERE id='D1'").fetchone()
    assert row["status"] == "new" and row["enrich_locked_at"] is None  # 재시도 가능 상태로 복원


def test_enrich_main_exit_nonzero_on_api_failure(test_db, monkeypatch, capsys):
    conn, db = test_db
    _add_new_doc(conn, "DA")
    _add_new_doc(conn, "DB")
    ec = _run_enrich(monkeypatch, RuntimeError("503 Service Unavailable"))
    assert ec.main() == 1
    out = capsys.readouterr().out
    assert "DA" in out and "DB" in out and "처리 실패 2건" in out
    for did in ("DA", "DB"):
        row = conn.execute(
            "SELECT status, enrich_locked_at FROM documents WHERE id=?", (did,)).fetchone()
        assert row["status"] == "new" and row["enrich_locked_at"] is None


def test_enrich_main_parse_error_counts_as_failure(test_db, monkeypatch):
    conn, db = test_db
    _add_new_doc(conn, "D1")
    ec = _run_enrich(monkeypatch, "이건 JSON 배열이 아님")  # parse_claims → ValueError
    assert ec.main() == 1
    assert conn.execute(
        "SELECT status FROM documents WHERE id='D1'").fetchone()["status"] == "new"


def test_enrich_main_zero_claims_is_not_failure(test_db, monkeypatch):
    conn, db = test_db
    _add_new_doc(conn, "D1")
    ec = _run_enrich(monkeypatch, "[]")  # 정상 응답, claim 0건
    assert ec.main() == 0
    row = conn.execute(
        "SELECT status, enrich_locked_at FROM documents WHERE id='D1'").fetchone()
    assert row["status"] == "enriched" and row["enrich_locked_at"] is None
    assert conn.execute("SELECT COUNT(*) n FROM claims").fetchone()["n"] == 0


def test_enrich_main_partial_failure_is_nonzero(test_db, monkeypatch):
    conn, db = test_db
    _add_new_doc(conn, "D1")
    _add_new_doc(conn, "D2")
    # select_target_docs는 collected_at 순 — 첫 문서 성공, 둘째 문서 API 오류
    ec = _run_enrich(monkeypatch, [CLAIM_JSON, RuntimeError("timeout")])
    assert ec.main() == 1
    statuses = {r["id"]: r["status"] for r in conn.execute("SELECT id, status FROM documents")}
    assert "enriched" in statuses.values()  # 성공분은 반영
    assert "new" in statuses.values()       # 실패분은 재시도 가능


# --------------------------------------------------------------------------- #
# PostgreSQL 모드 (DATABASE_URL 설정 시에만)                                   #
# --------------------------------------------------------------------------- #
@pytest.mark.skipif(not os.environ.get("DATABASE_URL"),
                    reason="DATABASE_URL 미설정 — PostgreSQL 잠금 테스트 생략")
def test_locks_on_postgres(monkeypatch):
    sys.modules.pop("db", None)
    import db
    assert db.IS_POSTGRES

    monkeypatch.setattr(db, "_collection_date", lambda: "2099-12-31")
    conn = db.connect()
    db.migrate(conn)
    try:
        conn.execute("DELETE FROM collection_runs WHERE run_date = ?", ("2099-12-31",))
        conn.commit()

        assert db.begin_collection(conn, "pg-a") == "acquired"
        assert db.begin_collection(conn, "pg-b") == "running"
        db.finish_collection(conn, ok=True)
        assert db.collection_done_today(conn) is True
        assert db.begin_collection(conn, "pg-c") == "done"
        assert db.begin_collection(conn, "pg-d", force=True) == "acquired"

        did = db.new_id()
        conn.execute(
            "INSERT INTO documents (id, source_id, tier, url, body, status) "
            "VALUES (?,?,?,?,?,'new')",
            (did, "pg-lock-test", "T3", f"http://pg-lock/{did}", "body"))
        conn.commit()
        assert db.claim_document_for_enrich(conn, did) is True
        assert db.claim_document_for_enrich(conn, did) is False
        db.release_enrich_lock(conn, did)
        assert db.claim_document_for_enrich(conn, did) is True
    finally:
        conn.execute("DELETE FROM collection_runs WHERE run_date = ?", ("2099-12-31",))
        conn.execute("DELETE FROM documents WHERE source_id = ?", ("pg-lock-test",))
        conn.commit()
        conn.close()

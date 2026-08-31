"""DB 연결·마이그레이션 유틸리티 — SQLite / PostgreSQL 이중 지원.

- 환경변수 DATABASE_URL 이 있으면 PostgreSQL(psycopg3), 없으면 SQLite.
- 로컬 개발·테스트는 SQLite(PIPELINE_DB 경로), 공유 운영 DB는 Supabase PostgreSQL.
- 애플리케이션 코드는 `?` 플레이스홀더와 SQLite 방언을 그대로 쓰고,
  PostgreSQL 실행 시 이 모듈의 커넥션 래퍼가 `?` → `%s` 로 치환한다.
- 마이그레이션 SQL의 방언 분기는 `-- +postgres` / `-- +sqlite` ~ `-- +end` 마커로 표시한다
  (마커 밖 구문은 양쪽 공통).
"""
from __future__ import annotations

import hashlib
import os
import secrets
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.environ.get("PIPELINE_DB", ROOT / "data" / "pipeline.db"))
MIGRATIONS_DIR = ROOT / "migrations"


def _database_url() -> str | None:
    url = os.environ.get("DATABASE_URL")
    return url or None


IS_POSTGRES = _database_url() is not None


# --------------------------------------------------------------------------- #
# 커넥션 래퍼 — SQLite / psycopg 공통 인터페이스                                #
# --------------------------------------------------------------------------- #
class _Cursor:
    """execute() 결과 커서 래퍼 (fetchone/fetchall/iter/rowcount만 위임)."""

    def __init__(self, cur):
        self._cur = cur

    def __iter__(self):
        return iter(self._cur)

    def fetchone(self):
        return self._cur.fetchone()

    def fetchall(self):
        return self._cur.fetchall()

    @property
    def rowcount(self):
        return self._cur.rowcount


def _translate(sql: str, is_postgres: bool) -> str:
    # 코드베이스 SQL 문자열에는 `?` 리터럴이 없으므로 단순 치환으로 충분.
    return sql.replace("?", "%s") if is_postgres else sql


class Connection:
    """sqlite3.Connection / psycopg.Connection 을 감싸 동일 API를 제공.

    PostgreSQL 모드에서는 수집처럼 오래 걸리는 작업 중 유휴 연결이 끊길 수 있어
    (Supabase 풀러·NAT 타임아웃), 연결 오류 시 1회 자동 재연결 후 재시도한다.
    쓰기는 소스/페이지 단위로 커밋하고 URL 중복 제거가 있어 재시도로 안전하다.
    """

    def __init__(self, raw, is_postgres: bool, reconnect=None):
        self._raw = raw
        self.is_postgres = is_postgres
        self._reconnect = reconnect  # () -> raw connection (PostgreSQL 전용)

    def _cursor_execute(self, sql: str, params: tuple):
        cur = self._raw.cursor()
        if params:
            cur.execute(_translate(sql, self.is_postgres), params)
        else:
            # 파라미터가 없으면 params 인자 자체를 생략하고 원문 그대로 실행 —
            # psycopg가 SQL 내 % 리터럴(LIKE 'x%' 등)을 플레이스홀더로 오인하지 않도록.
            cur.execute(sql)
        return _Cursor(cur)

    def execute(self, sql: str, params=()):
        params = tuple(params)
        if not (self.is_postgres and self._reconnect):
            return self._cursor_execute(sql, params)
        import psycopg
        try:
            return self._cursor_execute(sql, params)
        except psycopg.OperationalError:
            # 일시적 네트워크 장애(유휴 종료·DNS 플랩)에 대비해 백오프를 두고 재연결
            last: Exception | None = None
            for delay in (5, 15, 30):
                print(f"    ! DB 연결 끊김 — {delay}초 후 재연결 시도")
                try:
                    self._raw.close()
                except Exception:  # noqa: BLE001 — 이미 죽은 연결 정리 실패는 무시
                    pass
                time.sleep(delay)
                try:
                    self._raw = self._reconnect()
                    return self._cursor_execute(sql, params)
                except psycopg.OperationalError as e:
                    last = e
            raise last

    def executemany(self, sql: str, seq):
        cur = self._raw.cursor()
        cur.executemany(_translate(sql, self.is_postgres), [tuple(p) for p in seq])
        return _Cursor(cur)

    def executescript(self, script: str) -> None:
        if self.is_postgres:
            # 파라미터 없는 다중 구문 → psycopg는 simple query 프로토콜로 처리 (달러 인용 포함).
            with self._raw.cursor() as cur:
                cur.execute(script)
        else:
            self._raw.executescript(script)

    def commit(self) -> None:
        self._raw.commit()

    def rollback(self) -> None:
        self._raw.rollback()

    def close(self) -> None:
        self._raw.close()

    def cursor(self):
        return self._raw.cursor()


def connect() -> Connection:
    url = _database_url()
    if url:
        import psycopg
        from psycopg.rows import dict_row

        def _open():
            # prepare_threshold=None: Supabase 트랜잭션 풀러(pgbouncer) 호환.
            # keepalives: 느린 수집 중 NAT/풀러의 유휴 연결 종료 완화.
            return psycopg.connect(
                url, row_factory=dict_row, prepare_threshold=None,
                keepalives=1, keepalives_idle=30, keepalives_interval=10,
                keepalives_count=3)

        return Connection(_open(), is_postgres=True, reconnect=_open)

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    raw = sqlite3.connect(DB_PATH)
    raw.row_factory = sqlite3.Row
    raw.execute("PRAGMA foreign_keys = ON")
    return Connection(raw, is_postgres=False)


# --------------------------------------------------------------------------- #
# 마이그레이션                                                                 #
# --------------------------------------------------------------------------- #
def _strip_dialect(sql: str, dialect: str) -> str:
    """`-- +postgres` / `-- +sqlite` ~ `-- +end` 블록 중 현재 방언만 남긴다."""
    keep, skipping = [], False
    for line in sql.splitlines():
        marker = line.strip().lower()
        if marker in ("-- +postgres", "-- +sqlite"):
            skipping = marker != f"-- +{dialect}"
            continue
        if marker == "-- +end":
            skipping = False
            continue
        if not skipping:
            keep.append(line)
    return "\n".join(keep)


def migrate(conn: Connection) -> list[str]:
    """migrations/ 의 SQL을 파일명 순으로 적용. 새로 적용된 파일명 목록 반환."""
    dialect = "postgres" if conn.is_postgres else "sqlite"
    conn.executescript(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        "filename TEXT PRIMARY KEY, applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
    )
    done = {r["filename"] for r in conn.execute("SELECT filename FROM schema_migrations")}
    applied: list[str] = []
    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        if path.name in done:
            continue
        sql = _strip_dialect(path.read_text(encoding="utf-8"), dialect)
        conn.executescript(sql)
        conn.execute(
            "INSERT INTO schema_migrations(filename) VALUES (?) ON CONFLICT DO NOTHING",
            (path.name,),
        )
        applied.append(path.name)
    conn.commit()
    return applied


# --------------------------------------------------------------------------- #
# 전문 검색 — FTS5 대체 (PostgreSQL: pg_trgm 검색 함수 / SQLite: LIKE 폴백)      #
# --------------------------------------------------------------------------- #
_SEARCH = {
    "documents": ("search_documents", "documents", ("title", "body")),
    "claims": ("search_claims", "claims", ("claim_text",)),
    "internal": ("search_internal", "internal_docs", ("title", "body")),
}


def search(conn: Connection, target: str, query: str) -> list:
    """target ∈ {documents, claims, internal} 에서 query 를 포함하는 행 목록 반환."""
    fn, table, cols = _SEARCH[target]
    if conn.is_postgres:
        return conn.execute(f"SELECT * FROM {fn}(?)", (query,)).fetchall()
    like = f"%{query}%"
    where = " OR ".join(f"{c} LIKE ?" for c in cols)
    return conn.execute(
        f"SELECT * FROM {table} WHERE {where}", tuple([like] * len(cols))
    ).fetchall()


# --------------------------------------------------------------------------- #
# 실행 잠금 — 하루 1회 수집 보장 / claim 추출 문서 단위 동시성 제어              #
# (SQLite·PostgreSQL 공통: 잠금 타임스탬프는 파이썬 UTC 문자열로 통일해          #
#  두 백엔드의 CURRENT_TIMESTAMP 표현/시간대 차이에 의존하지 않는다)             #
# --------------------------------------------------------------------------- #
# 수집 "달력일" 기준 타임존 — GitHub Actions(UTC 러너)와 국내 PC(KST)가
# 항상 동일한 날짜 키(collection_runs.run_date)를 쓰도록 KST(UTC+9)로 고정한다.
# begin_collection / finish_collection / collection_done_today 이 모두 이 값을 쓴다.
_KST = timezone(timedelta(hours=9))


def _collection_date() -> str:
    return datetime.now(_KST).date().isoformat()


def _utcnow_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _hours_ago_str(hours: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")


def begin_collection(conn: Connection, host: str, *, force: bool = False,
                     stale_running_hours: int = 3) -> str:
    """오늘자 수집 실행권을 원자적으로 선점한다 (collection_runs.run_date PK).

    반환:
      'acquired' — 이 프로세스가 오늘 수집을 진행한다 (row status='running')
      'done'     — 오늘 이미 completed (재실행 불필요)
      'running'  — 다른 프로세스가 방금 시작해 진행 중 (중복 실행 방지)

    규칙:
      - completed  → 'done'
      - failed     → 자동 재시도 허용 (running 으로 되돌리고 'acquired')
      - running    → stale_running_hours 초과한 기록만 회수해 'acquired', 아니면 'running'
      - force=True → 상태와 무관하게 running 으로 갱신하고 'acquired'
    수집 종료 시 finish_collection() 으로 completed/failed 를 확정해야 한다.
    """
    today = _collection_date()
    now = _utcnow_str()
    if force:
        conn.execute(
            "INSERT INTO collection_runs (run_date, host, status, started_at, finished_at) "
            "VALUES (?,?, 'running', ?, NULL) "
            "ON CONFLICT (run_date) DO UPDATE SET host=excluded.host, status='running', "
            "started_at=excluded.started_at, finished_at=NULL",
            (today, host, now))
        conn.commit()
        return "acquired"

    cur = conn.execute(
        "INSERT INTO collection_runs (run_date, host, status, started_at) "
        "VALUES (?,?, 'running', ?) ON CONFLICT (run_date) DO NOTHING",
        (today, host, now))
    conn.commit()
    if cur.rowcount == 1:
        return "acquired"

    row = conn.execute(
        "SELECT status FROM collection_runs WHERE run_date=?", (today,)).fetchone()
    status = row["status"] if row else None
    if status == "completed":
        return "done"
    if status == "failed":
        cur = conn.execute(
            "UPDATE collection_runs SET status='running', host=?, started_at=?, finished_at=NULL "
            "WHERE run_date=? AND status='failed'",
            (host, now, today))
        conn.commit()
        # rowcount 0 = 다른 프로세스가 그 사이에 failed 를 먼저 회수함 — 중복 실행 금지
        return "acquired" if cur.rowcount == 1 else "running"

    # status == 'running' — 크래시로 남은 오래된 기록만 회수
    cur = conn.execute(
        "UPDATE collection_runs SET host=?, started_at=?, finished_at=NULL "
        "WHERE run_date=? AND status='running' AND started_at < ?",
        (host, now, today, _hours_ago_str(stale_running_hours)))
    conn.commit()
    return "acquired" if cur.rowcount == 1 else "running"


def finish_collection(conn: Connection, *, ok: bool) -> None:
    """오늘자 수집 결과를 확정. ok=False 면 failed 로 남겨 다음 실행이 재시도한다."""
    conn.execute(
        "UPDATE collection_runs SET status=?, finished_at=? WHERE run_date=?",
        ("completed" if ok else "failed", _utcnow_str(), _collection_date()))
    conn.commit()


def collection_done_today(conn: Connection) -> bool:
    """오늘 수집이 completed 인지 (읽기 전용 — 잠금을 취득하지 않는다).

    워커(rss/api)를 직접 실행할 때 이 값만 확인한다. collection_runs 행의
    생성·상태 전이는 오케스트레이터(collect.py) 또는 --force 만 담당한다.
    """
    row = conn.execute(
        "SELECT 1 FROM collection_runs WHERE run_date=? AND status='completed'",
        (_collection_date(),)).fetchone()
    return row is not None


def claim_document_for_enrich(conn: Connection, doc_id: str, *,
                              reclaim_hours: int = 6) -> bool:
    """문서를 claim 추출 대상으로 원자적으로 선점한다.

    status='new' 이고 (미선점 또는 reclaim_hours 초과한 선점)일 때만 성공.
    반환 True: 이 프로세스가 소유 / False: 다른 프로세스가 처리 중이거나 상태가 바뀜.
    """
    cur = conn.execute(
        "UPDATE documents SET enrich_locked_at=? "
        "WHERE id=? AND status='new' "
        "AND (enrich_locked_at IS NULL OR enrich_locked_at < ?)",
        (_utcnow_str(), doc_id, _hours_ago_str(reclaim_hours)))
    conn.commit()
    return cur.rowcount == 1


def release_enrich_lock(conn: Connection, doc_id: str) -> None:
    """처리 실패 시 문서 잠금을 즉시 해제 (다음 실행이 바로 재시도할 수 있도록)."""
    conn.execute("UPDATE documents SET enrich_locked_at=NULL WHERE id=?", (doc_id,))
    conn.commit()


# --------------------------------------------------------------------------- #
# 공통 유틸                                                                    #
# --------------------------------------------------------------------------- #
def new_id() -> str:
    """시간순 정렬 가능한 26자 ID (ulid 유사)."""
    ts = format(int(time.time() * 1000), "011x")
    return (ts + secrets.token_hex(8)).upper()


def content_hash(text: str) -> str:
    """중복 판정용 해시 — 공백·대소문자 정규화 후 sha256."""
    normalized = " ".join(text.lower().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

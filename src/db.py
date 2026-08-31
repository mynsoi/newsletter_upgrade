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
    """sqlite3.Connection / psycopg.Connection 을 감싸 동일 API를 제공."""

    def __init__(self, raw, is_postgres: bool):
        self._raw = raw
        self.is_postgres = is_postgres

    def execute(self, sql: str, params=()):
        cur = self._raw.cursor()
        cur.execute(_translate(sql, self.is_postgres), tuple(params))
        return _Cursor(cur)

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

        # Supabase 트랜잭션 풀러(pgbouncer) 호환 위해 prepared statement 비활성화.
        raw = psycopg.connect(url, row_factory=dict_row, prepare_threshold=None)
        return Connection(raw, is_postgres=True)

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

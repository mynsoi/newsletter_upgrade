"""SQLite 연결·마이그레이션 유틸리티."""
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


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def migrate(conn: sqlite3.Connection) -> list[str]:
    """migrations/ 의 SQL을 파일명 순으로 적용. 적용된 파일명 목록 반환."""
    conn.executescript(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        "filename TEXT PRIMARY KEY, applied_at DATETIME DEFAULT CURRENT_TIMESTAMP)"
    )
    done = {r["filename"] for r in conn.execute("SELECT filename FROM schema_migrations")}
    applied = []
    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        if path.name in done:
            continue
        conn.executescript(path.read_text(encoding="utf-8"))
        conn.execute("INSERT OR IGNORE INTO schema_migrations(filename) VALUES (?)", (path.name,))
        applied.append(path.name)
    conn.commit()
    return applied


def new_id() -> str:
    """시간순 정렬 가능한 26자 ID (ulid 유사)."""
    ts = format(int(time.time() * 1000), "011x")
    return (ts + secrets.token_hex(8)).upper()


def content_hash(text: str) -> str:
    """중복 판정용 해시 — 공백·대소문자 정규화 후 sha256."""
    normalized = " ".join(text.lower().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

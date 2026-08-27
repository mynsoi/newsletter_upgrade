"""수집기 공용 저장 로직.

rss/api 수집기가 문서를 저장할 때 반드시 이 모듈을 거친다.
중복 제거·summary_only 규칙이 수집 경로와 무관하게 동일 적용되도록 하기 위함이다.

동일 적용 규칙:
- 중복 제거: URL 일치 또는 content_hash(공백·대소문자 정규화) 일치 시 저장하지 않음
- summary_only(A3): 본문 800자 미만이면 summary_only=1 — claim 추출(enrich)에서 제외
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db import ROOT, content_hash, new_id  # noqa: E402

RAW_DIR = ROOT / "data" / "raw"
SUMMARY_ONLY_THRESHOLD = 800  # A3: 이 길이 미만은 요약뿐인 문서로 간주


def store_document(conn, source: dict, *, url: str, title: str, text: str,
                   author: str | None = None, published: str | None = None,
                   raw_dir: Path | None = None) -> str:
    """문서 1건 저장. 반환: 'new' | 'dup' | 'empty'."""
    if conn.execute("SELECT 1 FROM documents WHERE url = ?", (url,)).fetchone():
        return "dup"
    if not text or not text.strip():
        return "empty"
    c_hash = content_hash(text)
    if conn.execute("SELECT 1 FROM documents WHERE content_hash = ?", (c_hash,)).fetchone():
        return "dup"

    doc_id = new_id()
    raw_path = (raw_dir or RAW_DIR) / source["id"] / f"{doc_id}.txt"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(text, encoding="utf-8")
    try:
        raw_ref = str(raw_path.relative_to(ROOT))
    except ValueError:
        raw_ref = str(raw_path)

    summary_only = 1 if len(text.strip()) < SUMMARY_ONLY_THRESHOLD else 0
    title = title or "(무제)"
    conn.execute(
        """INSERT INTO documents
           (id, source_id, tier, url, title, author, published_at,
            lang, raw_path, content_hash, status, summary_only)
           VALUES (?,?,?,?,?,?,?,?,?,?, 'new', ?)""",
        (doc_id, source["id"], source["tier"], url, title, author, published,
         source.get("lang"), raw_ref, c_hash, summary_only),
    )
    conn.execute(
        "INSERT INTO documents_fts (id, title, body) VALUES (?,?,?)",
        (doc_id, title, text[:20000]),
    )
    conn.execute(
        "INSERT OR IGNORE INTO tags (document_id, axis, value) VALUES (?, 'tier', ?)",
        (doc_id, source["tier"]),
    )
    return "new"

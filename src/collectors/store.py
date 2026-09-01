"""수집기 공용 저장 로직.

rss/api 수집기가 문서를 저장할 때 반드시 이 모듈을 거친다.
중복 제거·summary_only 규칙이 수집 경로와 무관하게 동일 적용되도록 하기 위함이다.

동일 적용 규칙:
- 중복 제거: URL 일치 또는 content_hash(공백·대소문자 정규화) 일치 시 저장하지 않음
- 격상: 같은 URL의 기존 문서가 summary_only=1(요약뿐)이고 새 본문이 기존보다 길면서
  800자 임계를 통과하면, 기존 문서의 body를 새 본문으로 교체하고 summary_only=0,
  status='new'(추출 대기)로 되돌린다. fetched_by에 확보 경로를 기록.
  브라우저 보조 수집(/ingest-file)으로 전문을 확보한 경우가 주 대상이다.
- summary_only(A3): 본문 800자 미만이면 summary_only=1 — claim 추출(enrich)에서 제외.
  단 type=api 소스(arXiv·OSF 초록형)는 면제 — 초록이 문서의 완결된 본문이므로
  길이와 무관하게 추출 대상이다 (2026-08-31 관문 사전 점검 ④ 결정)
- 원문은 documents.body 컬럼에 직접 저장 (raw_path 파일 참조 폐지 — DB 이중지원 전환)
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db import content_hash, new_id  # noqa: E402

SUMMARY_ONLY_THRESHOLD = 800  # A3: 이 길이 미만은 요약뿐인 문서로 간주


def store_document(conn, source: dict, *, url: str, title: str, text: str,
                   author: str | None = None, published: str | None = None,
                   fetched_by: str | None = None,
                   raw_dir: Path | None = None) -> str:
    """문서 1건 저장. 반환: 'new' | 'dup' | 'upgraded' | 'empty'.

    raw_dir 인자는 하위호환을 위해 남겨두었으나 더 이상 사용하지 않는다(원문은 body 컬럼).
    """
    text_len = len(text.strip()) if text else 0
    existing = conn.execute(
        "SELECT id, summary_only, LENGTH(body) AS body_len FROM documents WHERE url = ?",
        (url,)).fetchone()
    if existing:
        # 격상: 요약뿐이던 문서에 임계(800자)를 넘는 더 긴 전문이 들어오면 본문 교체.
        # 새 본문이 더 길어도 임계 미달이면 여전히 요약 수준이므로 격상하지 않는다
        # (summary_only=0으로 만들 수 없어 A3 규칙과 충돌).
        if (existing["summary_only"] == 1
                and text_len >= SUMMARY_ONLY_THRESHOLD
                and text_len > (existing["body_len"] or 0)):
            conn.execute(
                """UPDATE documents SET body = ?, content_hash = ?, summary_only = 0,
                       status = 'new', fetched_by = ? WHERE id = ?""",
                (text, content_hash(text), fetched_by, existing["id"]))
            return "upgraded"
        return "dup"
    if not text or not text.strip():
        return "empty"
    c_hash = content_hash(text)
    if conn.execute("SELECT 1 FROM documents WHERE content_hash = ?", (c_hash,)).fetchone():
        return "dup"

    doc_id = new_id()
    # A3 임계 — api 소스(초록형)는 면제: 초록은 요약이 아니라 완결된 본문이다
    if source.get("type") == "api":
        summary_only = 0
    else:
        summary_only = 1 if len(text.strip()) < SUMMARY_ONLY_THRESHOLD else 0
    title = title or "(무제)"
    conn.execute(
        """INSERT INTO documents
           (id, source_id, tier, url, title, author, published_at,
            lang, body, content_hash, status, summary_only, fetched_by)
           VALUES (?,?,?,?,?,?,?,?,?,?, 'new', ?, ?)""",
        (doc_id, source["id"], source["tier"], url, title, author, published,
         source.get("lang"), text, c_hash, summary_only, fetched_by),
    )
    conn.execute(
        "INSERT INTO tags (document_id, axis, value) VALUES (?, 'tier', ?) "
        "ON CONFLICT DO NOTHING",
        (doc_id, source["tier"]),
    )
    return "new"

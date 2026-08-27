"""수기 URL 등록 — 담당자가 발견한 좋은 자료를 한 줄로 파이프라인에 태우는 경로.

사용: python src/collectors/ingest_url.py <URL> [--tier T3]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import httpx
import trafilatura

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db import ROOT, connect, content_hash, migrate, new_id  # noqa: E402

USER_AGENT = "SK-CultureInsights-Pipeline/0.1 (manual ingest)"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("url")
    p.add_argument("--tier", default="T5", choices=["T1", "T2", "T3", "T4", "T5"])
    p.add_argument("--title", default=None)
    args = p.parse_args()

    from handoff import ensure_active
    ensure_active("수기 등록")
    conn = connect()
    migrate(conn)

    if conn.execute("SELECT id FROM documents WHERE url=?", (args.url,)).fetchone():
        print("이미 등록된 URL입니다.")
        return 0

    with httpx.Client(headers={"User-Agent": USER_AGENT}) as client:
        r = client.get(args.url, follow_redirects=True, timeout=20)
        r.raise_for_status()
        html = r.text

    body = trafilatura.extract(html, include_comments=False)
    if not body:
        print("본문 추출 실패 — 페이월/JS 렌더링 페이지일 수 있습니다.")
        print("정식 구독 콘텐츠라면 본문을 파일로 저장 후 --file 등록 기능(Phase 1)을 사용하세요.")
        return 1

    meta = trafilatura.extract_metadata(html)
    title = args.title or (meta.title if meta else None) or "(무제)"

    c_hash = content_hash(body)
    dup = conn.execute("SELECT id FROM documents WHERE content_hash=?", (c_hash,)).fetchone()
    if dup:
        print(f"동일 본문이 이미 존재합니다 (doc {dup['id']}).")
        return 0

    doc_id = new_id()
    raw_path = ROOT / "data" / "raw" / "manual" / f"{doc_id}.txt"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(body, encoding="utf-8")

    conn.execute(
        """INSERT INTO documents (id, source_id, tier, url, title, author,
           published_at, lang, raw_path, content_hash, status)
           VALUES (?,?,?,?,?,?,?,?,?,?, 'new')""",
        (doc_id, "manual", args.tier, args.url, title,
         (meta.author if meta else None), (meta.date if meta else None),
         None, str(raw_path.relative_to(ROOT)), c_hash),
    )
    conn.execute("INSERT INTO documents_fts (id, title, body) VALUES (?,?,?)",
                 (doc_id, title, body[:20000]))
    conn.execute("INSERT OR IGNORE INTO tags (document_id, axis, value) VALUES (?, 'tier', ?)",
                 (doc_id, args.tier))
    conn.commit()
    print(f"등록 완료: [{args.tier}] {title}\n  id={doc_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""수기 URL 등록 — 담당자가 발견한 좋은 자료를 한 줄로 파이프라인에 태우는 경로.

사용: python src/collectors/ingest_url.py <URL> [--source <소스ID>] [--tier T3] [--detect]

소스 결정 (collectors.source_match):
- --source <ID>   : sources.yaml 그 소스의 id·tier로 저장. --tier가 소스 tier와 다르면 오류.
- --source manual : 판별 없이 수기(manual)로 저장 (tier는 --tier, 기본 T5).
- 미지정          : URL 도메인·경로로 sources.yaml 소스를 자동 판별. 하나로 정해지면 그 소스,
                    아니면 manual. 판별 결과는 실행 시 출력한다.
- --detect        : 판별 결과만 출력하고 끝낸다 (등록·네트워크 접속 없음).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import httpx
import trafilatura

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db import connect, content_hash, migrate, new_id  # noqa: E402
from collectors.source_match import SourceResolveError, resolve_source  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

USER_AGENT = "SK-CultureInsights-Pipeline/0.1 (manual ingest)"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("url")
    p.add_argument("--source", default=None,
                   help="sources.yaml 소스 id (manual = 판별 없이 수기 등록)")
    p.add_argument("--tier", default=None, choices=["T1", "T2", "T3", "T4", "T5"],
                   help="manual일 때 등급 (기본 T5). 소스가 정해지면 그 tier와 같아야 함")
    p.add_argument("--title", default=None)
    p.add_argument("--detect", action="store_true", help="소스 판별 결과만 출력")
    args = p.parse_args(argv)

    try:
        source, note = resolve_source(args.url, args.source, args.tier)
    except SourceResolveError as e:
        print(f"오류: {e}")
        return 2
    print(f"소스 {note}")
    if args.detect:
        return 0
    tier = source["tier"]

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
    conn.execute(
        """INSERT INTO documents (id, source_id, tier, url, title, author,
           published_at, lang, body, content_hash, status)
           VALUES (?,?,?,?,?,?,?,?,?,?, 'new')""",
        (doc_id, source["id"], tier, args.url, title,
         (meta.author if meta else None), (meta.date if meta else None),
         source.get("lang"), body, c_hash),
    )
    conn.execute("INSERT INTO tags (document_id, axis, value) VALUES (?, 'tier', ?) "
                 "ON CONFLICT DO NOTHING",
                 (doc_id, tier))
    conn.commit()
    print(f"등록 완료: [{source['id']} · {tier}] {title}\n  id={doc_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

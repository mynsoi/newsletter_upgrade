"""파일 등재 — 브라우저 보조 수집(browse)·구독 전문 파일을 documents에 등록 (A5, /ingest-file).

파일 형식: YAML frontmatter + 본문
  ---
  source_id: knowledge-wharton   # sources.yaml에 등재된 id
  url: https://...
  title: "..."
  published: 2026-08-24          # 선택
  fetched_at: ...                # 선택 (기록용)
  fetched_by: browse             # 선택 (기록용)
  ---
  (본문 — 원문 그대로. 이 스크립트는 본문을 어떤 식으로도 변형하지 않는다: 절대 규칙 8)

저장은 collectors.store 경유 — URL·내용 해시 중복 제거와 summary_only 규칙을
자동 수집 경로와 동일하게 적용한다. 등재(신규/중복) 처리된 파일은 같은 위치의
ingested/ 하위 폴더로 이동해 이중 등재를 방지한다.

사용: python src/collectors/ingest_file.py <파일.md> [<파일2.md> ...]
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db import ROOT, connect, migrate  # noqa: E402
from collectors.store import store_document  # noqa: E402
from internal_sync import parse_frontmatter  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SOURCES_PATH = ROOT / "config" / "sources.yaml"
REQUIRED = ("source_id", "url", "title")


def load_source(source_id: str) -> dict | None:
    data = yaml.safe_load(SOURCES_PATH.read_text(encoding="utf-8"))
    for s in data.get("sources", []):
        if s["id"] == source_id:
            return s
    return None


def ingest(path: Path, conn) -> str:
    """파일 1건 등재. 반환: 'new' | 'dup' | 'upgraded' | 'error'."""
    meta, body = parse_frontmatter(path.read_text(encoding="utf-8"))
    missing = [k for k in REQUIRED if not meta.get(k)]
    if missing:
        print(f"  오류  {path.name} — frontmatter 필수 필드 누락: {', '.join(missing)}")
        return "error"
    source = load_source(str(meta["source_id"]))
    if source is None:
        print(f"  오류  {path.name} — sources.yaml에 없는 source_id: {meta['source_id']}")
        return "error"
    if source.get("status") == "excluded":
        print(f"  오류  {path.name} — 제외(excluded)된 소스: {meta['source_id']}")
        return "error"

    result = store_document(
        conn, source, url=str(meta["url"]), title=str(meta["title"]), text=body,
        published=str(meta.get("published") or "") or None,
        fetched_by=str(meta.get("fetched_by") or "browse"))
    if result == "new":
        print(f"  등재  {path.name} → documents ({len(body):,}자)")
    elif result == "upgraded":
        print(f"  격상  {path.name} — 요약뿐이던 기존 문서의 본문을 전문으로 교체 "
              f"({len(body):,}자, 추출 대기로 복귀)")
    elif result == "dup":
        print(f"  중복  {path.name} — 같은 URL/내용이 이미 등재됨 (파이프라인 중복 제거)")
    else:
        print(f"  오류  {path.name} — 본문이 비어 있음")
        return "error"
    conn.commit()

    done_dir = path.parent / "ingested"
    done_dir.mkdir(exist_ok=True)
    shutil.move(str(path), done_dir / path.name)
    return result


def main(argv: list[str]) -> int:
    if not argv:
        print("사용: python src/collectors/ingest_file.py <파일.md> [...]")
        return 2
    conn = connect()
    migrate(conn)
    counts = {"new": 0, "dup": 0, "upgraded": 0, "error": 0}
    for arg in argv:
        p = Path(arg)
        if not p.exists():
            print(f"  오류  파일 없음: {arg}")
            counts["error"] += 1
            continue
        counts[ingest(p, conn)] += 1
    conn.close()
    print(f"\n완료: 신규 {counts['new']} / 중복 {counts['dup']} / "
          f"격상 {counts['upgraded']} / 오류 {counts['error']}")
    return 0 if counts["error"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

"""internal/ 디렉토리 색인 — SKMS·경영층 메시지 등 내부 자료.

정책 (2026-09-03 단순화 — CLAUDE.md 절대 규칙 4, 기획서 v1.5):
  - internal/에는 공개 가능 판단이 끝난 자료만 등록한다. 등급 체계는 미운용.
  - 이 폴더의 텍스트는 아티클 생성 시 외부 API로 전송된다.
  - 안전 가드: 프론트매터에 'A' 외의 security 표기(B·C 등 구 등급)가 남아 있으면
    실수 방지를 위해 등록을 보류하고 경고한다 — 공개 가능 여부를 재확인하고
    표기를 제거(또는 A로 정정)한 뒤 다시 sync 한다.
  - _TEMPLATE 파일과 밑줄로 시작하는 파일, internal/ 루트 파일(목록 등)은 건너뜀
  - supersedes 관계를 반영해 대체된 문서를 표시

DB의 security·api_eligible 컬럼은 스키마 호환을 위해 유지하며 'A'·1로 고정 기록한다.

사용: make sync
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from db import ROOT, connect, content_hash, migrate  # noqa: E402

INTERNAL_DIR = ROOT / "internal"


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """--- 로 감싼 YAML frontmatter와 본문을 분리."""
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    try:
        meta = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        return {}, text
    return meta, parts[2].strip()


def legacy_grade_mark(path: Path) -> str | None:
    """본문을 읽기 전에 구 등급 표기(A 외의 security 값)만 확인하는 안전 가드."""
    with path.open(encoding="utf-8") as f:
        head = f.read(2000)
    meta, _ = parse_frontmatter(head)
    sec = str(meta.get("security", "")).upper() or None
    return sec if sec not in (None, "A") else None


def sync() -> int:
    from handoff import ensure_active
    ensure_active("내부 자료 색인")
    conn = connect()
    migrate(conn)

    # 색인 대상: 하위 폴더(skms/ 등)의 .md만. 루트 파일(등록목록 등)과 _TEMPLATE은 제외.
    files = sorted(p for p in INTERNAL_DIR.rglob("*.md")
                   if not p.name.startswith("_") and p.parent != INTERNAL_DIR)
    stats = {"indexed": 0, "skipped": 0, "held": 0}

    for path in files:
        rel = path.relative_to(INTERNAL_DIR).as_posix()

        mark = legacy_grade_mark(path)
        if mark is not None:
            print(f"  보류  {rel} — 구 등급 표기(security: {mark}) 발견. 등급 체계는 미운용 — "
                  "공개 가능 여부 재확인 후 표기를 제거하고 다시 sync 하세요.")
            stats["held"] += 1
            continue

        text = path.read_text(encoding="utf-8")
        meta, body = parse_frontmatter(text)
        c_hash = content_hash(body)

        row = conn.execute("SELECT content_hash FROM internal_docs WHERE id=?", (rel,)).fetchone()
        if row and row["content_hash"] == c_hash:
            stats["skipped"] += 1
            continue

        conn.execute(
            """INSERT INTO internal_docs
               (id, path, title, type, speaker, security, effective_date,
                body, content_hash, api_eligible, indexed_at)
               VALUES (?,?,?,?,?, 'A', ?,?,?, 1, CURRENT_TIMESTAMP)
               ON CONFLICT(id) DO UPDATE SET
                 title=excluded.title, type=excluded.type, speaker=excluded.speaker,
                 security='A', effective_date=excluded.effective_date,
                 body=excluded.body, content_hash=excluded.content_hash,
                 api_eligible=1, indexed_at=CURRENT_TIMESTAMP""",
            (rel, str(path), meta.get("title"), meta.get("type"), meta.get("speaker"),
             str(meta.get("date", "")) or None, body, c_hash),
        )

        sup = meta.get("supersedes")
        if sup:
            # 대체 대상 문서의 디렉토리를 기준으로 상대경로 해석
            sup_rel = (path.parent / sup).resolve().relative_to(INTERNAL_DIR.resolve()).as_posix() \
                if (path.parent / sup).exists() else sup
            conn.execute("UPDATE internal_docs SET superseded_by=? WHERE id=?", (rel, sup_rel))

        print(f"  색인  {rel}")
        stats["indexed"] += 1

    conn.commit()
    print(f"\n완료: 색인 {stats['indexed']} / 변경없음 {stats['skipped']} / "
          f"등급 표기 보류 {stats['held']}")
    conn.close()
    return 0 if stats["held"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(sync())

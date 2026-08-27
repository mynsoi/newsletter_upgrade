"""internal/ 디렉토리 색인 — SKMS·경영층 메시지 등 내부 자료.

보안 규칙 (기획서 4.1, CLAUDE.md 절대 규칙 4):
  - security: C → 색인 자체를 거부하고 경고 (파일 내용을 읽는 즉시 중단)
  - security: B → 색인은 하되, api_eligible=0.
                  config/settings.yaml의 b_grade_api_approved: true 일 때만 api_eligible=1
  - security: A → api_eligible=1
  - _TEMPLATE 파일과 밑줄로 시작하는 파일은 건너뜀
  - supersedes 관계를 반영해 대체된 문서를 표시

사용: make sync
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from db import ROOT, connect, content_hash, migrate  # noqa: E402

INTERNAL_DIR = ROOT / "internal"
SETTINGS_PATH = ROOT / "config" / "settings.yaml"


def load_settings() -> dict:
    if SETTINGS_PATH.exists():
        return yaml.safe_load(SETTINGS_PATH.read_text(encoding="utf-8")) or {}
    return {}


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


def peek_security(path: Path) -> str | None:
    """본문을 읽기 전에 security 필드만 확인 (C등급 노출 최소화)."""
    with path.open(encoding="utf-8") as f:
        head = f.read(2000)
    meta, _ = parse_frontmatter(head)
    return str(meta.get("security", "")).upper() or None


def sync() -> int:
    from handoff import ensure_active
    ensure_active("내부 자료 색인")
    conn = connect()
    migrate(conn)
    settings = load_settings()
    b_approved = bool(settings.get("b_grade_api_approved", False))
    print(f"B등급 API 전송 승인 상태: {'승인됨' if b_approved else '미승인 (이행기 — 색인만 수행)'}")

    # 색인 대상: 하위 폴더(skms/ 등)의 .md만. 루트 파일(후보목록 등)과 _TEMPLATE은 제외.
    files = sorted(p for p in INTERNAL_DIR.rglob("*.md")
                   if not p.name.startswith("_") and p.parent != INTERNAL_DIR)
    stats = {"indexed": 0, "skipped": 0, "rejected_c": 0, "invalid": 0}

    for path in files:
        rel = path.relative_to(INTERNAL_DIR).as_posix()

        sec = peek_security(path)
        if sec == "C":
            print(f"  거부  {rel} — security: C 문서는 파이프라인 투입 금지 (기획서 4.1)")
            stats["rejected_c"] += 1
            continue
        if sec not in ("A", "B"):
            print(f"  오류  {rel} — security 필드가 A/B가 아님 (값: {sec}). 프론트매터를 확인하세요.")
            stats["invalid"] += 1
            continue

        text = path.read_text(encoding="utf-8")
        meta, body = parse_frontmatter(text)
        c_hash = content_hash(body)

        row = conn.execute("SELECT content_hash FROM internal_docs WHERE id=?", (rel,)).fetchone()
        if row and row["content_hash"] == c_hash:
            stats["skipped"] += 1
            continue

        api_eligible = 1 if (sec == "A" or (sec == "B" and b_approved)) else 0
        conn.execute(
            """INSERT INTO internal_docs
               (id, path, title, type, speaker, security, effective_date,
                content_hash, api_eligible, indexed_at)
               VALUES (?,?,?,?,?,?,?,?,?, CURRENT_TIMESTAMP)
               ON CONFLICT(id) DO UPDATE SET
                 title=excluded.title, type=excluded.type, speaker=excluded.speaker,
                 security=excluded.security, effective_date=excluded.effective_date,
                 content_hash=excluded.content_hash, api_eligible=excluded.api_eligible,
                 indexed_at=CURRENT_TIMESTAMP""",
            (rel, str(path), meta.get("title"), meta.get("type"), meta.get("speaker"),
             sec, str(meta.get("date", "")) or None, c_hash, api_eligible),
        )
        conn.execute("DELETE FROM internal_fts WHERE id=?", (rel,))
        conn.execute("INSERT INTO internal_fts (id, title, body) VALUES (?,?,?)",
                     (rel, meta.get("title", ""), body[:20000]))

        sup = meta.get("supersedes")
        if sup:
            # 대체 대상 문서의 디렉토리를 기준으로 상대경로 해석
            sup_rel = (path.parent / sup).resolve().relative_to(INTERNAL_DIR.resolve()).as_posix() \
                if (path.parent / sup).exists() else sup
            conn.execute("UPDATE internal_docs SET superseded_by=? WHERE id=?", (rel, sup_rel))

        grade_note = "" if api_eligible else "  [API 전송 제외 — B등급 이행기]"
        print(f"  색인  {rel} (security={sec}){grade_note}")
        stats["indexed"] += 1

    conn.commit()
    print(f"\n완료: 색인 {stats['indexed']} / 변경없음 {stats['skipped']} / "
          f"C거부 {stats['rejected_c']} / 형식오류 {stats['invalid']}")
    conn.close()
    return 0 if stats["invalid"] == 0 and stats["rejected_c"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(sync())

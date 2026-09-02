"""이론 카드 로더 — knowledge/theories/의 reviewed 카드를 claim 단위로 색인.

기획서 3.5:
  - status: reviewed 카드만 색인 (draft = LLM 초안 미검수 → 거부)
  - "## 핵심 명제"의 각 불릿 = claim 1건 (evidence_type='theory')
  - "## 경계 조건"의 각 불릿 = claim 1건 (stance='conditional')
  - documents에 tier=T1, source_id='theory-canon'으로 등록
  - 카드 수정 시 재실행하면 기존 claim을 교체 (해시 비교)

사용: make theories  (또는 python src/load_theories.py)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from db import ROOT, connect, content_hash, migrate, new_id  # noqa: E402

# Windows 콘솔(cp949)에서 한글·특수문자(—) 출력이 깨지거나 UnicodeEncodeError로
# 죽지 않도록 (rss.py·api.py·extract_claims.py 와 동일). Actions(UTF-8)에서는 영향 없음.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

THEORY_DIR = ROOT / "knowledge" / "theories"
SOURCE_ID = "theory-canon"


def parse_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    try:
        meta = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        return {}, text
    return meta, parts[2]


def extract_bullets(body: str, heading: str) -> list[str]:
    """'## heading' 섹션의 불릿 목록 추출.

    제외 대상: HTML 주석 불릿, 그리고 '전체가 괄호로 감싼 순수 메모'인 불릿
    (예: "- (추후 개발)"). 앞에 출처·계열을 괄호로 표기한 명제
    (예: "- (Cohen & Levinthal 1990) 흡수역량은 …")는 claim으로 살린다.
    """
    lines = body.splitlines()
    out, in_section = [], False
    for line in lines:
        s = line.strip()
        if s.startswith("## "):
            in_section = s[3:].strip().startswith(heading)
            continue
        if in_section and s.startswith("- "):
            item = s[2:].strip()
            if not item or "<!--" in item:
                continue
            if re.fullmatch(r"\([^()]*\)", item):  # 순수 괄호 메모만 제외
                continue
            out.append(item)
    return out


def load() -> int:
    from handoff import ensure_active
    ensure_active("이론 카드 색인")
    conn = connect()
    migrate(conn)
    cards = sorted(p for p in THEORY_DIR.glob("*.md")
                   if not p.name.startswith("_") and "목록" not in p.name)
    stats = {"indexed": 0, "skipped_draft": 0, "unchanged": 0, "claims": 0, "invalid": 0}

    for path in cards:
        meta, body = parse_frontmatter(path.read_text(encoding="utf-8"))
        name = meta.get("theory")
        if not name:
            print(f"  오류  {path.name} — frontmatter에 theory 필드 없음")
            stats["invalid"] += 1
            continue
        if meta.get("status") != "reviewed":
            print(f"  보류  {path.name} — status={meta.get('status')} (reviewed만 색인, 사람 검수 필요)")
            stats["skipped_draft"] += 1
            continue
        if not meta.get("reviewed_by"):
            print(f"  오류  {path.name} — reviewed인데 reviewed_by 미기재 (검수자 기록 필수)")
            stats["invalid"] += 1
            continue

        claims = [(t, "neutral") for t in extract_bullets(body, "핵심 명제")]
        claims += [(t, "conditional") for t in extract_bullets(body, "경계 조건")]
        if not claims:
            print(f"  오류  {path.name} — 핵심 명제 불릿이 없음")
            stats["invalid"] += 1
            continue

        c_hash = content_hash(body)
        row = conn.execute(
            "SELECT id, content_hash FROM documents WHERE source_id=? AND title=?",
            (SOURCE_ID, name),
        ).fetchone()
        if row and row["content_hash"] == c_hash:
            stats["unchanged"] += 1
            continue

        if row:  # 카드 수정 → 기존 claim 교체
            conn.execute("DELETE FROM claims WHERE document_id=?", (row["id"],))
            doc_id = row["id"]
            conn.execute(
                "UPDATE documents SET content_hash=?, body=?, status='enriched' WHERE id=?",
                (c_hash, body, doc_id),
            )
        else:
            doc_id = new_id()
            year_s = str(meta.get("year", "")).strip()
            # published_at 은 DATE 컬럼 — 카드의 연도만 있는 경우 해당 연도 1월 1일로 저장
            published = f"{year_s}-01-01" if year_s.isdigit() and len(year_s) == 4 else None
            conn.execute(
                """INSERT INTO documents
                   (id, source_id, tier, title, author, published_at, lang,
                    body, content_hash, status)
                   VALUES (?, ?, 'T1', ?, ?, ?, 'ko', ?, ?, 'enriched')""",
                (doc_id, SOURCE_ID, name, str(meta.get("originators", "")),
                 published, body, c_hash),
            )
            conn.execute(
                "INSERT INTO tags (document_id, axis, value) VALUES "
                "(?, 'tier', 'T1'), (?, 'content_type', 'theory'), (?, 'field', ?) "
                "ON CONFLICT DO NOTHING",
                (doc_id, doc_id, doc_id, str(meta.get("field", ""))),
            )

        for text, stance in claims:
            conn.execute(
                """INSERT INTO claims
                   (id, document_id, claim_text, evidence_type, stance, confidence)
                   VALUES (?, ?, ?, 'theory', ?, 1.0)""",
                (new_id(), doc_id, text, stance),
            )
        conn.commit()
        stats["indexed"] += 1
        stats["claims"] += len(claims)
        print(f"  색인  {name} — claim {len(claims)}건 (검수: {meta.get('reviewed_by')})")

    print(f"\n완료: 색인 {stats['indexed']}장(claim {stats['claims']}건) / "
          f"변경없음 {stats['unchanged']} / 검수대기 {stats['skipped_draft']} / 오류 {stats['invalid']}")
    conn.close()
    return 0 if stats["invalid"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(load())

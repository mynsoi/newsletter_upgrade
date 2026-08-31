"""파이프라인 핵심 동작 테스트 (네트워크 불필요 — 로컬 픽스처 사용)."""
import os
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))


@pytest.fixture()
def test_db(tmp_path, monkeypatch):
    monkeypatch.setenv("PIPELINE_DB", str(tmp_path / "test.db"))
    monkeypatch.delenv("DATABASE_URL", raising=False)  # 로컬 테스트는 SQLite 모드 강제
    # db 모듈 재로드로 경로 반영
    for mod in ["db"]:
        if mod in sys.modules:
            del sys.modules[mod]
    import db
    conn = db.connect()
    db.migrate(conn)
    yield conn, db
    conn.close()


def test_migrations_apply_and_are_idempotent(test_db):
    conn, db = test_db
    tables = {r["name"] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type IN ('table','virtual table') OR type='table'")}
    for t in ["documents", "claims", "tags", "internal_docs", "articles", "article_sources"]:
        assert t in tables, f"{t} 테이블 누락"
    assert db.migrate(conn) == []  # 재실행 시 추가 적용 없음


def test_content_hash_normalizes_whitespace_and_case(test_db):
    _, db = test_db
    assert db.content_hash("Hello  World") == db.content_hash("hello world\n")
    assert db.content_hash("a") != db.content_hash("b")


def test_rss_collect_with_local_fixture(test_db, tmp_path, monkeypatch):
    conn, db = test_db
    import collectors.rss as rss

    fixture = (Path(__file__).parent / "fixtures" / "sample_feed.xml").read_text(encoding="utf-8")
    monkeypatch.setattr(rss, "fetch_url", lambda url, client: fixture)

    source = {"id": "test-src", "tier": "T3", "feed_url": "http://x/feed", "lang": "en"}
    stats = rss.collect_source(source, conn, client=None, fetch_full=False)
    assert stats["new"] == 2
    # 재수집 시 전량 중복 처리
    stats2 = rss.collect_source(source, conn, client=None, fetch_full=False)
    assert stats2["new"] == 0 and stats2["dup"] == 2

    row = conn.execute("SELECT tier, status, body FROM documents LIMIT 1").fetchone()
    assert row["tier"] == "T3" and row["status"] == "new"
    assert row["body"]  # 원문이 body 컬럼에 저장됨 (raw_path 파일 대체)
    # 검색 동작 (FTS5 → db.search: PostgreSQL 검색함수 / SQLite LIKE 폴백)
    hit = db.search(conn, "documents", "productivity")
    assert len(hit) >= 1


def test_internal_sync_rejects_c_and_gates_b(test_db, tmp_path, monkeypatch):
    conn, db = test_db
    import internal_sync as isync

    internal = tmp_path / "internal"
    (internal / "skms").mkdir(parents=True)
    (internal / "skms" / "a-doc.md").write_text(
        "---\ntitle: 공개자료\ntype: skms\nsecurity: A\ndate: 2026-01-01\n---\n본문 A",
        encoding="utf-8")
    (internal / "skms" / "b-doc.md").write_text(
        "---\ntitle: 사내한자료\ntype: skms\nsecurity: B\ndate: 2026-01-01\n---\n본문 B",
        encoding="utf-8")
    (internal / "skms" / "c-doc.md").write_text(
        "---\ntitle: 기밀\ntype: skms\nsecurity: C\ndate: 2026-01-01\n---\n절대 색인 금지",
        encoding="utf-8")
    (internal / "skms" / "_TEMPLATE.md").write_text("---\nsecurity: A\n---\n템플릿", encoding="utf-8")

    monkeypatch.setattr(isync, "INTERNAL_DIR", internal)
    monkeypatch.setattr(isync, "load_settings", lambda: {"b_grade_api_approved": False})
    # sync는 같은 PIPELINE_DB 파일에 자체 연결을 생성 — 커밋 후 우리 conn으로 검증

    isync.sync()

    rows = {r["id"]: r for r in conn.execute("SELECT * FROM internal_docs")}
    assert "skms/a-doc.md" in rows and rows["skms/a-doc.md"]["api_eligible"] == 1
    assert "skms/b-doc.md" in rows and rows["skms/b-doc.md"]["api_eligible"] == 0  # 이행기 게이트
    assert "skms/c-doc.md" not in rows  # C등급 색인 거부
    assert not any("TEMPLATE" in k for k in rows)

    # 승인 후 재색인 시 B등급 API 적격 전환
    monkeypatch.setattr(isync, "load_settings", lambda: {"b_grade_api_approved": True})  # 승인 상태 시뮬레이션
    (internal / "skms" / "b-doc.md").write_text(
        "---\ntitle: 사내한자료\ntype: skms\nsecurity: B\ndate: 2026-01-01\n---\n본문 B 수정",
        encoding="utf-8")
    isync.sync()
    row = conn.execute("SELECT api_eligible FROM internal_docs WHERE id='skms/b-doc.md'").fetchone()
    assert row["api_eligible"] == 1


def test_claim_parsing_handles_fences_and_invalid_fields(test_db):
    from enrich.extract_claims import parse_claims
    raw = """```json
[
 {"claim_text": "테스트 주장", "stance": "optimistic", "evidence_type": "survey",
  "metric": "47%", "confidence": 0.8},
 {"claim_text": "분류 오류 주장", "stance": "banana", "evidence_type": "??"},
 {"stance": "neutral"}
]
```"""
    claims = parse_claims(raw)
    assert len(claims) == 2  # claim_text 없는 항목 제외
    assert claims[0]["metric"] == "47%"
    assert claims[1]["stance"] == "neutral" and claims[1]["evidence_type"] == "opinion"


def test_theory_loader_gates_and_claims(test_db, tmp_path, monkeypatch):
    conn, db = test_db
    import load_theories as lt

    tdir = tmp_path / "theories"
    tdir.mkdir()
    card = """---
theory: 심리적 안전감 (Psychological Safety)
originators: Edmondson
year: 1999
field: 팀·리더십
status: {status}
reviewed_by: {reviewer}
---
## 핵심 명제
- 팀의 심리적 안전감은 학습 행동을 매개로 팀 성과에 기여한다
- 심리적 안전감은 개인 성격이 아니라 팀 수준에서 형성되는 집단 특성이다
## 경계 조건
- 책무성이 함께 높지 않으면 안전감만으로는 성과로 이어지지 않는다
## AI 시대 연결점
- AI 실험·실패 공유 문화의 전제 조건 분석 렌즈
"""
    (tdir / "psych-safety.md").write_text(
        card.format(status="draft", reviewer=""), encoding="utf-8")
    monkeypatch.setattr(lt, "THEORY_DIR", tdir)

    lt.load()
    assert conn.execute(
        "SELECT COUNT(*) n FROM documents WHERE source_id='theory-canon'").fetchone()["n"] == 0  # draft 거부

    (tdir / "psych-safety.md").write_text(
        card.format(status="reviewed", reviewer="홍길동"), encoding="utf-8")
    lt.load()
    doc = conn.execute(
        "SELECT * FROM documents WHERE source_id='theory-canon'").fetchone()
    assert doc is not None and doc["tier"] == "T1"
    rows = conn.execute(
        "SELECT stance FROM claims WHERE document_id=?", (doc["id"],)).fetchall()
    assert len(rows) == 3  # 명제 2 + 경계조건 1
    assert sum(1 for r in rows if r["stance"] == "conditional") == 1

    # 카드 수정 시 claim 교체 (누적 아님)
    (tdir / "psych-safety.md").write_text(
        card.format(status="reviewed", reviewer="홍길동") + "\n", encoding="utf-8")
    lt.load()  # 해시 동일(공백 정규화) → 변경 없음
    assert conn.execute("SELECT COUNT(*) n FROM claims").fetchone()["n"] == 3


def test_handoff_roundtrip_and_guard(tmp_path, monkeypatch):
    import sqlite3 as sq
    import handoff as ho

    data_a = tmp_path / "pc_a" / "data"
    data_a.mkdir(parents=True)
    conn = sq.connect(data_a / "pipeline.db")
    conn.execute("CREATE TABLE documents (id TEXT)"); conn.execute("INSERT INTO documents VALUES ('d1'),('d2')")
    conn.execute("CREATE TABLE claims (id TEXT)"); conn.execute("INSERT INTO claims VALUES ('c1')")
    conn.commit(); conn.close()
    (data_a / "raw").mkdir(); (data_a / "raw" / "d1.txt").write_text("원문", encoding="utf-8")

    # PC-A에서 내보내기
    monkeypatch.setattr(ho, "DATA_DIR", data_a)
    monkeypatch.setattr(ho, "HANDOFF_DIR", tmp_path / "pc_a" / "handoff")
    assert ho.get_state() == "active"
    assert ho.export() == 0
    assert ho.get_state() == "handed_off"
    zips = list((tmp_path / "pc_a" / "handoff").glob("*.zip"))
    assert len(zips) == 1

    # 이관됨 상태에서 쓰기 가드 작동
    with pytest.raises(SystemExit):
        ho.ensure_active("수집")
    # 이중 내보내기 차단
    assert ho.export() == 1

    # PC-B에서 받기
    data_b = tmp_path / "pc_b" / "data"
    monkeypatch.setattr(ho, "DATA_DIR", data_b)
    assert ho.receive(str(zips[0])) == 0
    assert ho.get_state() == "active"
    assert (data_b / "raw" / "d1.txt").read_text(encoding="utf-8") == "원문"
    ho.ensure_active("수집")  # 활성 상태에서는 통과

    conn = sq.connect(data_b / "pipeline.db")
    assert conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 2
    conn.close()

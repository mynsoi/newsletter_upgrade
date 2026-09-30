"""인용 원장(article_sources) — src/article_ledger.py.

SQLite 모드(test_db 픽스처)로 돈다. 네트워크·API 불필요.
"""
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

MD = """# 제목입니다

<!-- slug: t | 판본: v1 -->

**세 줄 요약**

- 요약 한 줄.
<!-- claims: C1, C2 -->

## 첫 소제목

첫 문단.
<!-- claims: C1 -->

둘째 문단 — 같은 claim을 두 번 적어도 한 행.
<!-- claims: C2, C3, C2 -->

## 참고자료

- 출처 목록은 원장 대상이 아니다
"""

EVIDENCE = {"claims": [
    {"id": "C1", "role": "관찰된 신호 — 개인 체감"},
    {"id": "C2", "role": "경계 조건① — 효과 크기 한계"},
    {"id": "C3", "role": "이론 렌즈① — 핵심"},
]}


@pytest.fixture()
def test_db(tmp_path, monkeypatch):
    monkeypatch.setenv("PIPELINE_DB", str(tmp_path / "test.db"))
    monkeypatch.delenv("DATABASE_URL", raising=False)  # SQLite 모드 강제
    for mod in list(sys.modules):
        if mod in ("db", "article_ledger", "verify_article"):
            del sys.modules[mod]
    import db
    conn = db.connect()
    db.migrate(conn)
    yield conn, db
    conn.close()


def _seed(conn, sources=("src-a", "src-b", "src-a")):
    for i, src in enumerate(sources, 1):
        conn.execute(
            "INSERT INTO documents (id, source_id, tier, url, title, body, status) "
            "VALUES (?,?,?,?,?,?, 'enriched')",
            (f"D{i}", src, "T1", f"http://x/{i}", f"문서 {i}", "본문"))
        conn.execute(
            "INSERT INTO claims (id, document_id, claim_text, evidence_type, stance) "
            "VALUES (?,?,?,?,?)", (f"C{i}", f"D{i}", f"주장 {i}", "data", "neutral"))
    conn.execute("INSERT INTO articles (id, slug, title, status) VALUES ('A1','t','제목','approved')")
    conn.commit()


def test_map_role_is_conservative():
    import article_ledger as al
    assert al.map_role("경계 조건① — 측정 모호성") == "counter"
    assert al.map_role("관찰된 신호 — 개인 생산성 향상 체감 (상반 관점: 낙관)") == "counter"  # 상반이 우선
    assert al.map_role("관찰된 신호 — 동일 지표 교차 확인") == "context"
    assert al.map_role("이론 렌즈② 핵심 — 연결 구조") == "support"
    assert al.map_role(None) is None and al.map_role("") is None


def test_ledger_rows_pairs_paragraphs_and_dedupes(test_db):
    import article_ledger as al
    rows = al.ledger_rows(MD, EVIDENCE)
    refs = {(cid, ref) for cid, ref, _ in rows}
    assert ("C1", "첫 소제목 ¶1") in refs and ("C3", "첫 소제목 ¶2") in refs
    assert sum(1 for cid, ref, _ in rows if cid == "C2" and ref == "첫 소제목 ¶2") == 1  # 문단 안 중복 제거
    assert {r[2] for r in rows if r[0] == "C2"} == {"counter"}
    assert all(not ref.startswith("참고자료") for _, ref, _ in rows)
    assert al.ledger_rows(MD)[0][2] is None   # 증거 파일이 없으면 역할 미분류


def test_record_is_idempotent_and_counts_by_source(test_db):
    conn, _ = test_db
    import article_ledger as al
    _seed(conn)
    n1 = al.record(conn, "A1", MD, EVIDENCE)
    n2 = al.record(conn, "A1", MD, EVIDENCE)          # 재실행 — 중복 행이 생기지 않는다
    assert n1 == n2 == conn.execute("SELECT COUNT(*) c FROM article_sources").fetchone()["c"]
    by = {r["source_id"]: r for r in al.citations_by_source(conn)}
    assert by["src-a"]["claims"] == 2 and by["src-b"]["claims"] == 1   # C1·C3 → src-a, C2 → src-b
    assert by["src-a"]["articles"] == 1


def test_record_refuses_unknown_claims(test_db):
    """DB에 없는 claim이 있으면 아무것도 쓰지 않는다 — 발행본과 어긋난 원장을 남기지 않는다."""
    conn, _ = test_db
    import article_ledger as al
    _seed(conn, sources=("src-a", "src-b"))            # C3 없음
    with pytest.raises(ValueError, match="C3"):
        al.record(conn, "A1", MD, EVIDENCE)
    assert conn.execute("SELECT COUNT(*) c FROM article_sources").fetchone()["c"] == 0

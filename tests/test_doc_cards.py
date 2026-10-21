"""문서 카드 단계 테스트 (네트워크 불필요 — 모델 응답은 가짜, SQLite 모드)."""
import json
import sys
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

SOURCES = ["hbr", "dbr"]
BODY = "본문 " * 500  # 1,500자 — 800자 경계 통과
SETTINGS = {"card_enabled": True, "card_model": "claude-sonnet-5-5",
            "card_daily_limit": 100, "card_max_chars": 60000, "card_sources": SOURCES}


@pytest.fixture()
def test_db(tmp_path, monkeypatch):
    monkeypatch.setenv("PIPELINE_DB", str(tmp_path / "test.db"))
    monkeypatch.delenv("DATABASE_URL", raising=False)  # 로컬 테스트는 SQLite 모드 강제
    for mod in list(sys.modules):
        if mod in ("db", "handoff") or mod.startswith(("collectors", "enrich", "search")):
            del sys.modules[mod]
    import db
    conn = db.connect()
    db.migrate(conn)
    yield conn
    conn.close()


def add_doc(conn, doc_id, source="hbr", status="enriched", body=BODY, summary_only=0,
            collected_at="2026-10-20 06:00:00"):
    conn.execute(
        "INSERT INTO documents (id, source_id, tier, url, title, body, status, summary_only, "
        "collected_at) VALUES (?,?,?,?,?,?,?,?,?)",
        (doc_id, source, "T3", f"https://x/{doc_id}", f"제목 {doc_id}", body, status,
         summary_only, collected_at))
    conn.commit()


def card_json(episodes=2, material="사례형"):
    return json.dumps({"글쓴이가 하는 말": "글쓴이는 실험이 먼저라고 말한다.",
                       "있었던 일": [f"A사가 {i}번째 일을 했다." for i in range(1, episodes + 1)],
                       "재료 유형": material}, ensure_ascii=False)


class FakeClient:
    """messages.create만 흉내 낸다. reply는 프롬프트 → (stop_reason, 텍스트)."""

    def __init__(self, reply=lambda prompt: ("end_turn", card_json())):
        self.calls = []
        self._lock = threading.Lock()
        self._reply = reply
        self.messages = self

    def create(self, **kw):
        with self._lock:
            self.calls.append(kw)
        stop, text = self._reply(kw["messages"][0]["content"])
        return SimpleNamespace(
            content=[SimpleNamespace(type="text", text=text)],
            usage=SimpleNamespace(input_tokens=1000, output_tokens=500),
            stop_reason=stop)


def cards(conn):
    return {r["document_id"]: r for r in conn.execute("SELECT * FROM document_cards")}


def test_select_targets_conditions(test_db):
    from enrich import doc_cards
    conn = test_db
    add_doc(conn, "ok-old", collected_at="2026-10-01 06:00:00")
    add_doc(conn, "ok-new", source="dbr", collected_at="2026-10-21 06:00:00")
    add_doc(conn, "gate-new", status="new")           # 게이트 전
    add_doc(conn, "gate-off", status="rejected")      # 게이트 탈락
    add_doc(conn, "arxiv", source="arxiv-cs-cy")      # 대상 소스 아님
    add_doc(conn, "summary", summary_only=1)          # 요약뿐
    add_doc(conn, "short", body="짧다" * 100)          # 800자 미만
    add_doc(conn, "has-card")
    conn.execute("INSERT INTO document_cards (document_id, thesis) VALUES ('has-card', 'x')")
    conn.commit()

    ids = [d["id"] for d in doc_cards.select_targets(conn, SOURCES, 10)]
    assert ids == ["ok-new", "ok-old"]  # 최신 수집분 우선
    assert [d["id"] for d in doc_cards.select_targets(conn, SOURCES, 1)] == ["ok-new"]
    assert doc_cards.select_targets(conn, [], 10) == []
    # 미리보기는 카드 유무를 보지 않는다(표가 없는 DB에서도 읽기만으로 돈다)
    assert "has-card" in {d["id"] for d in
                          doc_cards.select_targets(conn, SOURCES, 10, skip_existing=False)}


def test_run_saves_structured_cards_and_records_cost(test_db):
    from enrich import doc_cards
    from enrich.extract_claims import CostState
    conn = test_db
    add_doc(conn, "d1")
    add_doc(conn, "d2", source="dbr")
    client = FakeClient(lambda p: ("end_turn", card_json(episodes=6 if "d1" in p else 0,
                                                         material="의견형")))
    cost = CostState()

    stats = doc_cards.run(conn, SETTINGS, cost, client=client)

    assert stats.made == 2 and not stats.failed
    saved = cards(conn)
    assert json.loads(saved["d1"]["episodes"]) == [f"A사가 {i}번째 일을 했다." for i in range(1, 5)]
    assert json.loads(saved["d2"]["episodes"]) == []
    assert saved["d1"]["thesis"] == "글쓴이는 실험이 먼저라고 말한다."
    assert saved["d1"]["material_type"] == "의견형"
    assert saved["d1"]["model"] == "claude-sonnet-5-5"
    assert saved["d1"]["prompt_version"] == doc_cards.prompt_version(doc_cards.load_template())

    call = client.calls[0]
    assert call["model"] == "claude-sonnet-5-5"
    assert call["output_config"]["effort"] == "medium"
    assert call["output_config"]["format"] == {"type": "json_schema",
                                               "schema": doc_cards.CARD_SCHEMA}
    prompt = call["messages"][0]["content"]
    assert "=== [원문] 제목 d" in prompt and "본문 본문" in prompt
    assert "<!--" not in prompt and "{title}" not in prompt and "{body}" not in prompt
    # 비용: claude-sonnet-5-5 $2 / $10 — 2회 × (1000 입력 + 500 출력)
    assert cost.calls == 2
    assert cost.cost == pytest.approx(2 * (1000 * 2 + 500 * 10) / 1_000_000)


def test_rerun_makes_no_duplicates(test_db):
    from enrich import doc_cards
    from enrich.extract_claims import CostState
    conn = test_db
    add_doc(conn, "d1")
    doc_cards.run(conn, SETTINGS, CostState(), client=FakeClient())
    client = FakeClient()
    stats = doc_cards.run(conn, SETTINGS, CostState(), client=client)
    assert stats.made == 0 and client.calls == []
    assert conn.execute("SELECT COUNT(*) c FROM document_cards").fetchone()["c"] == 1
    # 같은 문서를 두 번 저장하려 해도 행은 하나다
    doc_cards.save_card(conn, "d1", doc_cards.parse_card(card_json()), "m", "v")
    assert conn.execute("SELECT COUNT(*) c FROM document_cards").fetchone()["c"] == 1


def test_card_disabled_skips_without_calls(test_db):
    from enrich import doc_cards
    from enrich.extract_claims import CostState
    conn = test_db
    add_doc(conn, "d1")
    client = FakeClient()
    stats = doc_cards.run(conn, {**SETTINGS, "card_enabled": False}, CostState(), client=client)
    assert stats.made == 0 and client.calls == []
    assert cards(conn) == {}


def test_refusal_and_bad_output_are_skipped_then_retried(test_db):
    from enrich import doc_cards
    from enrich.extract_claims import CostState
    conn = test_db
    add_doc(conn, "refused", collected_at="2026-10-21 06:00:00")
    add_doc(conn, "broken", collected_at="2026-10-20 06:00:00")
    add_doc(conn, "fine", collected_at="2026-10-19 06:00:00")

    def reply(p):
        if "refused" in p:
            return "refusal", ""
        if "broken" in p:
            return "end_turn", '{"글쓴이가 하는 말": "", "있었던 일": [], "재료 유형": "사례형"}'
        return "end_turn", card_json()

    cost = CostState()
    stats = doc_cards.run(conn, SETTINGS, cost, client=FakeClient(reply))
    assert stats.made == 1 and sorted(stats.failed) == ["broken", "refused"]
    assert set(cards(conn)) == {"fine"}
    assert cost.calls == 3  # 실패한 호출도 비용은 기록

    # 다음 실행에서 실패한 두 편만 다시 대상이 된다
    client = FakeClient()
    doc_cards.run(conn, SETTINGS, CostState(), client=client)
    assert len(client.calls) == 2
    assert set(cards(conn)) == {"fine", "refused", "broken"}


def test_api_error_does_not_stop_others(test_db):
    from enrich import doc_cards
    from enrich.extract_claims import CostState
    conn = test_db
    add_doc(conn, "boom")
    add_doc(conn, "fine")

    class Flaky(FakeClient):
        def create(self, **kw):
            if "boom" in kw["messages"][0]["content"]:
                raise RuntimeError("overloaded")
            return super().create(**kw)

    stats = doc_cards.run(conn, SETTINGS, CostState(), client=Flaky())
    assert stats.made == 1 and stats.failed == ["boom"]


def test_parse_card_validation():
    from enrich import doc_cards
    card = doc_cards.parse_card(card_json(episodes=1, material="재료 없음"))
    assert card == {"thesis": "글쓴이는 실험이 먼저라고 말한다.",
                    "episodes": ["A사가 1번째 일을 했다."], "material_type": "재료 없음"}
    with pytest.raises(ValueError):
        doc_cards.parse_card('{"글쓴이가 하는 말": "x", "있었던 일": [], "재료 유형": "기타"}')
    with pytest.raises(ValueError):
        doc_cards.parse_card('{"글쓴이가 하는 말": "x", "있었던 일": "한 줄", "재료 유형": "사례형"}')
    with pytest.raises(ValueError):
        doc_cards.parse_card("JSON 아님")


def test_template_and_prompt_building():
    from enrich import doc_cards
    template = doc_cards.load_template()
    assert template.startswith("아래 [원문]을 재료로")
    assert template.endswith("=== [원문] {title} ===\n{body}")
    # 원문 속 '{title}' 글자는 다시 치환되지 않고, 본문은 card_max_chars에서 잘린다
    prompt = doc_cards.build_prompt(template, "T", "본문에 {title} 글자" + "가" * 100, 20)
    assert prompt.endswith("=== [원문] T ===\n" + ("본문에 {title} 글자" + "가" * 100)[:20])
    assert doc_cards.build_prompt(template, "", "b", 10).count("(무제)") == 1


def test_schema_keys_match_prompt_output_line():
    """스키마 키를 바꾸면 지시문의 출력 형식 줄도 같이 바꿔야 한다."""
    from enrich import doc_cards
    template = doc_cards.load_template()
    for key in doc_cards.CARD_SCHEMA["properties"]:
        assert f'"{key}"' in template
    for material in doc_cards.MATERIAL_TYPES:
        assert material in template


def test_card_parts_for_embedding():
    from search import embed
    sqlite_row = {"thesis": "주장", "episodes": json.dumps(["일1", "일2"], ensure_ascii=False)}
    assert embed.card_parts(sqlite_row) == [("thesis", "주장"), ("episode:1", "일1"),
                                            ("episode:2", "일2")]
    pg_row = {"thesis": "주장", "episodes": []}
    assert embed.card_parts(pg_row) == [("thesis", "주장")]

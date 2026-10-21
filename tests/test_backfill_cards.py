"""문서 카드 소급(Batch) 테스트 — 네트워크 없음, Batch 응답은 가짜, SQLite 모드."""
import json
from types import SimpleNamespace

from test_doc_cards import SETTINGS, add_doc, card_json, cards, test_db  # noqa: F401


def message(text, stop="end_turn"):
    return SimpleNamespace(content=[SimpleNamespace(type="text", text=text)],
                           usage=SimpleNamespace(input_tokens=1000, output_tokens=500),
                           stop_reason=stop)


class FakeBatchClient:
    """messages.batches.create/retrieve/results + messages.count_tokens만 흉내 낸다."""

    def __init__(self, outcomes):
        self.outcomes = outcomes  # custom_id → ("succeeded", text) | ("errored"|"expired", None)
        self.submitted = None
        self.messages = self
        self.batches = self

    def create(self, requests):
        self.submitted = requests
        return SimpleNamespace(id="msgbatch_test")

    def retrieve(self, batch_id):
        return SimpleNamespace(processing_status="ended", request_counts=SimpleNamespace(
            processing=0, succeeded=0, errored=0, expired=0))

    def results(self, batch_id):
        # 결과 순서는 보장되지 않는다 — 제출 순서와 반대로 돌려준다
        for doc_id, (kind, text) in reversed(list(self.outcomes.items())):
            res = SimpleNamespace(type=kind, message=message(text) if kind == "succeeded" else None)
            yield SimpleNamespace(custom_id=doc_id, result=res)

    def count_tokens(self, model, messages):
        return SimpleNamespace(input_tokens=len(messages[0]["content"]) // 2)


def test_requests_use_document_id_and_card_params(test_db):
    from enrich import backfill_cards, doc_cards
    conn = test_db
    add_doc(conn, "d1")
    add_doc(conn, "d2", source="dbr")
    docs = backfill_cards.all_targets(conn, SETTINGS)
    reqs = backfill_cards.build_requests(docs, SETTINGS)
    assert sorted(r["custom_id"] for r in reqs) == ["d1", "d2"]
    prompt = reqs[0]["params"]["messages"][0]["content"]
    assert reqs[0]["params"] == doc_cards.card_params("claude-sonnet-5-5", prompt)


def test_collect_maps_by_custom_id_and_skips_failures(test_db):
    from enrich import backfill_cards
    from enrich.extract_claims import CostState
    conn = test_db
    for d in ("a", "b", "c", "d", "e"):
        add_doc(conn, d)
    client = FakeBatchClient({
        "a": ("succeeded", card_json(episodes=1, material="사례형")),
        "b": ("succeeded", card_json(episodes=3, material="데이터형")),
        "c": ("errored", None),
        "d": ("expired", None),
        "e": ("succeeded", "JSON 아님"),
    })
    cost = CostState()
    result = backfill_cards.collect(conn, client, "msgbatch_test", SETTINGS, cost)

    saved = cards(conn)
    assert set(saved) == {"a", "b"}
    assert len(json.loads(saved["b"]["episodes"])) == 3 and saved["b"]["material_type"] == "데이터형"
    assert sorted(f["document_id"] for f in result["failed"]) == ["c", "d", "e"]
    assert result["materials"] == {"사례형": 1, "데이터형": 1}
    assert cost.calls == 3  # succeeded 3건만 사용량이 있다

    # 실패분은 카드가 없으니 다음 일일 실행의 대상에 그대로 남는다
    left = {d["id"] for d in backfill_cards.all_targets(conn, SETTINGS)}
    assert left == {"c", "d", "e"}


def test_main_submits_waits_and_saves(test_db, monkeypatch, tmp_path):
    from enrich import backfill_cards
    conn = test_db
    add_doc(conn, "a")
    add_doc(conn, "b")
    client = FakeBatchClient({"a": ("succeeded", card_json()), "b": ("succeeded", card_json())})
    monkeypatch.setattr(backfill_cards, "make_client", lambda: client)
    monkeypatch.setattr(backfill_cards, "connect", lambda: conn)
    monkeypatch.setattr(backfill_cards, "STATE_DIR", tmp_path)
    monkeypatch.setattr(backfill_cards.yaml, "safe_load", lambda _: SETTINGS)
    monkeypatch.setattr(conn, "close", lambda: None)

    assert backfill_cards.main(["--yes"]) == 0
    assert sorted(r["custom_id"] for r in client.submitted) == ["a", "b"]
    assert set(cards(conn)) == {"a", "b"}
    assert (tmp_path / "backfill-msgbatch_test.json").exists()
    out = json.loads((tmp_path / "backfill-msgbatch_test-result.json").read_text(encoding="utf-8"))
    assert out["targets"] == 2 and len(out["saved"]) == 2

    # 다시 돌리면 대상이 없어 제출하지 않는다
    client.submitted = None
    assert backfill_cards.main(["--yes"]) == 0
    assert client.submitted is None


def test_dry_run_estimates_without_billing(test_db):
    from enrich import backfill_cards
    conn = test_db
    add_doc(conn, "a")
    add_doc(conn, "b", source="dbr")
    client = FakeBatchClient({})
    r = backfill_cards.dry_run(conn, client, SETTINGS, backfill_cards.all_targets(conn, SETTINGS))
    assert r["targets"] == 2 and r["bad_custom_ids"] == []
    assert client.submitted is None  # 제출하지 않는다
    assert 0.49 < r["tokens_per_char"] < 0.51
    assert r["output_tokens"] == 2 * backfill_cards.OUTPUT_TOKENS_PER_CARD
    assert r["cost_batch"] == r["cost_standard"] * 0.5 > 0

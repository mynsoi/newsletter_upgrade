"""기존 대상 문서의 카드를 Message Batches API로 소급 생성 (지시문 2, 2026-10-21).

일일 실행(doc_cards.run)은 새 문서만 하루 card_daily_limit까지 만든다. 그 전부터 쌓인 대상
(약 1,076편)은 이 스크립트가 Batch(표준 단가의 절반)로 한 번에 만든다. 실행 위치는 개발 PC다
— GitHub Actions 무료 제공량(월 2,000분)을 쓰지 않기 위해서다.

대상 조건·카드 지시문·구조화 출력·저장 함수는 doc_cards의 것을 그대로 쓴다.

사용:
  python src/enrich/backfill_cards.py --dry-run          # 대상 수·토큰·예상 비용·DB 크기만 (API 과금 없음)
  python src/enrich/backfill_cards.py                    # Batch 제출 → 끝날 때까지 대기 → 저장 → 카드 임베딩
  python src/enrich/backfill_cards.py --resume msgbatch_…  # 이미 제출한 Batch의 결과만 받아 저장(끊겼을 때)

- custom_id = documents.id. 결과는 순서가 보장되지 않으므로 custom_id로만 매핑한다.
- succeeded만 저장한다. errored·expired·canceled·refusal·형식 오류는 목록으로 남기고 저장하지
  않는다 — 카드가 없으니 다음 일일 실행(enrich)의 카드 단계가 채운다.
- 저장이 끝나면 카드 임베딩(embed.embed_cards, 상한 없음)을 이어서 만든다.
- 개발 PC 전용 클라이언트: 기본 SSL 문맥을 직접 주고(Windows·Python 3.13 truststore 재귀 오류 회피)
  base_url을 api.anthropic.com으로 못 박는다(Claude 데스크톱 앱이 ANTHROPIC_BASE_URL을 앱
  프록시로 잡아 두는 경우가 있다). 키는 환경변수 ANTHROPIC_API_KEY로만 받는다.
"""
from __future__ import annotations

import argparse
import json
import random
import re
import ssl
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db import ROOT, connect  # noqa: E402
from enrich import doc_cards  # noqa: E402
from enrich.extract_claims import CostState, _price_for  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SETTINGS_PATH = ROOT / "config" / "settings.yaml"
STATE_DIR = ROOT / "output" / "doc-cards"
API_BASE_URL = "https://api.anthropic.com"
BATCH_DISCOUNT = 0.5
# 카드 1장 출력 토큰(생각 포함) — 2026-10-21 미리보기 10편 실측 평균 771.
OUTPUT_TOKENS_PER_CARD = 800
TOKEN_SAMPLE = 40          # --dry-run에서 count_tokens로 재는 표본 수
POLL_SECONDS = 60
CUSTOM_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")  # Batch custom_id 허용 형식


def make_client():
    import anthropic
    return anthropic.Anthropic(
        base_url=API_BASE_URL,
        http_client=anthropic.DefaultHttpxClient(verify=ssl.create_default_context()))


def cards_table_exists(conn) -> bool:
    if conn.is_postgres:
        return conn.execute("SELECT to_regclass('document_cards') AS t").fetchone()["t"] is not None
    return conn.execute("SELECT name FROM sqlite_master WHERE type='table' "
                        "AND name='document_cards'").fetchone() is not None


def db_size_mb(conn) -> float | None:
    if not conn.is_postgres:
        return None
    return conn.execute("SELECT pg_database_size(current_database()) AS b").fetchone()["b"] / 1048576


def all_targets(conn, settings: dict) -> list:
    """소급 대상 전부 — 일일 실행과 같은 조건(doc_cards.select_targets), 상한 없음.
    카드 표가 아직 없으면(009 적용 전) 카드 유무를 보지 않는다 — dry-run 전용."""
    return list(doc_cards.select_targets(conn, settings.get("card_sources") or [], 1_000_000,
                                         skip_existing=cards_table_exists(conn)))


def build_requests(docs, settings: dict) -> list[dict]:
    model = settings.get("card_model", doc_cards.DEFAULT_MODEL)
    max_chars = settings.get("card_max_chars", doc_cards.DEFAULT_MAX_CHARS)
    template = doc_cards.load_template()
    return [{"custom_id": d["id"],
             "params": doc_cards.card_params(model, doc_cards.build_prompt(
                 template, d["title"], d["body"], max_chars))}
            for d in docs]


def dry_run(conn, client, settings: dict, docs) -> dict:
    """대상 수·토큰(count_tokens 표본으로 추정)·예상 비용·DB 크기. 과금되는 호출은 없다."""
    model = settings.get("card_model", doc_cards.DEFAULT_MODEL)
    requests = build_requests(docs, settings)
    bad_ids = [r["custom_id"] for r in requests if not CUSTOM_ID_RE.match(r["custom_id"])]
    sample = random.Random(21).sample(requests, min(TOKEN_SAMPLE, len(requests)))
    sample_tokens = sum(client.messages.count_tokens(model=model, messages=r["params"]["messages"])
                        .input_tokens for r in sample)
    sample_chars = sum(len(r["params"]["messages"][0]["content"]) for r in sample)
    total_chars = sum(len(r["params"]["messages"][0]["content"]) for r in requests)
    ratio = sample_tokens / sample_chars if sample_chars else 0.0
    input_tokens = round(total_chars * ratio)
    output_tokens = OUTPUT_TOKENS_PER_CARD * len(requests)
    price_in, price_out = _price_for(model) or (0.0, 0.0)
    full = input_tokens / 1e6 * price_in + output_tokens / 1e6 * price_out
    by_source = Counter(d["source_id"] for d in docs)
    return {"targets": len(requests), "bad_custom_ids": bad_ids, "sample": len(sample),
            "tokens_per_char": ratio, "input_tokens": input_tokens, "output_tokens": output_tokens,
            "cost_standard": full, "cost_batch": full * BATCH_DISCOUNT,
            "db_size_mb": db_size_mb(conn), "cards_table": cards_table_exists(conn),
            "by_source": by_source.most_common()}


def submit(client, requests: list[dict]) -> str:
    batch = client.messages.batches.create(requests=requests)
    return batch.id


def wait(client, batch_id: str, poll: int = POLL_SECONDS):
    while True:
        batch = client.messages.batches.retrieve(batch_id)
        c = batch.request_counts
        print(f"  [{datetime.now():%H:%M:%S}] {batch.processing_status} — 처리 중 {c.processing}, "
              f"성공 {c.succeeded}, 오류 {c.errored}, 만료 {c.expired}", flush=True)
        if batch.processing_status == "ended":
            return batch
        time.sleep(poll)


def collect(conn, client, batch_id: str, settings: dict, cost: CostState) -> dict:
    """결과를 custom_id(documents.id)로 매핑해 succeeded만 저장. 이미 카드가 있으면 건너뛴다."""
    model = settings.get("card_model", doc_cards.DEFAULT_MODEL)
    version = doc_cards.prompt_version(doc_cards.load_template())
    saved, failed = [], []
    materials: Counter = Counter()
    for item in client.messages.batches.results(batch_id):
        doc_id, res = item.custom_id, item.result
        if res.type != "succeeded":
            failed.append({"document_id": doc_id, "reason": res.type})
            continue
        r = doc_cards.card_from_message(res.message)
        if r.reply is not None:
            cost.record(model, r.reply)
        if r.card is None:
            failed.append({"document_id": doc_id, "reason": r.error})
            continue
        doc_cards.save_card(conn, doc_id, r.card, model, version)
        saved.append(doc_id)
        materials[r.card["material_type"]] += 1
    return {"saved": saved, "failed": failed, "materials": dict(materials)}


def embed_new_cards(conn) -> tuple[int, int] | None:
    from search import embed
    if not embed.IS_POSTGRES:
        print("SQLite 모드 — 카드 임베딩 건너뜀")
        return None
    client = embed.get_client()
    if client is None:
        print("OPENAI_API_KEY_EMBED / OPENAI_API_KEY 미설정 — 카드 임베딩 건너뜀(다음 make embed가 채움)")
        return None
    return embed.embed_cards(conn, client, None)


def report(result: dict, targets: int, cost: CostState, size_before, size_after,
           embedded, batch_id: str) -> Path:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    path = STATE_DIR / f"backfill-{batch_id}-result.json"
    actual = cost.cost * BATCH_DISCOUNT
    path.write_text(json.dumps({**result, "batch_id": batch_id, "targets": targets,
                               "input_tokens": cost.input_tokens, "output_tokens": cost.output_tokens,
                               "cost_batch_usd": actual, "db_size_mb_before": size_before,
                               "db_size_mb_after": size_after, "embedded_parts": embedded},
                              ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n카드 {len(result['saved'])} / 대상 {targets}편 · 실패 {len(result['failed'])}건")
    print("재료 유형: " + ", ".join(f"{k} {v}" for k, v in sorted(result["materials"].items(),
                                                              key=lambda kv: -kv[1])))
    for f in result["failed"]:
        print(f"  실패 {f['document_id']} — {f['reason']} (다음 enrich 카드 단계가 채움)")
    print(f"토큰 입력 {cost.input_tokens:,} / 출력 {cost.output_tokens:,} — 실제 비용 ${actual:.4f} "
          f"(Batch 50%)")
    if size_before is not None:
        print(f"pg_database_size {size_before:.0f}MB → {size_after:.0f}MB")
    print(f"기록: {path}")
    return path


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="기존 문서 카드 소급 (Message Batches API)")
    p.add_argument("--dry-run", action="store_true", help="대상·토큰·예상 비용·DB 크기만 출력")
    p.add_argument("--resume", metavar="BATCH_ID", help="이미 제출한 Batch의 결과만 받아 저장")
    p.add_argument("--limit", type=int, help="앞에서 N편만 (시험용)")
    p.add_argument("--yes", action="store_true", help="제출 전 확인 질문 생략")
    args = p.parse_args(argv)

    settings = yaml.safe_load(SETTINGS_PATH.read_text(encoding="utf-8")) or {}
    conn = connect()
    client = make_client()
    docs = all_targets(conn, settings)
    if args.limit is not None:
        docs = docs[:args.limit]

    if args.dry_run:
        r = dry_run(conn, client, settings, docs)
        print(f"대상 {r['targets']}편 (카드 표 {'있음' if r['cards_table'] else '없음 — 009 적용 전, 카드 유무 미반영'})")
        print("소스별: " + ", ".join(f"{s} {n}" for s, n in r["by_source"]))
        if r["bad_custom_ids"]:
            print(f"[경고] custom_id 형식에 맞지 않는 문서 id {len(r['bad_custom_ids'])}건: "
                  f"{r['bad_custom_ids'][:5]}")
        print(f"토큰 추정: count_tokens 표본 {r['sample']}편 → 글자당 {r['tokens_per_char']:.2f}토큰 · "
              f"입력 약 {r['input_tokens']:,} · 출력 약 {r['output_tokens']:,}(장당 {OUTPUT_TOKENS_PER_CARD})")
        print(f"예상 비용: 표준 ${r['cost_standard']:.2f} → Batch ${r['cost_batch']:.2f}")
        if r["db_size_mb"] is not None:
            print(f"현재 pg_database_size {r['db_size_mb']:.0f}MB")
        conn.close()
        return 0

    if not cards_table_exists(conn):
        print("오류: document_cards 표가 없다 — migrations/009가 적용되지 않았다. 중단.")
        return 2
    size_before = db_size_mb(conn)
    targets = len(docs)
    if args.resume:
        batch_id = args.resume
        state = STATE_DIR / f"backfill-{batch_id}.json"
        if state.exists():  # 제출 때 기록한 대상 수·크기를 쓴다(그사이 카드가 생겨 docs가 줄었을 수 있다)
            s = json.loads(state.read_text(encoding="utf-8"))
            targets, size_before = len(s["document_ids"]), s["db_size_mb_before"]
    else:
        if not docs:
            print("소급 대상 없음 — 정상 종료.")
            return 0
        if not args.yes and input(f"대상 {len(docs)}편을 Batch로 제출할까요? [y/N] ").strip().lower() != "y":
            print("취소.")
            return 1
        batch_id = submit(client, build_requests(docs, settings))
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        (STATE_DIR / f"backfill-{batch_id}.json").write_text(json.dumps(
            {"batch_id": batch_id, "submitted_at": datetime.now().isoformat(timespec="seconds"),
             "document_ids": [d["id"] for d in docs], "db_size_mb_before": size_before},
            ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"제출: {batch_id} ({len(docs)}편) — 끊기면 --resume {batch_id}")
    wait(client, batch_id)
    cost = CostState()
    result = collect(conn, client, batch_id, settings, cost)
    embedded = embed_new_cards(conn)
    size_after = db_size_mb(conn)
    report(result, targets, cost, size_before, size_after, embedded and embedded[0], batch_id)
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

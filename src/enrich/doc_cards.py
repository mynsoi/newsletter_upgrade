"""게이트 통과 문서마다 '카드'(글쓴이가 하는 말 + 있었던 일 0~4개 + 재료 유형)를 만들어
document_cards에 저장 (migrations/009).

2026-10-21 카드 비교 시험(게이트 통과 원문 40편, 방식을 가린 평가)에서 Claude Sonnet 5.5 카드가
칼럼 주제를 뽑고 원문을 찾는 데 claim보다 나았다 — claim 추출은 그대로 두고 카드를 덧붙인다.
작업실(mentor-lab)은 카드 표를 읽기만 한다. 주제 묶기는 작업실 쪽 몫이다.

사용:
  python src/enrich/extract_claims.py          # 일일 실행 — claim 추출 다음에 이 단계가 돈다
  python src/enrich/doc_cards.py [--limit N]   # 카드 단계만 단독 실행
  python src/enrich/doc_cards.py --preview 10  # DB에 쓰지 않고 표본 카드를 output/에 미리보기

- 대상: status='enriched'(게이트 통과) · source_id ∈ settings.card_sources · summary_only=0 ·
  본문 800자 이상 · 카드가 아직 없는 문서. 최신 수집분 우선, 하루 card_daily_limit까지.
- 프롬프트 원본: prompts/doc_card.md (코드 내 프롬프트 금지 — CLAUDE.md). 머리 주석은 떼고 보낸다.
- 구조화 출력(output_config.format JSON 스키마)으로 JSON 깨짐을 막는다 — 시험에서 스키마 없이
  Haiku가 40편 중 1편 JSON을 깨뜨렸다. 스키마 키는 지시문의 출력 키(한국어) 그대로다.
- refusal·API 오류·파싱 실패는 행을 쓰지 않고 건너뛴다 → 다음 실행에서 다시 대상이 된다.
- 비용은 claim 추출과 같은 CostState에 기록된다(extract_claims.MODEL_PRICING).
- 기존 문서 소급은 이 스크립트가 아니라 Batch API 별도 스크립트로 한다(Actions 시간 보호).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db import ROOT, connect, migrate  # noqa: E402
from enrich.extract_claims import CostState, ModelReply  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROMPT_PATH = ROOT / "prompts" / "doc_card.md"
SETTINGS_PATH = ROOT / "config" / "settings.yaml"
PREVIEW_DIR = ROOT / "output" / "doc-cards"

DEFAULT_MODEL = "claude-sonnet-5-5"
DEFAULT_DAILY_LIMIT = 100
DEFAULT_MAX_CHARS = 60000
MIN_BODY_CHARS = 800      # summary_only 경계와 같은 값(migrations/002)
MAX_EPISODES = 4
# 시험과 같은 effort. Sonnet 5.5 기본값은 high라 명시한다.
EFFORT = "medium"
# 카드 출력은 생각 포함 2천 토큰 안팎이다. 넉넉히 두어도 실제 출력분만 과금된다.
MAX_OUTPUT_TOKENS = 16000
# 동시 호출 수 — 100편 날에도 Actions 시간이 10분 안팎에서 끝나도록. DB 쓰기는 메인 스레드 하나.
WORKERS = 4

KEY_THESIS = "글쓴이가 하는 말"
KEY_EPISODES = "있었던 일"
KEY_TYPE = "재료 유형"
MATERIAL_TYPES = ("사례형", "데이터형", "의견형", "재료 없음")

# 배열 개수 제약(maxItems)은 구조화 출력이 지원하지 않는다 — 4개 상한은 parse_card가 자른다.
CARD_SCHEMA = {
    "type": "object",
    "properties": {
        KEY_THESIS: {"type": "string"},
        KEY_EPISODES: {"type": "array", "items": {"type": "string"}},
        KEY_TYPE: {"type": "string", "enum": list(MATERIAL_TYPES)},
    },
    "required": [KEY_THESIS, KEY_EPISODES, KEY_TYPE],
    "additionalProperties": False,
}

_HEAD_COMMENT_RE = re.compile(r"\A\s*<!--.*?-->\s*", re.S)
_PLACEHOLDER_RE = re.compile(r"\{(title|body)\}")


def load_template() -> str:
    """지시문 본문 — 파일 머리의 HTML 주석(출처·관리 메모)과 끝 줄바꿈은 모델에 보내지 않는다
    (시험 때 프롬프트는 원문 본문으로 끝났다)."""
    return _HEAD_COMMENT_RE.sub("", PROMPT_PATH.read_text(encoding="utf-8"), count=1).rstrip()


def prompt_version(template: str) -> str:
    return hashlib.sha256(template.encode("utf-8")).hexdigest()[:12]


def build_prompt(template: str, title: str, body: str, max_chars: int) -> str:
    # 한 번에 치환한다 — 원문에 '{body}' 같은 글자가 있어도 다시 치환되지 않도록.
    values = {"title": title or "(무제)", "body": (body or "")[:max_chars]}
    return _PLACEHOLDER_RE.sub(lambda m: values[m.group(1)], template)


def parse_card(text: str) -> dict:
    """모델 출력(JSON) → 저장 칸 이름(thesis·episodes·material_type). 형식이 틀리면 ValueError."""
    data = json.loads(text)
    thesis = data.get(KEY_THESIS)
    if not isinstance(thesis, str) or not thesis.strip():
        raise ValueError(f"'{KEY_THESIS}'가 비었다")
    episodes = data.get(KEY_EPISODES)
    if not isinstance(episodes, list):
        raise ValueError(f"'{KEY_EPISODES}'가 배열이 아니다")
    material = data.get(KEY_TYPE)
    if material not in MATERIAL_TYPES:
        raise ValueError(f"알 수 없는 재료 유형: {material!r}")
    eps = [e.strip() for e in episodes if isinstance(e, str) and e.strip()]
    return {"thesis": thesis.strip(), "episodes": eps[:MAX_EPISODES], "material_type": material}


def select_targets(conn, sources: list[str], limit: int, *, skip_existing: bool = True):
    """카드 대상 문서, 최신 수집분 우선. skip_existing=False는 미리보기 전용 —
    document_cards 표가 아직 없는 DB(마이그레이션 적용 전)에서도 읽기만으로 돈다."""
    if not sources or limit <= 0:
        return []
    marks = ", ".join("?" for _ in sources)
    existing = (" AND NOT EXISTS (SELECT 1 FROM document_cards c WHERE c.document_id = d.id)"
                if skip_existing else "")
    return conn.execute(
        f"""SELECT d.id, d.source_id, d.tier, d.title, d.body FROM documents d
            WHERE d.status = 'enriched' AND d.source_id IN ({marks})
              AND COALESCE(d.summary_only, 0) = 0 AND LENGTH(d.body) >= ?{existing}
            ORDER BY d.collected_at DESC LIMIT ?""",
        (*sources, MIN_BODY_CHARS, limit),
    ).fetchall()


def make_client():
    import anthropic  # 지연 임포트 — 대상이 없거나 꺼져 있으면 SDK 불필요
    return anthropic.Anthropic()


@dataclass
class CardResult:
    card: dict | None = None
    reply: ModelReply | None = None
    error: str | None = None


def card_params(model: str, prompt: str) -> dict:
    """카드 요청 본문 — 일일 실행(messages.create)과 소급(Batch)이 같은 것을 쓴다."""
    return {
        "model": model,
        "max_tokens": MAX_OUTPUT_TOKENS,
        "output_config": {"effort": EFFORT,
                          "format": {"type": "json_schema", "schema": CARD_SCHEMA}},
        "messages": [{"role": "user", "content": prompt}],
    }


def generate_card(client, model: str, prompt: str) -> CardResult:
    """카드 1장. 예외를 밖으로 던지지 않는다 — 실패는 error로 돌려준다(스레드에서 돈다)."""
    try:
        msg = client.messages.create(**card_params(model, prompt))
    except Exception as e:  # noqa: BLE001 — 한 편의 API 오류가 단계를 멈추지 않도록
        return CardResult(error=f"{type(e).__name__}: {e}")
    return card_from_message(msg)


def card_from_message(msg) -> CardResult:
    """모델 응답(Message) → 카드. refusal·잘림·형식 오류는 error로 (Batch 결과도 같은 모양)."""
    usage = getattr(msg, "usage", None)
    text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
    reply = ModelReply(text, getattr(usage, "input_tokens", 0) or 0,
                       getattr(usage, "output_tokens", 0) or 0,
                       msg.stop_reason == "max_tokens")
    if msg.stop_reason == "refusal":
        return CardResult(reply=reply, error="refusal")
    if reply.truncated:
        return CardResult(reply=reply, error=f"응답이 출력 상한({MAX_OUTPUT_TOKENS} 토큰)에서 잘렸다")
    try:
        return CardResult(card=parse_card(text), reply=reply)
    except (ValueError, json.JSONDecodeError) as e:
        return CardResult(reply=reply, error=f"파싱 실패: {e}")


def save_card(conn, doc_id: str, card: dict, model: str, version: str) -> None:
    episodes = "?::jsonb" if conn.is_postgres else "?"
    conn.execute(
        f"""INSERT INTO document_cards
            (document_id, thesis, episodes, material_type, model, prompt_version)
            VALUES (?, ?, {episodes}, ?, ?, ?) ON CONFLICT (document_id) DO NOTHING""",
        (doc_id, card["thesis"], json.dumps(card["episodes"], ensure_ascii=False),
         card["material_type"], model, version),
    )
    conn.commit()


@dataclass
class CardStats:
    made: int = 0
    failed: list[str] = field(default_factory=list)
    cards: list[dict] = field(default_factory=list)  # 미리보기용


def make_cards(conn, docs, settings: dict, cost: CostState, *, client=None,
               save: bool = True) -> CardStats:
    """docs마다 카드를 만든다. 호출은 WORKERS개 동시에, 저장·비용 기록은 이 스레드에서만."""
    stats = CardStats()
    if not docs:
        return stats
    model = settings.get("card_model", DEFAULT_MODEL)
    max_chars = settings.get("card_max_chars", DEFAULT_MAX_CHARS)
    template = load_template()
    version = prompt_version(template)
    client = client or make_client()
    prompts = [build_prompt(template, d["title"], d["body"], max_chars) for d in docs]
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        results = ex.map(lambda p: generate_card(client, model, p), prompts)
        for d, r in zip(docs, results):
            if r.reply is not None:
                cost.record(model, r.reply)
            title = (d["title"] or "")[:50]
            if r.card is None:
                stats.failed.append(d["id"])
                print(f"  카드 건너뜀 [{d['source_id']}] {title} — {r.error} (다음 실행에서 재시도)")
                continue
            if save:
                save_card(conn, d["id"], r.card, model, version)
            stats.made += 1
            stats.cards.append({"document_id": d["id"], "source_id": d["source_id"],
                                "title": d["title"], "body_chars": len(d["body"] or ""),
                                **r.card})
            print(f"  카드 [{d['source_id']}] {title} → {r.card['material_type']}, "
                  f"있었던 일 {len(r.card['episodes'])}개")
    return stats


def run(conn, settings: dict, cost: CostState, *, limit: int | None = None,
        client=None) -> CardStats:
    """일일 실행의 카드 단계 (extract_claims.main이 claim 다음에 부른다)."""
    if settings.get("card_enabled", True) is False:
        print("\n[카드] card_enabled: false — 건너뜀. 정상 종료.")
        return CardStats()
    limit = limit if limit is not None else settings.get("card_daily_limit", DEFAULT_DAILY_LIMIT)
    docs = select_targets(conn, settings.get("card_sources") or [], limit)
    print(f"\n[카드] 대상 {len(docs)}건 (model={settings.get('card_model', DEFAULT_MODEL)}, "
          f"limit={limit})")
    stats = make_cards(conn, docs, settings, cost, client=client)
    if docs:
        print(f"[카드] {stats.made}건 생성, 건너뜀 {len(stats.failed)}건")
    return stats


def pick_preview(conn, sources: list[str], n: int, seed: int) -> list:
    """미리보기 표본 — 최근 대상 중에서 소스가 겹치지 않게 먼저 고르고, 모자라면 나머지에서."""
    pool = list(select_targets(conn, sources, 500, skip_existing=False))
    random.Random(seed).shuffle(pool)
    picked, seen = [], set()
    for d in pool:
        if d["source_id"] not in seen:
            picked.append(d)
            seen.add(d["source_id"])
    picked_ids = {d["id"] for d in picked}
    rest = [d for d in pool if d["id"] not in picked_ids]
    return (picked + rest)[:n]


def write_preview(stats: CardStats, cost: CostState) -> Path:
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    (PREVIEW_DIR / f"preview-{stamp}.json").write_text(
        json.dumps(stats.cards, ensure_ascii=False, indent=1), encoding="utf-8")
    lines = [f"# 문서 카드 미리보기 {stamp}", "",
             f"카드 {stats.made}장 · 건너뜀 {len(stats.failed)}건 · API 호출 {cost.calls}회 · "
             f"입력 {cost.input_tokens:,} / 출력 {cost.output_tokens:,} 토큰 · 실측 ${cost.cost:.4f}", ""]
    for c in stats.cards:
        lines += [f"## [{c['source_id']}] {c['title']}", "",
                  f"`{c['document_id']}` · 본문 {c['body_chars']:,}자 · **{c['material_type']}**", "",
                  f"**{KEY_THESIS}**: {c['thesis']}", "", f"**{KEY_EPISODES}**:"]
        lines += [f"{i}. {e}" for i, e in enumerate(c["episodes"], 1)] or ["(없음)"]
        lines.append("")
    path = PREVIEW_DIR / f"preview-{stamp}.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="문서 카드 생성 (claim 다음 단계)")
    p.add_argument("--limit", type=int, default=None,
                   help=f"처리 상한(미지정 시 settings의 card_daily_limit, 기본 {DEFAULT_DAILY_LIMIT})")
    p.add_argument("--preview", type=int, metavar="N",
                   help="DB에 쓰지 않고 표본 N편 카드를 output/doc-cards/에 미리보기 (마이그레이션도 하지 않음)")
    p.add_argument("--seed", type=int, default=21, help="--preview 표본 고정용")
    args = p.parse_args(argv)
    settings = yaml.safe_load(SETTINGS_PATH.read_text(encoding="utf-8")) or {}
    cost = CostState()
    conn = connect()

    if args.preview:
        docs = pick_preview(conn, settings.get("card_sources") or [], args.preview, args.seed)
        print(f"미리보기 {len(docs)}편 (DB 쓰기 없음, model={settings.get('card_model', DEFAULT_MODEL)})")
        stats = make_cards(conn, docs, settings, cost, save=False)
        conn.close()
        path = write_preview(stats, cost)
        print(f"\n저장: {path}")
    else:
        migrate(conn)
        run(conn, settings, cost, limit=args.limit)
        conn.close()
    print(f"API 호출 {cost.calls}회 (입력 {cost.input_tokens:,} / 출력 {cost.output_tokens:,} 토큰) "
          f"— 실측 비용 ${cost.cost:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

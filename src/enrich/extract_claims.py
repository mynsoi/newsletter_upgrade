"""status='new' 문서에서 claim을 추출해 claims 테이블에 저장.

사용: ANTHROPIC_API_KEY 설정 후
      python src/enrich/extract_claims.py [--limit 30] [--dry-run]

- 프롬프트 원본: prompts/claim_extraction.md (코드 내 프롬프트 금지 — CLAUDE.md)
- 모델: config/settings.yaml의 enrich_model (추출은 경량 모델 — 기획서 8장)
- 외부 문서(documents)만 대상. 내부 자료는 이 스크립트를 거치지 않음.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db import (  # noqa: E402
    ROOT, claim_document_for_enrich, connect, migrate, new_id, release_enrich_lock,
)

# Windows 콘솔(cp949)에서 한글·특수문자 출력이 깨지거나 UnicodeEncodeError 로
# 죽지 않도록 (rss.py·api.py 와 동일). Actions(UTF-8)에서는 영향 없음.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROMPT_PATH = ROOT / "prompts" / "claim_extraction.md"
GATE_PROMPT_PATH = ROOT / "prompts" / "relevance_gate.md"
SETTINGS_PATH = ROOT / "config" / "settings.yaml"
MAX_BODY_CHARS = 24000
GATE_BODY_CHARS = 4000

VALID_STANCE = {"optimistic", "cautious", "conditional", "neutral"}
VALID_EVIDENCE = {"survey", "experiment", "case", "data", "theory", "opinion"}


def build_prompt(title: str, tier: str, body: str) -> str:
    template = PROMPT_PATH.read_text(encoding="utf-8")
    return (template
            .replace("{title}", title or "(무제)")
            .replace("{tier}", tier)
            .replace("{body}", body[:MAX_BODY_CHARS]))


def parse_claims(raw: str) -> list[dict]:
    """모델 출력에서 JSON 배열을 파싱. 코드펜스가 섞여 있으면 제거."""
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    start, end = text.find("["), text.rfind("]")
    if start == -1 or end == -1:
        raise ValueError("JSON 배열을 찾을 수 없음")
    items = json.loads(text[start:end + 1])
    valid = []
    for it in items:
        if not it.get("claim_text"):
            continue
        if it.get("stance") not in VALID_STANCE:
            it["stance"] = "neutral"
        if it.get("evidence_type") not in VALID_EVIDENCE:
            it["evidence_type"] = "opinion"
        valid.append(it)
    return valid


def select_target_docs(conn, limit: int):
    """추출 대상: status='new'이면서 summary_only가 아닌 문서 (A3 게이트)."""
    return conn.execute(
        "SELECT * FROM documents WHERE status='new' AND COALESCE(summary_only, 0) = 0 "
        "ORDER BY collected_at LIMIT ?",
        (limit,),
    ).fetchall()


def check_relevance(title: str, body: str, model: str) -> bool:
    """A1 게이트: '일·조직·인재·AI와 일' 주제 판별. 첫 토큰 IRRELEVANT면 무관."""
    template = GATE_PROMPT_PATH.read_text(encoding="utf-8")
    prompt = (template
              .replace("{title}", title or "(무제)")
              .replace("{body}", body[:GATE_BODY_CHARS]))
    raw = call_model(prompt, model).strip().upper()
    return not raw.startswith("IRRELEVANT")


def call_model(prompt: str, model: str) -> str:
    import anthropic  # 지연 임포트 — dry-run 시 SDK 불필요
    client = anthropic.Anthropic()
    msg = client.messages.create(
        model=model,
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=30)
    p.add_argument("--dry-run", action="store_true",
                   help="API 호출 없이 대상 문서와 프롬프트 길이만 출력")
    args = p.parse_args()

    from handoff import ensure_active
    ensure_active("claim 추출")
    settings = yaml.safe_load(SETTINGS_PATH.read_text(encoding="utf-8")) or {}
    if settings.get("enrich_enabled", True) is False and not args.dry_run:
        print("enrich_enabled: false — claim 추출 비활성화 상태(크레딧 대기). "
              "config/settings.yaml에서 true로 변경 시 재개. 정상 종료.")
        return 0
    model = settings.get("enrich_model", "claude-haiku-4-5-20251001")

    conn = connect()
    migrate(conn)
    docs = select_target_docs(conn, args.limit)
    print(f"대상 문서 {len(docs)}건 (model={model}, dry_run={args.dry_run}) — summary_only 제외")

    total_claims = 0
    gated = 0
    locked = 0
    gate_errors = 0
    failed_docs: list[str] = []  # API 호출·파싱 오류로 처리 실패한 문서 id (claim 0건은 제외)
    for d in docs:
        body = d["body"] or ""

        if args.dry_run:
            prompt = build_prompt(d["title"], d["tier"], body)
            print(f"  DRY  [{d['tier']}] {d['title'][:60]}  (prompt {len(prompt):,}자)")
            continue

        # 문서 단위 원자적 선점 — 두 프로세스가 같은 문서를 동시에 처리하지 않도록.
        if not claim_document_for_enrich(conn, d["id"]):
            locked += 1
            print(f"  건너뜀 [{d['tier']}] {d['title'][:50]} — 다른 프로세스가 처리 중")
            continue

        prompt = build_prompt(d["title"], d["tier"], body)

        # A1 관련성 게이트 — 무관 문서는 추출하지 않고 rejected 처리
        try:
            relevant = check_relevance(d["title"], body, model)
        except Exception as e:  # noqa: BLE001 — 게이트 실패가 추출을 막지 않도록
            gate_errors += 1
            print(f"  게이트 오류 [{d['id']}]: {type(e).__name__} — 추출 단계로 진행")
            relevant = True
        if not relevant:
            conn.execute(
                "UPDATE documents SET status='rejected', enrich_locked_at=NULL WHERE id=?",
                (d["id"],))
            conn.execute(
                "INSERT INTO tags (document_id, axis, value) VALUES (?, 'gate', 'off_topic') "
                "ON CONFLICT DO NOTHING",
                (d["id"],))
            conn.commit()
            gated += 1
            print(f"  무관 [{d['tier']}] {d['title'][:50]} → rejected (관련성 게이트)")
            continue

        try:
            raw = call_model(prompt, model)
            claims = parse_claims(raw)
        except Exception as e:  # noqa: BLE001 — 개별 문서 실패가 배치를 중단시키지 않도록
            release_enrich_lock(conn, d["id"])  # 실패 → 잠금 해제, 다음 실행이 재시도
            failed_docs.append(d["id"])         # 기술적 처리 실패 (API 호출·파싱) — 최종 exit code에 반영
            print(f"  실패 [{d['id']}] {d['title'][:50]}: {type(e).__name__}: {e}")
            continue
        for c in claims:
            conf = c.get("confidence")
            conn.execute(
                """INSERT INTO claims
                   (id, document_id, claim_text, evidence_type, stance, metric, confidence)
                   VALUES (?,?,?,?,?,?,?)""",
                (new_id(), d["id"], c["claim_text"], c["evidence_type"],
                 c["stance"], c.get("metric"),
                 float(conf) if conf is not None else None),
            )
        # 정상 완료 → status 전이 + 잠금 정리를 한 번에
        conn.execute(
            "UPDATE documents SET status='enriched', enrich_locked_at=NULL WHERE id=?",
            (d["id"],))
        conn.commit()
        total_claims += len(claims)
        print(f"  완료 [{d['tier']}] {d['title'][:50]} → claim {len(claims)}건")

    if not args.dry_run:
        print(f"\n총 {total_claims}건 claim 추출, 관련성 게이트 제외 {gated}건, "
              f"동시성 잠금으로 건너뜀 {locked}건, 게이트 오류 {gate_errors}건, "
              f"처리 실패 {len(failed_docs)}건.")
        if failed_docs:
            print(f"[실패] 기술적 처리 실패(API 호출·파싱) {len(failed_docs)}건 "
                  f"— doc id: {', '.join(failed_docs)}")
            print("정상 처리분은 반영됨. 실패 문서는 잠금 해제됨 — 재실행 시 자동 재시도.")
            return 1
        print("다음: eval/claim_spotcheck.md 절차로 정확도 스팟체크")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

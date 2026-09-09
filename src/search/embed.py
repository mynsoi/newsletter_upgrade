"""claims.claim_text를 OpenAI 임베딩으로 변환해 claims.embedding(vector)에 저장.

PostgreSQL 전용 — SQLite 모드는 vector 컬럼이 없으므로 즉시 정상 종료(키워드 검색만 사용,
migrations/005_claims_embedding.sql 참고). 키 로드는 OPENAI_API_KEY_EMBED가 있으면 그것을,
없으면 OPENAI_API_KEY를 쓴다(환경변수 전용 — CLAUDE.md 절대 규칙 4: 비밀값은 파일에 쓰지
않는다. .env로 주입해도 결국 os.environ을 거치므로 동일하게 동작한다). 둘 다 없으면
실패가 아니라 "건너뜀(키 대기)"으로 성공 종료한다(collect.yml 일일 파이프라인이 이 단계로
막히지 않도록).

이미 embedding이 있는 claim은 건너뛴다(WHERE embedding IS NULL) — 재실행해도 중복 비용이
들지 않는다(증분 안전). 100건씩 배치 API 호출.

사용:
  python src/search/embed.py              # embedding IS NULL인 claim을 상한(기본 2000)까지
  python src/search/embed.py --limit 500
  python src/search/embed.py --backfill    # 상한 없이 잔여 전량 변환
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db import ROOT, IS_POSTGRES, connect, migrate  # noqa: E402

SETTINGS_PATH = ROOT / "config" / "settings.yaml"

# Windows 콘솔(cp949)에서 한글 출력이 깨지지 않도록 (rss.py·extract_claims.py와 동일)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MODEL = "text-embedding-3-small"
DIMENSIONS = 1536
BATCH_SIZE = 100
DEFAULT_DAILY_LIMIT = 2000
# $ / 1M 토큰 — OpenAI 공식 요금표(text-embedding-3-small). 단가가 바뀌면 이 값만 갱신.
PRICE_PER_1M_TOKENS = 0.02


def api_key() -> str | None:
    return os.environ.get("OPENAI_API_KEY_EMBED") or os.environ.get("OPENAI_API_KEY")


def get_client():
    """키가 없으면 None(호출부가 "건너뜀"으로 처리) — SDK는 지연 임포트(키 없을 때 불필요)."""
    key = api_key()
    if not key:
        return None
    import openai
    return openai.OpenAI(api_key=key)


def to_vector_literal(vec: list[float]) -> str:
    """pgvector 텍스트 입력 형식('[0.1,0.2,...]')으로 직렬화 — ?::vector 캐스트와 함께 쓴다."""
    return "[" + ",".join(repr(float(x)) for x in vec) + "]"


def embed_texts(client, texts: list[str]) -> tuple[list[list[float]], int]:
    """텍스트 목록을 한 번의 API 호출로 임베딩. 반환: (임베딩 목록, 사용 토큰 수)."""
    resp = client.embeddings.create(model=MODEL, input=texts, dimensions=DIMENSIONS)
    usage = getattr(resp, "usage", None)
    tokens = getattr(usage, "total_tokens", 0) or 0
    return [d.embedding for d in resp.data], tokens


def embed_one(text: str) -> list[float] | None:
    """질의 1건 임베딩 (검색용) — 키가 없으면 None."""
    client = get_client()
    if client is None:
        return None
    vecs, _ = embed_texts(client, [text])
    return vecs[0]


def select_pending(conn, limit: int | None) -> list:
    sql = "SELECT id, claim_text FROM claims WHERE embedding IS NULL ORDER BY id"
    if limit is not None:
        return conn.execute(sql + " LIMIT ?", (limit,)).fetchall()
    return conn.execute(sql).fetchall()


def run(limit: int | None) -> int:
    if not IS_POSTGRES:
        print("SQLite 모드 — claims.embedding 컬럼 없음(pgvector는 PostgreSQL 전용). "
              "의미 검색 건너뜀 — 키워드 검색만 사용. 정상 종료.")
        return 0

    client = get_client()
    if client is None:
        print("OPENAI_API_KEY_EMBED / OPENAI_API_KEY 미설정 — 건너뜀(키 대기). 정상 종료.")
        return 0

    conn = connect()
    migrate(conn)

    pending = select_pending(conn, limit)
    print(f"대상 {len(pending)}건 (embedding IS NULL, model={MODEL}"
          + (f", limit={limit}" if limit is not None else ", 무제한(--backfill)") + ")")
    if not pending:
        conn.close()
        return 0

    total_tokens = 0
    done = 0
    for i in range(0, len(pending), BATCH_SIZE):
        batch = pending[i:i + BATCH_SIZE]
        texts = [r["claim_text"] for r in batch]
        vecs, tokens = embed_texts(client, texts)
        total_tokens += tokens
        for row, vec in zip(batch, vecs):
            conn.execute("UPDATE claims SET embedding = ?::vector WHERE id = ?",
                         (to_vector_literal(vec), row["id"]))
        conn.commit()
        done += len(batch)
        print(f"  {done}/{len(pending)}건 변환 완료")

    cost = total_tokens / 1_000_000 * PRICE_PER_1M_TOKENS
    print(f"\n총 {done}건 임베딩 생성, 토큰 {total_tokens:,} — 실측 비용 ${cost:.4f}")
    conn.close()
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="claims.claim_text → OpenAI 임베딩 저장")
    p.add_argument("--backfill", action="store_true", help="상한 없이 잔여 claim 전량 변환")
    p.add_argument("--limit", type=int, default=None,
                   help=f"처리 상한(미지정 시 일반 실행은 {DEFAULT_DAILY_LIMIT}, "
                        f"--backfill은 무제한)")
    args = p.parse_args(argv)
    if args.limit is not None:
        limit = args.limit
    elif args.backfill:
        limit = None
    else:
        settings = yaml.safe_load(SETTINGS_PATH.read_text(encoding="utf-8")) or {}
        limit = settings.get("embed_daily_limit", DEFAULT_DAILY_LIMIT)
    return run(limit)


if __name__ == "__main__":
    raise SystemExit(main())

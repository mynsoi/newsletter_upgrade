"""문서 카드 조각을 OpenAI 임베딩으로 변환해 document_card_embeddings(halfvec)에 저장 (migrations/009).

카드 1장 = 조각 1 + 있었던 일 개수: 핵심 주장(thesis) 1개 + 있었던 일(episode) 각각. 아직 없는
조각만 만든다(ON CONFLICT DO NOTHING — 재실행해도 중복 비용이 들지 않는다). 100조각씩 배치 API 호출.
칼럼 작업실(mentor-lab-integration)이 이 표로 원문을 찾는다.

**2026-11-10 claim 임베딩 제거.** 예전에는 claims.embedding(768차원)을 먼저 채우고 발행 6개월이
지난 arXiv claim 벡터를 비운 다음 카드를 했다. claim 추출을 없애면서(src/enrich/relevance.py)
claim 임베딩과 arXiv 벡터 비우기(--prune-only, embed_arxiv_retention_months)도 뺐다.
claims 표의 벡터·인덱스 정리는 migrations/drafts/의 용량 회수 초안을 사람이 따로 실행한다.

PostgreSQL 전용 — SQLite 모드는 vector 컬럼이 없으므로 즉시 정상 종료. 키 로드는
OPENAI_API_KEY_EMBED가 있으면 그것을, 없으면 OPENAI_API_KEY를 쓴다(환경변수 전용 — CLAUDE.md
절대 규칙 4: 비밀값은 파일에 쓰지 않는다). 둘 다 없으면 실패가 아니라 "건너뜀(키 대기)"으로
성공 종료한다(collect.yml 일일 파이프라인이 이 단계로 막히지 않도록).

**차원**: 요청 차원은 상수가 아니라 컬럼의 선언 차원(column_dims)을 따른다(카드는 1536) — 코드와
DB 차원이 어긋나면 저장·검색이 실패하고, DB를 먼저 바꾸든 코드를 먼저 배포하든 같은 코드가
동작하게 하기 위해서다.

사용:
  python src/search/embed.py              # 조각이 덜 찬 카드를 상한(기본 2000장)까지
  python src/search/embed.py --limit 500
  python src/search/embed.py --backfill    # 상한 없이 잔여 전량 변환
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db import ROOT, IS_POSTGRES, connect, migrate  # noqa: E402

SETTINGS_PATH = ROOT / "config" / "settings.yaml"

# Windows 콘솔(cp949)에서 한글 출력이 깨지지 않도록 (rss.py·relevance.py와 동일)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MODEL = "text-embedding-3-small"
# 컬럼 차원을 읽지 못할 때의 기본값(모델 원래 차원). 실제 요청 차원은 column_dims()가 정한다.
DIMENSIONS = 1536
# 저장 타입 — 2바이트 반정밀도 halfvec (migrations/006). 값·인덱스 용량이 vector의
# 절반이고 코사인 상위 k 정렬은 동등하다. 텍스트 입력 형식은 vector와 같으므로
# to_vector_literal()은 그대로 쓴다. 타입을 바꿀 땐 이 상수와 마이그레이션만 손대면 된다.
VECTOR_TYPE = "halfvec"
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
    """pgvector 텍스트 입력 형식('[0.1,0.2,...]')으로 직렬화 — ?::halfvec 캐스트와 함께 쓴다.

    vector·halfvec의 텍스트 입력 형식이 동일해서 저장 타입이 바뀌어도 이 함수는 그대로다.
    """
    return "[" + ",".join(repr(float(x)) for x in vec) + "]"


def column_dims(conn, table: str) -> int:
    """table.embedding 컬럼의 선언 차원 — 'halfvec(1536)' → 1536. 읽지 못하면 DIMENSIONS."""
    row = conn.execute(
        "SELECT format_type(atttypid, atttypmod) AS t FROM pg_attribute "
        "WHERE attrelid = to_regclass(?) AND attname = 'embedding' AND NOT attisdropped",
        (table,)).fetchone()
    m = re.search(r"\((\d+)\)", row["t"] if row and row["t"] else "")
    return int(m.group(1)) if m else DIMENSIONS


def embed_texts(client, texts: list[str], dims: int = DIMENSIONS) -> tuple[list[list[float]], int]:
    """텍스트 목록을 한 번의 API 호출로 임베딩. 반환: (임베딩 목록, 사용 토큰 수)."""
    resp = client.embeddings.create(model=MODEL, input=texts, dimensions=dims)
    usage = getattr(resp, "usage", None)
    tokens = getattr(usage, "total_tokens", 0) or 0
    return [d.embedding for d in resp.data], tokens


def card_parts(card) -> list[tuple[str, str]]:
    """카드 1장 → [(part, 텍스트)]. 핵심 주장 1개 + 있었던 일 각각 (migrations/009)."""
    episodes = card["episodes"]
    if isinstance(episodes, str):  # SQLite는 JSON 문자열, PostgreSQL JSONB는 이미 리스트
        episodes = json.loads(episodes)
    return [("thesis", card["thesis"])] + [
        (f"episode:{i}", e) for i, e in enumerate(episodes, 1)]


def select_pending_cards(conn, limit: int | None) -> list:
    """조각 임베딩이 다 차지 않은 카드, 새 카드 먼저. 카드는 만든 뒤 바뀌지 않으므로
    조각 수(1 + 있었던 일 개수)만 맞으면 끝난 카드다."""
    sql = ("SELECT c.document_id, c.thesis, c.episodes FROM document_cards c "
           "WHERE (SELECT COUNT(*) FROM document_card_embeddings e "
           "       WHERE e.document_id = c.document_id) < 1 + jsonb_array_length(c.episodes) "
           "ORDER BY c.created_at DESC")
    params: tuple = ()
    if limit is not None:
        sql += " LIMIT ?"
        params = (limit,)
    return conn.execute(sql, params).fetchall()


def embed_cards(conn, client, limit: int | None) -> tuple[int, int]:
    """카드 조각 임베딩을 document_card_embeddings에 채운다. 반환: (조각 수, 토큰 수).

    차원은 이 표의 컬럼 차원(1536). limit은 카드 장수 기준(embed_daily_limit — 하루 카드는
    card_daily_limit 이하라 사실상 그날 새 카드 전부). 이미 있는 조각은 ON CONFLICT로
    건너뛴다 — 도중에 끊긴 카드를 다시 집어도 중복 행이 생기지 않는다.
    """
    cards = select_pending_cards(conn, limit)
    print(f"카드 임베딩 대상 {len(cards)}장")
    parts = [(c["document_id"], part, text) for c in cards for part, text in card_parts(c)]
    tokens_total = 0
    dims = column_dims(conn, "document_card_embeddings")
    for i in range(0, len(parts), BATCH_SIZE):
        batch = parts[i:i + BATCH_SIZE]
        vecs, tokens = embed_texts(client, [t for _, _, t in batch], dims)
        tokens_total += tokens
        for (doc_id, part, _), vec in zip(batch, vecs):
            conn.execute(
                "INSERT INTO document_card_embeddings (document_id, part, embedding) "
                f"VALUES (?, ?, ?::{VECTOR_TYPE}) ON CONFLICT (document_id, part) DO NOTHING",
                (doc_id, part, to_vector_literal(vec)))
        conn.commit()
        print(f"  카드 조각 {min(i + BATCH_SIZE, len(parts))}/{len(parts)} 변환 완료")
    return len(parts), tokens_total


def run(limit: int | None) -> int:
    if not IS_POSTGRES:
        print("SQLite 모드 — 카드 임베딩 컬럼 없음(pgvector는 PostgreSQL 전용). 건너뜀. 정상 종료.")
        return 0

    # 키부터 본다 — 키가 없으면 DB에 연결하지 않고 끝낸다(일일 파이프라인이 이 단계로 막히지 않도록).
    client = get_client()
    if client is None:
        print("OPENAI_API_KEY_EMBED / OPENAI_API_KEY 미설정 — 건너뜀(키 대기). 정상 종료.")
        return 0

    conn = connect()
    migrate(conn)
    print(f"카드 임베딩 (model={MODEL}"
          + (f", limit={limit}장" if limit is not None else ", 무제한(--backfill)") + ")")
    parts, tokens = embed_cards(conn, client, limit)
    cost = tokens / 1_000_000 * PRICE_PER_1M_TOKENS
    print(f"\n카드 {parts}조각 임베딩 생성, 토큰 {tokens:,} — 실측 비용 ${cost:.4f}")
    conn.close()
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="문서 카드 조각 → OpenAI 임베딩 저장")
    p.add_argument("--backfill", action="store_true", help="상한 없이 잔여 카드 전량 변환")
    p.add_argument("--limit", type=int, default=None,
                   help=f"카드 장수 상한(미지정 시 일반 실행은 {DEFAULT_DAILY_LIMIT}, "
                        f"--backfill은 무제한)")
    args = p.parse_args(argv)
    settings = yaml.safe_load(SETTINGS_PATH.read_text(encoding="utf-8")) or {}
    if args.limit is not None:
        limit = args.limit
    elif args.backfill:
        limit = None
    else:
        limit = settings.get("embed_daily_limit", DEFAULT_DAILY_LIMIT)
    return run(limit)


if __name__ == "__main__":
    raise SystemExit(main())

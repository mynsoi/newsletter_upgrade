"""claims.claim_text를 OpenAI 임베딩으로 변환해 claims.embedding(halfvec)에 저장.

PostgreSQL 전용 — SQLite 모드는 vector 컬럼이 없으므로 즉시 정상 종료(키워드 검색만 사용,
migrations/005_claims_embedding.sql 참고). 키 로드는 OPENAI_API_KEY_EMBED가 있으면 그것을,
없으면 OPENAI_API_KEY를 쓴다(환경변수 전용 — CLAUDE.md 절대 규칙 4: 비밀값은 파일에 쓰지
않는다. .env로 주입해도 결국 os.environ을 거치므로 동일하게 동작한다). 둘 다 없으면
실패가 아니라 "건너뜀(키 대기)"으로 성공 종료한다(collect.yml 일일 파이프라인이 이 단계로
막히지 않도록).

이미 embedding이 있는 claim은 건너뛴다(WHERE embedding IS NULL) — 재실행해도 중복 비용이
들지 않는다(증분 안전). 100건씩 배치 API 호출.

**arXiv 보존 기간 (2026-09-22)**: 발행 N개월(settings.yaml embed_arxiv_retention_months,
기본 6)이 지난 arXiv claim은 벡터를 비우고 다시 채우지 않는다. DB 용량(Supabase 무료 500MB)
절감용이다. 매 실행 앞에서 경계를 넘은 분을 비우고, 임베딩 대상 선정에서도 같은 조건을 뺀다
— 후자가 없으면 비운 claim이 "embedding IS NULL"로 다음 날 다시 채워진다.
- 토픽 발굴(/topics)은 발행일 기준 최근 42일 창만 쓰므로 영향이 없다.
- 증거 수집(hybrid_search)에서 해당 claim은 키워드 검색으로만 걸린다(의미 검색 제외).
- 사람이 골라 넣은 문서(documents.fetched_by='browse')는 기간과 무관하게 유지한다
  — 「GPTs are GPTs」(2023) 같은 핵심 논문이 여기 해당한다.
- 0 또는 null이면 비우기를 끈다(전량 유지).

사용:
  python src/search/embed.py              # embedding IS NULL인 claim을 상한(기본 2000)까지
  python src/search/embed.py --limit 500
  python src/search/embed.py --backfill    # 상한 없이 잔여 전량 변환
  python src/search/embed.py --prune-only  # 보존 기간 지난 arXiv 벡터 비우기만 (임베딩 없음)
"""
from __future__ import annotations

import argparse
import calendar
import os
import sys
from datetime import date
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
# 저장 타입 — 2바이트 반정밀도 halfvec (migrations/006). 값·인덱스 용량이 vector의
# 절반이고 코사인 상위 k 정렬은 동등하다. 텍스트 입력 형식은 vector와 같으므로
# to_vector_literal()은 그대로 쓴다. 타입을 바꿀 땐 이 상수와 마이그레이션만 손대면 된다.
VECTOR_TYPE = "halfvec"
BATCH_SIZE = 100
DEFAULT_DAILY_LIMIT = 2000
# $ / 1M 토큰 — OpenAI 공식 요금표(text-embedding-3-small). 단가가 바뀌면 이 값만 갱신.
PRICE_PER_1M_TOKENS = 0.02
# arXiv 보존 기간 기본값(개월) — settings.yaml embed_arxiv_retention_months가 없을 때.
DEFAULT_ARXIV_RETENTION_MONTHS = 6
# LIKE 패턴은 SQL 본문이 아니라 파라미터로 넘긴다 — '%'가 SQL 문자열에 있으면 psycopg가
# 자리표시자로 오인한다(extract_claims.build_doc_filters와 같은 이유).
ARXIV_SOURCE_PATTERN = "arxiv-%"


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


def months_ago(today: date, months: int) -> date:
    """today에서 months개월 전 같은 날(그 달에 없는 날이면 말일). 예: 8/31 - 6개월 = 2/28."""
    y, m = divmod(today.month - 1 - months, 12)
    year, month = today.year + y, m + 1
    return date(year, month, min(today.day, calendar.monthrange(year, month)[1]))


def arxiv_cutoff(months: int | None, today: date | None = None) -> str | None:
    """보존 경계 발행일(YYYY-MM-DD). months가 0·None이면 None — 비우기 비활성."""
    if not months:
        return None
    return months_ago(today or date.today(), months).isoformat()


def stale_arxiv_docs_sql(cutoff: str) -> tuple[str, list]:
    """보존 기간이 지난 arXiv 문서 id를 고르는 서브쿼리와 파라미터.

    published_at이 NULL인 문서는 경계 밖이라고 단정할 근거가 없어 **유지**한다
    (NULL < ?는 참이 아니다). fetched_by='browse'(사람이 골라 넣은 문서)도 유지한다.
    """
    return ("SELECT id FROM documents WHERE source_id LIKE ? AND published_at < ? "
            "AND COALESCE(fetched_by, '') <> 'browse'",
            [ARXIV_SOURCE_PATTERN, cutoff])


def prune_stale_arxiv(conn, cutoff: str | None) -> int:
    """경계를 넘은 arXiv claim의 벡터를 NULL로 비운다. 반환: 비운 건수."""
    if cutoff is None:
        return 0
    sub, params = stale_arxiv_docs_sql(cutoff)
    cur = conn.execute("UPDATE claims SET embedding = NULL "
                       f"WHERE embedding IS NOT NULL AND document_id IN ({sub})", tuple(params))
    conn.commit()
    return cur.rowcount or 0


def select_pending(conn, limit: int | None, cutoff: str | None = None) -> list:
    """임베딩 대상: embedding IS NULL이면서 보존 기간이 지난 arXiv가 아닌 claim."""
    sql = "SELECT id, claim_text FROM claims WHERE embedding IS NULL"
    params: list = []
    if cutoff is not None:
        sub, params = stale_arxiv_docs_sql(cutoff)
        sql += f" AND document_id NOT IN ({sub})"
    sql += " ORDER BY id"
    if limit is not None:
        sql += " LIMIT ?"
        params = [*params, limit]
    return conn.execute(sql, tuple(params)).fetchall()


def run(limit: int | None, retention_months: int | None = DEFAULT_ARXIV_RETENTION_MONTHS,
        prune_only: bool = False) -> int:
    if not IS_POSTGRES:
        print("SQLite 모드 — claims.embedding 컬럼 없음(pgvector는 PostgreSQL 전용). "
              "의미 검색 건너뜀 — 키워드 검색만 사용. 정상 종료.")
        return 0

    # 일반 실행은 키부터 본다 — 키가 없으면 DB에 연결하지 않고 끝낸다(일일 파이프라인이
    # 이 단계로 막히지 않도록). --prune-only는 API를 쓰지 않으므로 키 없이 돈다.
    client = None
    if not prune_only:
        client = get_client()
        if client is None:
            print("OPENAI_API_KEY_EMBED / OPENAI_API_KEY 미설정 — 건너뜀(키 대기). 정상 종료.")
            return 0

    cutoff = arxiv_cutoff(retention_months)
    conn = connect()
    migrate(conn)

    pruned = prune_stale_arxiv(conn, cutoff)
    if cutoff is None:
        print("arXiv 보존 기간 비활성 — 비우기 건너뜀")
    else:
        print(f"arXiv 보존 경계 {cutoff} (발행 {retention_months}개월, browse 제외) — "
              f"벡터 비움 {pruned}건")
    if prune_only:
        conn.close()
        return 0

    pending = select_pending(conn, limit, cutoff)
    print(f"대상 {len(pending)}건 (embedding IS NULL, 보존 경계 밖 arXiv 제외, model={MODEL}"
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
            conn.execute(f"UPDATE claims SET embedding = ?::{VECTOR_TYPE} WHERE id = ?",
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
    p.add_argument("--prune-only", action="store_true",
                   help="보존 기간이 지난 arXiv claim의 벡터 비우기만 하고 임베딩은 하지 않는다")
    args = p.parse_args(argv)
    settings = yaml.safe_load(SETTINGS_PATH.read_text(encoding="utf-8")) or {}
    if args.limit is not None:
        limit = args.limit
    elif args.backfill:
        limit = None
    else:
        limit = settings.get("embed_daily_limit", DEFAULT_DAILY_LIMIT)
    retention = settings.get("embed_arxiv_retention_months", DEFAULT_ARXIV_RETENTION_MONTHS)
    return run(limit, retention, prune_only=args.prune_only)


if __name__ == "__main__":
    raise SystemExit(main())

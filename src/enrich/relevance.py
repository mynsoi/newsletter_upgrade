"""status='new' 문서의 관련성을 판별해 enriched / rejected로 나눈다 (A1 게이트).

사용: ANTHROPIC_API_KEY 설정 후
      python src/enrich/relevance.py [--limit N] [--dry-run]
      python src/enrich/relevance.py --backlog --limit 500 --cost-cap 5
      python src/enrich/relevance.py --backlog --cost-cap 100   # 잔여 전량, 비용 상한만

**2026-11-10 claim 추출 제거.** 이 파일은 extract_claims.py였다. 판별을 통과한 문서마다 claim을
뽑아 claims 테이블에 넣었는데, 실제로 쓰는 칼럼 작업실(mentor-lab-integration)은 claims를 읽지
않고 문서 카드(document_cards)만 읽는다. 그래서 claim 추출·claim 임베딩과 그것을 읽던 아티클
기능(/topics·/draft 증거 검색·verify_article·인용 원장·이론 카드 색인)을 지우고 판별만 남겼다.
흐름: 판별 → status='enriched'(관련) / 'rejected'(무관) → 문서 카드(doc_cards.py) → 카드 임베딩
(search/embed.py).

- 장문은 청크로 나눠 판별한다(pack_chunks). 한 청크라도 관련 있으면 그 자리에서 멈추고 enriched로
  바꾼다 — 판정 결과는 claim이 있던 때(청크 하나라도 관련 → 통과)와 같고 호출 수만 줄었다.
  판별 호출이 실패하면 그 문서는 판정하지 않고 잠금만 풀어 다음 실행에서 다시 판별한다.
  예전에는 판별 오류를 '관련 있음'으로 보고 claim 추출로 넘겼는데, API 전체가 막히면(2026-09-13
  크레딧 소진) 추출도 실패해 문서가 new로 남았다. 추출이 없어진 지금 같은 규칙을 두면 판별 없이
  전부 enriched가 되므로 재시도로 바꿨다.
- summary_only(본문 800자 미만) 문서는 원칙적으로 제외하되, **T5(신호 감지 전용 소스)만
  예외로 포함**한다(SUMMARY_GATE_TIERS · migrations/008). claim이 없어진 뒤로는 이 판정 결과를
  쓰는 곳이 없다(카드·작업실은 summary_only=0만 쓴다) — T5 수집 중단 때 같이 정리할 대상이다.
- 2026-11-12: settings.summary_gate_sources(McKinsey·Wharton)의 요약분도 판별한다 — 격상 전 선판별.
  작업실 aside 격상은 rejected를 건너뛰므로, 업종 글처럼 무관한 글에 열람(차단에 민감)을 쓰지 않는다.
  관련 있음(enriched)으로 남은 요약분은 격상되면 status='new'로 돌아가 전문으로 다시 판별된다.
- 프롬프트 원본: prompts/relevance_gate.md (코드 내 프롬프트 금지 — CLAUDE.md)
- 모델: config/settings.yaml의 enrich_model (판별은 경량 모델 — 기획서 8장)
- 외부 문서(documents)만 대상. 내부 자료는 이 스크립트를 거치지 않음.
- 일반 실행은 판별 다음에 문서 카드 단계(src/enrich/doc_cards.py, 2026-10-21)를 부른다.
  --backlog·--doc-id·--dry-run에서는 돌지 않는다.
- 일반 실행은 collected_at **역순**(최신 수집분 우선 — 2026-09-09, 그날 유입이 누적
  백로그 뒤에서 굶지 않도록), --backlog는 티어별 라운드로빈(T1이 21,000건+로 압도적이라
  순서대로면 다른 티어가 굶는다) + 실측 비용이 --cost-cap(USD)에 닿으면 새 문서를 더 이상
  집지 않고 중단한다(진행 중이던 문서는 끝까지 처리 — 락을 반쯤 걸린 채로 남기지 않는다).
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db import (  # noqa: E402
    ROOT, claim_document_for_enrich, connect, migrate, release_enrich_lock,
)
from enrich.llm import CostState, ModelReply, _price_for, call_model  # noqa: E402,F401

# Windows 콘솔(cp949)에서 한글·특수문자 출력이 깨지거나 UnicodeEncodeError 로
# 죽지 않도록 (rss.py·api.py 와 동일). Actions(UTF-8)에서는 영향 없음.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

GATE_PROMPT_PATH = ROOT / "prompts" / "relevance_gate.md"
SETTINGS_PATH = ROOT / "config" / "settings.yaml"
# 청크 크기. claim 추출 프롬프트 한도(24k)에 맞춰 두었던 값을 그대로 쓴다 — 판별은 청크마다
# 앞 GATE_BODY_CHARS만 보므로, 값을 바꾸면 장문의 판정 범위가 달라진다.
MAX_BODY_CHARS = 24000
GATE_BODY_CHARS = 4000
DEFAULT_DAILY_LIMIT = 500  # settings.yaml에 enrich_daily_limit이 없을 때의 정상 운영 상한

LONG_DOC_CHARS = MAX_BODY_CHARS
MAX_CHUNKS = 8            # 문서당 청크 상한 (비용 방어 — 24k×8 = 최대 19.2만 자 판별)
MIN_CHUNK_CHARS = 200     # 이보다 짧은 조각은 버린다 (판단할 내용이 없는데 호출만 소모)
# 판별 응답은 RELEVANT / IRRELEVANT 한 단어다(prompts/relevance_gate.md).
GATE_MAX_TOKENS = 16
HEADING_RE = re.compile(r"^(#{1,4}\s+\S|제?\s?\d+\s*(장|절|부)\b|CHAPTER\b|Chapter\b)")

BACKLOG_BATCH_SIZE = 500  # --backlog 시 한 번에 DB에서 가져오는 문서 수 (본문 전체 메모리 적재 방지)
TIER_ORDER = ("T1", "T2", "T3", "T4", "T5")

# summary_only(본문 800자 미만) 문서 중 판별 대상에 넣는 티어 (migrations/008).
# T5는 "요즘 무슨 일이 있나" 신호 감지 전용 소스라(기획서 4.1) RSS가 요약 몇 줄만 주는 것이
# 정상이다. T2~T4의 summary_only는 브라우저 격상(/browse-round)을 기다리는 문서라 그대로 제외한다
# (aside 격상 소스는 예외 — summary_gate_sources, 격상 전 선판별).
SUMMARY_GATE_TIERS = ("T5",)
# 소스 id는 SQL에 리터럴로 넣으므로 형식을 검사한다(settings.yaml은 사람이 고치는 파일이라 오타 방어).
SOURCE_ID_RE = re.compile(r"[a-z0-9][a-z0-9-]*")


def summary_gate_sources() -> tuple[str, ...]:
    """요약뿐이어도 판별하는 소스(settings.summary_gate_sources) — 격상 전 선판별 대상(2026-11-12)."""
    settings = yaml.safe_load(SETTINGS_PATH.read_text(encoding="utf-8")) or {}
    ids = tuple(str(x) for x in settings.get("summary_gate_sources") or ())
    bad = [x for x in ids if not SOURCE_ID_RE.fullmatch(x)]
    if bad:
        raise ValueError(f"settings.summary_gate_sources 형식 오류: {bad}")
    return ids

# 실패율이 이 값 미만이면 "정상 종료"로 본다(exit 0, 경고 로그만 남김) — 대량 백로그
# 실행에서 개별 문서 1~2건의 일시적 오류로 워크플로 전체가 실패 처리되는 것을
# 막기 위함. 실패 문서는 락이 해제돼 다음 실행에서 자동 재시도되므로 데이터 유실은 없다.
FAILURE_RATE_WARN_THRESHOLD = 0.05


def split_sections(body: str) -> list[tuple[str, str]]:
    """본문을 장·절 경계로 자른다. 반환: [(소제목, 본문), ...].

    소제목이 없는 문서(PDF 추출본 등)는 전체를 한 절로 본다 — 이후 pack_chunks가
    문단 단위로 다시 나눈다.
    """
    lines = body.split("\n")
    sections: list[tuple[str, list[str]]] = []
    head, buf = "", []
    for line in lines:
        if HEADING_RE.match(line.strip()) and buf:
            sections.append((head, buf))
            head, buf = line.strip().lstrip("# ").strip()[:60], []
        elif HEADING_RE.match(line.strip()):
            head = line.strip().lstrip("# ").strip()[:60]
        else:
            buf.append(line)
    if buf or head:
        sections.append((head, buf))
    return [(h, "\n".join(b).strip()) for h, b in sections if "\n".join(b).strip()]


def pack_chunks(body: str, chunk_chars: int = MAX_BODY_CHARS,
                max_chunks: int = MAX_CHUNKS) -> list[tuple[str, str]]:
    """장·절을 chunk_chars 이하 청크로 묶는다. 한 절이 한도를 넘으면 문단(\\n\\n)으로 쪼갠다.

    반환: [(라벨, 본문), ...] — 라벨은 보고·디버깅용(첫 소제목 또는 '본문 n').
    max_chunks를 넘는 뒷부분은 버린다(비용 방어) — 호출부가 잘림 여부를 보고한다.
    """
    pieces: list[tuple[str, str]] = []
    for head, text in split_sections(body):
        if len(text) <= chunk_chars:
            pieces.append((head, text))
            continue
        cur: list[str] = []
        size = 0
        for para in text.split("\n\n"):
            # 문단 하나가 한도를 넘으면 그 문단만 잘라 담는다(줄 경계 유지 불가 시)
            while len(para) > chunk_chars:
                if cur:
                    pieces.append((head, "\n\n".join(cur)))
                    cur, size = [], 0
                pieces.append((head, para[:chunk_chars]))
                para = para[chunk_chars:]
            if size + len(para) + 2 > chunk_chars and cur:
                pieces.append((head, "\n\n".join(cur)))
                cur, size = [], 0
            cur.append(para)
            size += len(para) + 2
        if cur:
            pieces.append((head, "\n\n".join(cur)))

    # 인접한 짧은 절들을 한도까지 합쳐 호출 횟수를 줄인다
    merged: list[tuple[str, str]] = []
    for head, text in pieces:
        if merged and len(merged[-1][1]) + len(text) + 2 <= chunk_chars:
            prev_head, prev_text = merged[-1]
            merged[-1] = (prev_head or head, prev_text + "\n\n" + text)
        else:
            merged.append((head, text))

    # 합치고도 남은 아주 짧은 조각은 버린다 — 판단할 내용이 없는데 호출만 잡아먹는다
    kept = [(h, t) for h, t in merged if len(t) >= MIN_CHUNK_CHARS] or merged[:1]
    return [(h or f"본문 {i + 1}", t) for i, (h, t) in enumerate(kept[:max_chunks])]


def doc_chunks(body: str) -> list[tuple[str, str]]:
    """판별 단위. 장문만 나누고, 나머지는 문서 전체가 한 청크다."""
    return pack_chunks(body) if len(body) > LONG_DOC_CHARS else [("전체", body)]


def summary_gate_sql(sources: tuple[str, ...] | None = None) -> str:
    """판별 대상 문서의 summary_only 조건. SUMMARY_GATE_TIERS와 summary_gate_sources는
    요약뿐이어도 통과시킨다.

    티어 값은 코드 상수, 소스 id는 형식 검사(SOURCE_ID_RE)를 거친 값이라 SQL에 리터럴로
    박아도 안전하다 — 외부 입력이 섞이지 않는다.
    """
    if sources is None:
        sources = summary_gate_sources()
    tiers = ", ".join(f"'{t}'" for t in SUMMARY_GATE_TIERS)
    cond = f"COALESCE(summary_only, 0) = 0 OR tier IN ({tiers})"
    if sources:
        cond += f" OR source_id IN ({', '.join(f"'{x}'" for x in sources)})"
    return f"({cond})"


def build_doc_filters(exclude_sources: list[str] | None = None,
                      published_after: str | None = None,
                      tiers: list[str] | None = None,
                      collected_since: str | None = None,
                      collected_before: str | None = None,
                      only_summary: bool = False) -> tuple[str, list]:
    """계층 필터를 WHERE 절 조각과 파라미터로 만든다. 반환: (SQL 조각, 파라미터 목록).

    LIKE 패턴은 SQL 본문이 아니라 **파라미터로** 넘긴다 — 패턴의 '%'가 SQL 문자열에
    들어 있으면 psycopg가 자리표시자로 오인해 터진다(db.py의 % 리터럴 주의사항과 같은 이유).
    published_after는 published_at이 NULL인 문서를 **제외**한다 — 발행일을 모르는 문서를
    "하한 이후"라고 단정할 근거가 없다.

    collected_since / collected_before는 일일 실행의 2단계 처리가 쓰는 경계다. 같은 값을
    한쪽은 하한(>=)으로, 다른 쪽은 상한(<)으로 주면 두 단계가 문서를 겹치지 않게 나눠
    갖는다 — 중복 선정을 id 집합으로 걸러낼 필요가 없다.
    tiers는 T2~T5처럼 특정 티어만 처리할 때 쓴다(빈 목록은 필터 없음과 같다).
    only_summary는 소급 실행 전용 — summary_only=1 문서만 집는다(migrations/008 편입분).
    """
    clauses, params = [], []
    for pattern in exclude_sources or []:
        clauses.append("source_id NOT LIKE ?")
        params.append(pattern.replace("*", "%"))
    if published_after:
        clauses.append("published_at >= ?")
        params.append(published_after)
    if tiers:
        clauses.append(f"tier IN ({', '.join('?' for _ in tiers)})")
        params.extend(tiers)
    if collected_since:
        clauses.append("collected_at >= ?")
        params.append(collected_since)
    if collected_before:
        clauses.append("collected_at < ?")
        params.append(collected_before)
    if only_summary:
        # 소급 실행 전용 — 이미 처리된 전문 문서를 건드리지 않고 요약뿐인 문서만 집는다.
        clauses.append("COALESCE(summary_only, 0) = 1")
    return ("".join(f" AND {c}" for c in clauses), params)


def select_target_docs(conn, limit: int, exclude_sources: list[str] | None = None,
                       published_after: str | None = None, tiers: list[str] | None = None,
                       collected_since: str | None = None, collected_before: str | None = None,
                       only_summary: bool = False):
    """판별 대상: status='new'이면서 summary_gate_sql()을 통과한 문서(전문 문서 + T5
    요약분), **최신 수집분 우선** (collected_at 역순, 일반 실행).

    2026-09-09 오름차순 → 내림차순. 오름차순일 때 일일 상한 500칸이 관문 수집(2026-08-31)의
    arXiv 백로그로 전량 채워져, 그날 새로 들어온 T2~T4 문서가 백로그 12,000여 건 뒤에서
    3주 넘게 대기했다. 일일 실행은 "오늘 들어온 것을 오늘 처리한다"가 목적이고, 누적
    백로그는 enrich-backlog.yml(티어 라운드로빈 + 비용 상한)이 따로 담당한다.

    상한이 그날 유입보다 크면 남는 칸은 자연히 그 다음으로 새 문서부터 채워지므로,
    백로그도 최신 쪽부터 함께 줄어든다 — 처리 용량이 놀지 않는다.
    """
    where, params = build_doc_filters(exclude_sources, published_after, tiers,
                                      collected_since, collected_before, only_summary)
    return conn.execute(
        f"SELECT * FROM documents WHERE status='new' AND {summary_gate_sql()}"
        f"{where} ORDER BY collected_at DESC LIMIT ?",
        (*params, limit),
    ).fetchall()


def select_target_docs_round_robin(conn, limit: int, exclude_sources: list[str] | None = None,
                                   published_after: str | None = None,
                                   tiers: list[str] | None = None,
                                   collected_since: str | None = None,
                                   collected_before: str | None = None,
                                   only_summary: bool = False):
    """판별 대상을 티어별로 번갈아 뽑는다 (T1이 21,000건+로 압도적이라 순서대로면 다른
    티어가 굶는다). 윈도우 함수로 "티어 내 순번"을 매겨 그 순번 우선으로 정렬한다
    — collected_at 순은 티어 내에서 유지된다. (O(n log n) — SQLite 3.25+·PostgreSQL 공통)

    계층 필터는 순번을 매기기 **전에** 적용한다 — 걸러낸 뒤의 집합 안에서 라운드로빈이
    돌아야 제외된 소스가 순번만 잡아먹고 사라지는 일이 없다.
    """
    where, params = build_doc_filters(exclude_sources, published_after, tiers,
                                      collected_since, collected_before, only_summary)
    return conn.execute(
        f"""SELECT * FROM (
             SELECT *, ROW_NUMBER() OVER (PARTITION BY tier ORDER BY collected_at) AS _rank
             FROM documents
             WHERE status = 'new' AND {summary_gate_sql()}{where}
           ) ranked
           ORDER BY _rank, tier
           LIMIT ?""",
        (*params, limit),
    ).fetchall()


def latest_collection_cutoff(conn) -> str | None:
    """이번(가장 최근) 수집 실행이 시작된 시각. 일일 실행에서 "이번에 들어온 문서"와
    "그 전부터 쌓여 있던 백로그"를 가르는 경계다.

    collection_runs.started_at을 쓰는 이유: 달력일로 자르면 Actions(UTC 21시 = KST 익일
    06시)에서 실행일과 collected_at의 날짜가 어긋난다. 수집 실행 시작 시각을 쓰면 그
    실행이 집어넣은 문서만 정확히 "신규"가 된다.

    수집 이력이 없으면(첫 실행·테스트) None을 돌려주고, 호출부는 2단계를 나누지 않고
    최신 순 한 덩어리로 처리한다.
    """
    row = conn.execute(
        "SELECT started_at FROM collection_runs ORDER BY started_at DESC LIMIT 1").fetchone()
    if not row or not row["started_at"]:
        return None
    started = row["started_at"]
    if isinstance(started, str):
        return started[:19]
    return started.strftime("%Y-%m-%d %H:%M:%S")


def process_batch(conn, docs, model, cost, stats, *, dry_run: bool) -> None:
    """선정된 문서를 순서대로 처리. 비용 상한에 닿으면 남은 문서는 건드리지 않는다."""
    for d in docs:
        if not dry_run and cost.cap_reached():
            cost.cap_hit = True
            print(f"  중단 — 비용 상한(${cost.cap}) 도달, 실측 ${cost.cost:.4f} "
                  f"(이 문서부터 처리하지 않음, 다음 실행에서 재시도)")
            return
        if dry_run:
            print_dry_run(d, d["body"] or "")
            cost.tier_counts[d["tier"]] = cost.tier_counts.get(d["tier"], 0) + 1
        else:
            process_doc(conn, d, model, cost, stats)


def check_relevance(title: str, body: str, model: str, cost: CostState | None = None) -> bool:
    """A1 게이트: '일·조직·인재·AI와 일' 주제 판별. 첫 토큰 IRRELEVANT면 무관."""
    template = GATE_PROMPT_PATH.read_text(encoding="utf-8")
    prompt = (template
              .replace("{title}", title or "(무제)")
              .replace("{body}", body[:GATE_BODY_CHARS]))
    reply = call_model(prompt, model, GATE_MAX_TOKENS)
    if cost is not None:
        cost.record(model, reply)
    return not reply.text.strip().upper().startswith("IRRELEVANT")


@dataclass
class RunStats:
    passed: int = 0
    gated: int = 0
    locked: int = 0
    gate_errors: int = 0
    processed_count: int = 0  # 락 선점에 성공해 실제로 처리를 시도한 문서 수 (실패율의 분모)
    failed_docs: list[str] = field(default_factory=list)


def process_doc(conn, d, model: str, cost: CostState, stats: RunStats) -> None:
    """문서 1건: 락 선점 → 청크별 판별(관련 청크가 나오면 멈춤) → enriched / rejected.

    판별 호출이 실패하거나 DB 쓰기가 실패하면 판정을 남기지 않고 락을 풀어 다음 실행이 다시
    집게 한다(failed_docs — 실패율이 exit code를 정한다).
    """
    chunks = doc_chunks(d["body"] or "")
    cost.tier_counts[d["tier"]] = cost.tier_counts.get(d["tier"], 0) + 1

    if not claim_document_for_enrich(conn, d["id"]):
        stats.locked += 1
        print(f"  건너뜀 [{d['tier']}] {d['title'][:50]} — 다른 프로세스가 처리 중")
        return
    stats.processed_count += 1

    relevant_at = None
    try:
        for i, (label, text) in enumerate(chunks):
            try:
                relevant = check_relevance(d["title"], text, model, cost)
            except Exception:
                stats.gate_errors += 1
                raise
            if relevant:
                relevant_at = i
                break
        if relevant_at is None:
            conn.execute(
                "UPDATE documents SET status='rejected', enrich_locked_at=NULL WHERE id=?",
                (d["id"],))
            conn.execute(
                "INSERT INTO tags (document_id, axis, value) VALUES (?, 'gate', 'off_topic') "
                "ON CONFLICT DO NOTHING",
                (d["id"],))
        else:
            conn.execute(
                "UPDATE documents SET status='enriched', enrich_locked_at=NULL WHERE id=?",
                (d["id"],))
        conn.commit()
    except Exception as e:  # noqa: BLE001 — 개별 문서 실패가 배치를 중단시키지 않도록
        try:
            conn.rollback()
        except Exception:  # noqa: BLE001
            pass
        release_enrich_lock(conn, d["id"])  # 실패 → 잠금 해제, 다음 실행이 재시도
        stats.failed_docs.append(d["id"])
        print(f"  실패 [{d['id']}]: {type(e).__name__}: {e} — 판정 보류, 다음 실행에서 재시도")
        return

    if relevant_at is None:
        stats.gated += 1
        print(f"  무관 [{d['tier']}] {d['title'][:50]} → rejected (관련성 게이트)")
        return
    stats.passed += 1
    split_note = (f" (분할 {len(chunks)}청크 중 {relevant_at + 1}번째에서 통과)"
                  if len(chunks) > 1 else "")
    summary_note = " ※요약뿐" if (d["summary_only"] or 0) else ""
    print(f"  통과 [{d['tier']}] {d['title'][:50]} → enriched{split_note}{summary_note}")


def print_dry_run(d, body: str) -> None:
    chunks = doc_chunks(body)
    covered = sum(len(t) for _, t in chunks)
    note = ""
    if len(chunks) > 1:
        pct = covered * 100 // max(len(body), 1)
        note = (f"  → 분할 {len(chunks)}청크, 처리 {covered:,}자/{len(body):,}자({pct}%)"
                + (f"  ※ MAX_CHUNKS({MAX_CHUNKS}) 상한으로 뒷부분 제외"
                   if len(chunks) >= MAX_CHUNKS else ""))
    print(f"  DRY  [{d['tier']}] {(d['title'] or '')[:60]}  "
          f"(본문 {len(body):,}자, 판별 최대 {len(chunks)}회){note}")
    for label, text in chunks[:MAX_CHUNKS] if len(chunks) > 1 else []:
        print(f"         · {label[:44]:<44} {len(text):,}자")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=None,
                   help="처리할 문서 수. 미지정 시: 일반 실행은 settings의 enrich_daily_limit"
                        f"(기본 {DEFAULT_DAILY_LIMIT}), --backlog는 무제한(비용 상한이 경계)")
    p.add_argument("--backlog", action="store_true",
                   help="티어별 라운드로빈으로 선정 + 비용 상한 적용(백로그 처리용)")
    p.add_argument("--cost-cap", type=float, default=None,
                   help="실측 비용(USD)이 이 값에 닿으면 새 문서를 더 집지 않고 중단")
    p.add_argument("--exclude-sources",
                   help="제외할 source_id 패턴(쉼표 구분, '*' 와일드카드). 예: 'arxiv-*'")
    p.add_argument("--published-after",
                   help="발행일 하한(YYYY-MM-DD). 이 날짜 이후 발행분만 처리 "
                        "(published_at이 비어 있는 문서는 제외된다)")
    p.add_argument("--tiers",
                   help=f"처리할 티어만 지정(쉼표 구분). 예: 'T2,T3,T4,T5'. "
                        f"허용값 {'/'.join(TIER_ORDER)}")
    p.add_argument("--only-summary", action="store_true",
                   help=f"summary_only=1 문서만 처리 (소급 실행 전용). 판별 대상이 되는 티어는 "
                        f"{'/'.join(SUMMARY_GATE_TIERS)} 뿐이므로 사실상 그 티어의 요약분이다")
    p.add_argument("--dry-run", action="store_true",
                   help="API 호출 없이 대상 문서와 분할 계획만 출력")
    p.add_argument("--doc-id", help="특정 문서 1건만 처리 (장문 분할 점검용)")
    p.add_argument("--count-remaining", action="store_true",
                   help="현재 필터 기준 남은 대상 문서 수만 출력하고 종료 (연쇄 실행 판단용)")
    args = p.parse_args(argv)

    exclude_sources = [s.strip() for s in (args.exclude_sources or "").split(",") if s.strip()]
    tiers = [t.strip().upper() for t in (args.tiers or "").split(",") if t.strip()]
    unknown = [t for t in tiers if t not in TIER_ORDER]
    if unknown:
        # 오타를 그냥 두면 0건을 집고 "잔여 없음"으로 오인하기 쉽다 — 즉시 중단.
        print(f"오류: 알 수 없는 티어 {', '.join(unknown)} "
              f"(허용값: {', '.join(TIER_ORDER)})")
        return 2
    if args.published_after and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", args.published_after):
        # 형식이 틀리면 조용히 0건을 집어 "백로그가 비었다"로 오인하기 쉽다 — 즉시 중단.
        print(f"오류: --published-after 는 YYYY-MM-DD 형식이어야 한다 (받은 값: "
              f"{args.published_after})")
        return 2

    if args.count_remaining:
        # 숫자만 출력한다 — 워크플로가 그대로 변수에 담는다(같은 필터 로직을 재사용해
        # 연쇄 실행이 '보류 계층'을 잔여로 오인하고 헛도는 것을 막는다).
        where, params = build_doc_filters(exclude_sources, args.published_after, tiers,
                                          only_summary=args.only_summary)
        conn = connect()
        print(conn.execute(
            "SELECT COUNT(*) c FROM documents "
            f"WHERE status='new' AND {summary_gate_sql()}{where}",
            tuple(params)).fetchone()["c"])
        conn.close()
        return 0

    from handoff import ensure_active
    ensure_active("관련성 판별")
    settings = yaml.safe_load(SETTINGS_PATH.read_text(encoding="utf-8")) or {}
    if settings.get("enrich_enabled", True) is False and not args.dry_run:
        print("enrich_enabled: false — 판별·카드 비활성화 상태(크레딧 대기). "
              "config/settings.yaml에서 true로 변경 시 재개. 정상 종료.")
        return 0
    model = settings.get("enrich_model", "claude-haiku-4-5-20251001")

    if args.cost_cap is not None and not args.dry_run and _price_for(model) is None:
        print(f"오류: 모델 `{model}`의 단가를 모른다 — --cost-cap을 신뢰할 수 없어 중단한다. "
              f"src/enrich/llm.py의 MODEL_PRICING에 단가를 추가할 것.")
        return 2

    conn = connect()
    migrate(conn)

    cost = CostState(cap=args.cost_cap)
    stats = RunStats()

    if args.doc_id:
        docs = conn.execute("SELECT * FROM documents WHERE id = ?", (args.doc_id,)).fetchall()
        print(f"대상 문서 {len(docs)}건 (model={model}, dry_run={args.dry_run}) — --doc-id")
        for d in docs:
            if args.dry_run:
                print_dry_run(d, d["body"] or "")
            else:
                process_doc(conn, d, model, cost, stats)
    elif args.backlog:
        base_limit = args.limit  # None = 무제한(비용 상한만이 경계)
        mode = f"limit={base_limit}" if base_limit is not None else "limit=무제한(비용 상한만)"
        print(f"백로그 모드 — 티어별 라운드로빈, {mode}"
              + (f", cost_cap=${args.cost_cap}" if args.cost_cap is not None else "")
              + (f", 제외 소스={','.join(exclude_sources)}" if exclude_sources else "")
              + (f", 발행일 하한={args.published_after}" if args.published_after else "")
              + (f", 티어={','.join(tiers)}" if tiers else "")
              + (", 요약뿐 문서만(--only-summary)" if args.only_summary else ""))
        processed = 0
        while True:
            remaining = None if base_limit is None else base_limit - processed
            if remaining is not None and remaining <= 0:
                break
            batch_limit = BACKLOG_BATCH_SIZE if remaining is None else min(BACKLOG_BATCH_SIZE, remaining)
            docs = select_target_docs_round_robin(conn, batch_limit, exclude_sources,
                                                  args.published_after, tiers,
                                                  only_summary=args.only_summary)
            if not docs:
                break
            judged_before = stats.passed + stats.gated
            process_batch(conn, docs, model, cost, stats, dry_run=args.dry_run)
            processed += len(docs)
            if cost.cap_hit or args.dry_run:
                break
            if stats.passed + stats.gated == judged_before:
                # 한 배치에서 판정이 하나도 안 났다(API 키 없음·접속 불가·크레딧 소진, 남은 게 잠긴 문서뿐 등).
                # 실패·잠금 문서는 new로 남아 다음 배치에 그대로 다시 잡히므로, 멈추지 않으면 같은 실패를
                # 끝없이 반복한다(2026-11-12 실제 발생 — 85건 배치를 5바퀴 돌았다).
                print("  이번 배치에서 판정 0건 — 백로그 처리를 멈춘다(문서는 new로 남아 다음 실행에서 재시도)")
                break
        print(f"백로그 처리 {processed}건 시도 (티어 분포: "
              f"{', '.join(f'{t} {cost.tier_counts.get(t, 0)}' for t in TIER_ORDER if cost.tier_counts.get(t))})")
    else:
        base_limit = args.limit if args.limit is not None else settings.get(
            "enrich_daily_limit", DEFAULT_DAILY_LIMIT)
        cutoff = latest_collection_cutoff(conn)
        common = dict(exclude_sources=exclude_sources, published_after=args.published_after,
                      tiers=tiers, only_summary=args.only_summary)
        filter_note = ((f", 제외 소스={','.join(exclude_sources)}" if exclude_sources else "")
                       + (f", 발행일 하한={args.published_after}" if args.published_after else "")
                       + (f", 티어={','.join(tiers)}" if tiers else "")
                       + (", 요약뿐 문서만(--only-summary)" if args.only_summary else ""))
        print(f"일반 실행 (model={model}, dry_run={args.dry_run}, limit={base_limit}) "
              f"— summary_only는 {'/'.join(SUMMARY_GATE_TIERS + summary_gate_sources())}만 포함{filter_note}")

        # 1단계: 이번 수집분을 먼저 비운다 (최신 순).
        fresh = select_target_docs(conn, base_limit, collected_since=cutoff, **common)
        print(f"  ① 신규 수집분 {len(fresh)}건"
              + (f" (수집 실행 시작 {cutoff} 이후)" if cutoff else " (수집 이력 없음 — 전체 최신 순)"))
        process_batch(conn, fresh, model, cost, stats, dry_run=args.dry_run)

        # 2단계: 남은 칸으로 그 이전의 백로그를 처리한다. 여기서는 티어별 라운드로빈을
        # 쓴다 — 백로그는 T1(arXiv)이 90%대라 최신 순으로 집으면 다른 티어가 다시 굶는다.
        remaining = base_limit - len(fresh)
        if cutoff and remaining > 0 and not cost.cap_hit:
            print(f"  ② 백로그 {remaining}건까지 (티어별 라운드로빈, 수집 실행 시작 이전분)")
            done = 0
            while done < remaining and not cost.cap_hit:
                batch = select_target_docs_round_robin(
                    conn, min(BACKLOG_BATCH_SIZE, remaining - done),
                    collected_before=cutoff, **common)
                if not batch:
                    break
                process_batch(conn, batch, model, cost, stats, dry_run=args.dry_run)
                done += len(batch)
                if args.dry_run:
                    break  # dry-run은 status를 바꾸지 않아 같은 문서가 다시 잡힌다
            print(f"  ② 백로그 {done}건 시도")
        elif remaining > 0 and not cutoff:
            print("  ② 건너뜀 — 수집 이력이 없어 신규/백로그 경계를 정할 수 없다")

        # 문서 카드 — 같은 실행에서 판별 다음에 (src/enrich/doc_cards.py). 비용은 같은
        # CostState에 쌓여 아래 총계에 들어간다. 카드 실패는 판별 결과(exit code)를 바꾸지 않는다
        # — 실패한 문서는 카드가 없으니 다음 실행에서 다시 대상이 된다.
        if not args.dry_run:
            from enrich import doc_cards
            try:
                doc_cards.run(conn, settings, cost)
            except Exception as e:  # noqa: BLE001
                print(f"[카드] 단계 오류 — 건너뜀: {type(e).__name__}: {e}")

    if not args.dry_run:
        print(f"\n판별 통과 {stats.passed}건, 관련성 게이트 제외 {stats.gated}건, "
              f"동시성 잠금으로 건너뜀 {stats.locked}건, 게이트 오류 {stats.gate_errors}건, "
              f"처리 실패 {len(stats.failed_docs)}건.")
        print(f"API 호출 {cost.calls}회 (입력 {cost.input_tokens:,} / 출력 {cost.output_tokens:,} 토큰) "
              f"— 실측 비용 ${cost.cost:.4f}"
              + (f" (상한 ${args.cost_cap} 도달로 중단)" if cost.cap_hit else ""))
        if stats.failed_docs:
            failure_rate = (len(stats.failed_docs) / stats.processed_count
                            if stats.processed_count else 1.0)
            print(f"[실패] 기술적 처리 실패(판별 API·DB 쓰기) {len(stats.failed_docs)}건 "
                  f"— doc id: {', '.join(stats.failed_docs)}")
            print("정상 처리분은 반영됨. 실패 문서는 잠금 해제됨 — 재실행 시 자동 재시도.")
            if failure_rate < FAILURE_RATE_WARN_THRESHOLD:
                print(f"[경고] 실패율 {failure_rate:.1%} — 허용 기준"
                      f"({FAILURE_RATE_WARN_THRESHOLD:.0%}) 미만이라 정상 종료 처리(exit 0).")
                return 0
            print(f"[오류] 실패율 {failure_rate:.1%} — 허용 기준"
                  f"({FAILURE_RATE_WARN_THRESHOLD:.0%}) 이상이라 exit 1.")
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

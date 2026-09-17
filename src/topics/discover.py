"""토픽 발굴 — 최근 2주 claim을 의미 군집으로 묶고 후보 주제를 뽑는다 (기획서 8장 ③).

파이프라인 ③단계. 산출물은 `content/topics/YYYY-WW.md` 와 `--json` 페이로드다.
사람이 그중 하나를 고르면 ④ 증거 수집(/draft)으로 넘어간다.

계산 순서
  ① 창(window) 확정 — **published_at 기준** 최근 14일 / 직전 28일
  ② 창 안의 claim k-최근접 그래프를 pgvector로 한 번에 만든다
  ③ 리더 기준 탐욕 군집화 (사슬 연결 방지 — leader_cluster 주석)
  ④ 묶음마다 급증도(직전 28일 대비 — 창 전체 대비 비중 비. surge_ratio 주석)
  ⑤ 교차 가능성 필터 — 독립 출처 4곳+ / 상반 stance 실존 / 연결 이론 카드 2장+
     (+ T5 단독 근거 금지에서 따라오는 T1·T2 claim 2건+ — MIN_T12_CLAIMS 주석)
  ⑥ 미개척도 — 주제 축별 발행 이력으로 가중
  ⑦ 상위 3건을 표로

**시간 창은 반드시 published_at 기준이며 collected_at을 쓰지 않는다.**
수집 시각으로 자르면 소급 수집(arXiv 백필·브라우저 라운드·백로그 소진)이 들어온 날
2년 전 논문 수백 건이 "이번 주 급증"으로 잡힌다. 실제로 이 저장소는 관문 수집(2026-08-31)
하루에 2만 건 이상을 집어넣었고, 그날의 collected_at 기준 신호는 전부 허구다.
발행일 기준이면 소급분은 자기가 실제로 발행된 과거 창에 들어가 신호를 오염시키지 않는다.

PostgreSQL 전용 — 군집화·중심 벡터·이론 카드 연결이 모두 pgvector 연산이다.
SQLite 모드에서는 실패가 아니라 "건너뜀"으로 정상 종료한다 (embed.py와 같은 규약).

사용:
  python src/topics/discover.py                 # content/topics/YYYY-WW.md 생성
  python src/topics/discover.py --json          # 분석 페이로드만 stdout으로 (/topics 2단계용)
  python src/topics/discover.py --as-of 2026-09-01 --top 5
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db import ROOT, connect, migrate  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TOPICS_DIR = ROOT / "content" / "topics"
PUBLISHED_DIR = ROOT / "content" / "published"

# --- 시간 창 -------------------------------------------------------------- #
WINDOW_DAYS = 14      # "최근 2주" — 신호를 재는 창
BASELINE_DAYS = 28    # 급증도의 비교 기준이 되는 직전 창

# --- 군집화 --------------------------------------------------------------- #
# 군집화에 쓰는 차원. claims.embedding은 halfvec(1536)이고 여기서는 앞 CLUSTER_DIMS 차원만
# subvector로 잘라 쓴다. OpenAI text-embedding-3-small의 절단은 재정규화만 하면 dimensions
# 파라미터와 동등하고, 코사인(<=>)은 배율 불변이라 재정규화도 필요 없다
# (docs/phase2-plan.md 수요 트리거 목록의 차원 축소 실측 근거와 같은 성질).
# 군집화는 "비슷한 것끼리 묶는" 거친 작업이라 256차원으로 충분하고, 3,700건 규모의
# 전량 비교(k-NN 그래프)를 10초대로 끝내려면 차원을 줄이는 편이 실용적이다.
# 증거 수집(hybrid_search)은 이 축약을 쓰지 않는다 — 그쪽은 1536 전량 그대로다.
CLUSTER_DIMS = 256
KNN_K = 40            # claim 하나가 가질 수 있는 이웃 상한 = 묶음 크기 상한(+리더 1)
SIM_THRESHOLD = 0.62  # 이 코사인 유사도 이상만 같은 주제로 본다
MIN_CLUSTER_CLAIMS = 5

# --- 교차 가능성 필터 (③) -------------------------------------------------- #
MIN_SOURCES = 4          # 독립 출처 4곳 이상 (증거 규칙 3곳보다 한 칸 높게 — 후보 단계이므로)
MIN_THEORY_CARDS = 2     # 연결되는 이론 카드 2장 이상
# T1·T2 claim 하한. 기획서 4.1의 철칙 "T5는 신호 감지 전용이며 논지의 근거로 단독 사용 금지"와
# /draft ② 증거 수집의 강제 조건("T1·T2급 2건+")을 후보 단계로 앞당긴 것이다.
# 이 조건이 없으면 최근 2주 claim의 3분의 2를 차지하는 T5 뉴스만으로 "출처 4곳"이 채워져,
# 벤더·제품 뉴스 묶음이 후보 1~5위를 독식하고 ④ 증거 수집에서 전부 되튕긴다(2026-09-10 실측).
MIN_T12_CLAIMS = 2
T12_TIERS = ("T1", "T2")
THEORY_SIM_THRESHOLD = 0.42   # 이론 카드 claim은 추상 명제라 뉴스 claim과의 유사도가 낮게 나온다
THEORY_CARD_LIMIT = 5    # 보고서에 적는 이론 카드 수 상한
OPPOSED_STANCES = ("optimistic", "cautious")  # "상반 stance" 의 정의 (기획서 6.3)

# --- 주제 축 매핑 ---------------------------------------------------------- #
# 축 목록은 별도 설정 파일이 아니라 **이론 카드의 field 값**에서 나온다
# (load_theories.py가 tags(axis='field')로 색인한다). 카드가 늘거나 축이 신설되면
# 코드를 고치지 않아도 따라온다. 2026-09-10 실측 10개 축(reviewed 72장)이며,
# 기획서 13-3의 "9개 축"은 노사관계·ER 카드 추가 전 기록이라 한 칸 적다.
AXIS_TAG = "field"
AXIS_SIM_THRESHOLD = 0.30   # 이보다 낮으면 축 판정을 포기한다 ("축 미상")

TOP_N = 3
CLAIM_SAMPLE = 6   # 후보마다 보고서에 남기는 대표 claim 수


# --------------------------------------------------------------------------- #
# 순수 로직 (DB 불필요 — 테스트 대상)                                          #
# --------------------------------------------------------------------------- #
class Window:
    """분석 시간 창. 모든 경계는 published_at(DATE) 기준이고 끝은 열린 구간이다."""

    def __init__(self, recent_start: date, recent_end: date,
                 base_start: date, base_end: date,
                 window_days: int, baseline_days: int):
        self.recent_start = recent_start
        self.recent_end = recent_end      # 열린 끝 (미포함)
        self.base_start = base_start
        self.base_end = base_end          # 열린 끝 (= recent_start)
        self.window_days = window_days
        self.baseline_days = baseline_days

    def as_dict(self) -> dict:
        return {
            "recent": [self.recent_start.isoformat(), self.recent_end.isoformat()],
            "baseline": [self.base_start.isoformat(), self.base_end.isoformat()],
            "window_days": self.window_days,
            "baseline_days": self.baseline_days,
            "기준": "documents.published_at (수집 시각 아님)",
        }


def resolve_window(as_of: date, window_days: int = WINDOW_DAYS,
                   baseline_days: int = BASELINE_DAYS) -> Window:
    """as_of 를 포함하는 최근 window_days 일과, 그 직전 baseline_days 일을 만든다."""
    recent_start = as_of - timedelta(days=window_days - 1)
    recent_end = as_of + timedelta(days=1)          # 열린 끝 — as_of 당일까지 포함
    base_end = recent_start
    base_start = base_end - timedelta(days=baseline_days)
    return Window(recent_start, recent_end, base_start, base_end, window_days, baseline_days)


def leader_cluster(claim_ids: list[str], edges, min_size: int = 1) -> list[list[str]]:
    """이웃 그래프에서 리더를 잡고 그 이웃을 묶는 탐욕 군집화. 반환: 묶음별 claim id 목록.

    연결요소(connected components)를 쓰지 않는 이유: 임계를 넘는 간선만 남겨도 사슬로
    이어지면 묶음의 지름에 상한이 없다 — A-B-C-D-E까지 통째로 한 덩어리가 되고 양 끝은
    서로 아무 관계가 없다(chaining). 리더 기준이면 구성원이 전원 **리더와 직접** 임계
    이상이라 묶음이 리더에서 1홉 안으로 제한된다. 구성원끼리는 최대 2홉이므로 서로
    임계 이상이라는 보장까지는 없지만, "이 묶음은 리더 주장 주변의 것들"이라고
    한 문장으로 설명되는 성질이 생긴다 — 보고서의 주제 한 줄이 여기서 나온다.

    이웃이 많은 claim부터 리더로 삼고(동률은 id 오름차순), 이미 다른 묶음에 들어간
    claim은 건너뛴다. 입력 순서가 같으면 결과도 같다(결정적).

    edges 는 (a, b, sim) 3튜플의 순회 가능 객체. 코사인은 대칭이므로 방향은 무시하고
    양방향 이웃으로 취급한다.
    """
    neighbors: dict[str, set[str]] = defaultdict(set)
    known = set(claim_ids)
    for a, b, _sim in edges:
        if a in known and b in known and a != b:
            neighbors[a].add(b)
            neighbors[b].add(a)

    assigned: set[str] = set()
    clusters: list[list[str]] = []
    for leader in sorted(claim_ids, key=lambda c: (-len(neighbors[c]), c)):
        if leader in assigned:
            continue
        members = [leader] + sorted(n for n in neighbors[leader] if n not in assigned)
        assigned.update(members)
        if len(members) >= min_size:
            clusters.append(members)
    return clusters


def surge_ratio(recent_n: int, prior_n: int, recent_total: int, prior_total: int) -> float:
    """급증도 = 최근 창에서 이 주제가 차지한 비중 / 직전 창에서 차지한 비중.

    **건수 비가 아니라 비중 비를 쓰는 이유**: 이 저장소의 일별 claim 유입량은 아직
    정상 상태가 아니다. T5(뉴스) 수집이 2026-08-31에 시작돼 그 전후로 하루 60건대 →
    300건대로 뛰었다(실측). 건수 일평균으로 재면 T5가 많이 다루는 주제는 전부 5배쯤
    부풀고, 그 배수는 "주제가 뜨거워졌다"가 아니라 "우리가 뉴스를 긁기 시작했다"는
    뜻이다. 창 전체 대비 비중으로 재면 그 공통 요인이 약분된다.

    직전 창이 0이면 나눌 수 없으므로 "0.5건이 있었다"고 보고 계산한다 — 완전 신규
    주제가 무한대로 튀어 순위를 독식하지 않게 하는 하한이다.
    창 길이 차이(14일 vs 28일)는 비중을 쓰는 순간 자동으로 상쇄된다.
    """
    if not recent_total or not prior_total:
        return 0.0
    recent_share = recent_n / recent_total
    prior_share = max(prior_n, 0.5) / prior_total
    return recent_share / prior_share


def daily_rate_ratio(recent_n: int, prior_n: int, window_days: int, baseline_days: int) -> float:
    """참고용 원시 배수 — 일평균 건수 비. 보고서에 함께 적어 비중 비와 대조할 수 있게 한다."""
    prior_rate = max(prior_n, 0.5) / baseline_days
    return (recent_n / window_days) / prior_rate


def unexplored_weight(published_count: int | None) -> float:
    """미개척도 가중치 — 발행 이력이 없는 주제 축을 우대한다.

    0편이면 1.0, 1편이면 0.5, 2편이면 0.33… 재료가 쌓였는데 아직 안 쓴 축이 위로 온다.
    축을 판정하지 못한 묶음(None)은 벌점도 가점도 주지 않는다(1.0).
    """
    if published_count is None:
        return 1.0
    return 1.0 / (1.0 + published_count)


def cosine(u: list[float], v: list[float]) -> float:
    dot = sum(a * b for a, b in zip(u, v))
    nu = math.sqrt(sum(a * a for a in u))
    nv = math.sqrt(sum(b * b for b in v))
    if nu == 0 or nv == 0:
        return 0.0
    return dot / (nu * nv)


def parse_vector_literal(text: str) -> list[float]:
    """pgvector 텍스트 표기('[0.1,-0.2,...]')를 float 목록으로."""
    return [float(x) for x in text.strip().strip("[]").split(",") if x.strip()]


def to_vector_literal(vec) -> str:
    return "[" + ",".join(repr(float(x)) for x in vec) + "]"


def qualify(claims: list[dict], theory_cards: list[dict], *,
            min_sources: int = MIN_SOURCES,
            min_theory_cards: int = MIN_THEORY_CARDS,
            min_t12: int = MIN_T12_CLAIMS) -> tuple[bool, list[str], dict]:
    """교차 가능성 필터. 반환: (자격 여부, 미달 사유 목록, 집계).

    **증거로 쓸 수 있는 claim만 센다** — from_summary=1(T5 요약뿐 문서에서 나온 claim)은
    토픽 신호에는 포함되지만 증거로는 쓸 수 없으므로(migrations/008) 여기서 빠진다.
    이 구분이 없으면 뉴스 요약만으로 "출처 4곳"이 채워져, /draft 증거 수집 단계에서
    곧바로 증거 부족으로 되튕기는 후보가 올라온다.
    """
    evidence = [c for c in claims if not c.get("from_summary")]
    sources = sorted({c["source_id"] for c in evidence})
    stances = {c["stance"] for c in evidence if c.get("stance")}
    stats = {
        "claims_total": len(claims),
        "claims_evidence": len(evidence),
        "claims_from_summary": len(claims) - len(evidence),
        "sources": sources,
        "source_count": len(sources),
        "documents": len({c["document_id"] for c in claims}),
        "stance_counts": {s: sum(1 for c in evidence if c.get("stance") == s)
                          for s in sorted(stances)},
        "theory_card_count": len(theory_cards),
        "t12_claims": sum(1 for c in evidence if c["tier"] in T12_TIERS),
    }
    reasons = []
    if len(sources) < min_sources:
        reasons.append(f"독립 출처 {len(sources)}곳 (기준 {min_sources}곳)")
    missing = [s for s in OPPOSED_STANCES if stats["stance_counts"].get(s, 0) == 0]
    if missing:
        reasons.append(f"상반 stance 없음 ({'·'.join(missing)} 0건)")
    if len(theory_cards) < min_theory_cards:
        reasons.append(f"연결 이론 카드 {len(theory_cards)}장 (기준 {min_theory_cards}장)")
    if stats["t12_claims"] < min_t12:
        reasons.append(f"T1·T2 claim {stats['t12_claims']}건 (기준 {min_t12}건) "
                       f"— T5 단독 근거 금지(기획서 4.1)")
    return (not reasons), reasons, stats


def iso_week_label(d: date) -> str:
    """보고서 파일명에 쓰는 ISO 주차 라벨 (YYYY-WW)."""
    iso = d.isocalendar()
    return f"{iso[0]}-{iso[1]:02d}"


# --------------------------------------------------------------------------- #
# DB 질의 (PostgreSQL + pgvector 전용)                                         #
# --------------------------------------------------------------------------- #
def _sub(col: str, dims: int) -> str:
    """halfvec(1536) 컬럼을 dims 차원 vector 로 자르는 SQL 조각."""
    return f"subvector({col}::vector, 1, {int(dims)})"


def _no_nan(sim: str) -> str:
    """NaN 유사도를 배제하는 조건 — 유사도 임계 비교에는 반드시 함께 건다.

    pgvector에서 영벡터와의 코사인 거리는 NaN이고 `1 - NaN`도 NaN인데,
    **PostgreSQL은 NaN을 모든 수보다 크게 취급한다.** 그래서 `sim >= threshold` 필터를
    NaN이 그대로 통과해 엉뚱한 간선·집계가 생긴다
    (`SELECT (1 - ('[0,0,0]'::vector <=> '[1,0,0]'::vector)) >= 0.9` 이 실제로 true다).
    임베딩 1536차원 전체로는 0이 아니어도 `_sub`로 앞 dims 차원만 자르면 영벡터가 될 수
    있으므로 이 저장소에서도 실제로 발생할 수 있는 조건이다.
    PostgreSQL에서 NaN = NaN 은 true라 `<> 'NaN'` 으로 NaN만 정확히 걸러진다.
    """
    return f"({sim}) <> 'NaN'::float8"


def fetch_window_claims(conn, w: Window) -> list[dict]:
    """최근 창의 claim + 문서 메타. 임베딩이 없는 claim은 군집화할 수 없어 제외한다."""
    rows = conn.execute(
        """SELECT cl.id, cl.document_id, cl.claim_text, cl.stance, cl.evidence_type,
                  cl.metric, COALESCE(cl.from_summary, 0) AS from_summary,
                  d.source_id, d.tier, d.title AS document_title, d.url, d.published_at
           FROM claims cl JOIN documents d ON d.id = cl.document_id
           WHERE d.published_at >= ? AND d.published_at < ?
             AND cl.embedding IS NOT NULL
           ORDER BY cl.id""",
        (w.recent_start.isoformat(), w.recent_end.isoformat()),
    ).fetchall()
    return [dict(r) for r in rows]


def window_totals(conn, w: Window) -> tuple[int, int]:
    """최근 창 / 직전 창의 전체 claim 수. 급증도를 비중 비로 재기 위한 분모다."""
    row = conn.execute(
        """SELECT SUM(CASE WHEN d.published_at >= ? THEN 1 ELSE 0 END) AS recent_total,
                  SUM(CASE WHEN d.published_at < ? THEN 1 ELSE 0 END) AS prior_total
           FROM claims cl JOIN documents d ON d.id = cl.document_id
           WHERE d.published_at >= ? AND d.published_at < ? AND cl.embedding IS NOT NULL""",
        (w.recent_start.isoformat(), w.recent_start.isoformat(),
         w.base_start.isoformat(), w.recent_end.isoformat()),
    ).fetchone()
    return int(row["recent_total"] or 0), int(row["prior_total"] or 0)


def knn_edges(conn, w: Window, *, dims: int = CLUSTER_DIMS, k: int = KNN_K,
              threshold: float = SIM_THRESHOLD) -> list[tuple[str, str, float]]:
    """창 안 claim 사이의 k-최근접 이웃 간선을 한 번의 질의로 만든다.

    CTE로 창을 먼저 좁히므로 HNSW 인덱스는 쓰이지 않고 창 안에서 전량 비교가 된다.
    그래서 차원을 CLUSTER_DIMS로 줄인다 — 3,700건 규모에서 10초대다.
    """
    sub = _sub("cl.embedding", dims)
    sim = "1 - (a.v <=> b.v)"
    no_nan = _no_nan(sim)
    rows = conn.execute(
        f"""WITH w AS (
              SELECT cl.id, {sub} AS v
              FROM claims cl JOIN documents d ON d.id = cl.document_id
              WHERE d.published_at >= ? AND d.published_at < ?
                AND cl.embedding IS NOT NULL
            )
            SELECT a.id AS src, b.id AS dst, {sim} AS sim
            FROM w a
            JOIN LATERAL (
              SELECT b2.id, b2.v FROM w b2 WHERE b2.id <> a.id
              ORDER BY b2.v <=> a.v LIMIT {int(k)}
            ) b ON TRUE
            WHERE {no_nan} AND {sim} >= ?""",
        (w.recent_start.isoformat(), w.recent_end.isoformat(), threshold),
    ).fetchall()
    return [(r["src"], r["dst"], float(r["sim"])) for r in rows]


def cluster_centroid(conn, claim_ids: list[str], *, dims: int = CLUSTER_DIMS) -> str:
    """묶음의 중심 벡터(평균)를 pgvector 텍스트 표기로 반환."""
    ph = ", ".join("?" for _ in claim_ids)
    row = conn.execute(
        f"SELECT avg({_sub('embedding', dims)})::text AS c FROM claims WHERE id IN ({ph})",
        tuple(claim_ids),
    ).fetchone()
    return row["c"]


def signal_counts(conn, centroid: str, w: Window, *, dims: int = CLUSTER_DIMS,
                  threshold: float = SIM_THRESHOLD) -> dict:
    """중심 벡터 반경 안의 claim·문서 수를 최근 창 / 직전 창으로 나눠 센다.

    묶음 구성원 수가 아니라 **반경 기준**으로 다시 세는 이유: 직전 28일에는 묶음이라는
    것이 없으므로 같은 잣대(중심에서 임계 이상)로 양쪽을 세야 배수가 의미를 갖는다.
    """
    sub = _sub("cl.embedding", dims)
    sim = f"1 - ({sub} <=> ?::vector)"
    no_nan = _no_nan(sim)
    row = conn.execute(
        f"""SELECT
              SUM(CASE WHEN d.published_at >= ? THEN 1 ELSE 0 END) AS recent_claims,
              COUNT(DISTINCT CASE WHEN d.published_at >= ? THEN d.id END) AS recent_docs,
              SUM(CASE WHEN d.published_at < ? THEN 1 ELSE 0 END) AS prior_claims,
              COUNT(DISTINCT CASE WHEN d.published_at < ? THEN d.id END) AS prior_docs
            FROM claims cl JOIN documents d ON d.id = cl.document_id
            WHERE d.published_at >= ? AND d.published_at < ?
              AND cl.embedding IS NOT NULL
              AND {no_nan} AND {sim} >= ?""",
        (w.recent_start.isoformat(), w.recent_start.isoformat(),
         w.recent_start.isoformat(), w.recent_start.isoformat(),
         w.base_start.isoformat(), w.recent_end.isoformat(),
         centroid, centroid, threshold),
    ).fetchone()
    return {k: int(row[k] or 0) for k in
            ("recent_claims", "recent_docs", "prior_claims", "prior_docs")}


def theory_cards_for(conn, centroid: str, *, dims: int = CLUSTER_DIMS,
                     threshold: float = THEORY_SIM_THRESHOLD,
                     limit: int = THEORY_CARD_LIMIT) -> list[dict]:
    """중심 벡터에 의미로 연결되는 이론 카드(theory-canon 문서) 목록.

    카드 1장 = 문서 1건이고 그 안의 명제가 claim이므로, 카드 단위로 최대 유사도를 본다.
    """
    sub = _sub("cl.embedding", dims)
    sim = f"1 - ({sub} <=> ?::vector)"
    no_nan = _no_nan(sim)
    rows = conn.execute(
        f"""SELECT d.id, d.title, MAX({sim}) AS sim
            FROM claims cl JOIN documents d ON d.id = cl.document_id
            WHERE d.source_id = 'theory-canon' AND cl.embedding IS NOT NULL
              AND {no_nan}
            GROUP BY d.id, d.title
            HAVING MAX({sim}) >= ?
            ORDER BY sim DESC LIMIT ?""",
        (centroid, centroid, centroid, threshold, limit),
    ).fetchall()
    return [{"id": r["id"], "title": r["title"], "sim": float(r["sim"])} for r in rows]


def axis_centroids(conn, *, dims: int = CLUSTER_DIMS) -> dict[str, list[float]]:
    """주제 축별 중심 벡터 — 그 축에 속한 이론 카드 claim들의 평균.

    축 목록은 이론 카드의 field 값(tags.axis='field')에서 나온다. 설정 파일이 따로 없는
    이유는 카드가 곧 축의 정의이기 때문이다 (load_theories.py).
    """
    sub = _sub("cl.embedding", dims)
    rows = conn.execute(
        f"""SELECT t.value AS axis, avg({sub})::text AS centroid
            FROM tags t
            JOIN documents d ON d.id = t.document_id
            JOIN claims cl ON cl.document_id = d.id
            WHERE t.axis = ? AND d.source_id = 'theory-canon' AND cl.embedding IS NOT NULL
            GROUP BY t.value""",
        (AXIS_TAG,),
    ).fetchall()
    out = {}
    for r in rows:
        axis = (r["axis"] or "").strip()
        if axis and r["centroid"]:
            out[axis] = parse_vector_literal(r["centroid"])
    return out


def best_axis(centroid: str, axes: dict[str, list[float]],
              threshold: float = AXIS_SIM_THRESHOLD) -> tuple[str | None, float]:
    """중심 벡터와 가장 가까운 주제 축. 임계 미달이면 (None, 최고 유사도)."""
    if not axes:
        return None, 0.0
    vec = parse_vector_literal(centroid)
    scored = sorted(((cosine(vec, v), a) for a, v in axes.items()), reverse=True)
    sim, axis = scored[0]
    return (axis if sim >= threshold else None), sim


# --------------------------------------------------------------------------- #
# 미개척도 — 발행 이력의 주제 축 분포                                          #
# --------------------------------------------------------------------------- #
CLAIM_COMMENT_RE = re.compile(r"<!--\s*claims:\s*([^>]+?)-->")
SLUG_COMMENT_RE = re.compile(r"<!--\s*slug:\s*([A-Za-z0-9_-]+)")


def published_articles() -> list[dict]:
    """발행 이력 파일(content/published/*.md)에서 slug·제목·근거 claim ID를 읽는다."""
    out = []
    for path in sorted(PUBLISHED_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        m = SLUG_COMMENT_RE.search(text)
        slug = m.group(1) if m else path.stem
        title = next((ln.lstrip("# ").strip() for ln in text.splitlines()
                      if ln.startswith("# ")), path.stem)
        ids: set[str] = set()
        for cm in CLAIM_COMMENT_RE.finditer(text):
            ids |= {x.strip() for x in cm.group(1).split(",") if x.strip()}
        out.append({"slug": slug, "title": title, "claim_ids": sorted(ids),
                    "path": str(path.relative_to(ROOT)).replace("\\", "/")})
    return out


def article_axis(conn, article: dict, axes: dict[str, list[float]], *,
                 dims: int = CLUSTER_DIMS) -> tuple[str | None, str]:
    """발행 아티클 1편의 주제 축. 반환: (축 또는 None, 판정 근거 메모).

    ① 본문 주석의 근거 claim ID가 지금 DB에 살아 있으면 그 claim들의 중심으로 판정한다
       — 실제로 쓴 근거가 곧 그 글의 주제라는 뜻이라 가장 정확하다.
    ② 안 되면(Phase 0 유산 아티클처럼 claim ID가 재수집 DB와 끊긴 경우) 판정을 포기한다.
       제목만 임베딩해 추정할 수도 있지만 OpenAI 호출이 필요하고 근거도 약해, 여기서는
       "축 미상"으로 남기고 보고서에 드러낸다 — 미개척 판정을 조용히 틀리게 만드는 것보다
       모른다고 적는 편이 낫다.
    """
    ids = article["claim_ids"]
    if not ids:
        return None, "근거 claim 주석 없음"
    ph = ", ".join("?" for _ in ids)
    row = conn.execute(
        f"SELECT COUNT(*) AS n, avg({_sub('embedding', dims)})::text AS c "
        f"FROM claims WHERE id IN ({ph}) AND embedding IS NOT NULL",
        tuple(ids),
    ).fetchone()
    if not row["n"]:
        return None, f"근거 claim {len(ids)}건이 현재 DB에 없음(Phase 0 유산)"
    axis, sim = best_axis(row["c"], axes)
    if axis is None:
        return None, f"축 유사도 {sim:.2f} — 임계({AXIS_SIM_THRESHOLD}) 미만"
    return axis, f"근거 claim {row['n']}건 기준 (유사도 {sim:.2f})"


def published_axis_counts(conn, axes: dict[str, list[float]]) -> tuple[dict[str, int], list[dict]]:
    """주제 축별 발행 편수와, 편별 판정 내역."""
    counts = {a: 0 for a in axes}
    detail = []
    for art in published_articles():
        axis, note = article_axis(conn, art, axes)
        if axis:
            counts[axis] = counts.get(axis, 0) + 1
        detail.append({"slug": art["slug"], "title": art["title"], "axis": axis, "note": note,
                       "path": art["path"]})
    return counts, detail


# --------------------------------------------------------------------------- #
# 분석 본체                                                                    #
# --------------------------------------------------------------------------- #
def analyze(conn, *, as_of: date, top_n: int = TOP_N, dims: int = CLUSTER_DIMS,
            k: int = KNN_K, threshold: float = SIM_THRESHOLD,
            min_cluster: int = MIN_CLUSTER_CLAIMS, verbose: bool = False) -> dict:
    """군집화부터 순위까지. 반환: 보고서 렌더링에 필요한 전부를 담은 페이로드."""
    w = resolve_window(as_of)
    claims = fetch_window_claims(conn, w)
    if verbose:
        print(f"  창 {w.recent_start}~{as_of} (발행일 기준) claim {len(claims)}건", file=sys.stderr)

    by_id = {c["id"]: c for c in claims}
    edges = knn_edges(conn, w, dims=dims, k=k, threshold=threshold)
    if verbose:
        print(f"  이웃 간선 {len(edges)}개 (k={k}, 유사도 {threshold} 이상)", file=sys.stderr)
    clusters = leader_cluster(list(by_id), edges, min_size=min_cluster)
    if verbose:
        print(f"  묶음 {len(clusters)}개 (구성원 {min_cluster}건 이상)", file=sys.stderr)

    recent_total, prior_total = window_totals(conn, w)
    if verbose:
        print(f"  창 전체 claim — 최근 {recent_total}건 / 직전 {prior_total}건 "
              f"(급증도는 이 비중 대비로 잰다)", file=sys.stderr)

    axes = axis_centroids(conn, dims=dims)
    pub_counts, pub_detail = published_axis_counts(conn, axes)

    candidates = []
    for members in clusters:
        member_claims = [by_id[i] for i in members]
        centroid = cluster_centroid(conn, members, dims=dims)
        cards = theory_cards_for(conn, centroid, dims=dims)
        ok, reasons, stats = qualify(member_claims, cards)
        counts = signal_counts(conn, centroid, w, dims=dims, threshold=threshold)
        axis, axis_sim = best_axis(centroid, axes)
        pub_n = pub_counts.get(axis) if axis else None
        surge_claims = surge_ratio(counts["recent_claims"], counts["prior_claims"],
                                   recent_total, prior_total)
        raw_ratio = daily_rate_ratio(counts["recent_claims"], counts["prior_claims"],
                                     w.window_days, w.baseline_days)
        weight = unexplored_weight(pub_n)
        candidates.append({
            "leader_claim_id": members[0],
            "leader_claim_text": by_id[members[0]]["claim_text"],
            "claim_ids": members,
            "qualified": ok,
            "reasons": reasons,
            "stats": stats,
            "signal": {**counts, "surge_claims": round(surge_claims, 2),
                       "raw_daily_ratio": round(raw_ratio, 2)},
            "axis": axis,
            "axis_sim": round(axis_sim, 3),
            "axis_published": pub_n,
            "unexplored": (pub_n == 0) if pub_n is not None else None,
            "weight": round(weight, 3),
            "score": round(surge_claims * weight, 3),
            "theory_cards": cards,
            "sample_claims": [
                {"id": c["id"], "text": c["claim_text"], "stance": c["stance"],
                 "tier": c["tier"], "source_id": c["source_id"],
                 "from_summary": int(c["from_summary"]),
                 "document_title": c["document_title"], "url": c["url"],
                 "published_at": str(c["published_at"])}
                for c in sorted(member_claims,
                                key=lambda c: (int(c["from_summary"]), c["tier"], c["id"]))
                [:CLAIM_SAMPLE]],
        })

    qualified = sorted([c for c in candidates if c["qualified"]],
                       key=lambda c: (-c["score"], c["leader_claim_id"]))
    rejected = sorted([c for c in candidates if not c["qualified"]],
                      key=lambda c: (-c["score"], c["leader_claim_id"]))
    return {
        "as_of": as_of.isoformat(),
        "week": iso_week_label(as_of),
        "window": w.as_dict(),
        "params": {"cluster_dims": dims, "knn_k": k, "sim_threshold": threshold,
                   "min_cluster_claims": min_cluster, "min_sources": MIN_SOURCES,
                   "min_theory_cards": MIN_THEORY_CARDS, "min_t12_claims": MIN_T12_CLAIMS,
                   "theory_sim_threshold": THEORY_SIM_THRESHOLD},
        "totals": {"window_claims": len(claims), "edges": len(edges),
                   "clusters": len(clusters), "qualified": len(qualified),
                   "recent_total": recent_total, "prior_total": prior_total,
                   "from_summary_claims": sum(1 for c in claims if c["from_summary"])},
        "axis_published_counts": pub_counts,
        "axis_published_detail": pub_detail,
        "candidates": qualified[:top_n],
        "shortfall": len(qualified) < top_n,
        "near_miss": rejected[:top_n],
    }


# --------------------------------------------------------------------------- #
# 보고서                                                                       #
# --------------------------------------------------------------------------- #
def _signal_summary(c: dict) -> str:
    s = c["signal"]
    # 비중 배수가 1 미만이면 "이번 주에 튀어나온 주제"가 아니라 계속 다뤄지는 주제다.
    # 그대로 배수만 적으면 급증으로 오독되므로 성격을 한 단어로 달아 준다.
    kind = "급증" if s["surge_claims"] >= 1.2 else ("지속" if s["surge_claims"] >= 0.8 else "감소")
    return (f"claim {s['recent_claims']}건·문서 {s['recent_docs']}건 "
            f"(직전 28일 {s['prior_claims']}건 → 비중 {s['surge_claims']}배·{kind})")


def _material_summary(c: dict) -> str:
    st = c["stats"]
    stance = " / ".join(f"{k} {v}" for k, v in st["stance_counts"].items() if v) or "없음"
    t12 = f" · T1·T2 {st['t12_claims']}건"
    summary_note = (f", 요약분 {st['claims_from_summary']}건 제외"
                    if st["claims_from_summary"] else "")
    return (f"증거 claim {st['claims_evidence']}건{summary_note}{t12} · "
            f"출처 {st['source_count']}곳 · stance {stance}")


def _theory_summary(c: dict) -> str:
    if not c["theory_cards"]:
        return "없음"
    return " / ".join(f"{t['title']}({t['sim']:.2f})" for t in c["theory_cards"][:3])


def _unexplored_summary(c: dict) -> str:
    if c["axis"] is None:
        return "축 미상"
    if c["unexplored"]:
        return f"**미개척** ({c['axis']} 축 발행 0편)"
    return f"기발행 ({c['axis']} 축 {c['axis_published']}편)"


def render_report(payload: dict, *, angle_lines: dict[str, str] | None = None) -> str:
    """후보 표 + 후보별 상세 + 부족 사유를 마크다운으로.

    angle_lines 는 {leader_claim_id: "예상 앵글 한 줄"}. /topics 커맨드 2단계가 채운다
    (판단이 필요한 문장이라 스크립트가 지어내지 않는다 — CLAUDE.md 절대 규칙 3의 정신).
    """
    angle_lines = angle_lines or {}
    w = payload["window"]
    t = payload["totals"]
    lines = [
        f"# 토픽 후보 {payload['week']} ({w['recent'][0]} ~ {payload['as_of']})",
        "",
        f"<!-- 생성: src/topics/discover.py · 기준일 {payload['as_of']} -->",
        "",
        f"- **시간 창**: 발행일(published_at) 기준 최근 {w['window_days']}일, "
        f"급증도 비교 창은 직전 {w['baseline_days']}일 ({w['baseline'][0]} ~ {w['baseline'][1]}). "
        f"수집 시각은 쓰지 않는다 — 소급 수집분이 신호를 오염시키기 때문.",
        f"- **재료**: 창 안 claim {t['window_claims']}건 → 묶음 {t['clusters']}개 → "
        f"교차 가능 후보 {t['qualified']}개"
        + (f" (그중 요약뿐 문서에서 나온 claim {t['from_summary_claims']}건 — 신호에만 반영)"
           if t.get("from_summary_claims")
           else " (요약뿐 문서 claim 0건 — T5 요약분 소급 추출 전이라 신호에 아직 안 잡힘)"),
        f"- **자격 기준**: 독립 출처 {payload['params']['min_sources']}곳 이상 · "
        f"상반 stance(optimistic·cautious) 실존 · "
        f"연결 이론 카드 {payload['params']['min_theory_cards']}장 이상 · "
        f"T1·T2 claim {payload['params']['min_t12_claims']}건 이상"
        f"(T5 단독 근거 금지 — 기획서 4.1). "
        f"출처·stance·T1·T2는 증거로 쓸 수 있는 claim만 센다(요약뿐 문서 제외).",
        f"- **급증도**: 창 전체 claim 대비 **비중** 비 "
        f"(최근 {t['recent_total']}건 / 직전 {t['prior_total']}건 기준). "
        f"일별 유입량이 아직 정상 상태가 아니라 건수 배수는 부풀어 보인다 — surge_ratio() 주석.",
        "",
        "## 후보",
        "",
        "| # | 주제 | 신호 (최근 2주) | 재료 | 연결 이론 카드 | 예상 앵글 | 미개척 |",
        "|---|---|---|---|---|---|---|",
    ]
    for i, c in enumerate(payload["candidates"], 1):
        angle = angle_lines.get(c["leader_claim_id"], "_(/topics 2단계 기입)_")
        topic = c.get("topic_line") or c["leader_claim_text"]
        lines.append(
            f"| {i} | {topic} | {_signal_summary(c)} | {_material_summary(c)} | "
            f"{_theory_summary(c)} | {angle} | {_unexplored_summary(c)} |")
    if not payload["candidates"]:
        lines.append("| — | (자격을 갖춘 묶음 없음) | | | | | |")

    if payload["shortfall"]:
        lines += ["", "## 후보 부족", "",
                  f"자격 묶음이 {t['qualified']}개로 목표 3개에 못 미친다. "
                  f"자격을 놓친 상위 묶음과 사유:", ""]
        for c in payload["near_miss"]:
            lines.append(f"- **{c['leader_claim_text'][:70]}** — "
                         f"{' · '.join(c['reasons'])} "
                         f"(claim {c['stats']['claims_total']}건, 급증도 "
                         f"{c['signal']['surge_claims']}배)")

    lines += ["", "## 후보 상세", ""]
    for i, c in enumerate(payload["candidates"], 1):
        st = c["stats"]
        lines += [
            f"### {i}. {c.get('topic_line') or c['leader_claim_text']}",
            "",
            f"- 점수 {c['score']} = 급증도 {c['signal']['surge_claims']} × "
            f"미개척 가중치 {c['weight']} "
            f"(참고: 건수 일평균 비 {c['signal']['raw_daily_ratio']}배)",
            f"- 주제 축: {c['axis'] or '미상'} (유사도 {c['axis_sim']}) · "
            f"발행 이력 {c['axis_published'] if c['axis_published'] is not None else '판정 불가'}편",
            f"- claim {st['claims_total']}건 / 문서 {st['documents']}건 / "
            f"증거 가능 {st['claims_evidence']}건",
            f"- 출처({st['source_count']}곳): {', '.join(st['sources'])}",
            f"- stance: " + (", ".join(f"{k} {v}건" for k, v in st['stance_counts'].items()) or "없음"),
            f"- 이론 카드: " + (", ".join(f"{t['title']} ({t['sim']:.2f})"
                                        for t in c["theory_cards"]) or "없음"),
            "",
            "대표 claim:",
            "",
        ]
        for s in c["sample_claims"]:
            mark = " ※요약분" if s["from_summary"] else ""
            lines.append(f"- `{s['id']}` [{s['tier']}·{s['source_id']}·{s['stance']}]{mark} "
                         f"{s['text']}")
        lines.append("")

    lines += [
        "## 발행 이력 축 판정 (미개척도 산출 근거)",
        "",
    ]
    for d in payload["axis_published_detail"]:
        lines.append(f"- {d['title']} → {d['axis'] or '축 미상'} · {d['note']}")
    counted = {a: n for a, n in payload["axis_published_counts"].items() if n}
    lines += ["",
              f"축별 발행 편수: {counted or '(전 축 0편)'}",
              ""]
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# CLI                                                                          #
# --------------------------------------------------------------------------- #
def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="토픽 발굴 — 최근 2주 claim 군집화·신호 산출")
    p.add_argument("--as-of", help="기준일 YYYY-MM-DD (미지정 시 오늘)")
    p.add_argument("--top", type=int, default=TOP_N, help=f"후보 수 (기본 {TOP_N})")
    p.add_argument("--dims", type=int, default=CLUSTER_DIMS,
                   help=f"군집화에 쓸 임베딩 차원 (기본 {CLUSTER_DIMS})")
    p.add_argument("--knn", type=int, default=KNN_K, help=f"claim당 이웃 상한 (기본 {KNN_K})")
    p.add_argument("--threshold", type=float, default=SIM_THRESHOLD,
                   help=f"같은 주제로 볼 코사인 유사도 하한 (기본 {SIM_THRESHOLD})")
    p.add_argument("--min-cluster", type=int, default=MIN_CLUSTER_CLAIMS,
                   help=f"묶음 최소 claim 수 (기본 {MIN_CLUSTER_CLAIMS})")
    p.add_argument("--json", action="store_true",
                   help="보고서 파일을 쓰지 않고 분석 페이로드를 stdout으로 출력")
    p.add_argument("--out", help="보고서 경로 (기본 content/topics/YYYY-WW.md)")
    args = p.parse_args(argv)

    if args.as_of and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", args.as_of):
        print(f"오류: --as-of 는 YYYY-MM-DD 형식이어야 한다 (받은 값: {args.as_of})")
        return 2
    as_of = date.fromisoformat(args.as_of) if args.as_of else date.today()

    conn = connect()
    if not conn.is_postgres:
        # embed.py와 같은 규약 — SQLite 모드는 claims.embedding이 없어 군집화 자체가 불가.
        print("SQLite 모드 — claim 임베딩(pgvector)이 없어 토픽 발굴을 건너뜁니다. 정상 종료.")
        conn.close()
        return 0
    migrate(conn)

    payload = analyze(conn, as_of=as_of, top_n=args.top, dims=args.dims, k=args.knn,
                      threshold=args.threshold, min_cluster=args.min_cluster,
                      verbose=not args.json)
    conn.close()

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    out = Path(args.out) if args.out else TOPICS_DIR / f"{payload['week']}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_report(payload), encoding="utf-8")
    print(f"\n후보 {len(payload['candidates'])}건 → {out}")
    if payload["shortfall"]:
        print(f"[주의] 자격 묶음 {payload['totals']['qualified']}개 — 목표 {args.top}개 미달. "
              f"보고서의 '후보 부족' 절에 사유를 적었습니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

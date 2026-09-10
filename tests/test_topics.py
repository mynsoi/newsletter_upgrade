"""토픽 발굴(src/topics/discover.py) + from_summary 게이트 테스트.

- SQLite 모드(기본, test_db 픽스처): 순수 로직과 추출 게이트·검색 필터를 검증한다.
  네트워크·OpenAI 키 불필요.
- PostgreSQL 모드(DATABASE_URL 설정 시에만): pgvector 군집화 SQL 자체를 검증하되
  임베딩은 raw SQL로 직접 삽입해 API 호출 없이 돈다 (test_search.py의 기존 관행과 동일 —
  고유 source_id 마커로 삽입 후 finally에서 정리).
"""
import os
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))


@pytest.fixture()
def test_db(tmp_path, monkeypatch):
    monkeypatch.setenv("PIPELINE_DB", str(tmp_path / "test.db"))
    monkeypatch.delenv("DATABASE_URL", raising=False)  # 로컬 테스트는 SQLite 모드 강제
    monkeypatch.delenv("OPENAI_API_KEY_EMBED", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    for mod in list(sys.modules):
        if mod in ("db", "handoff") or mod.startswith(("collectors", "enrich", "search", "topics")):
            del sys.modules[mod]
    import db
    conn = db.connect()
    db.migrate(conn)
    yield conn, db
    conn.close()


def _claim(cid, doc_id, text="주장", *, stance="neutral", tier=None, from_summary=0):
    """qualify()에 넘길 claim 딕셔너리 (analyze가 만드는 것과 같은 모양)."""
    return {"id": cid, "document_id": doc_id, "claim_text": text, "stance": stance,
            "tier": tier or "T1", "source_id": doc_id, "from_summary": from_summary}


# --------------------------------------------------------------------------- #
# 시간 창 — published_at 기준 (수집 시각 금지)                                  #
# --------------------------------------------------------------------------- #
def test_window_covers_14_days_inclusive_and_prior_28():
    from topics.discover import resolve_window
    w = resolve_window(date(2026, 9, 10))
    assert w.recent_start == date(2026, 8, 28)          # 오늘 포함 14일
    assert w.recent_end == date(2026, 9, 11)            # 열린 끝 — 당일까지 포함
    assert (w.recent_end - w.recent_start).days == 14   # 열린 끝 기준 14일 분량
    assert w.base_end == w.recent_start                 # 두 창이 맞닿는다
    assert w.base_start == date(2026, 7, 31)
    assert (w.base_end - w.base_start).days == 28


def test_window_dict_declares_published_at_basis():
    """창 기준이 published_at임을 산출물에 명시한다 — 소급 수집분 오염 방지의 근거."""
    from topics.discover import resolve_window
    d = resolve_window(date(2026, 9, 10)).as_dict()
    assert "published_at" in d["기준"] and "수집" in d["기준"]


def test_fetch_window_claims_uses_published_at_not_collected_at(test_db):
    """수집은 오늘 했지만 발행일이 창 밖인 문서는 잡히지 않아야 한다 (소급 수집 오염 방지)."""
    conn, db = test_db
    from topics.discover import fetch_window_claims, resolve_window
    today = date(2026, 9, 10)
    for doc_id, published in (("in", "2026-09-05"), ("old", "2024-01-01")):
        conn.execute(
            "INSERT INTO documents (id, source_id, tier, url, title, body, status, "
            "published_at, collected_at) VALUES (?,?, 'T1', ?, ?, '본문', 'enriched', ?, ?)",
            (doc_id, f"src-{doc_id}", f"http://x/{doc_id}", doc_id, published,
             "2026-09-10 00:00:00"))
        conn.execute(
            "INSERT INTO claims (id, document_id, claim_text, stance, embedding) "
            "VALUES (?,?,?, 'neutral', ?)",
            (f"c-{doc_id}", doc_id, f"{doc_id} 주장", b"x"))
    conn.commit()
    got = fetch_window_claims(conn, resolve_window(today))
    assert [c["document_id"] for c in got] == ["in"]


# --------------------------------------------------------------------------- #
# 군집화 — 리더 기준 탐욕 (사슬 연결 방지)                                      #
# --------------------------------------------------------------------------- #
def test_leader_cluster_groups_neighbors_of_densest_claim():
    from topics.discover import leader_cluster
    edges = [("a", "b", 0.9), ("a", "c", 0.8), ("b", "c", 0.7), ("d", "e", 0.9)]
    clusters = leader_cluster(["a", "b", "c", "d", "e"], edges)
    assert ["a", "b", "c"] in clusters
    assert ["d", "e"] in clusters


def test_leader_cluster_does_not_chain_beyond_the_leader():
    """a-b-c-d 사슬에서 양 끝(a, d)이 한 묶음이 되면 안 된다 (연결요소를 쓰지 않는 이유).

    연결요소였다면 넷이 통째로 한 묶음이 된다 — 사슬이 길수록 서로 무관한 claim이 섞인다.
    리더 기준이면 묶음은 리더에서 1홉 안으로 제한된다.
    """
    from topics.discover import leader_cluster
    edges = [("a", "b", 0.7), ("b", "c", 0.7), ("c", "d", 0.7)]
    clusters = leader_cluster(["a", "b", "c", "d"], edges)
    assert not any({"a", "d"} <= set(c) for c in clusters)


def test_leader_cluster_members_are_all_direct_neighbors_of_the_leader():
    """묶음의 반경 보장: 구성원은 전원 리더와 직접 이어져 있다."""
    from topics.discover import leader_cluster
    edges = [("a", "b", 0.7), ("b", "c", 0.7), ("c", "d", 0.7), ("b", "d", 0.7)]
    linked = {("a", "b"), ("b", "c"), ("c", "d"), ("b", "d")}
    for cluster in leader_cluster(["a", "b", "c", "d"], edges):
        leader, members = cluster[0], cluster[1:]
        for m in members:
            assert (leader, m) in linked or (m, leader) in linked


def test_leader_cluster_is_deterministic_and_partitions_every_claim():
    from topics.discover import leader_cluster
    ids = ["c1", "c2", "c3", "c4"]
    edges = [("c1", "c2", 0.9), ("c3", "c4", 0.9)]
    first = leader_cluster(ids, edges)
    assert first == leader_cluster(list(reversed(ids)), list(reversed(edges)))
    assert sorted(i for c in first for i in c) == ids   # 중복 배정 없음, 누락 없음


def test_leader_cluster_min_size_drops_small_groups_without_reassigning():
    from topics.discover import leader_cluster
    clusters = leader_cluster(["a", "b", "z"], [("a", "b", 0.9)], min_size=2)
    assert clusters == [["a", "b"]]      # 고립된 z는 버려지고 다른 묶음에 섞이지 않는다


def test_leader_cluster_ignores_edges_to_unknown_claims():
    from topics.discover import leader_cluster
    clusters = leader_cluster(["a"], [("a", "ghost", 0.99)])
    assert clusters == [["a"]]


# --------------------------------------------------------------------------- #
# 급증도 — 창 전체 대비 비중 비                                                 #
# --------------------------------------------------------------------------- #
def test_surge_ratio_cancels_corpus_wide_volume_growth():
    """창 전체가 2배로 늘었는데 주제도 2배면 급증이 아니다 (T5 수집 개시 효과 상쇄)."""
    from topics.discover import surge_ratio
    assert surge_ratio(20, 10, 2000, 1000) == pytest.approx(1.0)
    assert surge_ratio(40, 10, 2000, 1000) == pytest.approx(2.0)
    assert surge_ratio(10, 10, 2000, 1000) == pytest.approx(0.5)


def test_surge_ratio_floors_empty_baseline_instead_of_dividing_by_zero():
    from topics.discover import surge_ratio
    v = surge_ratio(10, 0, 1000, 1000)
    assert v == pytest.approx(20.0)   # 0건은 0.5건으로 본다
    assert v < float("inf")


def test_surge_ratio_returns_zero_when_a_window_is_empty():
    from topics.discover import surge_ratio
    assert surge_ratio(5, 0, 0, 100) == 0.0
    assert surge_ratio(5, 0, 100, 0) == 0.0


def test_daily_rate_ratio_normalizes_unequal_window_lengths():
    from topics.discover import daily_rate_ratio
    assert daily_rate_ratio(14, 28, 14, 28) == pytest.approx(1.0)


# --------------------------------------------------------------------------- #
# 교차 가능성 필터                                                              #
# --------------------------------------------------------------------------- #
def _qualifying_claims():
    return [
        _claim("1", "arxiv-cs-cy", stance="optimistic", tier="T1"),
        _claim("2", "mckinsey-insights", stance="cautious", tier="T2"),
        _claim("3", "hbr-korea", stance="neutral", tier="T3"),
        _claim("4", "aitimes", stance="cautious", tier="T5"),
    ]


def _cards(n=2):
    return [{"id": f"t{i}", "title": f"이론 {i}", "sim": 0.5} for i in range(n)]


def test_qualify_passes_when_all_conditions_met():
    from topics.discover import qualify
    ok, reasons, stats = qualify(_qualifying_claims(), _cards(2))
    assert ok and reasons == []
    assert stats["source_count"] == 4 and stats["t12_claims"] == 2


def test_qualify_rejects_when_sources_below_minimum():
    from topics.discover import qualify
    claims = _qualifying_claims()[:3]
    ok, reasons, _ = qualify(claims, _cards(2))
    assert not ok and any("독립 출처" in r for r in reasons)


def test_qualify_requires_both_opposed_stances():
    from topics.discover import qualify
    claims = [dict(c, stance="optimistic") for c in _qualifying_claims()]
    ok, reasons, _ = qualify(claims, _cards(2))
    assert not ok and any("상반 stance" in r and "cautious" in r for r in reasons)


def test_qualify_requires_two_theory_cards():
    from topics.discover import qualify
    ok, reasons, _ = qualify(_qualifying_claims(), _cards(1))
    assert not ok and any("이론 카드" in r for r in reasons)


def test_qualify_rejects_t5_only_bundle():
    """T5만으로 출처 4곳이 채워진 묶음은 후보가 될 수 없다 (기획서 4.1 철칙)."""
    from topics.discover import qualify
    claims = [_claim(str(i), f"news-{i}", tier="T5",
                     stance="optimistic" if i % 2 else "cautious") for i in range(4)]
    ok, reasons, stats = qualify(claims, _cards(2))
    assert stats["source_count"] == 4          # 출처 수만 보면 통과했을 묶음
    assert not ok and any("T1·T2" in r for r in reasons)


def test_qualify_excludes_from_summary_claims_from_evidence_counts():
    """from_summary claim은 신호에는 남고 자격 계산(출처·stance·T1·T2)에서는 빠진다."""
    from topics.discover import qualify
    claims = _qualifying_claims() + [
        _claim("s1", "chosun-economy", tier="T5", stance="optimistic", from_summary=1),
        _claim("s2", "donga-economy", tier="T5", stance="cautious", from_summary=1),
    ]
    _, _, stats = qualify(claims, _cards(2))
    assert stats["claims_total"] == 6
    assert stats["claims_evidence"] == 4 and stats["claims_from_summary"] == 2
    assert stats["source_count"] == 4                      # 요약분 출처 2곳은 세지 않는다
    assert "chosun-economy" not in stats["sources"]


def test_qualify_reports_all_failed_conditions_at_once():
    """미달 사유는 첫 번째에서 멈추지 않고 전부 모은다 — 보고서의 '부족 사유'가 재료다."""
    from topics.discover import qualify
    ok, reasons, _ = qualify([_claim("1", "aitimes", tier="T5")], [])
    assert not ok
    assert [r.split()[0] for r in reasons] == ["독립", "상반", "연결", "T1·T2"]


# --------------------------------------------------------------------------- #
# 미개척도                                                                      #
# --------------------------------------------------------------------------- #
def test_unexplored_weight_favors_axes_without_published_articles():
    from topics.discover import unexplored_weight
    assert unexplored_weight(0) == 1.0
    assert unexplored_weight(1) == pytest.approx(0.5)
    assert unexplored_weight(3) == pytest.approx(0.25)
    assert unexplored_weight(None) == 1.0    # 축 미상은 가점도 벌점도 없다


def test_published_articles_reads_slug_and_claim_ids_from_comments():
    """실제 발행물에서 slug와 근거 claim 주석을 읽어낸다 (미개척도 산출의 입력)."""
    from topics.discover import published_articles
    arts = {a["slug"]: a for a in published_articles()}
    assert "ai-productivity-paradox" in arts
    assert len(arts["ai-productivity-paradox"]["claim_ids"]) >= 5


def test_article_axis_returns_none_without_claim_comments(test_db):
    conn, _ = test_db
    from topics.discover import article_axis
    axis, note = article_axis(conn, {"claim_ids": [], "slug": "x"}, {"문화": [1.0]})
    assert axis is None and "주석 없음" in note


# --------------------------------------------------------------------------- #
# 벡터 유틸 / 축 판정                                                           #
# --------------------------------------------------------------------------- #
def test_vector_literal_roundtrip():
    from topics.discover import parse_vector_literal, to_vector_literal
    assert parse_vector_literal("[0.1,-0.2,3]") == [0.1, -0.2, 3.0]
    assert to_vector_literal([0.1, -0.2, 3.0]) == "[0.1,-0.2,3.0]"


def test_best_axis_picks_nearest_and_gives_up_below_threshold():
    from topics.discover import best_axis
    axes = {"문화": [1.0, 0.0], "평가·공정성": [0.0, 1.0]}
    assert best_axis("[1.0,0.05]", axes)[0] == "문화"
    assert best_axis("[1.0,-1.0]", axes, threshold=0.9)[0] is None   # 최고 유사도 0.707


def test_best_axis_handles_empty_axis_set():
    from topics.discover import best_axis
    assert best_axis("[1.0,0.0]", {}) == (None, 0.0)


def test_cosine_of_orthogonal_and_zero_vectors():
    from topics.discover import cosine
    assert cosine([1, 0], [0, 1]) == pytest.approx(0.0)
    assert cosine([0, 0], [1, 1]) == 0.0


def test_iso_week_label_format():
    from topics.discover import iso_week_label
    assert iso_week_label(date(2026, 9, 10)) == "2026-37"
    assert iso_week_label(date(2026, 1, 5)) == "2026-02"


# --------------------------------------------------------------------------- #
# 보고서 렌더링                                                                 #
# --------------------------------------------------------------------------- #
def _payload(candidates, qualified_n=None, near_miss=()):
    return {
        "as_of": "2026-09-10", "week": "2026-37",
        "window": {"recent": ["2026-08-28", "2026-09-11"],
                   "baseline": ["2026-07-31", "2026-08-28"],
                   "window_days": 14, "baseline_days": 28, "기준": "published_at"},
        "params": {"min_sources": 4, "min_theory_cards": 2, "min_t12_claims": 2},
        "totals": {"window_claims": 100, "edges": 10, "clusters": 5,
                   "qualified": qualified_n if qualified_n is not None else len(candidates),
                   "recent_total": 100, "prior_total": 50, "from_summary_claims": 7},
        "axis_published_counts": {"문화": 0},
        "axis_published_detail": [{"slug": "s", "title": "제목", "axis": "문화", "note": "메모"}],
        "candidates": candidates, "near_miss": list(near_miss),
        "shortfall": (qualified_n if qualified_n is not None else len(candidates)) < 3,
    }


def _candidate(cid="c1", **over):
    base = {
        "leader_claim_id": cid, "leader_claim_text": "리더 주장", "claim_ids": [cid],
        "qualified": True, "reasons": [],
        "stats": {"claims_total": 6, "claims_evidence": 5, "claims_from_summary": 1,
                  "sources": ["a", "b", "c", "d"], "source_count": 4, "documents": 5,
                  "stance_counts": {"cautious": 2, "optimistic": 3}, "theory_card_count": 2,
                  "t12_claims": 2},
        "signal": {"recent_claims": 20, "recent_docs": 12, "prior_claims": 4,
                   "prior_docs": 3, "surge_claims": 2.5, "raw_daily_ratio": 5.0},
        "axis": "문화", "axis_sim": 0.51, "axis_published": 0, "unexplored": True,
        "weight": 1.0, "score": 2.5, "theory_cards": [{"id": "t", "title": "이론 A", "sim": 0.5}],
        "sample_claims": [{"id": "c1", "text": "대표 주장", "stance": "cautious", "tier": "T1",
                           "source_id": "arxiv-cs-cy", "from_summary": 0,
                           "document_title": "문서", "url": "http://x",
                           "published_at": "2026-09-05"}],
    }
    base.update(over)
    return base


def test_render_report_notes_when_summary_claims_are_absent():
    """요약분 claim이 0건이면 '소급 추출 전'임을 밝힌다 — 신호를 과신하지 않도록."""
    from topics.discover import render_report
    payload = _payload([_candidate()])
    payload["totals"]["from_summary_claims"] = 0
    assert "소급 추출 전" in render_report(payload)
    payload["totals"]["from_summary_claims"] = 7
    assert "신호에만 반영" in render_report(payload)


def test_render_report_emits_table_with_required_columns():
    from topics.discover import render_report
    md = render_report(_payload([_candidate()]))
    header = next(ln for ln in md.splitlines() if ln.startswith("| # |"))
    for col in ("주제", "신호", "재료", "연결 이론 카드", "예상 앵글", "미개척"):
        assert col in header
    assert "**미개척**" in md and "이론 A" in md


def test_render_report_marks_shortfall_with_reasons():
    from topics.discover import render_report
    near = _candidate("c9", qualified=False,
                      reasons=["독립 출처 2곳 (기준 4곳)", "상반 stance 없음 (cautious 0건)"])
    md = render_report(_payload([_candidate()], qualified_n=1, near_miss=[near]))
    assert "## 후보 부족" in md
    assert "독립 출처 2곳" in md and "상반 stance 없음" in md


def test_render_report_handles_zero_candidates():
    from topics.discover import render_report
    md = render_report(_payload([], qualified_n=0))
    assert "자격을 갖춘 묶음 없음" in md and "## 후보 부족" in md


def test_render_report_fills_angle_line_when_provided():
    from topics.discover import render_report
    md = render_report(_payload([_candidate()]), angle_lines={"c1": "앵글 한 줄"})
    assert "앵글 한 줄" in md and "/topics 2단계 기입" not in md


def test_render_report_labels_flat_share_as_persistent_not_surge():
    from topics.discover import render_report
    c = _candidate(signal={"recent_claims": 20, "recent_docs": 12, "prior_claims": 4,
                           "prior_docs": 3, "surge_claims": 0.9, "raw_daily_ratio": 3.0})
    assert "지속" in render_report(_payload([c]))


# --------------------------------------------------------------------------- #
# from_summary — 추출 대상 편입과 증거 검색 제외                                #
# --------------------------------------------------------------------------- #
def _doc(conn, doc_id, tier, *, summary_only, status="new"):
    conn.execute(
        "INSERT INTO documents (id, source_id, tier, url, title, body, status, summary_only) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (doc_id, f"src-{doc_id}", tier, f"http://x/{doc_id}", f"제목 {doc_id}",
         "본문", status, summary_only))


def test_select_target_docs_includes_t5_summary_only_but_not_other_tiers(test_db):
    conn, _ = test_db
    from enrich.extract_claims import select_target_docs
    _doc(conn, "full", "T3", summary_only=0)
    _doc(conn, "t5sum", "T5", summary_only=1)
    _doc(conn, "t2sum", "T2", summary_only=1)   # 브라우저 격상 대기 — 계속 제외
    conn.commit()
    assert sorted(d["id"] for d in select_target_docs(conn, 10)) == ["full", "t5sum"]


def test_select_target_docs_round_robin_applies_same_summary_gate(test_db):
    conn, _ = test_db
    from enrich.extract_claims import select_target_docs_round_robin
    _doc(conn, "t5sum", "T5", summary_only=1)
    _doc(conn, "t2sum", "T2", summary_only=1)
    conn.commit()
    assert [d["id"] for d in select_target_docs_round_robin(conn, 10)] == ["t5sum"]


def test_only_summary_filter_selects_retroactive_targets_only(test_db):
    conn, _ = test_db
    from enrich.extract_claims import select_target_docs
    _doc(conn, "full", "T5", summary_only=0)
    _doc(conn, "t5sum", "T5", summary_only=1)
    conn.commit()
    assert [d["id"] for d in select_target_docs(conn, 10, only_summary=True)] == ["t5sum"]


def test_summary_gate_sql_lists_only_allowed_tiers():
    from enrich.extract_claims import SUMMARY_CLAIM_TIERS, summary_gate_sql
    sql = summary_gate_sql()
    assert "'T5'" in sql and "'T2'" not in sql
    assert SUMMARY_CLAIM_TIERS == ("T5",)


def test_hybrid_search_excludes_from_summary_claims_by_default(test_db):
    conn, db = test_db
    from search.semantic import hybrid_search
    _doc(conn, "d1", "T5", summary_only=1, status="enriched")
    conn.execute("INSERT INTO claims (id, document_id, claim_text, stance, from_summary) "
                 "VALUES (?,?,?, 'neutral', 1)", ("cs", "d1", "요약뿐 문서의 심리적 안전감 주장"))
    conn.execute("INSERT INTO claims (id, document_id, claim_text, stance, from_summary) "
                 "VALUES (?,?,?, 'neutral', 0)", ("cf", "d1", "전문 문서의 심리적 안전감 주장"))
    conn.commit()

    default_hits = {r["id"] for r in hybrid_search("심리적 안전감", conn=conn)}
    assert default_hits == {"cf"}
    with_summary = {r["id"] for r in hybrid_search("심리적 안전감", conn=conn,
                                                   include_from_summary=True)}
    assert with_summary == {"cf", "cs"}


def test_discover_main_skips_cleanly_on_sqlite(test_db, capsys):
    """SQLite 모드는 실패가 아니라 '건너뜀'으로 정상 종료한다 (embed.py와 같은 규약)."""
    from topics.discover import main
    assert main([]) == 0
    assert "건너" in capsys.readouterr().out


def test_discover_main_rejects_malformed_as_of(test_db):
    from topics.discover import main
    assert main(["--as-of", "2026-9-1"]) == 2


# --------------------------------------------------------------------------- #
# PostgreSQL 모드 (DATABASE_URL 설정 시에만) — pgvector 군집화 SQL 검증          #
# --------------------------------------------------------------------------- #
@pytest.mark.skipif(not os.environ.get("DATABASE_URL"),
                    reason="DATABASE_URL 미설정 — pgvector 군집화 테스트 생략")
def test_knn_edges_and_centroid_on_postgres():
    for mod in list(sys.modules):
        if mod == "db" or mod.startswith(("search", "topics")):
            del sys.modules[mod]
    import db
    assert db.IS_POSTGRES
    from search.embed import VECTOR_TYPE
    from topics.discover import (article_axis, cluster_centroid, fetch_window_claims,
                                 knn_edges, leader_cluster, resolve_window, signal_counts,
                                 to_vector_literal, window_totals)

    conn = db.connect()
    db.migrate(conn)
    marker = "pg-topics-test"
    as_of = date.today()
    w = resolve_window(as_of)
    try:
        # 최근 창에 서로 가까운 claim 2건 + 멀리 떨어진 claim 1건
        near_doc, far_doc = db.new_id(), db.new_id()
        for doc_id, src in ((near_doc, marker), (far_doc, marker + "-far")):
            conn.execute(
                "INSERT INTO documents (id, source_id, tier, url, title, body, status, "
                "published_at) VALUES (?,?, 'T2', ?, '테스트', '본문', 'enriched', ?)",
                (doc_id, src, f"http://{marker}/{doc_id}",
                 (as_of - timedelta(days=1)).isoformat()))
        ids = {}
        vecs = {"n1": [1.0] + [0.0] * 1535, "n2": [0.99, 0.01] + [0.0] * 1534,
                "far": [0.0] * 1535 + [1.0]}
        for key, vec in vecs.items():
            cid = db.new_id()
            ids[key] = cid
            conn.execute(
                "INSERT INTO claims (id, document_id, claim_text, stance) VALUES (?,?,?,?)",
                (cid, near_doc if key != "far" else far_doc, f"{key} 주장", "neutral"))
            conn.execute(f"UPDATE claims SET embedding = ?::{VECTOR_TYPE} WHERE id = ?",
                         (to_vector_literal(vec), cid))
        conn.commit()

        edges = knn_edges(conn, w, k=40, threshold=0.9)
        mine = {(a, b) for a, b, _ in edges if a in ids.values() and b in ids.values()}
        assert (ids["n1"], ids["n2"]) in mine or (ids["n2"], ids["n1"]) in mine
        assert not any(ids["far"] in pair for pair in mine)   # 먼 벡터는 이어지지 않는다

        clusters = leader_cluster(list(ids.values()),
                                  [e for e in edges if e[0] in ids.values()])
        assert any(set(c) == {ids["n1"], ids["n2"]} for c in clusters)

        centroid = cluster_centroid(conn, [ids["n1"], ids["n2"]])
        assert centroid.startswith("[")
        counts = signal_counts(conn, centroid, w, threshold=0.9)
        assert counts["recent_claims"] >= 2 and counts["recent_docs"] >= 1

        recent_total, prior_total = window_totals(conn, w)
        window_claims = fetch_window_claims(conn, w)
        assert recent_total == len(window_claims) and prior_total >= 0

        # Phase 0 유산처럼 claim ID가 현재 DB에 없으면 축을 추정하지 않고 '미상'으로 남긴다
        axis, note = article_axis(conn, {"claim_ids": ["없는ID"], "slug": "x"}, {})
        assert axis is None and "현재 DB에 없음" in note
    finally:
        conn.execute(
            "DELETE FROM claims WHERE document_id IN "
            "(SELECT id FROM documents WHERE source_id LIKE ?)", (marker + "%",))
        conn.execute("DELETE FROM documents WHERE source_id LIKE ?", (marker + "%",))
        conn.commit()
        conn.close()

"""아티클 실사용 기준 검증 테스트 (A2) — 네트워크·DB 불필요."""
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

import verify_article as va  # noqa: E402


def claim(cid, source, stance, text="본문 근거 문장", tier="T2", etype="data", doc=None, metric=None):
    c = {"id": cid, "source": source, "stance": stance, "text": text,
         "tier": tier, "evidence_type": etype, "doc": doc or f"{source} 문서"}
    if metric:
        c["metric"] = metric
    return c


def evidence(*claims):
    return {c["id"]: c for c in claims}


BASE = evidence(
    claim("C1", "hbr", "optimistic"),
    claim("C2", "mckinsey-insights", "cautious"),
    claim("C3", "theory-canon", "neutral", tier="T1", etype="theory"),
)

GOOD_ARTICLE = """<!-- slug: t -->
# 제목

## 관찰된 신호

첫 문단이다.
<!-- claims: C1 -->

둘째 문단이다.
<!-- claims: C2 -->

## 교차 해석

셋째 문단이다.
<!-- claims: C3 -->
"""


def test_parse_article_pairs_paragraph_with_claims():
    segs, refs = va.parse_article(GOOD_ARTICLE)
    used = [s for s in segs if s.claim_ids]
    assert [s.claim_ids for s in used] == [["C1"], ["C2"], ["C3"]]
    assert used[0].heading == "관찰된 신호" and used[2].heading == "교차 해석"
    assert used[0].text == "첫 문단이다."
    assert refs == []


def test_passes_when_conditions_met_on_used_claims():
    r = va.verify(GOOD_ARTICLE, BASE)
    assert r["passed"] is True
    assert len(r["used"]) == 3 and r["unused"] == []
    assert set(r["counts"]) == {"hbr", "mckinsey-insights", "theory-canon"}


def test_unregistered_claim_fails_and_points_to_sentence():
    md = GOOD_ARTICLE + "\n넷째 문단이다.\n<!-- claims: C9 -->\n"
    r = va.verify(md, BASE)
    fails = [i for i in r["issues"] if i.level == "fail"]
    assert r["passed"] is False
    assert any(i.kind == "미등록 claim" and "C9" in i.message for i in fails)
    assert any("넷째 문단이다" in i.where for i in fails)  # 문장 지목


def test_unregistered_source_in_prose_fails():
    md = """<!-- slug: t -->
## 관찰된 신호

Josh Bersin이 지적한 대로 상황이 바뀌었다.
<!-- claims: C1 -->
"""
    r = va.verify(md, BASE)
    assert any(i.kind == "미등록 출처" for i in r["issues"] if i.level == "fail")


def test_recalculates_conditions_on_used_claims_not_whole_evidence():
    """evidence에는 출처가 넉넉해도 본문이 한 출처만 쓰면 실패해야 한다."""
    ev = evidence(
        claim("C1", "hbr", "optimistic"), claim("C2", "hbr", "cautious"),
        claim("C3", "mckinsey-insights", "neutral"), claim("C4", "mit-smr", "neutral"),
        claim("C5", "theory-canon", "neutral"),
    )
    md = """<!-- slug: t -->
## 관찰된 신호

한 출처만 쓴 문단.
<!-- claims: C1 -->

같은 출처를 또 쓴 문단.
<!-- claims: C2 -->
"""
    r = va.verify(md, ev)
    kinds = {i.kind for i in r["issues"] if i.level == "fail"}
    assert "독립 출처 부족" in kinds        # 사용 claim 기준 1곳
    assert "단일 출처 편중" in kinds        # hbr 100%
    assert len(r["unused"]) == 3           # evidence에는 남아 있지만 계산에 넣지 않음


def test_opposing_stance_required_among_used_claims():
    ev = evidence(claim("C1", "hbr", "neutral"), claim("C2", "mckinsey-insights", "neutral"),
                  claim("C3", "theory-canon", "neutral"))
    r = va.verify(GOOD_ARTICLE, ev)
    assert any(i.kind == "상반 stance 없음" for i in r["issues"] if i.level == "fail")


def test_number_check_uses_used_claim_metric_and_exempts_year_and_actions():
    ev = evidence(
        claim("C1", "hbr", "optimistic", text="생산성이 47% 올랐다", metric="47%"),
        claim("C2", "mckinsey-insights", "cautious"),
        claim("C3", "theory-canon", "neutral"),
    )
    md = """<!-- slug: t -->
## 관찰된 신호

생산성이 47% 올랐다는 보고가 있다.
<!-- claims: C1 -->

근거 없는 수치 88%를 쓴 문단이다.
<!-- claims: C2 -->

2026년 신년사에서 언급됐다.
<!-- claims: C3 -->

## 다음 주에 시도할 것

주 1회 2주 동안 기록한다.
<!-- claims: C3 -->
"""
    r = va.verify(md, ev)
    checked = {tok: ok for _, tok, ok in r["numbers"]}
    assert checked.get("47%") is True                      # 사용 claim의 metric과 일치
    assert checked.get("88%") is False                     # 근거 없음 → 실패
    assert "2026년" not in checked                          # 달력 연도는 서지 표기 — 면제
    assert "2주" not in checked and "1회" not in checked     # 액션 섹션 면제
    assert any(i.kind == "수치 근거 없음" for i in r["issues"] if i.level == "fail")


def test_references_are_built_from_used_docs_only():
    ev = evidence(
        claim("C1", "hbr", "optimistic", doc="HBR 기사 A"),
        claim("C2", "mckinsey-insights", "cautious", doc="McKinsey 리포트"),
        claim("C3", "theory-canon", "neutral", doc="심리적 안전감 (Psychological Safety)"),
        claim("C9", "mit-smr", "neutral", doc="쓰지 않은 문서"),
    )
    md = GOOD_ARTICLE + """
## 참고자료

- HBR: HBR 기사 A
- MIT SMR: 쓰지 않은 문서
"""
    r = va.verify(md, ev)
    assert set(r["used_docs"]) == {"hbr", "mckinsey-insights", "theory-canon"}
    assert "mit-smr" not in r["used_docs"]                 # 참고자료는 실사용 문서만
    assert any(i.kind == "참고자료 실사용 없음" for i in r["issues"])


def test_flags_paragraphs_missing_claim_comment():
    """주석 없는 문단에 수치·인용 표현이 있으면 경고로 지목한다."""
    md = """<!-- slug: t -->
## 관찰된 신호

근거를 단 문단이다.
<!-- claims: C1 -->

한 조사에 따르면 상황이 달라졌다고 한다.

응답자 63% 가 그렇게 답했다.

주장만 있고 수치도 인용도 없는 문단이다.

## 다음 주에 시도할 것

주 1회 2주 동안 기록한다.

메타분석 결과를 참고해 설계한다.
"""
    r = va.verify(md, BASE)
    marks = {seg.line: reason for seg, reason in r["missing_marks"]}
    sentences = [seg.text for seg, _ in r["missing_marks"]]

    assert any("조사에 따르면" in s for s in sentences)      # 인용 표현
    assert any("63%" in s for s in sentences)                # 수치
    assert not any("주장만 있고" in s for s in sentences)     # 평서 문단은 잡지 않음
    assert not any("주 1회 2주" in s for s in sentences)      # 액션의 처방 값은 면제
    assert any("메타분석" in s for s in sentences)            # 액션이어도 인용 표현은 잡는다
    assert all("수치" in v or "인용 표현" in v for v in marks.values())
    assert all(i.level == "warn" for i in r["issues"] if i.kind == "근거 주석 누락 의심")


def test_missing_claim_comment_ignores_year_and_references():
    md = """<!-- slug: t -->
## SK 맥락에서의 의미

2026년 신년사에서 언급된 방향과 맞닿는다.
<!-- claims: C1 -->

2020년에 개정된 기준을 따른다.

## 참고자료

- HBR: 47% 라는 수치가 담긴 기사
"""
    r = va.verify(md, BASE)
    sentences = [seg.text for seg, _ in r["missing_marks"]]
    assert not any("2020년" in s for s in sentences)   # 달력 연도만 있는 문단은 제외
    assert not any("참고자료" in s or "47%" in s for s in sentences)  # 참고자료 섹션 제외


def test_report_includes_missing_comment_section():
    md = GOOD_ARTICLE + "\n한 연구 결과 수치가 12% 라고 한다.\n"
    r = va.verify(md, BASE)
    report = va.render_report("t", Path("a.md"), Path("e.json"), r)
    assert "근거 주석 누락 의심" in report
    assert "12%" in report
    # 표가 깨지지 않도록 문장 발췌는 한 줄로 접힌다
    table_rows = [ln for ln in report.splitlines() if ln.startswith("| ") and "12%" in ln]
    assert table_rows and all(ln.count("\n") == 0 for ln in table_rows)


def test_report_includes_sentence_to_claim_mapping():
    r = va.verify(GOOD_ARTICLE, BASE)
    report = va.render_report("t", Path("a.md"), Path("e.json"), r)
    assert "본문 사용 claim (문장 ↔ claim ID)" in report
    assert "첫 문단이다" in report and "`C1`" in report
    assert "강제 조건 재계산" in report and "참고자료 (실사용 문서만)" in report


def test_cli_writes_report_and_exit_code(tmp_path, monkeypatch, capsys):
    import json
    art = tmp_path / "t.md"
    art.write_text(GOOD_ARTICLE, encoding="utf-8")
    ev = tmp_path / "t.json"
    ev.write_text(json.dumps({"claims": list(BASE.values())}, ensure_ascii=False), encoding="utf-8")
    out = tmp_path / "t-verification.md"

    assert va.main([str(art), "--evidence", str(ev), "--out", str(out)]) == 0
    assert "본문 사용 claim" in out.read_text(encoding="utf-8")

    bad = tmp_path / "bad.md"
    bad.write_text(GOOD_ARTICLE + "\n문제 문단.\n<!-- claims: ZZZ -->\n", encoding="utf-8")
    assert va.main([str(bad), "--evidence", str(ev), "--out", str(out)]) == 1  # 실패 시 비정상 종료

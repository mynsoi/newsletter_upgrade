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
    checked = {tok: status for _, tok, status in r["numbers"]}
    assert checked.get("47%") == "ok"                      # 사용 claim의 metric과 일치
    assert checked.get("88%") == "fail"                    # 근거 없음 → 실패
    assert "2026년" not in checked                          # 달력 연도는 서지 표기 — 면제
    assert checked.get("2주") == "prescriptive"             # 액션 섹션의 기간 값은 처방 값
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


def test_action_marker_paragraph_exempts_prescriptive_values_without_section_name():
    """소제목이 메시지 문장이어도(article_style 4절) 액션 마커로 처방 값을 인식한다."""
    md = """<!-- slug: t -->
## 먼저 정할 것은 도구가 아니라 목적지입니다

첫 문단이다.
<!-- claims: C1 -->

**리더가 할 일.** 팀장은 4주 안에 쓸 곳을 정합니다. 확인지표는 4주 뒤 회의입니다.

**실무자가 할 일.** 구성원은 2주 동안 주 1회 기록합니다.
"""
    r = va.verify(md, BASE)
    checked = {tok: status for _, tok, status in r["numbers"]}
    assert checked.get("4주") == "prescriptive"
    assert checked.get("2주") == "prescriptive"
    # 처방 값이므로 "근거 주석 누락 의심" 경고도 뜨지 않는다
    assert not [i for i in r["issues"] if i.kind == "근거 주석 누락 의심"]


def test_prescriptive_exemption_does_not_hide_real_numbers_in_action_paragraph():
    """액션 문단이라도 기간·횟수가 아닌 수치(%)는 그대로 근거 대조한다."""
    md = """<!-- slug: t -->
## 무엇을 할 것인가

첫 문단이다.
<!-- claims: C1 -->

**리더가 할 일.** 팀장은 2주 안에 생산성 88% 향상을 목표로 잡습니다.
"""
    r = va.verify(md, BASE)
    checked = {tok: status for _, tok, status in r["numbers"]}
    assert checked.get("2주") == "prescriptive"
    assert checked.get("88%") == "fail"        # 근거 없는 수치는 여전히 잡힌다
    assert any(i.kind == "수치 근거 없음" for i in r["issues"] if i.level == "fail")


INTERNAL = [{"id": "internal/ceo.md", "title": "이천포럼 CEO 패널토의",
             "speaker": "SK이노베이션 E&S 대표이사",
             "effective_date": "2026-08-20",
             "body": "제가 말씀드리고 싶은 건, 사람이 남는다는 문제가 아니라 "
                     "사람의 남는 시간을 어디에 쓸 것인가의 문제입니다."}]


def test_internal_quote_matches_source_text():
    md = GOOD_ARTICLE + """
대표이사는 **"사람의 남는 시간을 어디에 쓸 것인가의 문제"**라고 정리했습니다.
<!-- claims: C1 -->
"""
    r = va.verify(md, BASE, INTERNAL)
    q = [x for x in r["quotes"] if x["status"] == "match"]
    assert q and q[0]["doc"] == "이천포럼 CEO 패널토의"
    assert q[0]["speaker"] == "SK이노베이션 E&S 대표이사"
    report = va.render_report("t", Path("a.md"), Path("e.json"), r)
    assert "내부 자료 인용 대조" in report
    assert "발언 맥락 왜곡 여부는 사람 확인 항목" in report


def test_internal_quote_not_found_is_warned():
    md = GOOD_ARTICLE + """
대표이사는 **"우리는 내년까지 전 직원을 재배치하겠습니다"**라고 말했습니다.
<!-- claims: C1 -->
"""
    r = va.verify(md, BASE, INTERNAL)
    assert any(i.kind == "인용 원문 미확인" for i in r["issues"])
    assert r["passed"] is True          # 경고일 뿐 실패는 아니다 (사람 확인 항목)


def test_internal_quote_check_skipped_without_db():
    """DB를 못 읽으면 단정하지 않고 '확인 불가'로 남긴다."""
    md = GOOD_ARTICLE + """
대표이사는 **"확인할 수 없는 인용문입니다"**라고 말했습니다.
<!-- claims: C1 -->
"""
    r = va.verify(md, BASE, [])
    assert r["internal_available"] is False
    assert not [i for i in r["issues"] if i.kind == "인용 원문 미확인"]
    report = va.render_report("t", Path("a.md"), Path("e.json"), r)
    assert "내부 자료를 읽지 못해" in report


def test_prose_recommendation_paragraph_exempts_prescriptive_values():
    """박스 구조를 없애고 제언형 산문으로 써도 기간·횟수는 처방 값으로 인식한다.
    (2026-09-03 D1 편집 피드백 ⑧ — '리더가 할 일' 마커가 사라진 형태)"""
    md = GOOD_ARTICLE + """
## 우리 조직에 적용해본다면

팀에서는 AI가 줄여준 시간을 모아 보는 일부터 해볼 수 있습니다. 4주쯤 지나 그 시간으로
새로 시작한 일을 말할 수 있다면 통로가 생긴 것입니다. 개인은 한 줄씩 적어 두는 것으로
충분합니다. 2주쯤 모이면 어디서 여유가 생기는지 보이기 시작합니다.
"""
    r = va.verify(md, BASE)
    checked = {tok: status for _, tok, status in r["numbers"]}
    assert checked.get("4주") == "prescriptive"
    assert checked.get("2주") == "prescriptive"
    assert not [i for i in r["issues"] if i.kind == "근거 주석 누락 의심"]
    assert r["passed"] is True


def test_action_paragraph_quotes_are_not_treated_as_citations():
    """액션 문단의 따옴표는 확인지표 이름이지 인용이 아니다 — 오탐을 만들지 않는다."""
    md = GOOD_ARTICLE + """
**리더가 할 일.** 확인지표는 "재배치한 시간으로 새로 시작한 일"을 말할 수 있는지입니다.
"""
    r = va.verify(md, BASE, INTERNAL)
    assert not [i for i in r["issues"] if i.kind == "인용 원문 미확인"]
    assert not [q for q in r["quotes"] if q["status"] == "unmatched"]


def test_cdata_wrapper_stripped_from_reference_titles():
    ev = evidence(
        claim("C1", "bain-insights", "optimistic",
              doc="<![CDATA[Why Pharma Transformations Stall]]>"),
        claim("C2", "mckinsey-insights", "cautious", doc="The state of AI"),
        claim("C3", "theory-canon", "neutral", doc="흡수역량 (Absorptive Capacity)"),
    )
    md = GOOD_ARTICLE + """
## 참고자료

- Bain Insights, "Why Pharma Transformations Stall"
"""
    r = va.verify(md, ev)
    assert r["used_docs"]["bain-insights"] == {"Why Pharma Transformations Stall"}
    report = va.render_report("t", Path("a.md"), Path("e.json"), r)
    assert "CDATA" not in report
    # 제목이 정리되면 참고자료 실사용 매칭도 성공한다
    assert not [i for i in r["issues"] if i.kind == "참고자료 실사용 없음"]


def test_clean_title_handles_plain_and_wrapped():
    assert va.clean_title("<![CDATA[ Industrial CEOs ]]>") == "Industrial CEOs"
    assert va.clean_title("평범한 제목") == "평범한 제목"
    assert va.clean_title("") == ""


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


# --- 내부 자료 시점 표기 (article_style 5절) -------------------------------------

INTERNAL_REF_SECTION = """
## 참고자료

- 내부: 이천포럼 CEO 패널토의
"""


def test_internal_reference_without_year_is_warned():
    """인용부호 없는 간접 서술도 잡는다 — 제목 낱말('이천포럼')로 문단을 찾는다."""
    md = GOOD_ARTICLE + """
이천포럼 패널토의에서 남는 시간을 어디에 쓸 것인가의 문제로 규정했습니다.
<!-- claims: C1 -->
""" + INTERNAL_REF_SECTION
    r = va.verify(md, BASE, INTERNAL)
    warn = [i for i in r["issues"] if i.kind == "내부 자료 시점 미표기"]
    assert warn and "2026년" in warn[0].message
    assert r["passed"] is True            # 경고일 뿐 실패는 아니다
    report = va.render_report("t", Path("a.md"), Path("e.json"), r)
    assert "시점 표기" in report and "⚠️ 없음" in report


def test_internal_reference_with_year_passes():
    md = GOOD_ARTICLE + """
2026년 이천포럼 패널토의에서 남는 시간을 어디에 쓸 것인가의 문제로 규정했습니다.
<!-- claims: C1 -->
""" + INTERNAL_REF_SECTION
    r = va.verify(md, BASE, INTERNAL)
    assert not [i for i in r["issues"] if i.kind == "내부 자료 시점 미표기"]
    assert r["internal_refs"] and r["internal_refs"][0]["dated"] is True
    assert "✅ 있음" in va.render_report("t", Path("a.md"), Path("e.json"), r)


def test_internal_date_check_skipped_without_db():
    md = GOOD_ARTICLE + """
이천포럼 패널토의에서 남는 시간의 쓰임을 논의했습니다.
<!-- claims: C1 -->
""" + INTERNAL_REF_SECTION
    r = va.verify(md, BASE, [])
    assert not [i for i in r["issues"] if i.kind == "내부 자료 시점 미표기"]
    assert r["internal_refs"] == []


def test_generic_title_tokens_do_not_match():
    """'CEO'·'패널토의' 같은 흔한 낱말로는 무관한 문단을 내부 인용으로 잡지 않는다."""
    assert va._title_tokens("2026 이천포럼 CEO 패널토의") == ["이천포럼"]
    md = GOOD_ARTICLE + """
설문에서 CEO들의 투자 수익 낙관도가 1년 전보다 높아졌습니다.
<!-- claims: C1 -->
"""
    r = va.verify(md, BASE, INTERNAL)
    assert r["internal_refs"] == []


def test_year_bearing_title_token_does_not_match_every_paragraph():
    """'2026년 …신년사' 같은 제목의 '2026년'이 연도 쓴 문단마다 걸리면 안 된다."""
    assert va._title_tokens("2026년 SK이노베이션 E&S 신년사") == ["SK이노베이션", "E&S", "신년사"]
    assert va._title_tokens("SK그룹 사례를 통한 의미부여와 의미형성") == ["SK그룹", "의미형성"]
    docs = [{"id": "internal/ny.md", "title": "2026년 SK이노베이션 E&S 신년사",
             "speaker": "대표이사", "effective_date": "2026-01-01", "body": "본문"}]
    md = GOOD_ARTICLE + """
McKinsey가 해마다 돌리는 2026년판 설문을 보면 응답이 갈립니다.
<!-- claims: C1 -->
"""
    r = va.verify(md, BASE, docs)
    assert r["internal_refs"] == []


def test_undeclared_internal_doc_is_not_matched_indirectly():
    """참고자료에 밝히지 않은 내부 문서는 제목 낱말만으로 잡지 않는다 (오탐 차단)."""
    docs = [{"id": "internal/x.md", "title": "회장과의 대화 (4) AI 혁신 불안과 에이전트 활용",
             "speaker": "회장", "effective_date": "2026-06-01", "body": "본문"}]
    md = GOOD_ARTICLE + """
에이전트를 도입한 팀에서는 검토 시간이 줄었다고 말합니다.
<!-- claims: C1 -->
"""
    r = va.verify(md, BASE, docs)
    assert r["internal_refs"] == []
    assert not [i for i in r["issues"] if i.kind == "내부 자료 시점 미표기"]


# --- 작성 모델 기록 (config/settings.yaml write_model 대조용) -------------------

def test_write_model_from_yaml_frontmatter():
    md = "---\nmodel: claude-opus-5\ndate: 2026-09-08\n---\n\n# 제목\n"
    assert va.parse_write_model(md) == "claude-opus-5"


def test_write_model_from_html_comment_with_multiple_fields():
    """<!-- 모델: x · 생성일: y --> 처럼 한 줄에 여러 필드가 와도 모델만 집는다."""
    md = "<!-- 모델: claude-fable-5-1 · 생성일: 2026-09-08 · base: 376850a -->\n\n# 제목\n"
    assert va.parse_write_model(md) == "claude-fable-5-1"


def test_write_model_absent_is_empty_not_error():
    assert va.parse_write_model("# 제목\n\n본문입니다.\n") == ""


def test_write_model_ignores_body_mentions():
    """머리말 범위 밖(본문)의 'model:' 표기는 집지 않는다."""
    md = "# 제목\n" + "\n본문 문장입니다.\n" * 20 + "\nmodel: 엉뚱한값\n"
    assert va.parse_write_model(md) == ""


def test_write_model_appears_in_report():
    md = "<!-- 모델: claude-opus-5 -->\n" + GOOD_ARTICLE
    r = va.verify(md, BASE)
    assert r["write_model"] == "claude-opus-5"
    report = va.render_report("t", Path("a.md"), Path("e.json"), r)
    assert "작성 모델: claude-opus-5" in report
    assert "머리말 미기재" in va.render_report(
        "t", Path("a.md"), Path("e.json"), va.verify(GOOD_ARTICLE, BASE))


# --- 참고자료 제목 중복 (같은 출처의 별개 글이 제목 앞부분을 공유하는 경우) ---------- #
# 실제 사례: josh-bersin "The Rise Of The Supermanager"(2025-10-20)와
# "The Rise Of The Supermanager: A New Role In The World of AI"(2025-09-23)는
# URL·발행일·본문이 다른 별개 글인데 참고자료에서는 같은 글로 보였다.

SUPERMANAGER_A = "The Rise Of The Supermanager"
SUPERMANAGER_B = "The Rise Of The Supermanager: A New Role In The World of AI"
BERSIN_DATES = {
    ("josh-bersin", SUPERMANAGER_A): "2025-10-20",
    ("josh-bersin", SUPERMANAGER_B): "2025-09-23",
    ("hbr", "HBR 기사 A"): "2026-01-02",
}


def test_reference_titles_annotate_only_indistinguishable_titles():
    out = va.reference_titles("josh-bersin", {SUPERMANAGER_A, SUPERMANAGER_B, "Affordability Is Not Just Inflation"},
                              BERSIN_DATES)
    assert out == [
        "Affordability Is Not Just Inflation",           # 구분되므로 발행일 없음
        f"{SUPERMANAGER_A} (2025-10-20)",
        f"{SUPERMANAGER_B} (2025-09-23)",
    ]


def test_reference_titles_leave_unique_title_alone_even_with_date():
    """발행일을 알아도 제목이 구분되면 병기하지 않는다 — 목록이 서지 정보로 붐비지 않게."""
    assert va.reference_titles("hbr", {"HBR 기사 A"}, BERSIN_DATES) == ["HBR 기사 A"]


def test_reference_titles_survive_missing_dates():
    """DB를 못 읽어 발행일이 없으면 제목 그대로 둔다 (검증은 DB 없이도 돌아야 한다)."""
    assert va.reference_titles("josh-bersin", {SUPERMANAGER_A, SUPERMANAGER_B}, {}) == [
        SUPERMANAGER_A, SUPERMANAGER_B]
    assert va.reference_titles("josh-bersin", {SUPERMANAGER_A}, None) == [SUPERMANAGER_A]


def test_report_disambiguates_same_source_documents_with_publish_date():
    ev = evidence(
        claim("C1", "josh-bersin", "optimistic", doc=SUPERMANAGER_A),
        claim("C2", "josh-bersin", "cautious", doc=SUPERMANAGER_B),
        claim("C3", "mckinsey-insights", "cautious", doc="McKinsey 리포트"),
        claim("C4", "theory-canon", "neutral", tier="T1", etype="theory", doc="흡수역량"),
    )
    md = """<!-- slug: t -->
# 제목

## 관찰된 신호

첫 문단이다.
<!-- claims: C1 -->

둘째 문단이다.
<!-- claims: C2 -->

셋째 문단이다.
<!-- claims: C3, C4 -->
"""
    r = va.verify(md, ev, None, BERSIN_DATES)
    report = va.render_report("t", Path("a.md"), Path("e.json"), r)
    assert f"{SUPERMANAGER_A} (2025-10-20)" in report
    assert f"{SUPERMANAGER_B} (2025-09-23)" in report
    assert "McKinsey 리포트 (" not in report          # 구분되는 제목에는 붙이지 않는다


def test_cdata_title_is_cleaned_before_date_annotation():
    """CDATA 래퍼가 섞인 제목도 벗긴 뒤 발행일과 짝지어야 한다."""
    # 앞 14자가 같아야 구분 불가로 잡힌다 (REF_TITLE_KEY_LEN)
    a, b = "같은 앞부분을 공유하는 기사 하나", "같은 앞부분을 공유하는 기사 둘"
    dates = {("bain-insights", a): "2026-02-01", ("bain-insights", b): "2026-03-01"}
    out = va.reference_titles("bain-insights", {f"<![CDATA[{a}]]>", b}, dates)
    assert out == [f"{b} (2026-03-01)", f"{a} (2026-02-01)"]

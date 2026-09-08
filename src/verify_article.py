"""아티클 검증 — 실사용 기준 (A2).

evidence 파일 전체가 아니라 **본문이 실제로 인용한 claim**만으로 강제 조건을 재계산한다.
본문 각 문단 뒤의 `<!-- claims: ID, ID -->` 주석이 사용 근거의 유일한 원본이다.

검사 항목
  1. 미등록 claim/출처 — 본문이 evidence에 없는 claim ID나 출처를 인용하면 실패(문장 지목)
  2. 독립 출처 3곳 이상 (사용 claim 기준)
  3. 상반 stance — optimistic·cautious 각 1건 이상 (CLAUDE.md 절대 규칙 2)
  4. 단일 출처 40% 초과 금지 (기획서 6.3)
  5. 수치 대조 — 본문 수치가 사용 claim의 metric/text에 있는지 (절대 규칙 3)
     · 달력 연도·참고자료 섹션은 면제(서지 정보)
     · 액션 문단의 기간·횟수(N주·주 N회 등)는 "처방 값"으로 분류해 대조하지 않는다.
       액션 판정은 섹션 이름이 아니라 문단의 액션 마커("리더가 할 일" 등)로 한다 —
       소제목을 메시지 문장으로 쓰라는 문체 지침과 충돌하지 않도록.
  6. 내부 자료 인용 대조 — 본문 직접 인용을 internal_docs 원문과 문구 대조
     · 문구 일치까지만 기계 검증. 발언 맥락 왜곡 여부는 사람 확인 항목이다.
     · 내부 자료를 인용한 문단에 연도 표기가 없으면 "내부 자료 시점 미표기"로 경고한다
       (article_style 5절 — 연례 행사·정기 발행물은 어느 해 것인지가 근거의 일부다).
  7. 참고자료 — 실사용 문서만 남기고, 올바른 목록을 리포트에 생성 (CDATA 래퍼 제거)

사용:
  python src/verify_article.py content/drafts/{slug}.md [--evidence ...] [--out ...] [--stdout]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from db import ROOT  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SOURCES_PATH = ROOT / "config" / "sources.yaml"

CLAIM_COMMENT_RE = re.compile(r"<!--\s*claims?:\s*([^>]+?)\s*-->", re.I)
HEADING_RE = re.compile(r"^#{1,6}\s+(.*)$")
# 정량 주장 후보 — 단위가 붙거나 범위로 쓰인 수치만 본다(목록 번호·연도 단독은 제외)
NUMBER_RE = re.compile(r"\d[\d,.]*\s*(?:~\s*\d[\d,.]*\s*)?(?:%|퍼센트|배|년|개월|주|일|명|건|점|만|억|조|배로)")
# 달력 연도(2026년·1999년)는 서지·시점 표기지 근거 수치가 아니다 — 기간("20~30년")과 구분한다
CALENDAR_YEAR_RE = re.compile(r"^(?:19|20)\d{2}\s*년$")
# 내부 자료(SKMS·경영층 메시지)는 claims 테이블을 거치지 않으므로 claim 대조 대상이 아니다
INTERNAL_REF_HINTS = ("내부:", "skms", "신년사", "internal/")
# 근거를 끌어다 쓰는 전형적 표현 — 주석 없는 문단에 있으면 claim 주석 누락을 의심한다
EVIDENTIAL_RE = re.compile(
    r"에\s*따르면|(?:연구|조사|설문|실험|보고서|분석|통계)\s*(?:결과|에서)|메타\s*분석"
    r"|보고(?:됐|된|되었)|관측(?:됐|된|되었)|실측(?:됐|된|되었)"
    r"|according to|study (?:finds|shows)|research shows", re.I)

MIN_INDEPENDENT_SOURCES = 3
MAX_SINGLE_SOURCE_RATIO = 0.40
# 수치 대조·출처 검사를 면제하는 섹션 (처방 값·서지 정보)
EXEMPT_HEADING_HINTS = ("시도할 것", "참고자료", "액션", "리더용", "실무자용",
                        "적용해본다면", "적용한다면", "제언")
# 액션·제언 문단 — 소제목을 메시지 문장으로 쓰라는 문체 지침(article_style 4절) 때문에
# 섹션 이름만으로는 못 찾는다. 문단 자체의 마커로도 인식한다.
# 박스 구조("리더가 할 일")뿐 아니라 제언형 산문("~해볼 수 있습니다")도 잡는다.
ACTION_MARKER_RE = re.compile(
    r"(?:리더|실무자|팀장|구성원|매니저|담당자)\s*(?:가|는|들이|들은)?\s*할\s*일"
    r"|리더용|실무자용|시도할\s*것|확인\s*지표|점검\s*지표"
    r"|적용해\s*본다면|적용한다면"
    r"|해\s*볼\s*수\s*있습니다|해\s*보는\s*것|시작해\s*볼|정해\s*둡?니다|적어\s*둡?니다"
    r"|권합니다|제안합니다|충분합니다")
# 처방 값 — 액션에서 "언제까지·몇 번"을 정하는 기간·횟수 단위. 근거 수치가 아니므로
# 우연히 claim 숫자에 매칭돼 "근거 있음"으로 잘못 통과하는 일이 없도록 따로 분류한다.
PRESCRIPTIVE_UNIT_RE = re.compile(r"^\d[\d,.]*\s*(?:주|개월|일|년|회|건|개|차례|분|시간)$")
# 본문의 직접 인용 — 내부 자료(경영층 발언 등) 원문 대조 대상
QUOTE_RE = re.compile(r"[\"“]([^\"“”]{10,200})[\"”]")
# 시점 표기 — 내부 자료를 인용한 문단에 연도가 있는지 본다 (2026년 / 2026 / '26년 아님)
YEAR_RE = re.compile(r"(?:19|20)\d{2}")
# 내부 문서 제목에서 이 문서를 특정하는 낱말만 골라낸다. 짧거나 흔한 말은 오탐이 된다
# ("CEO", "메시지"가 걸리면 무관한 문단까지 내부 인용으로 잡힌다).
TITLE_TOKEN_STOP = {"ceo", "패널토의", "메시지", "발표", "자료", "보고", "회의", "말씀",
                    "토의", "간담회", "워크숍", "워크샵", "세미나", "가이드", "지침", "문서",
                    "타운홀미팅", "상반기", "하반기", "wrap", "script", "vision", "system",
                    "management", "why", "next", "free", "human", "resource", "session"}
# 조사·어미가 붙은 어절은 고유명사가 아니라 서술형 제목의 조각이다("사례를", "중심으로").
# 이런 말로 문단을 찾으면 무관한 본문이 걸린다.
PARTICLE_TAIL_RE = re.compile(r"(?:의|를|을|와|과|로|으로|에|에서|는|은|이|가|도|만|과의|와의)$")
# RSS CDATA 래퍼가 제목에 섞여 들어온 경우 (bain-insights 등) 리포트에서는 벗겨 쓴다
CDATA_RE = re.compile(r"<!\[CDATA\[(.*?)\]\]>", re.S)


def clean_title(title: str) -> str:
    """CDATA 래퍼·잉여 공백을 벗긴 문서 제목."""
    if not title:
        return title
    return CDATA_RE.sub(r"\1", title).strip()


@dataclass
class Segment:
    """문단 하나와 그 문단이 인용한 claim ID."""
    heading: str
    text: str
    claim_ids: list[str] = field(default_factory=list)
    line: int = 0

    @property
    def exempt(self) -> bool:
        """섹션 이름 기반 면제 (참고자료·액션 섹션)."""
        return any(h in self.heading for h in EXEMPT_HEADING_HINTS)

    @property
    def is_action(self) -> bool:
        """액션 문단인가 — 섹션 이름 또는 문단 안의 액션 마커로 판정."""
        return self.exempt or bool(ACTION_MARKER_RE.search(self.text))


@dataclass
class Issue:
    level: str      # "fail" | "warn"
    kind: str
    message: str
    where: str = ""


def load_evidence(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {c["id"]: c for c in data.get("claims", [])}


def load_internal_docs() -> list[dict]:
    """internal_docs에서 api_eligible=1 문서를 읽어온다 (인용 원문 대조용).

    DB에 붙지 못하면 빈 목록을 반환한다 — 검증 자체는 DB 없이도 돌아야 하므로
    내부 인용 대조만 "확인 불가"로 남기고 나머지 검사는 그대로 진행한다.
    """
    try:
        from db import connect
        conn = connect()
        rows = conn.execute(
            "SELECT id, title, speaker, body, effective_date "
            "FROM internal_docs WHERE api_eligible = 1"
        ).fetchall()
        conn.close()
        return [{"id": r["id"], "title": r["title"], "speaker": r["speaker"],
                 "body": r["body"] or "", "effective_date": r["effective_date"]}
                for r in rows]
    except Exception:  # noqa: BLE001 — DB 없음·스키마 미적용 등은 치명적이지 않다
        return []


def _squash(s: str) -> str:
    """공백·문장부호 차이를 무시한 대조용 정규화."""
    return re.sub(r"[\s·,.\"'“”‘’]+", "", s or "")


def _title_tokens(title: str) -> list[str]:
    """내부 문서를 특정하는 제목 낱말 — 간접 서술(인용부호 없는 언급)을 잡기 위한 것.

    "2026 이천포럼 CEO 패널토의" → ["이천포럼"]. 연도가 섞인 어절("2026년"),
    조사가 붙은 어절("사례를", "회장의"), 흔한 낱말은 버린다. 남는 게 없으면 빈
    목록이고, 그 문서는 간접 서술로 찾지 않는다.
    """
    toks = re.split(r"[\s·,()\[\]—–\-/_:]+", clean_title(title) or "")
    return [t for t in toks
            if len(t) >= 3
            and not YEAR_RE.search(t)                 # "2026년"은 아무 문단에나 걸린다
            and not PARTICLE_TAIL_RE.search(t)
            and t.lower() not in TITLE_TOKEN_STOP]


def _declared_internal_docs(references: list[str], docs: list[dict]) -> list[dict]:
    """참고자료의 `내부:` 항목이 가리키는 내부 문서만 골라낸다.

    간접 서술을 제목 낱말로 찾을 때, 내부 문서 전체(수십 건)를 대상으로 하면 "에이전트",
    "인프라" 같은 제목 낱말이 무관한 문단에 걸린다. 아티클이 참고자료에 스스로 밝힌
    문서로 후보를 좁히면 그 오탐이 사라진다. 직접 인용 대조(9)는 이 제한을 받지 않는다.
    """
    internal_refs = [r for r in references if any(h in r.lower() for h in INTERNAL_REF_HINTS)]
    out = []
    for d in docs:
        title = clean_title(d.get("title") or "")
        squashed = _squash(title)
        toks = _title_tokens(title)
        for ref in internal_refs:
            if (squashed and squashed in _squash(ref)) or                sum(1 for t in toks if t in ref) >= 2:
                out.append(d)
                break
    return out


def _doc_year(doc: dict) -> str:
    """내부 자료의 시점 — 머리말 date(effective_date)의 연도. 없으면 제목에서 찾는다."""
    m = YEAR_RE.search(str(doc.get("effective_date") or ""))
    if not m:
        m = YEAR_RE.search(clean_title(doc.get("title") or ""))
    return m.group(0) if m else ""


def source_aliases() -> dict[str, str]:
    """sources.yaml의 name·id → source_id 별칭표 (본문 출처 표기 탐지용)."""
    out: dict[str, str] = {}
    try:
        data = yaml.safe_load(SOURCES_PATH.read_text(encoding="utf-8")) or {}
    except OSError:
        return out
    for s in data.get("sources", []):
        sid = s.get("id")
        if not sid:
            continue
        out[sid.lower()] = sid
        name = (s.get("name") or "").strip()
        if name:
            out[name.lower()] = sid
            # "DBR(동아비즈니스리뷰)" → "DBR"
            short = re.split(r"[(（]", name)[0].strip()
            if len(short) >= 3:
                out[short.lower()] = sid
    return out


def parse_article(md: str) -> tuple[list[Segment], list[str]]:
    """문단과 뒤따르는 claims 주석을 짝짓는다. 반환: (문단 목록, 참고자료 항목)."""
    segments: list[Segment] = []
    references: list[str] = []
    heading = ""
    buf: list[str] = []
    buf_line = 0

    def flush(claim_ids: list[str] | None = None) -> None:
        text = "\n".join(buf).strip()
        if text:
            segments.append(Segment(heading, text, claim_ids or [], buf_line))
        buf.clear()

    for i, raw in enumerate(md.splitlines(), 1):
        line = raw.rstrip()
        m_head = HEADING_RE.match(line)
        if m_head:
            flush()
            heading = m_head.group(1).strip()
            continue
        m_claim = CLAIM_COMMENT_RE.search(line)
        if m_claim:
            ids = [c.strip() for c in re.split(r"[,\s]+", m_claim.group(1)) if c.strip()]
            flush(ids)
            continue
        if line.startswith("<!--"):        # slug·유산 표기 등 다른 주석은 본문이 아님
            continue
        if not line.strip():
            flush()
            continue
        if "참고자료" in heading and line.strip().startswith("-"):
            references.append(line.strip().lstrip("- ").strip())
        if not buf:
            buf_line = i
        buf.append(line)
    flush()
    return segments, references


def _first_sentence(text: str, limit: int = 70) -> str:
    """표·목록에 넣어도 깨지지 않도록 한 줄로 접은 첫 문장."""
    flat = re.sub(r"\s+", " ", text.strip()).replace("|", "\\|")
    s = re.split(r"(?<=[.!?。])\s|(?<=다)\s", flat)[0]
    return (s[:limit] + "…") if len(s) > limit else s


def verify(md: str, evidence: dict, internal_docs: list[dict] | None = None) -> dict:
    """실사용 기준 검증 결과를 dict로 반환.

    internal_docs를 주면 본문의 직접 인용을 내부 자료 원문과 대조한다(문구 일치까지만 —
    발언 맥락 왜곡 여부는 사람 확인 항목이다, CLAUDE.md 문체 규칙).
    """
    segments, references = parse_article(md)
    used_segments = [s for s in segments if s.claim_ids]
    issues: list[Issue] = []

    # 1) 미등록 claim ID — 본문이 evidence에 없는 근거를 인용한 경우
    used_ids: list[str] = []
    for seg in used_segments:
        for cid in seg.claim_ids:
            if cid not in evidence:
                issues.append(Issue(
                    "fail", "미등록 claim",
                    f"evidence에 없는 claim ID `{cid}`를 인용",
                    f"{seg.heading or '(제목 없음)'} / {seg.line}행: “{_first_sentence(seg.text)}”"))
            else:
                used_ids.append(cid)

    used = [evidence[c] for c in dict.fromkeys(used_ids)]     # 순서 유지 중복 제거
    unused = [c for cid, c in evidence.items() if cid not in set(used_ids)]

    # 2) 본문이 인용한 출처 표기 검사
    aliases = source_aliases()
    evidence_sources = {c.get("source") for c in evidence.values()}
    for seg in segments:
        if seg.exempt:
            continue
        seg_sources = {evidence[c].get("source") for c in seg.claim_ids if c in evidence}
        low = seg.text.lower()
        for alias, sid in aliases.items():
            if len(alias) < 3 or alias not in low:
                continue
            if sid not in evidence_sources:
                issues.append(Issue(
                    "fail", "미등록 출처",
                    f"evidence에 없는 출처 `{sid}`를 본문에서 인용",
                    f"{seg.heading or '(제목 없음)'} / {seg.line}행: “{_first_sentence(seg.text)}”"))
            elif seg_sources and sid not in seg_sources:
                issues.append(Issue(
                    "warn", "출처-근거 불일치",
                    f"문단이 `{sid}`를 언급하지만 이 문단의 claim 출처는 {sorted(seg_sources)}",
                    f"{seg.heading or '(제목 없음)'} / {seg.line}행"))

    # 3~5) 사용 claim 기준 강제 조건
    sources = [c.get("source", "?") for c in used]
    counts: dict[str, int] = {}
    for s in sources:
        counts[s] = counts.get(s, 0) + 1
    stances = {c.get("stance") for c in used}
    top_source, top_n = (max(counts.items(), key=lambda kv: kv[1]) if counts else ("-", 0))
    ratio = (top_n / len(used)) if used else 0.0

    if len(counts) < MIN_INDEPENDENT_SOURCES:
        issues.append(Issue("fail", "독립 출처 부족",
                            f"사용 claim의 독립 출처 {len(counts)}곳 — {MIN_INDEPENDENT_SOURCES}곳 이상 필요"))
    if not ({"optimistic", "cautious"} <= stances):
        issues.append(Issue("fail", "상반 stance 없음",
                            f"사용 claim의 stance {sorted(s for s in stances if s)} — "
                            "optimistic·cautious 각 1건 이상 필요"))
    if ratio > MAX_SINGLE_SOURCE_RATIO:
        issues.append(Issue("fail", "단일 출처 편중",
                            f"`{top_source}` {top_n}/{len(used)}건 = {ratio:.0%} "
                            f"— {MAX_SINGLE_SOURCE_RATIO:.0%} 초과"))

    # 6) 수치 대조 — 사용 claim의 metric/text에 근거가 있는지
    haystack = " ".join((c.get("metric") or "") + " " + (c.get("text") or "") for c in used)
    hay_digits = set(re.findall(r"\d[\d,.]*", haystack))
    # status: "ok"(근거 있음) | "fail"(근거 없음) | "prescriptive"(처방 값 — 대조 대상 아님)
    numbers: list[tuple[Segment, str, str]] = []
    for seg in segments:
        if "참고자료" in seg.heading:      # 서지 정보 — 통째 면제
            continue
        for token in NUMBER_RE.findall(seg.text):
            tok = token.strip()
            if CALENDAR_YEAR_RE.match(tok):             # 연도 표기는 서지 정보 — 근거 수치 아님
                continue
            # 액션 문단의 기간·횟수는 실행 처방으로 제안한 값이다. 근거 대조를 하면
            # 한 자리 숫자가 claim의 큰 수에 부분 일치해 "근거 있음"으로 잘못 통과한다.
            if seg.is_action and PRESCRIPTIVE_UNIT_RE.match(tok):
                numbers.append((seg, tok, "prescriptive"))
                continue
            digits = re.findall(r"\d[\d,.]*", tok)
            ok = all(any(d.rstrip(".,") in h or h in d.rstrip(".,") for h in hay_digits)
                     for d in digits) if digits else True
            numbers.append((seg, tok, "ok" if ok else "fail"))
            if not ok:
                issues.append(Issue(
                    "fail", "수치 근거 없음",
                    f"본문 수치 “{tok}”가 사용 claim의 metric·text에 없음",
                    f"{seg.heading or '(제목 없음)'} / {seg.line}행: “{_first_sentence(seg.text)}”"))

    # 7) 참고자료 — 실사용 문서만
    used_docs: dict[str, set[str]] = {}
    for c in used:
        # 수집 단계에서 섞여 들어온 CDATA 래퍼는 벗겨서 싣는다 (참고자료에 그대로 나가지 않도록)
        used_docs.setdefault(c.get("source", "?"), set()).add(
            clean_title(c.get("doc") or "") or "(문서명 없음)")
    for ref in references:
        low = ref.lower()
        if any(h in low for h in INTERNAL_REF_HINTS):   # 내부 자료는 claim 대조 대상이 아님
            continue
        by_source = any(sid in low or alias in low
                        for alias, sid in aliases.items() if sid in used_docs)
        # 문서명 매칭은 괄호 앞 제목만 본다("심리적 안전감 (Psychological Safety)" → "심리적 안전감")
        by_doc = any(re.split(r"[(（]", doc)[0].strip().lower()[:14] in low
                     for docs in used_docs.values() for doc in docs
                     if len(re.split(r"[(（]", doc)[0].strip()) >= 4)
        if not (by_source or by_doc):
            issues.append(Issue("warn", "참고자료 실사용 없음",
                                f"사용 claim과 연결되지 않는 참고자료 항목 — 실사용만 남긴다: “{ref[:60]}”"))

    # 8) 근거 주석 누락 의심 — 주석 없는 문단인데 정량·인용 표현이 있으면 사람 검토로 넘긴다
    missing_marks: list[tuple[Segment, str]] = []
    for seg in segments:
        if seg.claim_ids or "참고자료" in seg.heading:
            continue
        reasons = []
        if EVIDENTIAL_RE.search(seg.text):
            reasons.append("인용 표현")
        # 액션 문단의 처방 값은 근거 주석 대상이 아니다 (인용 표현만 본다).
        # 섹션 이름이 아니라 문단의 액션 마커로 판정하므로 소제목이 메시지 문장이어도 걸린다.
        nums = [t.strip() for t in NUMBER_RE.findall(seg.text)
                if not CALENDAR_YEAR_RE.match(t.strip())
                and not (seg.is_action and PRESCRIPTIVE_UNIT_RE.match(t.strip()))]
        if nums:
            reasons.append(f"수치({', '.join(nums[:3])})")
        if reasons:
            missing_marks.append((seg, " · ".join(reasons)))
            issues.append(Issue(
                "warn", "근거 주석 누락 의심",
                f"{' · '.join(reasons)}이 있는데 `<!-- claims: ... -->` 주석이 없음",
                f"{seg.heading or '(제목 없음)'} / {seg.line}행: “{_first_sentence(seg.text)}”"))

    # 9) 내부 자료 인용 대조 — 본문의 직접 인용이 내부 문서 원문과 문구까지 일치하는지
    quotes: list[dict] = []
    docs = internal_docs or []
    for seg in segments:
        # 액션 문단의 따옴표는 인용이 아니라 확인지표에 이름을 붙인 표현이다
        # ("재배치한 시간으로 새로 시작한 일"). 대조 대상으로 잡으면 오탐만 쌓인다.
        if "참고자료" in seg.heading or seg.is_action:
            continue
        for q in QUOTE_RE.findall(seg.text):
            hit = next((d for d in docs if _squash(q) in _squash(d["body"])), None)
            if hit:
                quotes.append({"quote": q, "seg": seg, "status": "match",
                               "doc": clean_title(hit["title"]), "speaker": hit.get("speaker")})
                continue
            # 내부 자료에 없으면 외부 claim 본문에서 온 인용인지 확인한다
            if any(_squash(q) in _squash((c.get("text") or "") + (c.get("metric") or ""))
                   for c in used):
                quotes.append({"quote": q, "seg": seg, "status": "external",
                               "doc": "(사용 claim 본문)", "speaker": None})
                continue
            quotes.append({"quote": q, "seg": seg, "status": "unmatched",
                           "doc": None, "speaker": None})
            if docs:   # DB를 못 읽었으면 단정하지 않는다
                issues.append(Issue(
                    "warn", "인용 원문 미확인",
                    f"직접 인용 “{q[:40]}…”의 원문을 내부 자료·사용 claim에서 찾지 못함",
                    f"{seg.heading or '(제목 없음)'} / {seg.line}행"))

    # 10) 내부 자료 인용의 시점 표기 — 연례 행사·정기 발행물은 어느 해 것인지가 근거의
    #     일부다(article_style 5절). 직접 인용뿐 아니라 인용부호 없는 간접 서술도 본다:
    #     "이천포럼 패널토의에서 …" 처럼 쓰면 인용부호가 없어 9)에서는 잡히지 않는다.
    #     액션 문단도 대상이다 — 수치 면제와 달리 시점 표기는 면제 사유가 없다.
    internal_refs: list[dict] = []
    quoted_doc = {id(q["seg"]): q["doc"] for q in quotes if q["status"] == "match"}
    declared = _declared_internal_docs(references, docs)
    for seg in segments:
        if "참고자료" in seg.heading:
            continue
        doc = next((d for d in docs if clean_title(d["title"]) == quoted_doc.get(id(seg))), None)
        if doc is None:
            doc = next((d for d in declared
                        if any(t in seg.text for t in _title_tokens(d["title"]))), None)
        if doc is None:
            continue
        title, year = clean_title(doc["title"]), _doc_year(doc)
        dated = bool(YEAR_RE.search(seg.text))
        internal_refs.append({"seg": seg, "doc": title, "year": year, "dated": dated})
        if not dated:
            issues.append(Issue(
                "warn", "내부 자료 시점 미표기",
                f"내부 자료 「{title}」를 인용했는데 문단에 연도 표기가 없음"
                + (f" — 자료 시점은 {year}년이다" if year else ""),
                f"{seg.heading or '(제목 없음)'} / {seg.line}행: “{_first_sentence(seg.text)}”"))

    return {
        "segments": segments, "used_segments": used_segments, "used": used, "unused": unused,
        "missing_marks": missing_marks,
        "counts": counts, "ratio": ratio, "top_source": top_source, "stances": stances,
        "numbers": numbers, "references": references, "used_docs": used_docs,
        "quotes": quotes, "internal_refs": internal_refs, "internal_available": bool(docs),
        "issues": issues,
        "passed": not any(i.level == "fail" for i in issues),
    }


def _rel(p: Path) -> str:
    """리포트에는 저장소 상대경로로 적는다 (실행 위치에 따라 달라지지 않도록)."""
    try:
        return p.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return p.as_posix()


def render_report(slug: str, article_path: Path, evidence_path: Path, r: dict) -> str:
    used, counts = r["used"], r["counts"]
    lines = [
        f"# 검증 리포트 (실사용 기준) — {slug}", "",
        f"대상: `{_rel(article_path)}` · 증거: `{_rel(evidence_path)}`",
        f"판정: **{'통과' if r['passed'] else '실패'}** "
        f"(실패 {sum(1 for i in r['issues'] if i.level == 'fail')}건 · "
        f"경고 {sum(1 for i in r['issues'] if i.level == 'warn')}건)",
        "",
        "> 이 리포트는 evidence 파일 전체가 아니라 **본문이 실제 인용한 claim**만으로 계산한다.",
        "",
        "## 1. 본문 사용 claim (문장 ↔ claim ID)", "",
    ]
    if not r["used_segments"]:
        lines.append("사용 claim 없음 — 본문에 `<!-- claims: ... -->` 주석이 없다.")
    for seg in r["used_segments"]:
        lines.append(f"**[{seg.heading or '(제목 없음)'}] {seg.line}행** — “{_first_sentence(seg.text, 90)}”")
        for cid in seg.claim_ids:
            c = next((x for x in used if x["id"] == cid), None)
            if c:
                lines.append(f"- `{cid}` · {c.get('source')} · {c.get('tier')} · "
                             f"{c.get('stance')}/{c.get('evidence_type')} — {c.get('text', '')[:70]}")
            else:
                lines.append(f"- `{cid}` · **evidence에 없음(실패)**")
        lines.append("")

    lines += [
        f"사용 claim {len(used)}건 / evidence 전체 {len(used) + len(r['unused'])}건 "
        f"(미사용 {len(r['unused'])}건)", "",
        "## 2. 강제 조건 재계산 (사용 claim 기준)", "",
        "| 조건 | 기준 | 실측 | 판정 |", "|---|---|---|---|",
        f"| 독립 출처 | {MIN_INDEPENDENT_SOURCES}곳 이상 | {len(counts)}곳 "
        f"({', '.join(f'{k} {v}' for k, v in sorted(counts.items(), key=lambda kv: -kv[1]))}) | "
        f"{'✅' if len(counts) >= MIN_INDEPENDENT_SOURCES else '❌'} |",
        f"| 상반 stance | optimistic·cautious 각 1건+ | "
        f"{', '.join(sorted(s for s in r['stances'] if s)) or '없음'} | "
        f"{'✅' if {'optimistic', 'cautious'} <= r['stances'] else '❌'} |",
        f"| 단일 출처 비중 | {MAX_SINGLE_SOURCE_RATIO:.0%} 이하 | "
        f"{r['top_source']} {r['ratio']:.0%} | "
        f"{'✅' if r['ratio'] <= MAX_SINGLE_SOURCE_RATIO else '❌'} |",
        "",
        "## 3. 수치 대조 (절대 규칙 3)", "",
    ]
    if r["numbers"]:
        verdict = {"ok": "✅ 사용 claim에 있음", "fail": "❌ 근거 없음",
                   "prescriptive": "— 해당 없음 · 처방 값(실행 제안)"}
        lines += ["| 본문 수치 | 위치 | 근거 |", "|---|---|---|"]
        for seg, token, status in r["numbers"]:
            lines.append(f"| {token} | {seg.heading or '-'} {seg.line}행 | "
                         f"{verdict.get(status, status)} |")
        n_pres = sum(1 for _, _, s in r["numbers"] if s == "prescriptive")
        if n_pres:
            lines += ["", f"처방 값 {n_pres}건은 근거 대조 대상이 아니다 — 액션에서 제안한 "
                          "기간·횟수이므로 claim 수치와 우연히 일치해도 근거로 세지 않는다."]
    else:
        lines.append("검사 대상 수치 없음 (참고자료 섹션은 면제).")

    lines += ["", "## 4. 내부 자료 인용 대조 (경영층 발언·SKMS)", ""]
    if not r.get("internal_available"):
        lines.append("내부 자료를 읽지 못해 대조하지 못했다 (DB 미연결) — 사람 확인 필요.")
    elif not r.get("quotes"):
        lines.append("본문에 직접 인용 없음.")
    else:
        mark = {"match": "✅ 원문 문구 일치", "external": "· 외부 claim 본문에서 인용",
                "unmatched": "⚠️ 원문 미확인"}
        lines += ["| 본문 인용 | 위치 | 대조 대상 | 결과 |", "|---|---|---|---|"]
        for q in r["quotes"]:
            src = q["doc"] or "찾지 못함"
            if q.get("speaker"):
                src += f" ({q['speaker']})"
            lines.append(f"| “{q['quote'][:50]}{'…' if len(q['quote']) > 50 else ''}” | "
                         f"{q['seg'].heading or '-'} {q['seg'].line}행 | {src} | "
                         f"{mark.get(q['status'], q['status'])} |")
        if any(q["status"] == "match" for q in r["quotes"]):
            lines += ["", "> 문구 일치까지만 기계 검증했다. **발언 맥락 왜곡 여부는 사람 확인 항목**"
                          "이다 (CLAUDE.md 문체 규칙 — 경영층 인용은 발언 맥락 확인 후 발행)."]

    if r.get("internal_available"):
        lines += ["", "**시점 표기** (article_style 5절 — 내부 자료 인용은 연도 명시가 필수)", ""]
        if not r.get("internal_refs"):
            lines.append("본문에 내부 자료 인용 없음.")
        else:
            lines += ["| 인용한 내부 자료 | 위치 | 자료 시점 | 본문 연도 표기 |", "|---|---|---|---|"]
            for ref in r["internal_refs"]:
                lines.append(f"| {ref['doc']} | {ref['seg'].heading or '-'} {ref['seg'].line}행 | "
                             f"{ref['year'] + '년' if ref['year'] else '(미상)'} | "
                             f"{'✅ 있음' if ref['dated'] else '⚠️ 없음'} |")

    lines += ["", "## 5. 근거 주석 누락 의심 (사람 검토)", ""]
    if r["missing_marks"]:
        lines += ["주석 없는 문단 중 정량·인용 표현이 있는 것 — 근거를 달았는지 확인한다.", "",
                  "| 위치 | 사유 | 문장 |", "|---|---|---|"]
        for seg, reason in r["missing_marks"]:
            lines.append(f"| {seg.heading or '-'} {seg.line}행 | {reason} | "
                         f"{_first_sentence(seg.text, 60)} |")
    else:
        lines.append("없음.")

    lines += ["", "## 6. 참고자료 (실사용 문서만)", ""]
    if r["used_docs"]:
        for src, docs in sorted(r["used_docs"].items()):
            lines.append(f"- **{src}**: {' / '.join(sorted(docs))}")
    else:
        lines.append("(사용 claim 없음)")

    lines += ["", "## 7. 지적 사항", ""]
    if not r["issues"]:
        lines.append("없음.")
    for i in r["issues"]:
        mark = "❌ 실패" if i.level == "fail" else "⚠️ 경고"
        lines.append(f"- {mark} · **{i.kind}** — {i.message}")
        if i.where:
            lines.append(f"  - 위치: {i.where}")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="아티클 실사용 기준 검증 (A2)")
    p.add_argument("article", help="검증할 아티클 md 경로")
    p.add_argument("--evidence", help="evidence json 경로 (기본: content/evidence/{slug}.json)")
    p.add_argument("--out", help="리포트 저장 경로 (기본: content/drafts/{slug}-verification.md)")
    p.add_argument("--stdout", action="store_true", help="파일로 쓰지 않고 리포트를 출력만 한다")
    args = p.parse_args(argv)

    article_path = Path(args.article)
    md = article_path.read_text(encoding="utf-8")
    m = re.search(r"<!--\s*slug:\s*([\w-]+)", md)
    slug = m.group(1) if m else article_path.stem.replace("-verification", "")

    evidence_path = Path(args.evidence) if args.evidence else ROOT / "content" / "evidence" / f"{slug}.json"
    if not evidence_path.exists():
        print(f"evidence 파일 없음: {evidence_path}")
        return 2

    result = verify(md, load_evidence(evidence_path), load_internal_docs())
    report = render_report(slug, article_path, evidence_path, result)

    if args.stdout:
        print(report)
    else:
        out = Path(args.out) if args.out else ROOT / "content" / "drafts" / f"{slug}-verification.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report, encoding="utf-8")
        print(f"검증 리포트 저장: {out}")

    fails = sum(1 for i in result["issues"] if i.level == "fail")
    print(f"판정: {'통과' if result['passed'] else '실패'} — 사용 claim {len(result['used'])}건, "
          f"실패 {fails}건, 경고 {sum(1 for i in result['issues'] if i.level == 'warn')}건")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

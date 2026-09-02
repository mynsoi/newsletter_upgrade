"""아티클 검증 — 실사용 기준 (A2).

evidence 파일 전체가 아니라 **본문이 실제로 인용한 claim**만으로 강제 조건을 재계산한다.
본문 각 문단 뒤의 `<!-- claims: ID, ID -->` 주석이 사용 근거의 유일한 원본이다.

검사 항목
  1. 미등록 claim/출처 — 본문이 evidence에 없는 claim ID나 출처를 인용하면 실패(문장 지목)
  2. 독립 출처 3곳 이상 (사용 claim 기준)
  3. 상반 stance — optimistic·cautious 각 1건 이상 (CLAUDE.md 절대 규칙 2)
  4. 단일 출처 40% 초과 금지 (기획서 6.3)
  5. 수치 대조 — 본문 수치가 사용 claim의 metric/text에 있는지 (절대 규칙 3)
     · 액션·참고자료 섹션은 면제(처방 값·서지 연도는 근거 수치가 아님)
  6. 참고자료 — 실사용 문서만 남기고, 올바른 목록을 리포트에 생성

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

MIN_INDEPENDENT_SOURCES = 3
MAX_SINGLE_SOURCE_RATIO = 0.40
# 수치 대조·출처 검사를 면제하는 섹션 (처방 값·서지 정보)
EXEMPT_HEADING_HINTS = ("시도할 것", "참고자료", "액션", "리더용", "실무자용")


@dataclass
class Segment:
    """문단 하나와 그 문단이 인용한 claim ID."""
    heading: str
    text: str
    claim_ids: list[str] = field(default_factory=list)
    line: int = 0

    @property
    def exempt(self) -> bool:
        return any(h in self.heading for h in EXEMPT_HEADING_HINTS)


@dataclass
class Issue:
    level: str      # "fail" | "warn"
    kind: str
    message: str
    where: str = ""


def load_evidence(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {c["id"]: c for c in data.get("claims", [])}


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
    s = re.split(r"(?<=[.!?。])\s|(?<=다)\s", text.strip())[0]
    return (s[:limit] + "…") if len(s) > limit else s


def verify(md: str, evidence: dict) -> dict:
    """실사용 기준 검증 결과를 dict로 반환."""
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
    numbers: list[tuple[Segment, str, bool]] = []
    for seg in segments:
        if seg.exempt:
            continue
        for token in NUMBER_RE.findall(seg.text):
            if CALENDAR_YEAR_RE.match(token.strip()):   # 연도 표기는 서지 정보 — 근거 수치 아님
                continue
            digits = re.findall(r"\d[\d,.]*", token)
            ok = all(any(d.rstrip(".,") in h or h in d.rstrip(".,") for h in hay_digits)
                     for d in digits) if digits else True
            numbers.append((seg, token.strip(), ok))
            if not ok:
                issues.append(Issue(
                    "fail", "수치 근거 없음",
                    f"본문 수치 “{token.strip()}”가 사용 claim의 metric·text에 없음",
                    f"{seg.heading or '(제목 없음)'} / {seg.line}행: “{_first_sentence(seg.text)}”"))

    # 7) 참고자료 — 실사용 문서만
    used_docs: dict[str, set[str]] = {}
    for c in used:
        used_docs.setdefault(c.get("source", "?"), set()).add(c.get("doc") or "(문서명 없음)")
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

    return {
        "segments": segments, "used_segments": used_segments, "used": used, "unused": unused,
        "counts": counts, "ratio": ratio, "top_source": top_source, "stances": stances,
        "numbers": numbers, "references": references, "used_docs": used_docs,
        "issues": issues,
        "passed": not any(i.level == "fail" for i in issues),
    }


def render_report(slug: str, article_path: Path, evidence_path: Path, r: dict) -> str:
    used, counts = r["used"], r["counts"]
    lines = [
        f"# 검증 리포트 (실사용 기준) — {slug}", "",
        f"대상: `{article_path.as_posix()}` · 증거: `{evidence_path.as_posix()}`",
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
        lines += ["| 본문 수치 | 위치 | 근거 |", "|---|---|---|"]
        for seg, token, ok in r["numbers"]:
            lines.append(f"| {token} | {seg.heading or '-'} {seg.line}행 | "
                         f"{'✅ 사용 claim에 있음' if ok else '❌ 근거 없음'} |")
    else:
        lines.append("검사 대상 수치 없음 (액션·참고자료 섹션은 면제).")

    lines += ["", "## 4. 참고자료 (실사용 문서만)", ""]
    if r["used_docs"]:
        for src, docs in sorted(r["used_docs"].items()):
            lines.append(f"- **{src}**: {' / '.join(sorted(docs))}")
    else:
        lines.append("(사용 claim 없음)")

    lines += ["", "## 5. 지적 사항", ""]
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

    result = verify(md, load_evidence(evidence_path))
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

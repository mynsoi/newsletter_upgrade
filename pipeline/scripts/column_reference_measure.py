"""칼럼 레퍼런스 골격 실측 — eval/column-reference-analysis.md의 기계 측정 부분.

원문 md 폴더(「유정식의 경영일기」 압축본을 푼 곳, 저장소 밖)를 받아 편별 수치만 출력한다.
원문 문장은 출력하지 않는다 (CLAUDE.md 절대 규칙 1). 도입 유형·명시 인용·개념 명명·마무리
유형은 사람이 코딩한 값이라 여기서 세지 않는다.

사용:
  python scripts/column_reference_measure.py <원문 폴더>
"""
from __future__ import annotations

import re
import statistics as st
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def body_paragraphs(text: str) -> list[str]:
    """머리말·인사말·이미지·(끝)·참고 목록을 뺀 본문 문단."""
    body = text.split("\n---\n", 1)[1]
    m = re.search(r"\n-{5,}\n", body)              # 연재 인사말 뒤 구분선 (06·20번)
    if m and m.start() < 600:
        body = body[m.end():]
    cut = re.search(r"\n\s*\*\s*참고", body)
    if cut:
        body = body[:cut.start()]
    body = body.replace("(끝)", "")
    paras = [p.strip() for p in re.split(r"\n\s*\n", body)
             if p.strip() and not p.strip().startswith("![")]
    fixed: list[str] = []                          # 페이지 넘김으로 끊긴 문단을 붙인다
    for p in paras:
        if fixed and (len(fixed[-1]) < 3 or (
                len(fixed[-1]) > 20 and not re.search(r"[.?!\"”)\]요죠다]$", fixed[-1]))):
            fixed[-1] += p
        else:
            fixed.append(p)
    return fixed


def ns(s: str) -> int:
    return len(re.sub(r"\s", "", s))


def measure(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    paras = body_paragraphs(text)
    joined = " ".join(paras)
    sents = [s.strip() for s in re.split(r"(?<=[.?!])\s+", joined) if s.strip()]
    ends = {"니다": 0, "죠": 0, "요": 0, "물음": 0, "기타": 0}
    advice = 0
    for s in sents:
        s2 = re.sub(r"[\s\"”’')\]]+$", "", s)
        if s2.endswith("?"):
            ends["물음"] += 1
        elif re.search(r"니다[.!]$", s2):
            ends["니다"] += 1
        elif re.search(r"죠[.!]$", s2):
            ends["죠"] += 1
        elif re.search(r"요[.!]$", s2):
            ends["요"] += 1
        else:
            ends["기타"] += 1
        if re.search(r"(?:세요|바랍니다|십시오|야 합니다)[.!]$", s2):
            advice += 1
    lens = [ns(p) for p in paras]
    turn = next((i + 1 for i, p in enumerate(paras)
                 if re.search(r"(^|\s)(하지만|그러나|그런데)", p)), None)
    m_ref = re.search(r"\*\s*참고", text)
    ref = text[m_ref.end():] if m_ref else ""
    return {
        "chars": ns("\n".join(paras)), "chars_ws": len(re.sub(r"\s+", " ", "\n".join(paras))),
        "paras": len(paras), "para_med": int(st.median(lens)), "first": lens[0], "last": lens[-1],
        "sents": len(sents), "q_first2": "?" in "".join(paras[:2]), "turn_para": turn,
        "advice": advice, "refs": len([ln for ln in ref.splitlines()
                                       if re.search(r"https?://|\(\d{4}", ln)]),
        **{f"end_{k}": v for k, v in ends.items()},
        "yeoreobun": joined.count("여러분"),
    }


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    files = sorted(p for p in Path(argv[0]).glob("[0-9][0-9]_*.md") if not p.name.startswith("00"))
    rows = [(p.name[:2], measure(p)) for p in files]
    keys = list(rows[0][1])
    print("#\t" + "\t".join(keys))
    for n, r in rows:
        print(n + "\t" + "\t".join(str(r[k]) for k in keys))
    for k in ("chars", "chars_ws", "paras", "para_med", "advice", "refs"):
        v = [r[k] for _, r in rows]
        print(f"{k}: 중앙값 {st.median(v)} · 범위 {min(v)}~{max(v)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

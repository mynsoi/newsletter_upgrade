"""수치 원문 대조 — 원고 본문의 숫자가 그 글이 고른 원문에 있는지 본다(2026-10-23 사용자: "출처에 없는 수치 0건"은 필요).

수치 개수는 제한하지 않는다(사용자 결정 — 맥락상 필요한 수치는 쓴다). 원문에서 찾지 못한 숫자만 확정 전에 경고로 보여 준다.
LLM 없이 코드로만 — 한국어 원고와 영어 원문 사이의 표기 차이(5천/5,000, 25만/quarter-million, 3주/three weeks,
3분의 2/two-thirds, 5%p/5 percentage points)를 값으로 맞춘다. '약·가량·넘게' 같은 어림 표시가 붙은 숫자는 큰 수는 5%, 작은 수는 ±1까지 같은 값으로 본다.
한계: 원문 전체에서 값을 찾으므로 1~12 같은 작은 수는 원문 어딘가에 같은 수가 있으면 통과한다(문맥까지는 안 본다).
  python3 -I scripts/num_check.py <원고 파일> <원문 경로(sources/ 기준)> ...   → JSON
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "sources"

KO_MUL = {"천": 1e3, "만": 1e4, "억": 1e8, "조": 1e12}
EN_MUL = {"thousand": 1e3, "k": 1e3, "million": 1e6, "m": 1e6, "mn": 1e6, "billion": 1e9, "bn": 1e9, "b": 1e9, "trillion": 1e12}
EN_NUM = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen "
                                      "fifteen sixteen seventeen eighteen nineteen twenty".split())}
EN_NUM.update({"thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
               "hundred": 100, "dozen": 12, "a": 1, "an": 1})
EN_FRAC = {"half": 0.5, "third": 1 / 3, "thirds": 1 / 3, "quarter": 0.25, "quarters": 0.25, "fifth": 0.2, "fifths": 0.2,
           "tenth": 0.1, "tenths": 0.1}
APPROX = re.compile(r"(약|대략|가량|여|넘게|넘는|이상|이하|정도|거의|안팎|남짓|미만|가까이|수준)")
YEAR = re.compile(r"^(19|20)\d\d$")


def _f(s):
    return float(s.replace(",", ""))


def source_values(text):
    """원문에 나오는 수 — 숫자 + 배수(thousand·만…), 영어 수 낱말, 분수 낱말."""
    vals = set()
    t = text.replace(" ", " ").replace("\xa0", " ")
    for m in re.finditer(r"(?<![\w.])(\d{1,3}(?:,\d{3})+|\d+)(\.\d+)?\s*-?\s*(thousand|million|billion|trillion|bn|mn|[kKmMbB](?![a-zA-Z])|천|만|억|조)?", t):
        v = _f(m.group(1) + (m.group(2) or ""))
        mul = (m.group(3) or "").lower()
        vals.add(v)
        if mul:
            vals.add(v * (KO_MUL.get(mul) or EN_MUL.get(mul, 1)))
    # 영어 수 낱말: "three people", "twenty-five", "a quarter-million", "two-thirds", "half a million"
    words = re.findall(r"[A-Za-z]+", t.lower())
    for i, w in enumerate(words):
        nxt = words[i + 1] if i + 1 < len(words) else ""
        if w in EN_NUM and w not in ("a", "an"):
            v = EN_NUM[w]
            if nxt in EN_NUM and EN_NUM[nxt] < 10 and v >= 20:  # twenty-five
                v += EN_NUM[nxt]
            vals.add(float(v))
            if nxt in EN_MUL:
                vals.add(v * EN_MUL[nxt])
            if nxt in EN_FRAC:  # two-thirds
                vals.add(v * EN_FRAC[nxt])
        if w in EN_FRAC:
            f = EN_FRAC[w]
            vals.add(f)
            if nxt in EN_MUL:  # quarter-million
                vals.add(f * EN_MUL[nxt])
            if nxt in ("a", "an") and i + 2 < len(words) and words[i + 2] in EN_MUL:  # half a million
                vals.add(f * EN_MUL[words[i + 2]])
    # 분수는 퍼센트로도(두 쪽 어느 표기든)
    for v in list(vals):
        if 0 < v < 1:
            vals.add(round(v * 100, 1))
    return vals


def body_numbers(text):
    """원고 본문의 숫자 — [(보이는 표기, 값, 어림 여부, 문장)]. 제목·그림 줄·연도는 뺀다."""
    out = []
    lines = [x for x in text.splitlines() if x.strip() and not x.startswith("#") and not x.startswith("![")]
    body = "\n".join(lines)
    for sent in re.split(r"(?<=[.?!。])\s+|\n+", body):
        for m in re.finditer(r"(\d+)\s*분의\s*(\d+)", sent):  # 3분의 2
            out.append((m.group(0), int(m.group(2)) / int(m.group(1)), True, sent.strip()))
        s2 = re.sub(r"\d+\s*분의\s*\d+", " ", sent)
        for m in re.finditer(r"(?<![\w.])(\d{1,3}(?:,\d{3})+|\d+)(\.\d+)?\s*(천|만|억|조)?", s2):
            raw = m.group(1) + (m.group(2) or "")
            if YEAR.match(raw) and not m.group(3):
                continue
            v = _f(raw) * KO_MUL.get(m.group(3) or "", 1)
            around = s2[max(0, m.start() - 4):m.end() + 6]
            out.append((m.group(0).strip(), v, bool(APPROX.search(around)), sent.strip()))
    return out


def found(v, approx, vals):
    """어림 표시가 있으면 큰 수(100 이상)는 5%, 작은 수(퍼센트 등)는 ±1까지 — 68%를 원문 70%로 봐주지 않게."""
    def ok(s):
        if not approx:
            return abs(v - s) <= max(0.005 * abs(s), 0.006)
        return abs(v - s) <= (0.05 * abs(s) if abs(s) >= 100 else 1)
    return any(ok(s) for s in vals)


def check(text, sources):
    """원고 본문 숫자 중 원문에서 못 찾은 것 — {"total": n, "missing": [{"num", "sentence"}], "sources": n}."""
    vals = set()
    n_src = 0
    for p in sources:
        f = SRC / p
        if f.is_file():
            vals |= source_values(f.read_text(encoding="utf-8"))
            n_src += 1
    nums = body_numbers(text)
    miss, seen = [], set()
    for disp, v, approx, sent in nums:
        if not found(v, approx, vals) and (disp, sent) not in seen:
            seen.add((disp, sent))
            miss.append({"num": disp, "sentence": sent[:160]})
    return {"total": len(nums), "missing": miss, "sources": n_src}


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    print(json.dumps(check(Path(a[0]).read_text(encoding="utf-8"), a[1:]), ensure_ascii=False, indent=1))

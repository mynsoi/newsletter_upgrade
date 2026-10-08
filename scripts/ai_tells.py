"""한국어 칼럼 초안의 AI 버릇을 센다 (멘토 지적 기준 + 흔한 번역투). 판정이 아니라 비교용 개수.

사용: python3 ai_tells.py 파일1.md 파일2.md ...
"""
import re
import sys

PATS = {
    "대비(아니라·아닙니다·보다)": r"아니라|(?:것은|건|게|때문은) 아닙|보다[ ,]",
    "나열(첫째·둘째)": r"(?:^|\s)(?:첫째|둘째|셋째|첫 번째|두 번째|세 번째)[,는 ]",
    "선언(저는 ~말하고 싶·분명히)": r"분명히 말|말하고 싶|말씀드리겠",
    "자문자답(~일까요? 바로)": r"[가-힣]+(?:을|를)? ?(?:까요|나요)\?",
    "번역투(~를 통해·~에 있어·~에 의해)": r"(?:을|를) 통해|에 있어(?:서)?\b|에 의해|에 대해",
    "형식명사(~것입니다·~셈)": r"것입니다|셈입니다|셈이죠",
    "구어 종결(~죠·~거든요·~는데요)": r"죠[.!?]|거든요|는데요|더군요|답니다",
    "끝(끝)·경구형 마무리": r"\(끝\)",
}


def body(path):
    t = open(path, encoding="utf-8").read()
    t = re.sub(r"^#.*\n", "", t, count=1)
    return t


def sentences(t):
    return [s for s in re.split(r"(?<=[.?!])\s+", re.sub(r"\s+", " ", t)) if len(s) > 1]


rows = []
for p in sys.argv[1:]:
    t = body(p)
    n = len(re.sub(r"\s", "", t))
    ss = sentences(t)
    avg = sum(len(re.sub(r"\s", "", s)) for s in ss) / max(1, len(ss))
    last = ss[-1] if ss else ""
    counts = {k: len(re.findall(v, t, flags=re.M)) for k, v in PATS.items()}
    rows.append((p, n, len(ss), avg, counts, last))

keys = list(PATS)
print("| 글 | 공백 제외 | 문장 | 문장 평균 | " + " | ".join(keys) + " |")
print("|---" * (4 + len(keys)) + "|")
for p, n, ns, avg, c, last in rows:
    name = "/".join(p.split("/")[-2:])
    print(f"| {name} | {n:,} | {ns} | {avg:.0f} | " + " | ".join(str(c[k]) for k in keys) + " |")
print()
for p, *_, last in rows:
    print(f"- {'/'.join(p.split('/')[-2:])} 마지막 문장: {last[:90]}")

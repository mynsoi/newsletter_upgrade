"""docs/2026-10-10-주제-위키-시험.html 만들기 — 표와 목록은 시험 결과 파일(wiki-eval/)에서 그대로 채운다.

사용: python3 docs/build_wiki_report.py
디자인: .herdr-web-ui/design-20261009-192345-8f64450b.md(Sparta) — 틀은 docs/report_template.html
"""
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVAL = ROOT / "wiki-eval"
DOCS = ROOT / "docs"


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def who(path):
    t = (ROOT / "sources" / path).read_text(encoding="utf-8")
    m = dict(re.findall(r"^(\w+): (.*)$", t.split("---", 2)[1], re.M)) if t.startswith("---") else {}
    return (m.get("author") or "").strip("'\"")


def topics(items):
    out = []
    for t in items:
        n = len(t["sources"])
        authors = len({who(s) for s in t["sources"]})
        out.append(f'<div class="topic"><b>{html.escape(t["name"])}</b><span>{html.escape(t["thesis"])}</span>'
                   f'<div class="src">원문 {n}편 · 작성자 {authors}명</div></div>')
    return "".join(out)


def main():
    m = load(EVAL / "metrics.json")
    A, B, C = m["A · 지금 방식"], m["B · 지금 방식 + 기억"], m["C · 위키"]
    keys = ["주제 수", "앞 회차와 겹치는 주제", "작성자 2명 이상인 주제", "원문 1편짜리 주제", "쓴 원문(40편 중)",
            "새로 모은 18편 중 쓴 것", "같은 주제로 보이는 쌍(목록 안)", "이미 쓴 글과 겹치는 주제", "새 18편 처리"]
    rows = "".join(f'<tr><th>{html.escape(k)}</th><td>{html.escape(str(A.get(k, "—")))}</td><td>{html.escape(str(B.get(k, "—")))}</td>'
                   f'<td class="pick">{html.escape(str(C.get(k, "—")))}</td></tr>' for k in keys)
    rows += '<tr><th>걸린 시간 (astra)</th><td>101초</td><td>116 + 175초</td><td class="pick">처음 40편 약 37분 · 이후 1편당 ~1분</td></tr>'
    merge = re.search(r"합침 (\d+)", C["새 18편 처리"]).group(1)
    page = (DOCS / "report_template.html").read_text(encoding="utf-8")
    fill = {
        "__BIG__": str(C["쓴 원문(40편 중)"]), "__A_USED__": str(A["쓴 원문(40편 중)"]), "__B_USED__": str(B["쓴 원문(40편 중)"]),
        "__C_MULTI__": str(C["작성자 2명 이상인 주제"]), "__C_MERGE__": merge, "__C_SINGLE__": str(C["원문 1편짜리 주제"]),
        "__ROWS__": rows,
        "__A_LIST__": topics(load(ROOT / "runs/topics/20261010-011350/astra.json")), "__A_N__": str(A["주제 수"]),
        "__B_LIST__": topics(load(EVAL / "B3.json")), "__B_N__": str(B["주제 수"]),
        "__C_LIST__": topics(load(EVAL / "C.json")), "__C_N__": str(C["주제 수"]),
    }
    for k, v in fill.items():
        page = page.replace(k, v)
    assert "__" not in re.sub(r"<script.*?</script>", "", page, flags=re.S).replace("__init__", ""), "채우지 않은 자리 있음"
    out = DOCS / "2026-10-10-주제-위키-시험.html"
    out.write_text(page, encoding="utf-8")
    print(out.relative_to(ROOT))


if __name__ == "__main__":
    main()

"""세 방식(A 지금 · B 지금+기억 · C 위키)의 원문 40편 최종 주제 후보를 비교한다.

사용: python3 wiki-eval/evaluate.py
결과: wiki-eval/report/index.html (블라인드 1·2·3 — '공개'를 누르면 정체·기계 지표) · wiki-eval/mapping.json · wiki-eval/metrics.json
기계 지표는 보조 근거일 뿐이다. 주제의 질은 멘토가 판단한다(LLM 채점 없음).
"""
import html
import json
import random
import re
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVAL = ROOT / "wiki-eval"
SRC = ROOT / "sources"
TOPICS = ROOT / "runs" / "topics"
WRITTEN = {"퇴근": {"originals/threads/05.md", "originals/linkedin/10.md"},
           "작은 반복": {"originals/linkedin/10.md", "originals/linkedin/07.md", "originals/threads/06.md"}}


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def meta(path):
    t = (SRC / path).read_text(encoding="utf-8")
    m = dict(re.findall(r"^(\w+): (.*)$", t.split("---", 2)[1], re.M)) if t.startswith("---") else {}
    who = (m.get("author") or m.get("title") or "").strip("'\"")
    return {"who": who, "site": path.split("/")[1], "date": m.get("date", "").strip("'\""), "url": m.get("url", "")}


def same(t, u):
    """같은 주제로 볼 근거(기계적 대용): 중심 원문이 같거나 원문 2편 이상을 함께 씀."""
    a, b = t["sources"], u["sources"]
    return bool(a and b) and (a[0] == b[0] or len(set(a) & set(b)) >= 2)


def metrics(final, earlier, phases):
    pool = set(phases["A"] + phases["B"])
    used = {s for t in final for s in t["sources"]}
    dup = sum(1 for t, u in combinations(final, 2) if same(t, u))
    rep = sum(1 for t in final if any(same(t, u) for r in earlier for u in r)) if earlier else None
    multi = sum(1 for t in final if len({meta(s)["who"] for s in t["sources"]}) >= 2)
    newu = len(used & set(phases["B"]))
    written = sum(1 for t in final if any(len(set(t["sources"]) & w) >= 2 or (t["sources"] and t["sources"][0] in w and len(w & set(t["sources"])) >= 1 and len(t["sources"]) <= 2) for w in WRITTEN.values()))
    return {"주제 수": len(final), "같은 주제로 보이는 쌍(목록 안)": dup,
            "앞 회차와 겹치는 주제": rep if rep is not None else "해당 없음(지도가 유지됨)",
            "작성자 2명 이상인 주제": multi, "쓴 원문(40편 중)": f"{len(used & pool)}",
            "새로 모은 18편 중 쓴 것": newu, "이미 쓴 글과 겹치는 주제": written}


def wiki_dispositions():
    log = (ROOT / "wiki" / "log.md").read_text(encoding="utf-8") if (ROOT / "wiki" / "log.md").exists() else ""
    phases = load(EVAL / "phases.json")
    out = {"합침": 0, "새 주제": 0, "보탬 없음": 0}
    for p in phases["B"]:
        m = re.search(r"ingest\s+\S*" + re.escape(p) + r"\s*\|\s*([^|\n]+)", log)
        if m:
            for k in out:
                if k in m.group(1):
                    out[k] += 1
    return out


def times():
    rows = []
    for f in ("timing.json", "timing-b.json"):
        if (EVAL / f).exists():
            rows += load(EVAL / f)
    return rows


def card(t, i):
    srcs = "".join(
        f'<li><a href="{html.escape(meta(s)["url"])}" target="_blank">{html.escape(meta(s)["site"])} · {html.escape(meta(s)["who"][:40])}</a> <span>{html.escape(meta(s)["date"])}</span></li>'
        for s in t["sources"])
    return (f'<div class="card" data-k="{i}"><div class="n">{i + 1:02d}</div><h3>{html.escape(t["name"])}</h3>'
            f'<p>{html.escape(t["thesis"])}</p><ul>{srcs}</ul>'
            f'<div class="vote"><button data-v="1">좋음</button><button data-v="0">별로</button></div></div>')


def main():
    phases = load(EVAL / "phases.json")
    a_rounds = [load(TOPICS / r / "astra.json") for r in ("20261009-200958", "20261009-211031", "20261010-004359")]
    arms = {
        "A · 지금 방식": (load(TOPICS / "20261010-011350" / "astra.json"), a_rounds),
        "B · 지금 방식 + 기억": (load(EVAL / "B3.json"), [a_rounds[0], load(EVAL / "B2.json")]),
        "C · 위키": (load(EVAL / "C.json"), []),
    }
    names = list(arms)
    random.Random(20261010).shuffle(names)
    mapping = {str(i + 1): n for i, n in enumerate(names)}
    (EVAL / "mapping.json").write_text(json.dumps(mapping, ensure_ascii=False, indent=1), encoding="utf-8")
    ms = {n: metrics(arms[n][0], arms[n][1], phases) for n in names}
    ms["C · 위키"]["새 18편 처리(합침/새 주제/보탬 없음)"] = wiki_dispositions()
    (EVAL / "metrics.json").write_text(json.dumps(ms, ensure_ascii=False, indent=1), encoding="utf-8")

    cols = "".join(f'<section data-arm="{k}"><h2>{k}</h2>' + "".join(card(t, i) for i, t in enumerate(arms[n][0])) + "</section>"
                   for k, n in mapping.items())
    keys = sorted({k for m in ms.values() for k in m})
    rows = "".join(f"<tr><th>{html.escape(k)}</th>" + "".join(f"<td>{html.escape(str(ms[n].get(k, '')))}</td>" for n in names) + "</tr>" for k in keys)
    tsum = {}
    for r in times():
        arm = "C · 위키" if r["step"].startswith(("ingest", "lint", "query")) else "B · 지금 방식 + 기억"
        tsum.setdefault(arm, []).append(f'{r["step"]} {r["sec"]}초')
    timing = "".join(f"<li><b>{html.escape(k)}</b>: {html.escape(' · '.join(v))}</li>" for k, v in tsum.items())
    page = (EVAL / "report_template.html").read_text(encoding="utf-8")
    page = (page.replace("__COLS__", cols).replace("__HEAD__", "".join(f"<th>{html.escape(n)}</th>" for n in names))
            .replace("__ROWS__", rows).replace("__TIMING__", timing).replace("__MAP__", json.dumps(mapping, ensure_ascii=False)))
    (EVAL / "report").mkdir(exist_ok=True)
    (EVAL / "report" / "index.html").write_text(page, encoding="utf-8")
    print(json.dumps(ms, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()

"""한 번만 — 오늘 시험 결과로 주제 지도(wiki/)를 새 형식으로 옮긴다 (2026-10-11, AI를 쓰지 않음)

- 카드: runs/topic-full/20261011-full/cards.json (원문 59편)
- 주제·판정: wiki-eval/filter_by_claude.json (Claude가 거르고 멘토가 "괜찮네") — 묶음도 이 판정의 묶음을 따른다
- 제목 후보: runs/topic-full/20261011-full/titles/<중심 원문>/astra.md
- 씀·진행 중: 예전 위키(git HEAD)의 status·used_in → 그 글의 첫 원문이 들어간 새 주제로. 글 설정의 from_wiki도 새 주제로 바꾼다
- 판정 예시: wiki/판정예시.md (다음 거르기가 따를 결)
예전 위키 페이지는 지운다(git 기록에 남는다).
사용: python3 -I wiki-eval/migrate_wiki_20261011.py
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import wiki as W  # noqa: E402

RUN = ROOT / "runs" / "topic-full" / "20261011-full"
F = json.loads((ROOT / "wiki-eval" / "filter_by_claude.json").read_text(encoding="utf-8"))
USED_VERDICT = {"threads/23": "쓸 만함", "linkedin/26": "보통", "linkedin/22": "뺌", "threads/05": "보통"}


def old_pages():
    """예전 위키(git HEAD)의 주제 페이지 — status·used_in만 읽는다."""
    ls = subprocess.run(["git", "-c", "core.quotepath=off", "ls-tree", "-r", "--name-only", "HEAD", "wiki"], cwd=ROOT,
                        capture_output=True, text=True, encoding="utf-8").stdout.split()
    out = []
    for p in ls:
        if p.count("/") == 2 and p.endswith(".md") and not p.startswith(("wiki/주제/",)):
            t = subprocess.run(["git", "show", f"HEAD:{p}"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8").stdout
            st = re.search(r"^status:\s*(\S+(?: \S+)?)", t, re.M)
            ui = re.search(r"^used_in:\s*\[(.*)\]", t, re.M)
            out.append((p, st.group(1).split("#")[0].strip() if st else "", [x.strip() for x in (ui.group(1).split(",") if ui else []) if x.strip()]))
    return out


def first_source(u):
    f = ROOT / u
    if u.startswith("columns/"):
        f = ROOT / u.replace(".md", ".process.json")
    if not f.exists():
        return None
    s = json.loads(f.read_text(encoding="utf-8")).get("sources", [])
    return W.key(s[0][0] if isinstance(s[0], list) else s[0]) if s else None


def main():
    cs = json.loads((RUN / "cards.json").read_text(encoding="utf-8"))
    olds = old_pages()
    # 예전 위키 지우기 — 주제 폴더들과 예전 규칙(새 규칙으로 바꿔 쓴다)
    for d in W.WIKI.iterdir():
        if d.is_dir() and d.name != "주제":
            shutil.rmtree(d)
    if W.TOPICS.exists():
        shutil.rmtree(W.TOPICS)
    W.CARDS.write_text(json.dumps(cs, ensure_ascii=False, indent=1), encoding="utf-8")

    entries = [(x, "쓸 만함") for x in F["good"]] + [(x, "보통") for x in F["ok"]] + [(x, None) for x in F["used"]] + [(x, "뺌") for x in F["drop"]]
    made = {}
    for x, verdict in entries:
        srcs = x[0].split(" + ")
        c = srcs[0]
        if len(x) == 2:  # 뺌: "무엇 — 왜"
            line, _, why = x[1].partition(" — ")
        else:
            line, why = x[1], x[2]
        aud = x[3] if len(x) > 3 else "전 직원"
        tf = RUN / "titles" / c.replace("/", "-") / "astra.md"
        titles = [re.sub(r"^\s*(?:\d+[.)]|[-*])\s*", "", l).strip().strip("*") for l in tf.read_text(encoding="utf-8").splitlines() if l.strip()] if tf.exists() else []
        t = {"center": c, "sources": srcs, "title": line, "why": why, "verdict": verdict or USED_VERDICT.get(c, "보통"),
             "audience": aud, "status": "쓸 수 있음", "used_in": [], "titles": titles[:8]}
        made[c] = t
        W.write_topic(t, cs)

    # 씀·진행 중 옮기기
    moved = []
    for page, st, ui in olds:
        if st not in ("씀", "진행 중"):
            continue
        for u in ui:
            s = first_source(u)
            t = next((t for t in made.values() if s in t["sources"]), None)
            if not t:
                continue
            t["used_in"] = list(dict.fromkeys(t["used_in"] + [u]))
            t["status"] = "씀" if (st == "씀" or u.startswith("columns/")) else (t["status"] if t["status"] == "씀" else "진행 중")
            W.write_topic(t, cs)
            newp = f"wiki/주제/{t['center'].replace('/', '-')}.md"
            moved.append(f"{page} ({st}) · {u} → {newp}")
            bp = ROOT / u
            if u.startswith("briefs/") and bp.exists():
                b = json.loads(bp.read_text(encoding="utf-8"))
                if b.get("from_wiki"):
                    b["from_wiki"] = newp
                    bp.write_text(json.dumps(b, ensure_ascii=False, indent=1), encoding="utf-8")

    # 판정 예시
    def ex_line(x):
        if len(x) == 2:
            return f"- [{x[0]}] {x[1]}"
        return f"- [{x[0]}] {x[1]} — {x[2]}" + (f" (대상: {x[3]})" if len(x) > 3 else "")
    ex = ["# 판정 예시", "",
          "거르기(Claude)가 따를 결. 금지 목록이 아니라 실제 판정이다. 멘토가 작업실에서 판정을 바꾸면 맨 아래 '멘토가 바꾼 판정'에 쌓인다.", "",
          "## 멘토가 괜찮다고 한 판정 (2026-10-11 — Claude가 원문 59편을 직접 읽고 거름, 멘토 \"괜찮네\")", "",
          "### 쓸 만함", *[ex_line(x) for x in F["good"]], "",
          "### 보통", *[ex_line(x) for x in F["ok"]], "",
          "### 이미 쓴 글과 겹침 (판정은 쓸 만함·보통·뺌 중 하나로, 겹침은 상태로 본다)", *[ex_line(x) for x in F["used"]], "",
          "### 뺌", *[ex_line(x) for x in F["drop"] + F["excluded_before"]], ""]
    W.EXAMPLES.write_text("\n".join(ex), encoding="utf-8")

    W.write_index(W.topics())
    (W.WIKI / "log.md").write_text("# 위키 이력\n", encoding="utf-8")
    W.log(["- 새 형식으로 옮김: 카드 59 · 주제 " + str(len(made)) + " (원문 카드 → 같은 주장 묶기 → 거르기 → 제목 후보). 예전 위키는 git 기록에.",
           *[f"- 옮김 {m}" for m in moved]])
    print("주제", len(made), "· 옮긴 상태", len(moved))
    print("\n".join(moved))


if __name__ == "__main__":
    main()

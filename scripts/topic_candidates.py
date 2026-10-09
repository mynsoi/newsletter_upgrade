"""주제 후보 — 모아 둔 원문 전체를 astra가 읽고 칼럼 주제를 낸다. 멘토는 고르기만 한다 (2026-10-09 멘토: "주제를 뽑는 것부터가 ai로").

사용:
  python3 topic_candidates.py                → runs/topics/<시각>/astra.json (주제마다 thesis·중심 원문·보조 원문)
  python3 topic_candidates.py --pick <회차> <번호>  → briefs/<회차>-<번호>.json (제목 후보 단계로 넘길 설정)
재료: sources/originals/ 아래 모든 원문(경영일기 infuture는 문체 참고라 뺀다). 원문 수 제한 없음.
"""
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "sources"
OUT = ROOT / "runs" / "topics"
STYLE_ONLY = {"infuture"}


def originals():
    rows = []
    for f in sorted((SRC / "originals").glob("*/*.md")):
        if f.parent.name in STYLE_ONLY or f.name.startswith("_"):
            continue
        rows.append(f)
    return rows


def meta(f):
    t = f.read_text(encoding="utf-8")
    m, body = {}, t
    if t.startswith("---"):
        _, head, body = t.split("---", 2)
        for line in head.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                m[k.strip()] = v.strip().strip("'\"")
    return m, body.strip()


def label(f):
    m, _ = meta(f)
    site = {"threads": "Threads", "linkedin": "LinkedIn"}.get(f.parent.name, f.parent.name)
    who = m.get("headline") or m.get("author") or ""
    date = m.get("date", "")
    return ", ".join(x for x in [site, who, date] if x)


def prompt(files):
    srcs = "\n\n".join(f"=== {f.relative_to(SRC)} ({label(f)}) ===\n{meta(f)[1]}" for f in files)
    return f"""아래 원문들은 사내 뉴스레터(SK E&S 전 직원 대상, 대부분 비개발 사무·현장 직군) 칼럼의 재료로 모은 글입니다.
이 재료로 쓸 수 있는 칼럼 주제를 내 주세요.

주제마다:
- thesis: 이 글이 말할 것 한두 문장
- sources: 중심 재료가 될 원문 경로를 맨 앞에, 보조 원문을 뒤에 (경로는 아래 === 뒤에 적힌 그대로)
- name: 주제를 부르는 짧은 이름

출력: JSON 배열만 주세요. [{{"name": "...", "thesis": "...", "sources": ["originals/...", ...]}}]
파일을 만들거나 명령을 실행하지 마세요.

{srcs}"""


def run():
    files = originals()
    d = OUT / time.strftime("%Y%m%d-%H%M%S")
    d.mkdir(parents=True, exist_ok=True)
    p = prompt(files)
    (d / "prompt.md").write_text(p, encoding="utf-8")
    out = d / "astra.md"
    with open(d / "run.log", "w", encoding="utf-8") as log:
        subprocess.run(["codex", "exec", "-m", "gpt-6-astra", "-C", str(d), "--skip-git-repo-check", "-s", "read-only",
                        "--ephemeral", "--color", "never", "-o", str(out), p],
                       cwd=d, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
    raw = out.read_text(encoding="utf-8") if out.exists() else ""
    m = re.search(r"\[.*\]", raw, re.S)
    items = json.loads(m.group(0)) if m else []
    known = {str(f.relative_to(SRC)) for f in files}
    for it in items:
        it["sources"] = [s for s in it.get("sources", []) if s in known]  # 없는 경로는 버린다 (시뮬레이션에서 틀린 경로가 단계를 멈춤)
    items = [it for it in items if it["sources"]]
    (d / "astra.json").write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"주제 후보 {len(items)}개 · 원문 {len(files)}편 → {d.relative_to(ROOT)}")


def pick(rnd, n):
    items = json.loads((OUT / rnd / "astra.json").read_text(encoding="utf-8"))
    it = items[int(n) - 1]
    k = f"{rnd}-{n}"
    b = {"topic": k, "label": it["name"], "thesis": it["thesis"],
         "sources": [[s, label(SRC / s)] for s in it["sources"]], "from_topics": f"runs/topics/{rnd}"}
    bp = ROOT / "briefs" / f"{k}.json"
    bp.write_text(json.dumps(b, ensure_ascii=False, indent=1), encoding="utf-8")
    print(bp.relative_to(ROOT))


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["--pick"]:
        pick(a[1], a[2])
    else:
        run()

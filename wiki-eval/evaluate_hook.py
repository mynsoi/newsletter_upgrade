"""지금 위키(wiki/)와 '이 글만의 것' 위키(wiki-hook/)의 주제를 블라인드 1·2로 비교한다 (2026-10-10).

사용: python3 -I wiki-eval/evaluate_hook.py
결과: docs/2026-10-10-이글만의것-블라인드.html (작업실 /docs/로 열림) · wiki-eval/mapping-hook.json · wiki-eval/metrics-hook.json
블라인드에는 제목·논지·원문만 보인다. '공개'를 누르면 정체·기계 지표, 그리고 새 위키의 '이 글만의 것'이 카드에 나온다.
기계 지표는 보조 근거일 뿐이다. 주제의 질은 멘토가 판단한다(LLM 채점 없음).
"""
import html
import json
import random
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVAL = ROOT / "wiki-eval"
SRC = ROOT / "sources"
OUT = ROOT / "docs" / "2026-10-10-이글만의것-블라인드.html"
ARMS = {"지금 위키": ROOT / "wiki", "'이 글만의 것' 위키": ROOT / "wiki-hook"}
ADVICE = re.compile(r"(하자|부터|의 몫|까지|하라|해야 한다)$")


def front(t):
    m = re.match(r"^---\n(.*?)\n---\n", t, re.S)
    return (dict(re.findall(r"^(\w+):\s*(.*)$", m.group(1), re.M)), t[m.end():]) if m else ({}, t)


def sections(body):
    out, cur = {}, None
    for line in body.splitlines():
        if line.startswith("## "):
            cur = line[3:].strip()
            out[cur] = []
        elif cur:
            out[cur].append(line)
    return {k: "\n".join(v).strip() for k, v in out.items()}


def meta(path):
    t = (SRC / path).read_text(encoding="utf-8")
    m, _ = front(t)
    who = (m.get("author") or m.get("title") or "").strip("'\"")
    return {"who": who, "site": path.split("/")[1], "url": m.get("url", "").strip("'\"")}


def topics(wiki):
    out = []
    for f in sorted(wiki.glob("*/*.md")):
        m, body = front(f.read_text(encoding="utf-8"))
        if m.get("type", "").strip() != "topic":
            continue
        sec = sections(body)
        srcs = list(dict.fromkeys(re.findall(r"\]\(\.\./\.\./sources/(originals/[^)]+?\.md)\)", sec.get("원문", ""))))
        out.append({"title": m.get("title", f.stem).strip("'\""), "thesis": sec.get("이 글이 말할 것", ""),
                    "hook": sec.get("이 글만의 것", ""), "sources": [s for s in srcs if (SRC / s).is_file()],
                    "page": f.relative_to(ROOT).as_posix()})
    return out


def metrics(ts):
    used = {s for t in ts for s in t["sources"]}
    pool = {f.relative_to(SRC).as_posix() for f in (SRC / "originals").glob("*/[0-9]*.md") if f.parent.name != "infuture"}
    return {"주제 수": len(ts),
            "제목이 권고형(~하자·~부터·~의 몫 등)으로 끝나는 주제": sum(1 for t in ts if ADVICE.search(t["title"])),
            "'이 글만의 것' 칸이 있는 주제": sum(1 for t in ts if t["hook"]),
            "원문 1편짜리 주제": sum(1 for t in ts if len(t["sources"]) == 1),
            "원문이 가장 많은 주제의 원문 수": max((len(t["sources"]) for t in ts), default=0),
            "작성자 2명 이상인 주제": sum(1 for t in ts if len({meta(s)["who"] for s in t["sources"]}) >= 2),
            f"쓴 원문 ({len(pool)}편 중)": len(used & pool)}


def card(t, i):
    srcs = "".join(f'<li><a href="{html.escape(meta(s)["url"])}" target="_blank" rel="noopener">{html.escape(meta(s)["site"])} · '
                   f'{html.escape(meta(s)["who"][:36])}</a></li>' for s in t["sources"])
    hook = f'<div class="hook"><b>이 글만의 것</b>{html.escape(t["hook"])}</div>' if t["hook"] else ""
    return (f'<article class="card" data-k="{i}"><div class="n">{i + 1:02d} · 원문 {len(t["sources"])}</div>'
            f'<h3>{html.escape(t["title"])}</h3><p>{html.escape(t["thesis"])}</p>{hook}<ul>{srcs}</ul>'
            f'<div class="vote"><button data-v="1">좋음</button><button data-v="0">별로</button></div></article>')


def main():
    arms = {n: topics(w) for n, w in ARMS.items()}
    names = list(arms)
    random.Random(202610102).shuffle(names)
    mapping = {str(i + 1): n for i, n in enumerate(names)}
    (EVAL / "mapping-hook.json").write_text(json.dumps(mapping, ensure_ascii=False, indent=1), encoding="utf-8")
    for n in names:  # 위키 안 순서(분야·파일 이름)가 정체를 드러내지 않게 섞는다
        random.Random(n).shuffle(arms[n])
    ms = {n: metrics(arms[n]) for n in names}
    (EVAL / "metrics-hook.json").write_text(json.dumps(ms, ensure_ascii=False, indent=1), encoding="utf-8")
    timing = json.loads((EVAL / "timing-hook.json").read_text(encoding="utf-8")) if (EVAL / "timing-hook.json").exists() else {}

    cols = "".join(f'<section data-arm="{k}"><h2>{k}</h2>' + "".join(card(t, i) for i, t in enumerate(arms[n])) + "</section>"
                   for k, n in mapping.items())
    keys = list(next(iter(ms.values())))
    rows = "".join(f"<tr><th>{html.escape(k)}</th>" + "".join(f"<td>{ms[n][k]}</td>" for n in names) + "</tr>" for k in keys)
    head = "".join(f"<th>{html.escape(n)}</th>" for n in names)
    t_line = (f"새 위키: 원문 넣기 {timing.get('ingest_s', 0) // 60}분 · 정리 {timing.get('lint_s', 0) // 60}분"
              + (f" · 못 넣은 원문 {len(timing['left'])}편" if timing.get("left") else "")) if timing else ""
    page = TEMPLATE.replace("__COLS__", cols).replace("__HEAD__", head).replace("__ROWS__", rows) \
        .replace("__MAP__", json.dumps(mapping, ensure_ascii=False)).replace("__TIMING__", html.escape(t_line))
    OUT.write_text(page, encoding="utf-8")
    print(json.dumps({"mapping": mapping, "metrics": ms}, ensure_ascii=False, indent=1))


TEMPLATE = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>주제 지도 비교</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Noto+Sans+KR:wght@400;500;600;700&display=swap" />
<style>
  :root { --canvas:#ffffff; --surface-soft:#f7f7f7; --surface-strong:#f2f2f2; --hairline:#dddddd; --hairline-soft:#ebebeb;
          --ink:#222222; --body:#3f3f3f; --muted:#6a6a6a; --muted-soft:#929292; --primary:#ff385c; --primary-active:#e00b41; --on-primary:#ffffff; }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--canvas); color:var(--ink); font-family:Inter, "Noto Sans KR", -apple-system, system-ui, sans-serif; }
  header { max-width:1400px; margin:0 auto; padding:40px 32px 20px; display:flex; align-items:end; justify-content:space-between; gap:16px; border-bottom:1px solid var(--hairline-soft); }
  h1 { font-size:28px; font-weight:700; margin:0; letter-spacing:-.01em; }
  header p { margin:6px 0 0; color:var(--muted); font-size:14px; }
  button { font:inherit; cursor:pointer; border-radius:8px; }
  #open { background:var(--primary); color:var(--on-primary); border:0; padding:12px 24px; font-weight:500; }
  #open:active { background:var(--primary-active); }
  main { max-width:1400px; margin:0 auto; padding:24px 32px 64px; display:grid; grid-template-columns:repeat(2, minmax(0, 1fr)); gap:32px; }
  section h2 { font-size:56px; font-weight:700; margin:0 0 4px; }
  section h2 small { display:block; font-size:15px; font-weight:600; color:var(--primary); margin-top:2px; }
  .score { font-size:14px; color:var(--muted); margin-bottom:14px; }
  .card { border:1px solid var(--hairline); border-radius:14px; padding:18px 20px; margin-bottom:12px; background:var(--canvas); }
  .card .n { font-size:12px; color:var(--muted-soft); }
  .card h3 { margin:4px 0 8px; font-size:18px; font-weight:600; line-height:1.4; word-break:keep-all; }
  .card p { margin:0 0 10px; color:var(--body); font-size:14.5px; line-height:1.7; word-break:keep-all; }
  .hook { display:none; background:var(--surface-soft); border-radius:8px; padding:10px 12px; margin:0 0 10px; font-size:13.5px; line-height:1.65; color:var(--body); word-break:keep-all; }
  .hook b { display:block; font-size:12px; color:var(--primary); margin-bottom:2px; }
  body.revealed .hook { display:block; }
  .card ul { margin:0; padding:0; list-style:none; font-size:12.5px; display:flex; flex-wrap:wrap; gap:4px 10px; }
  .card li a { color:var(--muted); text-decoration:none; }
  .card li a:hover { text-decoration:underline; }
  .vote { margin-top:12px; display:flex; gap:6px; }
  .vote button { border:1px solid var(--hairline); background:var(--canvas); color:var(--ink); padding:5px 14px; font-size:13px; border-radius:9999px; }
  .vote button.on[data-v="1"] { background:var(--ink); color:#fff; border-color:var(--ink); }
  .vote button.on[data-v="0"] { background:var(--surface-strong); color:var(--muted); border-color:var(--hairline); text-decoration:line-through; }
  #reveal { display:none; max-width:1400px; margin:0 auto; padding:0 32px 80px; }
  body.revealed #reveal { display:block; }
  h4 { font-size:22px; font-weight:600; margin:36px 0 12px; }
  table { width:100%; border-collapse:collapse; font-size:14px; }
  th, td { border-bottom:1px solid var(--hairline); padding:12px; text-align:left; vertical-align:top; }
  thead th { color:var(--muted); font-weight:500; }
  #reveal li { line-height:1.75; color:var(--body); }
  @media (max-width: 900px) { main { grid-template-columns:1fr; padding:16px 16px 40px; } header, #reveal { padding-left:16px; padding-right:16px; } }
</style>
</head>
<body>
<header>
  <div><h1>주제 지도 비교 — 원문 59편</h1><p>같은 원문, 다른 규칙. 카드마다 좋음·별로를 누른 뒤 공개하세요.</p></div>
  <button id="open">공개</button>
</header>
<main>__COLS__</main>
<div id="reveal">
  <h4>정체</h4>
  <p id="map"></p>
  <h4>기계 지표 (보조 근거 — 주제의 질은 멘토 판단)</h4>
  <table><thead><tr><th></th>__HEAD__</tr></thead><tbody>__ROWS__</tbody></table>
  <h4>무엇을 바꿨나</h4>
  <ul>
    <li>두 위키 모두 같은 원문 59편, 같은 '회사 이야기로 옮겨 쓰기'·대상 독자 규칙.</li>
    <li>새 위키만 다른 것: 주제마다 <b>이 글만의 것</b>(원문에서 가져온 구체적인 한 가지 — 이름·이유·장면·방법·고민·숫자)을 남기고, 논지는 거기서 나오게. 교육 자료에 이미 있는 일반 권고로만 읽히면 다시 쓴다. 합치기는 그 한 가지가 같을 때만.</li>
    <li>지금 위키는 원문을 한 편씩 쌓으며 여러 번 정리됐고, 새 위키는 59편을 한 번에 처음부터 넣고 한 번 정리했다 — 넣은 순서·횟수가 다르다.</li>
    <li>__TIMING__</li>
  </ul>
</div>
<script>
  const MAP = __MAP__;
  const key = (a, k) => `hook-eval:${a}:${k}`;
  const get = (k) => { try { return localStorage.getItem(k); } catch (e) { return null; } };
  const set = (k, v) => { try { localStorage.setItem(k, v); } catch (e) {} };
  function score() {
    document.querySelectorAll("section").forEach((s) => {
      const a = s.dataset.arm, cards = s.querySelectorAll(".card");
      let g = 0, b = 0;
      cards.forEach((c) => { const v = get(key(a, c.dataset.k)); if (v === "1") g++; if (v === "0") b++; });
      let el = s.querySelector(".score");
      if (!el) { el = document.createElement("div"); el.className = "score"; s.querySelector("h2").after(el); }
      el.textContent = `${cards.length}개 · 좋음 ${g} · 별로 ${b}`;
    });
  }
  document.querySelectorAll("section").forEach((s) => {
    const a = s.dataset.arm;
    s.querySelectorAll(".card").forEach((c) => {
      const v = get(key(a, c.dataset.k));
      c.querySelectorAll(".vote button").forEach((btn) => {
        if (btn.dataset.v === v) btn.classList.add("on");
        btn.onclick = () => {
          const on = btn.classList.contains("on");
          c.querySelectorAll(".vote button").forEach((x) => x.classList.remove("on"));
          if (!on) { btn.classList.add("on"); set(key(a, c.dataset.k), btn.dataset.v); } else set(key(a, c.dataset.k), "");
          score();
        };
      });
    });
  });
  score();
  document.getElementById("open").onclick = () => {
    document.body.classList.add("revealed");
    document.getElementById("map").innerHTML = Object.entries(MAP).map(([k, v]) => `<b>${k}</b> = ${v}`).join(" &nbsp;·&nbsp; ");
    document.querySelectorAll("section").forEach((s) => { const h = s.querySelector("h2"); if (!h.querySelector("small")) h.insertAdjacentHTML("beforeend", `<small>${MAP[s.dataset.arm]}</small>`); });
    document.getElementById("reveal").scrollIntoView({ behavior: "smooth" });
  };
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()

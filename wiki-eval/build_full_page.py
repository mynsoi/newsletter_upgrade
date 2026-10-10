"""원문 전체 주제 카드 + 제목 후보를 HTML로 — 작업실 /docs/에서 연다 (2026-10-11)

사용: python3 -I wiki-eval/build_full_page.py runs/topic-full/20261011-full
결과: docs/2026-10-11-주제별-제목후보-전체.html
제목 후보는 고르지 않고 astra가 낸 순서 그대로. 숫자 점검(checks.json)에 걸린 카드는 표시한다.
"""
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import title_candidates as tc  # noqa: E402

SRC = ROOT / "sources"
OUT = ROOT / "docs" / "2026-10-11-주제별-제목후보-전체.html"
e = html.escape


def front(t):
    m = re.match(r"^---\n(.*?)\n---\n", t, re.S)
    return dict(re.findall(r"^(\w+):\s*(.*)$", m.group(1), re.M)) if m else {}


def meta(k):
    m = front((SRC / "originals" / f"{k}.md").read_text(encoding="utf-8"))
    g = lambda x: m.get(x, "").strip().strip("'\"")
    return {"author": g("author"), "date": g("date"), "url": g("url")}


def wiki_titles(keys):
    out = []
    for f in sorted((ROOT / "wiki").glob("*/*.md")):
        t = f.read_text(encoding="utf-8")
        if any(f"originals/{k}.md" in t for k in keys):
            out.append(front(t).get("title", f.stem).strip("'\""))
    return list(dict.fromkeys(out))


def src_block(k, f, center, checks):
    m = meta(k)
    flag = f'<span class="flag">원문에 없는 숫자? {e(", ".join(checks[k]))}</span>' if k in checks else ""
    return f"""<div class="src {'center' if center else ''}">
  <div class="who"><a href="{e(m['url'])}" target="_blank" rel="noopener">{e(k.split('/')[0])} · {e(m['author'])}</a><span>{e(m['date'])}</span>{flag}</div>
  <div class="label">글쓴이가 하는 말</div><p class="claim">{e(f.get('글쓴이가 하는 말', ''))}</p>
  <div class="label">있었던 일</div><p>{e(f.get('있었던 일', ''))}</p>
</div>"""


def main(run):
    run = ROOT / run
    cards = json.loads((run / "cards.json").read_text(encoding="utf-8"))
    groups = json.loads((run / "groups.json").read_text(encoding="utf-8"))
    checks = json.loads((run / "checks.json").read_text(encoding="utf-8")) if (run / "checks.json").exists() else {}
    gs = [g for g in groups["groups"] if g["center"] in cards]
    gs.sort(key=lambda g: -len(g["sources"]))
    arts = []
    for i, g in enumerate(gs, 1):
        keys = [g["center"]] + [s for s in g["sources"] if s != g["center"] and s in cards]
        tf = run / "titles" / g["center"].replace("/", "-") / "astra.md"
        titles = "".join(f"<li>{e(t)}</li>" for t in (tc.round_items(tf) if tf.exists() else [])) or "<li class='none'>(제목 후보 없음 — 연결 끊김)</li>"
        olds = "".join(f"<li>{e(t)}</li>" for t in wiki_titles(keys)) or "<li>—</li>"
        srcs = "".join(src_block(k, cards[k], k == g["center"], checks) for k in keys)
        arts.append(f"""<article class="card" id="t{i}">
  <div class="n">주제 {i:02d} · 원문 {len(keys)}편</div>
  <ol class="titles">{titles}</ol>
  {srcs}
  <div class="foot"><div class="label">지금 주제 지도에서는</div><ul>{olds}</ul></div>
</article>""")
    ex = "".join(f"<li><b>{e(x['source'])}</b> — {e(x.get('reason', ''))}</li>" for x in groups.get("excluded", []))
    summary = f"원문 {len(cards)}편 → 주제 {len(gs)}개 · 칼럼 재료가 없어 뺀 원문 {len(groups.get('excluded', []))}편 · 숫자 점검에 걸린 카드 {len(checks)}개"
    OUT.write_text(PAGE.replace("__SUMMARY__", e(summary)).replace("__CARDS__", "".join(arts)).replace("__EXCLUDED__", ex or "<li>없음</li>"),
                   encoding="utf-8")
    print(OUT)


PAGE = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>주제별 제목 후보</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Noto+Sans+KR:wght@400;500;600;700&display=swap" />
<style>
  :root { --canvas:#ffffff; --surface-soft:#f7f7f7; --hairline:#dddddd; --hairline-soft:#ebebeb;
          --ink:#222222; --body:#3f3f3f; --muted:#6a6a6a; --muted-soft:#929292; --primary:#ff385c; }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--canvas); color:var(--ink); font-family:Inter, "Noto Sans KR", -apple-system, system-ui, sans-serif; }
  header { max-width:1100px; margin:0 auto; padding:48px 32px 24px; border-bottom:1px solid var(--hairline-soft); }
  h1 { font-size:28px; font-weight:700; margin:0 0 8px; letter-spacing:-.01em; }
  header p { margin:0; color:var(--muted); font-size:15px; line-height:1.7; }
  main { max-width:1100px; margin:0 auto; padding:24px 32px 40px; display:grid; gap:20px; }
  .card { border:1px solid var(--hairline); border-radius:14px; padding:24px 28px; }
  .n { font-size:13px; color:var(--muted-soft); }
  .titles { margin:12px 0 20px; padding-left:28px; display:grid; gap:6px; }
  .titles li { font-size:19px; font-weight:600; line-height:1.5; word-break:keep-all; }
  .titles li::marker { color:var(--muted-soft); font-weight:500; }
  .titles li.none { color:var(--muted-soft); font-weight:500; list-style:none; }
  .src { border-top:1px solid var(--hairline-soft); padding-top:14px; margin-top:14px; }
  .src:not(.center) { opacity:.85; }
  .who { display:flex; gap:12px; align-items:center; font-size:13px; color:var(--muted-soft); margin-bottom:8px; }
  .who a { color:var(--muted); text-decoration:none; font-weight:500; }
  .who a:hover { text-decoration:underline; }
  .flag { margin-left:auto; color:var(--primary); font-weight:600; }
  .label { font-size:12px; font-weight:600; color:var(--muted-soft); margin-bottom:4px; }
  p { margin:0 0 10px; font-size:15px; line-height:1.8; color:var(--body); word-break:keep-all; }
  .claim { color:var(--ink); }
  .foot { border-top:1px solid var(--hairline-soft); margin-top:14px; padding-top:12px; }
  .foot ul, .excluded ul { margin:0; padding-left:18px; font-size:14px; color:var(--muted); line-height:1.7; }
  .excluded { max-width:1100px; margin:0 auto; padding:0 32px 72px; }
  .excluded h2 { font-size:20px; font-weight:600; margin:16px 0 10px; }
  @media (max-width: 800px) { header, main, .excluded { padding-left:16px; padding-right:16px; } }
</style>
</head>
<body>
<header>
  <h1>주제별 글 제목 후보</h1>
  <p>__SUMMARY__<br>주제 = 글쓴이의 주장이 같은 원문 묶음. 제목 후보는 작업실 제목 단계 그대로(astra, 경영일기 제목 60개 + 멘토 제목 참고), 고르지 않고 나온 순서대로입니다.</p>
</header>
<main>__CARDS__</main>
<section class="excluded"><h2>칼럼 재료가 없어 뺀 원문</h2><ul>__EXCLUDED__</ul></section>
</body>
</html>
"""

if __name__ == "__main__":
    main(sys.argv[1])

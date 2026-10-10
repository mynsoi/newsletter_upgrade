"""주제 카드 시험(있었던 일 + 글쓴이가 하는 말) 결과를 보기 좋은 HTML로 — 작업실 /docs/에서 연다 (2026-10-11).

사용: python3 -I wiki-eval/build_plain_page.py runs/topic-plain/20261011-000210
결과: docs/2026-10-11-주제카드-시험.html  →  http://100.73.64.64:8771/docs/2026-10-11-주제카드-시험.html
"""
import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "sources"
OUT = ROOT / "docs" / "2026-10-11-주제카드-시험.html"
ORDER = ["linkedin/02", "threads/23", "linkedin/09", "linkedin/26", "threads/05", "linkedin/08"]
NOTE = {  # 보여 드리기 전 점검 — 원문과 대조해 본 것
    "linkedin/02": ("살아남", "원문의 핵심(봇 10개 vs 회사 지도)이 그대로 남았다"),
    "threads/23": ("살아남", "원문이 하고 싶은 말(제일 먼저 사라진 건 시시한 반복 업무)과 숫자가 그대로"),
    "linkedin/09": ("살아남", "'통과'와 '실제 채택'의 차이가 그대로. 고유명사가 많아 글에서는 풀어야 한다"),
    "linkedin/26": ("살아남", "편해졌는데 불안하다는 원문의 고민이 그대로. 말끝 '~것이다'가 두 번 겹친다"),
    "threads/05": ("약함", "원문 자체가 일반론 쪽이라 카드도 교육 자료처럼 읽힌다"),
    "linkedin/08": ("약함", "주장이 흐릿하고 말끝 '~리라는 기대다'가 어색하다"),
}


def front(t):
    m = re.match(r"^---\n(.*?)\n---\n", t, re.S)
    return dict(re.findall(r"^(\w+):\s*(.*)$", m.group(1), re.M)) if m else {}


def meta(key):
    m = front((SRC / "originals" / f"{key}.md").read_text(encoding="utf-8"))
    g = lambda k: m.get(k, "").strip().strip("'\"")
    return {"who": g("headline") or g("author"), "author": g("author"), "date": g("date"), "url": g("url")}


def wiki_titles(key):
    out = []
    for f in sorted((ROOT / "wiki").glob("*/*.md")):
        t = f.read_text(encoding="utf-8")
        if f"originals/{key}.md" in t:
            out.append(front(t).get("title", f.stem).strip("'\""))
    return out


def parse(all_md):
    cards = {}
    for block in re.split(r"^## ", all_md, flags=re.M)[1:]:
        head, _, body = block.partition("\n")
        key = head.strip().removeprefix("originals/").removesuffix(".md")
        fields = dict(re.findall(r"^(있었던 일|글쓴이가 하는 말):\s*(.+)$", body, re.M))
        cards[key] = fields
    return cards


def card(key, f):
    m = meta(key)
    kind, note = NOTE.get(key, ("", ""))
    olds = "".join(f"<li>{html.escape(t)}</li>" for t in wiki_titles(key)) or "<li>—</li>"
    site = key.split("/")[0]
    return f"""
<article class="card {'weak' if kind == '약함' else ''}">
  <div class="src"><a href="{html.escape(m['url'])}" target="_blank" rel="noopener">{html.escape(site)} · {html.escape(m['author'])}</a>
    <span>{html.escape(m['date'])}</span><span class="tag">{html.escape(kind)}</span></div>
  <h2>{html.escape(f.get('글쓴이가 하는 말', ''))}</h2>
  <div class="label">있었던 일</div>
  <p>{html.escape(f.get('있었던 일', ''))}</p>
  <div class="foot">
    <div><div class="label">지금 주제 지도에서는</div><ul>{olds}</ul></div>
    <div><div class="label">점검</div><p class="note">{html.escape(note)}</p></div>
  </div>
</article>"""


def main(run_dir):
    cards = parse((ROOT / run_dir / "all.md").read_text(encoding="utf-8"))
    body = "".join(card(k, cards[k]) for k in ORDER if k in cards)
    OUT.write_text(PAGE.replace("__CARDS__", body).replace("__RUN__", html.escape(run_dir)), encoding="utf-8")
    print(OUT)


PAGE = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>주제 카드 시험</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Noto+Sans+KR:wght@400;500;600;700&display=swap" />
<style>
  :root { --canvas:#ffffff; --surface-soft:#f7f7f7; --hairline:#dddddd; --hairline-soft:#ebebeb;
          --ink:#222222; --body:#3f3f3f; --muted:#6a6a6a; --muted-soft:#929292; --primary:#ff385c; }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--canvas); color:var(--ink); font-family:Inter, "Noto Sans KR", -apple-system, system-ui, sans-serif; }
  header { max-width:1100px; margin:0 auto; padding:48px 32px 24px; border-bottom:1px solid var(--hairline-soft); }
  h1 { font-size:28px; font-weight:700; margin:0 0 8px; letter-spacing:-.01em; }
  header p { margin:0; color:var(--muted); font-size:15px; line-height:1.7; }
  main { max-width:1100px; margin:0 auto; padding:24px 32px 72px; display:grid; gap:20px; }
  .card { border:1px solid var(--hairline); border-radius:14px; padding:24px 28px; }
  .card.weak { background:var(--surface-soft); }
  .src { display:flex; gap:12px; align-items:center; font-size:13px; color:var(--muted-soft); }
  .src a { color:var(--muted); text-decoration:none; font-weight:500; }
  .src a:hover { text-decoration:underline; }
  .tag { margin-left:auto; font-weight:600; color:var(--primary); }
  .weak .tag { color:var(--muted); }
  h2 { font-size:21px; font-weight:600; line-height:1.55; margin:12px 0 16px; word-break:keep-all; }
  .label { font-size:12px; font-weight:600; color:var(--muted-soft); margin-bottom:4px; }
  p { margin:0; font-size:15px; line-height:1.8; color:var(--body); word-break:keep-all; }
  .foot { display:grid; grid-template-columns:1fr 1fr; gap:24px; margin-top:18px; padding-top:16px; border-top:1px solid var(--hairline-soft); }
  .foot ul { margin:0; padding-left:18px; font-size:14px; color:var(--muted); line-height:1.7; }
  .note { font-size:14px; color:var(--muted); }
  @media (max-width: 800px) { header, main { padding-left:16px; padding-right:16px; } .foot { grid-template-columns:1fr; } }
</style>
</head>
<body>
<header>
  <h1>주제 카드 — 제목 없이</h1>
  <p>원문 6편 · astra · 카드 머리는 원문 글쓴이가 하는 말, 아래는 원문에서 있었던 일. 제목은 글을 고른 뒤 제목 단계에서 짓는다.</p>
</header>
<main>__CARDS__</main>
</body>
</html>
"""

if __name__ == "__main__":
    main(sys.argv[1])

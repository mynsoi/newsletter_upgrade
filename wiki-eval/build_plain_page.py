"""주제 카드 시험(있었던 일 + 글쓴이가 하는 말) 결과를 보기 좋은 HTML로 — 작업실 /docs/에서 연다 (2026-10-11).

사용: python3 -I wiki-eval/build_plain_page.py runs/topic-plain/20261011-000210
결과: docs/2026-10-11-주제카드-시험.html  →  http://100.73.64.64:8771/docs/2026-10-11-주제카드-시험.html
"""
import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import title_candidates as tc  # noqa: E402
RUN = None
SRC = ROOT / "sources"
OUT = ROOT / "docs" / "2026-10-11-주제카드-시험.html"
ORDER = ["linkedin/02", "threads/23", "linkedin/09", "linkedin/26", "threads/05", "linkedin/08"]
NOTE = {  # 보여 드리기 전 점검 — 원문과 대조해 본 것(제목 후보는 고르지 않고 그대로)
    "linkedin/02": ("", "제목 후보의 표현은 모두 원문에 있는 것(매일이 입사 첫날 → '매일 신입사원', 열어야 할 툴 → '열어야 할 창')"),
    "threads/23": ("", "숫자(3시간 → 5분)와 '에이전트보다 체감이 크다'는 원문 그대로"),
    "linkedin/09": ("", "원문과 어긋난 후보 없음"),
    "linkedin/26": ("", "원문과 어긋난 후보 없음"),
    "threads/05": ("", "원문과 어긋난 후보 없음. 원문 자체가 일반론 쪽"),
    "linkedin/08": ("", "1번은 원문 내용(판단 기준·회고)과 거리가 있음"),
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
    tf = RUN / "titles" / key / "astra.md"
    titles = "".join(f"<li>{html.escape(x)}</li>" for x in (tc.round_items(tf) if tf.exists() else []))
    site = key.split("/")[0]
    return f"""
<article class="card {'weak' if kind == '약함' else ''}">
  <div class="src"><a href="{html.escape(m['url'])}" target="_blank" rel="noopener">{html.escape(site)} · {html.escape(m['author'])}</a>
    <span>{html.escape(m['date'])}</span><span class="tag">{html.escape(kind)}</span></div>
  <ol class="titles">{titles}</ol>
  <div class="label">글쓴이가 하는 말</div>
  <p class="claim">{html.escape(f.get('글쓴이가 하는 말', ''))}</p>
  <div class="label">있었던 일</div>
  <p>{html.escape(f.get('있었던 일', ''))}</p>
  <div class="foot">
    <div><div class="label">지금 주제 지도에서는</div><ul>{olds}</ul></div>
    <div><div class="label">점검</div><p class="note">{html.escape(note)}</p></div>
  </div>
</article>"""


def main(run_dir):
    global RUN
    RUN = ROOT / run_dir
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
  .titles { margin:14px 0 18px; padding-left:28px; display:grid; gap:6px; }
  .titles li { font-size:19px; font-weight:600; line-height:1.5; word-break:keep-all; }
  .titles li::marker { color:var(--muted-soft); font-weight:500; }
  .claim { margin-bottom:12px; }
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
  <h1>주제별 글 제목 후보</h1>
  <p>원문 6편 · 주제마다 astra 제목 후보 8개(작업실 제목 단계 그대로 — 경영일기 제목 60개 + 멘토 제목 참고). 후보는 고르지 않고 나온 순서 그대로입니다.</p>
</header>
<main>__CARDS__</main>
</body>
</html>
"""

if __name__ == "__main__":
    main(sys.argv[1])

"""화면 시험으로 뽑은 확정 칼럼을 한 페이지로 (2026-10-11) — 작업실 /docs/에서 연다(그림은 작업실 /img/로)

사용: python3 -I wiki-eval/build_columns_page.py → docs/2026-10-11-시험-칼럼-3편.html
"""
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
e = html.escape
ITEMS = [  # (글, 원문 대조 점검)
    ("w-20261011-013836", "숫자·사실(서울시 전자문서, D-day, 10초, 깃허브, 압축 파일, PC 안의 AI) 모두 원문에 있음. "
     "다만 '서울시', '깃허브'처럼 기관·플랫폼 이름이 본문에 남음 — 멘토 기준 5(출처의 사람·기관·플랫폼 이름을 본문에 쓰지 않는다)와 어긋남."),
    ("w-20261011-013856", "사실(5-6년, 메뉴얼 방식대로 복사·붙이기, 초기 셋업 시간, 몰래 자동화, 잔소리) 모두 원문에 있음. "
     "대상 독자 사수급이 글에 드러남('위로 보고하고 아래로 일을 나눠 주는 사수라면'). 출처 인물 소개 없음."),
    ("w-20261011-013917", "숫자(열 번 중 여섯 번, 40%·41%·44.5%·45.7%, 1~2%p, 24.7% → 95%) 모두 원문에 있음. "
     "다만 '토스'라는 회사 이름이 본문에 남음 — 멘토 기준 5와 어긋남."),
]


def chars(body):
    return len(re.sub(r"\s", "", re.sub(r"!\[[^]]*\]\([^)]*\)", "", body)))


def render(md):
    out = []
    for block in [b.strip() for b in re.split(r"\n\s*\n", md) if b.strip()]:
        m = re.match(r"^!\[([^]]*)\]\(img/([^)]+)\)$", block)
        if m:
            out.append(f'<figure><img src="/img/columns/img/{e(m.group(2))}?w=1400" alt="{e(m.group(1))}"><figcaption>{e(m.group(1))}</figcaption></figure>')
        else:
            out.append(f"<p>{e(block)}</p>")
    return "\n".join(out)


def main():
    arts, nav = [], []
    for i, (k, check) in enumerate(ITEMS, 1):
        b = json.loads((ROOT / "briefs" / f"{k}.json").read_text(encoding="utf-8"))
        conf = b.get("confirmed") or {}
        md = (ROOT / conf["file"]).read_text(encoding="utf-8")
        title, _, body = md.partition("\n")
        title = title.lstrip("# ").strip()
        page = ROOT / b.get("from_wiki", "")
        topic = re.search(r"^title:\s*(.+)$", page.read_text(encoding="utf-8"), re.M).group(1).strip("'\"") if page.is_file() else ""
        t1 = (ROOT / "runs" / "titles0" / k / "astra.md").read_text(encoding="utf-8").splitlines()[0] if (ROOT / "runs" / "titles0" / k / "astra.md").exists() else ""
        nav.append(f'<a href="#c{i}"><span>{i:02d}</span>{e(title)}</a>')
        arts.append(f"""<section class="col" id="c{i}">
  <dl class="meta">
    <div><dt>고른 주제</dt><dd>{e(topic)}</dd></div>
    <div><dt>대상 독자</dt><dd>{e(b.get('target', '전 직원'))}</dd></div>
    <div><dt>제목</dt><dd>astra 후보 {e(t1.split('.', 1)[0])}번 그대로(시험이라 고르지 않음)</dd></div>
    <div><dt>분량</dt><dd>공백 제외 {chars(body):,}자 · 과정 {conf.get('step')} · 본문 그림 {conf.get('inline')}</dd></div>
  </dl>
  <article>
    <h2>{e(title)}</h2>
    {render(body)}
  </article>
  <div class="check"><b>원문 대조</b> {e(check)} <a href="/#/a/{e(k)}/confirm">작업실에서 열기</a></div>
</section>""")
    page = PAGE.replace("__NAV__", "".join(nav)).replace("__COLS__", "".join(arts))
    out = ROOT / "docs" / "2026-10-11-시험-칼럼-3편.html"
    out.write_text(page, encoding="utf-8")
    print(out)


PAGE = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>시험 칼럼 3편</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Noto+Sans+KR:wght@400;500;600;700&display=swap" />
<style>
  :root { --canvas:#ffffff; --surface-soft:#f7f7f7; --hairline:#dddddd; --hairline-soft:#ebebeb;
          --ink:#222222; --body:#3f3f3f; --muted:#6a6a6a; --muted-soft:#929292; --primary:#ff385c; }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--surface-soft); color:var(--ink); font-family:Inter, "Noto Sans KR", -apple-system, system-ui, sans-serif; word-break:keep-all; }
  .wrap { max-width:860px; margin:0 auto; padding:0 32px 80px; }
  header { padding:56px 0 20px; }
  h1 { font-size:30px; font-weight:700; margin:0 0 10px; }
  header p { margin:0 0 20px; color:var(--muted); font-size:15px; line-height:1.75; }
  nav { display:grid; gap:8px; }
  nav a { display:flex; gap:14px; align-items:baseline; background:var(--canvas); border:1px solid var(--hairline); border-radius:12px; padding:14px 18px; color:var(--ink); text-decoration:none; font-weight:600; font-size:16px; }
  nav a span { color:var(--muted-soft); font-weight:500; font-size:13px; }
  nav a:hover { border-color:var(--ink); }
  .col { margin-top:56px; }
  .meta { display:grid; grid-template-columns:1fr 1fr; gap:8px 24px; margin:0 0 14px; font-size:13.5px; }
  .meta dt { color:var(--muted-soft); font-weight:600; font-size:12px; }
  .meta dd { margin:2px 0 0; color:var(--body); line-height:1.5; }
  article { background:var(--canvas); border:1px solid var(--hairline); border-radius:14px; padding:44px 52px; }
  article h2 { font-size:28px; font-weight:700; line-height:1.4; margin:0 0 24px; letter-spacing:-.01em; }
  article p { font-size:16.5px; line-height:1.95; color:var(--body); margin:0 0 18px; }
  figure { margin:26px 0; }
  figure img { width:100%; border-radius:10px; display:block; }
  figcaption { font-size:12.5px; color:var(--muted-soft); margin-top:6px; }
  .check { margin-top:12px; font-size:13.5px; line-height:1.7; color:var(--muted); }
  .check b { color:var(--ink); margin-right:6px; }
  .check a { color:var(--primary); margin-left:8px; text-decoration:none; font-weight:600; }
  @media (max-width: 800px) { .wrap { padding:0 16px 60px; } article { padding:28px 22px; } .meta { grid-template-columns:1fr; } }
</style>
</head>
<body>
<div class="wrap">
<header>
  <h1>화면 시험으로 뽑은 칼럼 3편</h1>
  <p>작업실 화면에서 그대로 눌러 만든 글입니다 — 주제 지도의 '쓸 만함' 주제 고르기 → 미리 뽑힌 제목 후보 중 1번 → 쓰기(과정 1·2·3, 공백 제외 1,500자 이하) → 본문 그림 뽑기 → 2개 고르기 → 확정.</p>
  <nav>__NAV__</nav>
</header>
__COLS__
</div>
</body>
</html>
"""

if __name__ == "__main__":
    main()

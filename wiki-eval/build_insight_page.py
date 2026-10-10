"""직원 인사이트(빌려 오기) 시험 결과를 HTML로 — 작업실 /docs/에서 연다 (2026-10-11)

사용: python3 -I wiki-eval/build_insight_page.py runs/topic-full/20261011-full/insight/<시각> <docs 파일 이름>
제목 후보는 고르지 않고 astra가 낸 순서 그대로. 점검(CHECK)은 보여 드리기 전에 원문과 대조한 결과.
"""
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import title_candidates as tc  # noqa: E402

e = html.escape
CHECK = {  # 원문 대조
    "linkedin/02": "원문 그대로: 노션 최근 페이지 400개 중 12개, '브랜드'·'광고' 키워드로 골랐다가 남의 주간회의록·단가표가 올라온 실패",
    "threads/23": "원문 그대로: 매달 5일, 매출의 1%, 3시간 → 5분",
    "linkedin/26": "원문과 어긋난 것 없음",
    "linkedin/30": "원문 그대로: 후보 4개, 전문가들이 로고를 어떻게 만드는지 확인하라는 개입",
    "threads/21": "원문 그대로: 물리법칙·디테일 모션감을 프롬프트에 적용",
    "linkedin/25": "'90초'는 원문에서 '1분 30초' — 단위를 바꿔 씀",
}
ORDER = ["linkedin/02", "threads/23", "linkedin/26", "linkedin/30", "threads/21", "linkedin/25"]


def front(t):
    m = re.match(r"^---\n(.*?)\n---\n", t, re.S)
    return dict(re.findall(r"^(\w+):\s*(.*)$", m.group(1), re.M)) if m else {}


def main(run, name):
    run = ROOT / run
    full = run.parent.parent
    cards = json.loads((full / "cards.json").read_text(encoding="utf-8"))
    ins = json.loads((run / "insight.json").read_text(encoding="utf-8"))
    short = json.loads((run / "short.json").read_text(encoding="utf-8")) if (run / "short.json").exists() else {}
    keys = [k for k in ORDER if k in ins] + [k for k in ins if k not in ORDER]
    rows, arts = [], []
    for i, k in enumerate(keys, 1):
        f, c, s = ins[k], cards[k], short.get(k, {})
        m = front((ROOT / "sources" / "originals" / f"{k}.md").read_text(encoding="utf-8"))
        g = lambda x: m.get(x, "").strip().strip("'\"")
        tf = run / k.replace("/", "-") / "titles" / "astra.md"
        titles = "".join(f"<li>{e(t)}</li>" for t in (tc.round_items(tf) if tf.exists() else []))
        use = f.get("쓸모", "")
        case1, ins1 = s.get("사례 한 줄", ""), s.get("인사이트 한 줄", "")
        rows.append(f'<tr><td class="no">{i}</td><td><a href="#c{i}">{e(case1)}</a></td><td class="arrow">→</td><td><a href="#c{i}"><b>{e(ins1)}</b></a></td></tr>')
        arts.append(f"""<article class="card" id="c{i}">
  <div class="meta"><span class="no">{i:02d}</span><a href="{e(g('url'))}" target="_blank" rel="noopener">{e(k.split('/')[0])} · {e(g('author'))}</a></div>
  <div class="flow">
    <div class="from"><div class="label">원문 사례</div><div class="line">{e(case1)}</div></div>
    <div class="to"><div class="label">직원에게</div><div class="line">{e(ins1)}</div></div>
  </div>
  <div class="label">제목 후보 <span class="sub">astra · 고르지 않음</span></div>
  <ol class="titles">{titles}</ol>
  <details><summary>자세히 — 인사이트 전문 · 빌려 올 점 · 직원 장면 · 원문 · 점검</summary>
    <dl>
      <dt>인사이트</dt><dd>{e(f.get('인사이트', ''))}</dd>
      <dt>빌려 올 점</dt><dd>{e(f.get('빌려 올 점', ''))}</dd>
      <dt>직원 장면 (가정)</dt><dd>{e(f.get('직원 장면', ''))}</dd>
      <dt>원문에서 있었던 일</dt><dd>{e(c['있었던 일'])}</dd>
      <dt>글쓴이가 하는 말</dt><dd>{e(c['글쓴이가 하는 말'])}</dd>
      <dt>점검</dt><dd>{e(CHECK.get(k, ''))}<br>쓸모 {e(use)}</dd>
    </dl>
  </details>
</article>""")
    out = ROOT / "docs" / name
    out.write_text(PAGE.replace("__ROWS__", "".join(rows)).replace("__CARDS__", "".join(arts)), encoding="utf-8")
    print(out)


PAGE = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>직원 인사이트</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Noto+Sans+KR:wght@400;500;600;700&display=swap" />
<style>
  :root { --canvas:#ffffff; --surface-soft:#f7f7f7; --surface-strong:#f2f2f2; --hairline:#dddddd; --hairline-soft:#ebebeb;
          --ink:#222222; --body:#3f3f3f; --muted:#6a6a6a; --muted-soft:#929292; --primary:#ff385c; }
  * { box-sizing:border-box; }
  html { scroll-behavior:smooth; }
  body { margin:0; background:var(--canvas); color:var(--ink); font-family:Inter, "Noto Sans KR", -apple-system, system-ui, sans-serif; word-break:keep-all; }
  .wrap { max-width:960px; margin:0 auto; padding:0 32px; }
  header { padding:56px 0 28px; }
  h1 { font-size:30px; font-weight:700; margin:0 0 10px; letter-spacing:-.01em; }
  header p { margin:0; color:var(--muted); font-size:15px; line-height:1.7; }
  table { width:100%; border-collapse:collapse; margin:8px 0 48px; }
  td { padding:14px 10px; border-bottom:1px solid var(--hairline-soft); font-size:15.5px; line-height:1.55; vertical-align:top; }
  td a { color:inherit; text-decoration:none; }
  td a:hover { text-decoration:underline; }
  td.no { color:var(--muted-soft); width:28px; }
  td.arrow { color:var(--primary); width:24px; text-align:center; }
  .card { padding:36px 0 32px; border-top:1px solid var(--hairline); }
  .meta { display:flex; gap:12px; align-items:baseline; font-size:13px; color:var(--muted-soft); margin-bottom:16px; }
  .meta .no { font-size:22px; font-weight:700; color:var(--ink); }
  .meta a { color:var(--muted); text-decoration:none; }
  .flow { display:grid; grid-template-columns:1fr 1.3fr; gap:14px; margin-bottom:24px; }
  .from, .to { border-radius:14px; padding:18px 20px; }
  .from { background:var(--surface-soft); }
  .to { background:#fff1f3; }
  .label { font-size:12.5px; font-weight:600; color:var(--muted-soft); margin-bottom:6px; }
  .label .sub { font-weight:400; margin-left:6px; }
  .from .line { font-size:16.5px; line-height:1.6; color:var(--body); }
  .to .line { font-size:19px; font-weight:600; line-height:1.55; color:var(--ink); }
  .titles { list-style:none; counter-reset:t; margin:0 0 18px; padding:0; display:grid; grid-template-columns:1fr 1fr; grid-template-rows:repeat(4, auto); grid-auto-flow:column; gap:8px 28px; }
  .titles li { counter-increment:t; font-size:15.5px; line-height:1.5; padding-left:26px; position:relative; }
  .titles li::before { content:counter(t); position:absolute; left:0; color:var(--muted-soft); font-size:13px; top:2px; }
  details summary { cursor:pointer; font-size:13.5px; color:var(--muted); padding:6px 0; }
  dl { margin:10px 0 0; display:grid; grid-template-columns:130px 1fr; gap:10px 16px; font-size:14.5px; line-height:1.75; }
  dt { color:var(--muted-soft); font-weight:600; font-size:13px; padding-top:2px; }
  dd { margin:0; color:var(--body); }
  @media (max-width: 800px) { .wrap { padding:0 16px; } .flow { grid-template-columns:1fr; } .titles { grid-template-columns:1fr; grid-template-rows:none; grid-auto-flow:row; } dl { grid-template-columns:1fr; } }
</style>
</head>
<body>
<div class="wrap">
<header>
  <h1>직원 인사이트 — 개인 사례도 빌려 오기</h1>
  <p>원문 6편 (개인·크리에이터 사례 3편 포함) · 원문 사례에서 직원의 AI 업무에 통하는 점을 빌려 왔습니다. 직원 장면은 가정입니다.</p>
</header>
<table>__ROWS__</table>
__CARDS__
</div>
</body>
</html>
"""


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])

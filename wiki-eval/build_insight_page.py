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
    arts = []
    for k in [k for k in ORDER if k in ins] + [k for k in ins if k not in ORDER]:
        f, c = ins[k], cards[k]
        m = front((ROOT / "sources" / "originals" / f"{k}.md").read_text(encoding="utf-8"))
        g = lambda x: m.get(x, "").strip().strip("'\"")
        tf = run / k.replace("/", "-") / "titles" / "astra.md"
        titles = "".join(f"<li>{e(t)}</li>" for t in (tc.round_items(tf) if tf.exists() else []))
        use = f.get("쓸모", "")
        arts.append(f"""<article class="card">
  <div class="who"><a href="{e(g('url'))}" target="_blank" rel="noopener">{e(k.split('/')[0])} · {e(g('author'))}</a><span>{e(g('date'))}</span><span class="use">쓸모 {e(use.split('—')[0].strip())}</span></div>
  <div class="label">직원 인사이트</div>
  <p class="insight">{e(f.get('인사이트', ''))}</p>
  <div class="label">제목 후보 (astra, 작업실 제목 단계 그대로)</div>
  <ol class="titles">{titles}</ol>
  <div class="grid">
    <div><div class="label">빌려 올 점</div><p>{e(f.get('빌려 올 점', ''))}</p></div>
    <div><div class="label">직원 장면 (가정)</div><p>{e(f.get('직원 장면', ''))}</p></div>
  </div>
  <details><summary>원문 카드 — 있었던 일 · 글쓴이가 하는 말</summary>
    <p><b>있었던 일</b> {e(c['있었던 일'])}</p><p><b>글쓴이가 하는 말</b> {e(c['글쓴이가 하는 말'])}</p></details>
  <div class="check"><span class="label">점검</span> {e(CHECK.get(k, ''))} · 쓸모 이유: {e(use.split('—', 1)[1].strip() if '—' in use else '')}</div>
</article>""")
    out = ROOT / "docs" / name
    out.write_text(PAGE.replace("__CARDS__", "".join(arts)), encoding="utf-8")
    print(out)


PAGE = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>직원 인사이트 시험</title>
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
  .who { display:flex; gap:12px; align-items:center; font-size:13px; color:var(--muted-soft); margin-bottom:12px; }
  .who a { color:var(--muted); text-decoration:none; font-weight:500; }
  .use { margin-left:auto; font-weight:600; color:var(--primary); }
  .label { font-size:12px; font-weight:600; color:var(--muted-soft); margin-bottom:4px; }
  .insight { font-size:19px; font-weight:600; color:var(--ink); line-height:1.65; margin:0 0 18px; word-break:keep-all; }
  .titles { margin:6px 0 18px; padding-left:26px; display:grid; gap:4px; }
  .titles li { font-size:16px; font-weight:500; line-height:1.5; word-break:keep-all; }
  .titles li::marker { color:var(--muted-soft); }
  p { margin:0 0 10px; font-size:15px; line-height:1.8; color:var(--body); word-break:keep-all; }
  .grid { display:grid; grid-template-columns:1fr 1fr; gap:24px; border-top:1px solid var(--hairline-soft); padding-top:14px; }
  details { border-top:1px solid var(--hairline-soft); padding-top:10px; margin-top:4px; }
  summary { cursor:pointer; font-size:13px; color:var(--muted); margin-bottom:8px; }
  .check { border-top:1px solid var(--hairline-soft); margin-top:10px; padding-top:10px; font-size:13px; color:var(--muted); line-height:1.7; }
  @media (max-width: 800px) { header, main { padding-left:16px; padding-right:16px; } .grid { grid-template-columns:1fr; } }
</style>
</head>
<body>
<header>
  <h1>직원 인사이트 — 개인 사례도 빌려 오기</h1>
  <p>원문 6편(개인·크리에이터 사례 3편 포함) · 원문 카드에서 직원의 AI 업무에 통하는 점을 빌려 와 인사이트로, 그 인사이트로 제목 후보 8개.<br>
  직원 장면은 가정이고, 원문 속 사례는 그 사람의 일로 사실대로 둡니다.</p>
</header>
<main>__CARDS__</main>
</body>
</html>
"""

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])

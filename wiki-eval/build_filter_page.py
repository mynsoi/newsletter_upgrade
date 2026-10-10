"""Claude가 직접 거른 결과(filter_by_claude.json)를 읽기 쉬운 HTML로 (2026-10-11)

사용: python3 -I wiki-eval/build_filter_page.py  →  docs/2026-10-11-주제-거르기.html
"""
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
e = html.escape
F = json.loads((ROOT / "wiki-eval" / "filter_by_claude.json").read_text(encoding="utf-8"))


def link(keys):
    out = []
    for k in keys.split(" + "):
        t = (ROOT / "sources" / "originals" / f"{k}.md").read_text(encoding="utf-8")
        m = re.search(r"^url:\s*(.+)$", t, re.M)
        a = re.search(r"^author:\s*(.+)$", t, re.M)
        url = m.group(1).strip().strip("'\"") if m else ""
        who = a.group(1).strip().strip("'\"") if a else ""
        out.append(f'<a href="{e(url)}" target="_blank" rel="noopener">{e(k)} · {e(who)}</a>')
    return " ".join(out)


good = "".join(f"""<article class="g">
  <div class="top"><span class="src">{link(k)}</span><span class="aud">{e(aud)}</span></div>
  <p class="what">{e(what)}</p>
  <p class="why">{e(why)}</p>
</article>""" for k, what, why, aud in F["good"])
ok = "".join(f'<tr><td class="src">{link(k)}</td><td><b>{e(what)}</b><br><span class="why">{e(why)}</span></td></tr>' for k, what, why in F["ok"])
used = "".join(f'<tr><td class="src">{link(k)}</td><td><b>{e(what)}</b><br><span class="why">{e(why)}</span></td></tr>' for k, what, why in F["used"])
drop = "".join(f'<li><span class="src">{link(k)}</span> {e(why)}</li>' for k, why in F["drop"] + F["excluded_before"])

PAGE = f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>주제 거르기</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Noto+Sans+KR:wght@400;500;600;700&display=swap" />
<style>
  :root {{ --canvas:#ffffff; --surface-soft:#f7f7f7; --hairline:#dddddd; --hairline-soft:#ebebeb;
          --ink:#222222; --body:#3f3f3f; --muted:#6a6a6a; --muted-soft:#929292; --primary:#ff385c; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--canvas); color:var(--ink); font-family:Inter, "Noto Sans KR", -apple-system, system-ui, sans-serif; word-break:keep-all; }}
  .wrap {{ max-width:980px; margin:0 auto; padding:0 32px 80px; }}
  header {{ padding:56px 0 24px; }}
  h1 {{ font-size:30px; font-weight:700; margin:0 0 10px; }}
  header p {{ margin:0; color:var(--muted); font-size:15px; line-height:1.75; }}
  .sum {{ display:flex; gap:12px; margin:22px 0 8px; flex-wrap:wrap; }}
  .sum div {{ background:var(--surface-soft); border-radius:12px; padding:14px 18px; min-width:140px; }}
  .sum b {{ display:block; font-size:28px; }}
  .sum span {{ font-size:13px; color:var(--muted); }}
  .sum .hi {{ background:#fff1f3; }} .sum .hi b {{ color:var(--primary); }}
  .six {{ border:1px solid var(--hairline); border-radius:14px; padding:18px 22px; margin:24px 0 8px; font-size:14.5px; line-height:1.8; color:var(--body); }}
  .six b {{ color:var(--ink); }}
  h2 {{ font-size:22px; font-weight:700; margin:44px 0 6px; }}
  h2 small {{ font-size:14px; font-weight:500; color:var(--muted); margin-left:8px; }}
  .g {{ border-top:1px solid var(--hairline); padding:20px 0; }}
  .top {{ display:flex; gap:10px; align-items:baseline; justify-content:space-between; }}
  .src, .src a {{ font-size:12.5px; color:var(--muted-soft); text-decoration:none; }}
  .src a:hover {{ text-decoration:underline; }}
  .aud {{ font-size:12.5px; font-weight:600; color:var(--primary); white-space:nowrap; }}
  .what {{ font-size:17.5px; font-weight:600; line-height:1.6; margin:6px 0 6px; }}
  .why {{ font-size:14.5px; line-height:1.7; color:var(--muted); margin:0; }}
  table {{ width:100%; border-collapse:collapse; }}
  td {{ border-top:1px solid var(--hairline-soft); padding:14px 8px; vertical-align:top; font-size:15px; line-height:1.65; }}
  td.src {{ width:200px; }}
  td b {{ font-weight:600; }}
  ul.drop {{ columns:2; column-gap:32px; padding-left:18px; font-size:14px; line-height:1.7; color:var(--muted); }}
  ul.drop li {{ break-inside:avoid; margin-bottom:6px; }}
  @media (max-width: 800px) {{ .wrap {{ padding:0 16px 60px; }} ul.drop {{ columns:1; }} td.src {{ width:auto; }} }}
</style>
</head>
<body>
<div class="wrap">
<header>
  <h1>쓸모 있는 주제 거르기</h1>
  <p>원문 59편의 카드를 Claude가 직접 읽고 거른 판단입니다. 기준: SK E&S의 개발자가 아닌 사무·현장 직원이 AI와 일하는 데 쓸모가 있는가(원문이 개인 사례여도 직원에게 통하면 됨) · 교육 자료에 이미 있는 말이 아닌가 · 구체적인 사례가 있는가 · 이미 쓴 글과 겹치지 않는가.</p>
  <div class="sum">
    <div class="hi"><b>{len(F['good'])}</b><span>쓸 만함</span></div>
    <div><b>{len(F['ok'])}</b><span>보통</span></div>
    <div><b>{len(F['used'])}</b><span>이미 쓴 글과 겹침</span></div>
    <div><b>{len(F['drop']) + len(F['excluded_before'])}</b><span>뺌</span></div>
  </div>
  <div class="six"><b>앞의 6편 시험에 대해</b> — 새로 쓸 만한 건 1~2개였습니다. linkedin/02(팀장·AX 담당에게)와 linkedin/30(단, '후보를 더 달라기 전에 순서를 바로잡는다'는 구체적인 요령으로). threads/23은 진행 중인 글과 겹치고, linkedin/26은 지난 글의 재료였고, 애니메이션·영상 도구 두 편은 직원의 일과 거리가 멀어 억지로 빌린 것이었습니다. 시험 원문을 제가 잘못 골랐고, 인사이트를 다시 쓰는 단계가 오히려 원문의 날카로운 점을 흐린 경우도 있었습니다.</div>
</header>

<h2>쓸 만함 <small>원문에서 있었던 일 · 왜 직원에게 쓸모 있는지 · 대상</small></h2>
{good}

<h2>보통 <small>통하지만 소재가 좁거나 겹침</small></h2>
<table>{ok}</table>

<h2>이미 쓴 글과 겹침</h2>
<table>{used}</table>

<h2>뺌 <small>직원의 일과 거리 · 홍보 · 일반론</small></h2>
<ul class="drop">{drop}</ul>
</div>
</body>
</html>
"""
out = ROOT / "docs" / "2026-10-11-주제-거르기.html"
out.write_text(PAGE, encoding="utf-8")
print(out)

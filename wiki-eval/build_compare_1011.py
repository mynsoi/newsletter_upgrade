"""글 품질 원인 비교 페이지 — docs/2026-10-11-글-비교.html (run_compare_1011.py 결과 + 지금 글 + 기준 글)

판마다 본문과 사실 표지(셈은 기계적으로 — 순위는 매기지 않는다). 점검 메모는 사람이 원문과 대조해 적은 것을 notes.json에서.
"""
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
e = html.escape
NOW = ROOT / "runs" / "columns" / "m-20261011-173414"
CMP = ROOT / "runs" / "compare-1011"
NOTES = json.loads((Path(__file__).parent / "compare_1011_notes.json").read_text(encoding="utf-8")) if (Path(__file__).parent / "compare_1011_notes.json").exists() else {}


def body_of(f):
    t = Path(f).read_text(encoding="utf-8").strip() if Path(f).exists() else ""
    t = re.sub(r"^#\s*", "", t)
    title, _, rest = t.partition("\n")
    return title.strip().strip("*"), rest.strip()


def marks(t, own=False):
    q = len(re.findall(r"[^.!?\n]*\?", t))
    return [
        ("공백 제외", f"{len(re.sub(r'[\s]', '', t)):,}자"),
        ("지난 글 예문", "이 글의 원래 문장" if own else ("있음" if "형태만 바뀔 뿐" in t else "없음")),
        ("'한 회사'", str(t.count("한 회사"))),
        ("물음 문장", str(q)),
        ("~해 보세요·~기 바랍니다", str(len(re.findall(r"해 보세요|기 바랍니다|하시기 바랍니다", t)))),
        ("'할 일은'", str(t.count("할 일은"))),
    ]


PANES = [
    ("기준 글", "퇴근 시간 칼럼 · 멘토가 만족한 글(R4 방식, 확정본)", ROOT / "columns" / "2026-10-08-ai-퇴근시간.md"),
    ("지금 · 과정 2", "내 주제로 쓰기 · astra 재작성(과정 3 전)", NOW / "r4.md"),
    ("지금 · 과정 3", "멘토가 본 글 · 기준 반영", NOW / "final.md"),
    ("지금 · 과정 4", "멘토 피드백 '진짜 별로고…' 반영", NOW / "final-r1.md"),
    ("B · 과정 2", "기준 글 방식 — 원문 하나, 말할 것 = 원문의 주장, 지킬 것 1·2", CMP / "B" / "r4.md"),
    ("B3 · 과정 2", "B + 회사 장면 지시 + 대상 독자(팀장급)", CMP / "B3" / "r4.md"),
]


def pane(name, sub, f):
    title, text = body_of(f)
    if not text:
        return ""
    paras = "".join(f"<p>{e(p)}</p>" for p in re.split(r"\n\s*\n", text) if p.strip())
    mk = "".join(f"<span><b>{e(v)}</b>{e(k)}</span>" for k, v in marks(text, own=name == "기준 글"))  # 예문은 원래 기준 글의 문장
    note = NOTES.get(name, "")
    return f"""<section class="pane">
  <div class="head"><div class="name">{e(name)}</div><div class="sub">{e(sub)}</div></div>
  <div class="marks">{mk}</div>
  {f'<div class="note">{e(note)}</div>' if note else ''}
  <details><summary><b>{e(title)}</b></summary><article>{paras}</article></details>
</section>"""


summary = NOTES.get("_summary", [])
PAGE = f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>글 원인 비교</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Noto+Sans+KR:wght@400;500;600;700&display=swap" />
<style>
  :root {{ --canvas:#ffffff; --soft:#f7f7f7; --hair:#dddddd; --hair2:#ebebeb; --ink:#222; --body:#3f3f3f; --muted:#6a6a6a; --primary:#ff385c; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--canvas); color:var(--ink); font-family:Inter, "Noto Sans KR", system-ui, sans-serif; word-break:keep-all; }}
  .wrap {{ max-width:1100px; margin:0 auto; padding:0 32px 80px; }}
  header {{ padding:52px 0 10px; }}
  h1 {{ font-size:28px; margin:0 0 16px; }}
  .lead {{ background:var(--soft); border-radius:14px; padding:16px 22px; font-size:15px; line-height:1.8; }}
  .lead li {{ margin-bottom:4px; }}
  .pane {{ border:1px solid var(--hair); border-radius:16px; padding:18px 22px; margin-top:16px; }}
  .head {{ display:flex; align-items:baseline; gap:12px; }}
  .name {{ font-size:18px; font-weight:700; }}
  .sub {{ font-size:13.5px; color:var(--muted); }}
  .marks {{ display:flex; flex-wrap:wrap; gap:8px; margin-top:10px; }}
  .marks span {{ background:var(--soft); border-radius:999px; padding:3px 12px; font-size:12.5px; color:var(--muted); }}
  .marks b {{ color:var(--ink); margin-right:5px; }}
  .note {{ margin-top:10px; font-size:14px; line-height:1.7; color:var(--body); }}
  details {{ margin-top:12px; }}
  summary {{ cursor:pointer; font-size:15px; }}
  article {{ margin-top:10px; font-size:15.5px; line-height:1.9; color:var(--body); max-width:720px; }}
  article p {{ margin:0 0 14px; }}
</style>
</head>
<body><div class="wrap">
<header>
  <h1>글이 왜 별로인지 — 같은 제목으로 나란히</h1>
  <div class="lead"><ul>{''.join(f'<li>{e(s)}</li>' for s in summary)}</ul></div>
</header>
{''.join(pane(*p) for p in PANES)}
</div></body></html>"""
out = ROOT / "docs" / "2026-10-11-글-비교.html"
out.write_text(PAGE, encoding="utf-8")
print(out.relative_to(ROOT))

"""C2(비교판, 과정 2까지) vs D(고친 실제 글쓰기 과정으로 끝까지) — docs/2026-10-11-글-비교-3.html

멘토(C2를 읽고): "이런게 조금 낯설고 글을 읽다가 방해하게 하네 — 자, 여러분은 어느 숫자에 주목하셨나요? 저는 95%라는 성적보다 74%라는 출발점이 더 값지다고 봅니다…"
표지는 기계적으로 센다(순위는 매기지 않음). 점검 메모는 compare_1011d_notes.json(사람이 원문과 대조해 적은 것).
"""
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
e = html.escape
D = ROOT / "runs" / "columns" / "zz-d-1011"
C2 = ROOT / "runs" / "compare-1011" / "C2"
NOTES = json.loads((Path(__file__).parent / "compare_1011d_notes.json").read_text(encoding="utf-8")) \
    if (Path(__file__).parent / "compare_1011d_notes.json").exists() else {}


def body_of(f):
    t = Path(f).read_text(encoding="utf-8").strip() if Path(f).exists() else ""
    t = re.sub(r"^#\s*", "", t)
    title, _, rest = t.partition("\n")
    return title.strip().strip("*"), rest.strip()


def sents(t):
    return [s for s in re.split(r"(?<=[.!?])\s+", t) if s.strip()]


def marks(t, origin=False):
    ss = sents(t)
    last = " ".join(ss[-3:])
    return [
        ("공백 제외", f"{len(re.sub(r'[\s]', '', t)):,}자"),
        ("'자, '로 여는 말", str(len(re.findall(r"(?:^|\s)자,\s", t)))),
        ("물음 문장", str(sum(1 for s in ss if s.strip().endswith("?")))),
        ("'~보다 … 더' 대비", str(len(re.findall(r"보다[^.?!]{0,30}더", t)))),
        ("지난 글 예문", "짚은 대목이 원래 있던 판" if origin else ("있음" if ("형태만 바뀔 뿐" in t or "어느 숫자에 주목" in t) else "없음")),
        ("'한 회사'", str(t.count("한 회사"))),
        ("지시로 맺음", "예" if re.search(r"바랍니다|해 보세요|보세요\.|하세요\.", last) else "아니오"),
    ]


def latest_final(d):
    revs = sorted(d.glob("final-r*.md"), key=lambda p: int(p.stem.split("-r")[1]))
    return revs[-1] if revs else d / "final.md"


PANES = [
    ("C2 · 과정 2", "비교판 — 멘토가 '굳이 따지면 나은' 판. 짚은 대목이 들어 있음", C2 / "r4.md"),
    ("D · 과정 1", "고친 과정 — Claude 초안(멘토 말을 받은 그대로 봄)", D / "draft.md"),
    ("D · 과정 2", "astra 재작성(멘토 말을 받은 그대로 봄)", D / "r4.md"),
    ("D · 과정 3", "기준 반영", D / "final.md"),
]
if latest_final(D) != D / "final.md":
    PANES.append((f"D · 과정 {3 + int(latest_final(D).stem.split('-r')[1])}", "1,500자 줄이기", latest_final(D)))


def pane(name, sub, f):
    title, text = body_of(f)
    if not text:
        return ""
    paras = "".join(f"<p>{e(p)}</p>" for p in re.split(r"\n\s*\n", text) if p.strip())
    mk = "".join(f"<span><b>{e(v)}</b>{e(k)}</span>" for k, v in marks(text, origin=name.startswith("C2")))
    note = NOTES.get(name, "")
    return f"""<section class="pane">
  <div class="head"><div class="name">{e(name)}</div><div class="sub">{e(sub)}</div></div>
  <div class="marks">{mk}</div>
  {f'<div class="note">{e(note)}</div>' if note else ''}
  <details><summary><b>{e(title)}</b></summary><article>{paras}</article></details>
</section>"""


summary = NOTES.get("_summary", [])
point = (C2 / "thesis.md").read_text(encoding="utf-8").strip()
PAGE = f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>고친 과정 확인</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Noto+Sans+KR:wght@400;500;600;700&display=swap" />
<style>
  :root {{ --soft:#f7f7f7; --hair:#dddddd; --ink:#222; --body:#3f3f3f; --muted:#6a6a6a; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:#fff; color:var(--ink); font-family:Inter, "Noto Sans KR", system-ui, sans-serif; word-break:keep-all; }}
  .wrap {{ max-width:1100px; margin:0 auto; padding:0 32px 80px; }}
  header {{ padding:52px 0 10px; }}
  h1 {{ font-size:28px; margin:0 0 16px; }}
  .lead {{ background:var(--soft); border-radius:14px; padding:16px 22px; font-size:15px; line-height:1.8; }}
  .lead li {{ margin-bottom:4px; }}
  .pt {{ margin:14px 0 0; font-size:15px; }} .pt b {{ margin-right:6px; }}
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
  <h1>고친 과정으로 끝까지 — C2와 나란히</h1>
  <div class="lead"><ul>{''.join(f'<li>{e(s)}</li>' for s in summary)}</ul></div>
  <p class="pt"><b>말할 것(둘 다 같음)</b>{e(point)}</p>
</header>
{''.join(pane(*p) for p in PANES)}
</div></body></html>"""
out = ROOT / "docs" / "2026-10-11-글-비교-3.html"
out.write_text(PAGE, encoding="utf-8")
print(out.relative_to(ROOT))

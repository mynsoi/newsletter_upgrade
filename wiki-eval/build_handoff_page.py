"""handoff.md를 작업실 /docs/에서 읽을 수 있는 HTML로 (2026-10-11 — 멘토: "md 말고 … html로 열어서 mac에서 볼수있게")

사용: python3 -I wiki-eval/build_handoff_page.py  →  docs/<오늘>-handoff.html (md 원문을 그대로 넣고 브라우저에서 marked로 그린다)
"""
import html
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
md = (ROOT / "handoff.md").read_text(encoding="utf-8")
out = ROOT / "docs" / f"{date.today().isoformat()}-handoff.html"
out.write_text(f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>handoff</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Noto+Sans+KR:wght@400;500;600;700&display=swap" />
<script src="https://cdn.jsdelivr.net/npm/marked@12.0.2/marked.min.js"></script>
<style>
  :root {{ --canvas:#ffffff; --surface-soft:#f7f7f7; --hairline:#dddddd; --hairline-soft:#ebebeb;
          --ink:#222222; --body:#3f3f3f; --muted:#6a6a6a; --primary:#ff385c; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--canvas); color:var(--ink); font-family:Inter, "Noto Sans KR", -apple-system, system-ui, sans-serif; word-break:keep-all; }}
  main {{ max-width:920px; margin:0 auto; padding:48px 32px 96px; }}
  h1 {{ font-size:30px; font-weight:700; margin:0 0 8px; }}
  h2 {{ font-size:22px; font-weight:700; margin:44px 0 12px; padding-top:20px; border-top:1px solid var(--hairline-soft); }}
  p, li {{ font-size:15.5px; line-height:1.8; color:var(--body); }}
  li {{ margin:4px 0; }}
  strong {{ color:var(--ink); }}
  a {{ color:var(--primary); }}
  code {{ background:var(--surface-soft); border-radius:6px; padding:1px 6px; font-size:13.5px; }}
  table {{ width:100%; border-collapse:collapse; margin:12px 0 18px; font-size:14.5px; }}
  th, td {{ border-bottom:1px solid var(--hairline); padding:10px 8px; text-align:left; vertical-align:top; line-height:1.65; }}
  th {{ color:var(--muted); font-weight:600; }}
  @media (max-width: 800px) {{ main {{ padding:28px 16px 60px; }} }}
</style>
</head>
<body>
<main id="doc"></main>
<script id="md" type="text/plain">{html.escape(md)}</script>
<script>
  const t = document.createElement("textarea");
  t.innerHTML = document.getElementById("md").textContent;
  document.getElementById("doc").innerHTML = marked.parse(t.value);
</script>
</body>
</html>
""", encoding="utf-8")
print(out)

"""
발행물 → Vercel 정적 사이트(site/) 내보내기

output/<slug>/ (로컬 발행 결과, gitignore) 를 site/<web_path_token>/<slug>/ 로 복사하고
같은 토큰 아래 아카이브 목록 index.html을 다시 만든다. site/ 는 저장소에 커밋되고
vercel.json이 이 디렉토리를 그대로 배포한다.

    python web/site_export.py <slug>     # 한 편 내보내기 + 아카이브 갱신
    python web/site_export.py --index    # 아카이브만 다시 만들기
"""
import html
import json
import shutil
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "output"
SITE_DIR = ROOT / "site"
SETTINGS_PATH = ROOT / "config" / "settings.yaml"

# 웹에 올리지 않는 발행 부산물 (메일용)
_SKIP_FILES = {
    "newsletter.eml", "newsletter-teaser.eml",
    "email-head.html", "email-body.html",
    "email_head.png", "email_body.png", "email_screenshot.png",
}


def load_web_settings() -> dict:
    settings = yaml.safe_load(SETTINGS_PATH.read_text(encoding="utf-8")) or {}
    token = (settings.get("web_path_token") or "").strip()
    if not token:
        raise RuntimeError("config/settings.yaml에 web_path_token이 없습니다.")
    return {
        "base_url": (settings.get("web_base_url") or "").strip().rstrip("/"),
        "token": token,
    }


def article_web_url(slug: str) -> str:
    """발행물의 웹 주소. web_base_url이 비어 있으면 빈 문자열."""
    cfg = load_web_settings()
    if not cfg["base_url"]:
        return ""
    return f"{cfg['base_url']}/{cfg['token']}/{slug}/"


def export_article(slug: str) -> Path:
    src = OUTPUT_DIR / slug
    if not (src / "index.html").exists():
        raise FileNotFoundError(f"발행물을 찾을 수 없습니다: {src}")
    dest = SITE_DIR / load_web_settings()["token"] / slug
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    for f in src.iterdir():
        if f.is_file() and f.name not in _SKIP_FILES:
            shutil.copy2(f, dest / f.name)
    build_archive_index()
    return dest


def build_archive_index() -> Path:
    """site/<token>/ 아래 발행물(article.json)을 최신순 카드 목록으로 묶는다."""
    token_dir = SITE_DIR / load_web_settings()["token"]
    token_dir.mkdir(parents=True, exist_ok=True)
    _write_site_root()

    entries = []
    for meta in token_dir.glob("*/article.json"):
        article = json.loads(meta.read_text(encoding="utf-8"))
        entries.append((article.get("pub_date", ""), meta.parent.name, article))
    entries.sort(key=lambda e: (e[0], e[1]), reverse=True)

    cards = "\n".join(_card(slug, a) for _, slug, a in entries) or (
        '<p class="empty">아직 발행된 글이 없습니다.</p>'
    )
    page = _INDEX_TEMPLATE.replace("{{ cards }}", cards)
    out = token_dir / "index.html"
    out.write_text(page, encoding="utf-8")
    return out


def _card(slug: str, a: dict) -> str:
    e = html.escape
    issue = a.get("issue_number", "")
    label = f"Issue #{issue} · " if issue else ""
    summary = "".join(f"<li>{e(p)}</li>" for p in a.get("tldr_points", []))
    thumb = ""
    hero = a.get("hero_file", "")
    if hero:
        thumb = f'<img src="{e(slug)}/{e(hero)}" alt="" loading="lazy">'
    return (
        f'<a class="card" href="{e(slug)}/">{thumb}'
        f'<div class="card-body"><div class="card-meta">{e(label)}{e(a.get("pub_date", ""))}</div>'
        f'<h2>{e(a.get("title", slug))}</h2><ul>{summary}</ul></div></a>'
    )


def _write_site_root():
    """사이트 루트는 빈 페이지 — 토큰 경로를 모르면 아무것도 찾을 수 없게 한다."""
    SITE_DIR.mkdir(exist_ok=True)
    (SITE_DIR / "index.html").write_text(
        '<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8">'
        '<meta name="robots" content="noindex, nofollow"><title></title></head><body></body></html>\n',
        encoding="utf-8",
    )
    (SITE_DIR / "robots.txt").write_text("User-agent: *\nDisallow: /\n", encoding="utf-8")


_INDEX_TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>Insight Weekly</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable.min.css">
<style>
  :root { --accent:#0B6E4F; --canvas:#F7F8FA; --surface:#FFFFFF; --ink:#101114; --ink2:#3D4148; --muted:#6E7278; --line:#DFE1E5; }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--canvas); color:var(--ink); font-family:"Pretendard Variable",Pretendard,"Malgun Gothic",sans-serif; }
  header { max-width:760px; margin:0 auto; padding:20px 16px; font-weight:800; letter-spacing:0.1em; }
  main { max-width:760px; margin:0 auto; padding:0 16px 48px; display:grid; gap:16px; }
  .card { display:block; background:var(--surface); border:1px solid var(--line); border-radius:16px; overflow:hidden; color:inherit; text-decoration:none; }
  .card:hover { border-color:var(--accent); }
  .card img { display:block; width:100%; aspect-ratio:16/7; object-fit:cover; }
  .card-body { padding:20px 24px; }
  .card-meta { font-size:13px; color:var(--muted); }
  .card h2 { margin:6px 0 10px; font-size:20px; line-height:1.4; letter-spacing:-0.02em; }
  .card ul { margin:0; padding-left:18px; color:var(--ink2); font-size:15px; line-height:1.7; }
  .empty { color:var(--muted); }
</style>
</head>
<body>
<header>INSIGHT WEEKLY</header>
<main>
{{ cards }}
</main>
</body>
</html>
"""


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    if sys.argv[1] == "--index":
        print(build_archive_index().relative_to(ROOT))
    else:
        print(export_article(sys.argv[1]).relative_to(ROOT))

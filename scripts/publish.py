"""확정 칼럼 → 웹 발행(Vercel 정적 사이트) + 이미지 메일(.eml).

HTML 구조·디자인과 메일 방식은 main 브랜치(web/server.py · web/email_renderer.py · web/site_export.py)를 따른다.
- 웹: web/article.html + web/article.css (Offpiste식 1컬럼, Pine Green)
- 메일: 웹페이지의 메일 전용 변형(email-head.html · email-body.html)을 800px 폭으로 찍어 넣은 이미지 메일.
  보내지는 않는다 — .eml을 Outlook에서 열어 확인한 뒤 사람이 보낸다.
- 배포: site/<web_path_token>/<글>/ 로 복사하고 아카이브 목록을 다시 만든 뒤 커밋·푸시 → vercel.json이 site/를 배포.

사용:
  python3 -I scripts/publish.py build <글>                         # 미리보기만 — publish/<글>/ (git 밖)
  python3 -I scripts/publish.py release <글> --to a@x,b@x [--cc …] [--no-push]
설정: config/publish.json (web_base_url · web_path_token · 보내는 사람 · 기본 수신자)
"""
import argparse
import html
import json
import re
import shutil
import subprocess
import sys
from datetime import date
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
OUT = ROOT / "publish"
SITE = ROOT / "site"
SETTINGS = ROOT / "config" / "publish.json"
ID = re.compile(r"^[0-9A-Za-z가-힣][0-9A-Za-z가-힣_.-]{0,80}$")

# 웹에 올리지 않는 발행 부산물 (메일용)
SKIP = {"newsletter.eml", "email.html", "email-head.html", "email-body.html", "email_head.png", "email_body.png", "email_screenshot.png"}

# 디자인 토큰 — web/article.css와 같은 값
ACCENT, CANVAS, INK_MUTED = "#0B6E4F", "#F7F8FA", "#6E7278"
FONT = "Malgun Gothic, sans-serif"
EMAIL_WIDTH = 800  # main은 600 — 데스크톱 Outlook에서 좁아 보여 넓힘(2026-10-20, 960은 넓다고 해 800). 캡처 CSS(article.css .email-capture)가 이 폭 기준


def settings():
    return json.loads(SETTINGS.read_text(encoding="utf-8"))


def meta_path(k):
    if not ID.match(k) or ".." in k:
        raise SystemExit("잘못된 글 이름: " + k)
    for p in (ROOT / "columns" / f"{k}.process.json", ROOT / "briefs" / f"{k}.json"):
        if p.exists():
            return p
    raise SystemExit("글 없음: " + k)


def front(text):
    """원문 머리말(--- … ---)에서 url만 읽는다."""
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return {}
    return dict(re.findall(r"^(\w+):\s*'?(.*?)'?\s*$", m.group(1), re.M))


# ---------- 칼럼 읽기 ----------

def load(k):
    mp = meta_path(k)
    meta = json.loads(mp.read_text(encoding="utf-8"))
    conf = meta.get("confirmed")
    if not conf:
        raise SystemExit("확정하지 않은 글입니다: " + k)
    md = ROOT / conf["file"]
    text = md.read_text(encoding="utf-8")
    title, blocks = "", []
    for b in (x.strip() for x in re.split(r"\n\s*\n", text)):
        if not b:
            continue
        if b.startswith("# ") and not title:
            title = b[2:].strip()
            continue
        im = re.fullmatch(r"!\[(.*?)\]\((.+?)\)", b)
        if im:
            blocks.append({"type": "image", "alt": im.group(1), "src": (md.parent / im.group(2)).as_posix()})
        elif b.startswith("## "):
            blocks.append({"type": "h2", "text": b[3:].strip()})
        elif b.startswith(">"):
            blocks.append({"type": "quote", "text": re.sub(r"^>\s?", "", b, flags=re.M)})
        else:
            blocks.append({"type": "p", "text": b})
    hero = conf.get("hero") or meta.get("hero", "")
    refs = []
    for path, label in meta.get("sources", []):
        src = ROOT / "sources" / path
        url = front(src.read_text(encoding="utf-8")).get("url", "") if src.is_file() else ""
        refs.append({"label": label, "url": url})
    return {"id": k, "meta": mp, "title": title or meta.get("title", k), "blocks": blocks,
            "hero": (ROOT / hero).as_posix() if hero else "", "references": refs,
            "confirmed": conf, "pub_date": date.today().isoformat()}


# ---------- HTML ----------

def inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    return s.replace("\n", "<br>")


def render(a, files, body_class=""):
    """files: 원본 그림 경로 → 발행 폴더 안 파일 이름"""
    cfg, e = settings(), html.escape
    body = []
    for b in a["blocks"]:
        if b["type"] == "image":
            body.append(f'<img class="section-image" src="{e(files[b["src"]])}" alt="{e(b["alt"])}">')
        elif b["type"] == "h2":
            body.append(f"<h2>{inline(b['text'])}</h2>")
        elif b["type"] == "quote":
            body.append(f"<blockquote><p>{inline(b['text'])}</p></blockquote>")
        else:
            body.append(f"<p>{inline(b['text'])}</p>")
    hero = ""
    if a["hero"]:
        hero = (f'<div class="hero">\n  <img src="{e(files[a["hero"]])}" alt="{e(a["title"])}">\n  <div class="hero-scrim"></div>\n'
                f'  <div class="hero-caption">\n    <div class="hero-kicker">{e(cfg["kicker"])}</div>\n'
                f'    <h1 class="hero-title">{e(a["title"])}</h1>\n  </div>\n</div>')
    else:  # 머리 그림이 없으면 제목만 — 템플릿의 제목이 사라지지 않게
        hero = f'<div class="article-page"><h1 class="plain-title">{e(a["title"])}</h1></div>'
    refs = ""
    if a["references"]:
        items = "\n".join(
            f'      <li><a href="{e(r["url"])}" target="_blank" rel="noopener">{e(r["label"])}</a></li>' if r["url"]
            else f"      <li>{e(r['label'])}</li>" for r in a["references"])
        refs = f'<section class="references">\n    <h3>참고자료</h3>\n    <ul>\n{items}\n    </ul>\n  </section>'
    rep = {
        "{{ title }}": e(a["title"]), "{{ kicker }}": e(cfg["kicker"]), "{{ issue_label }}": e(a["pub_date"]),
        "{{ hero_html }}": hero, "{{ tldr_html }}": "",
        "{{ body_html }}": "\n    ".join(body), "{{ references_html }}": refs, "{{ footer }}": cfg["footer"],
        "{{ body_class }}": body_class,
    }
    page = (WEB / "article.html").read_text(encoding="utf-8")
    for key, v in rep.items():
        page = page.replace(key, v)
    return page


def build(k):
    """publish/<글>/ — 웹 발행본(index.html)과 메일 캡처용 변형 두 장, 그림, article.json"""
    a = load(k)
    out = OUT / k
    out.mkdir(parents=True, exist_ok=True)
    for f in out.iterdir():  # 지난 발행의 메일(.eml·캡처)은 남긴다 — 미리보기를 다시 만들어도 받을 수 있게
        if f.is_file() and f.suffix != ".eml" and not f.name.startswith("email_"):
            f.unlink()
    files = {}
    if a["hero"]:
        files[a["hero"]] = "hero.png"
    n = 0
    for b in a["blocks"]:
        if b["type"] == "image" and b["src"] not in files:
            n += 1
            files[b["src"]] = f"img-{n}.png"
    for src, name in files.items():
        if not Path(src).is_file():
            raise SystemExit("그림 없음: " + src)
        shutil.copyfile(src, out / name)
    shutil.copyfile(WEB / "article.css", out / "style.css")
    (out / "index.html").write_text(render(a, files), encoding="utf-8")
    # email.html은 작업실 미리보기용(머리·본문을 한 장으로), 캡처는 머리·본문을 나눠 그 사이에 "웹에서 보기" 줄을 넣는다
    (out / "email.html").write_text(render(a, files, "email-capture"), encoding="utf-8")
    for part in ("head", "body"):
        (out / f"email-{part}.html").write_text(render(a, files, f"email-capture email-part-{part}"), encoding="utf-8")
    info = {"id": k, "title": a["title"], "pub_date": a["pub_date"], "hero_file": files.get(a["hero"], ""),
            "teaser": next((b["text"] for b in a["blocks"] if b["type"] == "p"), "")[:140],
            "web_url": web_url(k)}  # 웹에도 올라가는 파일 — 내부 경로(columns/…)는 넣지 않는다
    (out / "article.json").write_text(json.dumps(info, ensure_ascii=False, indent=1), encoding="utf-8")
    return a, out, info


# ---------- 메일 (main web/email_renderer.py 방법 B) ----------

def web_url(k):
    cfg = settings()
    base = (cfg.get("web_base_url") or "").strip().rstrip("/")
    return f"{base}/{cfg['web_path_token']}/{quote(k)}/" if base else ""


def trim_bottom(img, pad=60):
    """하단의 빈 영역(균일 색상 행)을 지우고 pad 픽셀만 남긴다."""
    w, h = img.size
    xs = list(range(10, w - 10, max(1, w // 30)))
    px = img.convert("RGB").load()
    for y in range(h - 1, -1, -1):
        row = [px[x, y] for x in xs]
        if any(max(abs(c[i] - row[0][i]) for i in range(3)) > 10 for c in row):
            return img.crop((0, 0, w, min(y + 1 + pad, h)))
    return img


def capture(pages):
    """[(html 파일, png 파일, 아래 여백)] — EMAIL_WIDTH 폭·2배율 전체 페이지 캡처. 번들 크로미움이 없으면 설치된 Chrome."""
    from PIL import Image
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        try:
            br = p.chromium.launch()
        except Exception:
            br = p.chromium.launch(channel="chrome")
        pg = br.new_page(viewport={"width": EMAIL_WIDTH, "height": 900}, device_scale_factor=2)
        for src, png, pad in pages:
            pg.goto(src.resolve().as_uri(), wait_until="networkidle")
            pg.evaluate("document.fonts.ready")
            pg.screenshot(path=str(png), full_page=True)
            trim_bottom(Image.open(png), pad).save(png)
        br.close()


def web_link_row(url, top=False):
    """"웹에서 보기" 줄 — 이미지 안의 참고자료 링크는 눌리지 않으므로 웹페이지로 보낸다."""
    if not url:
        return ""
    u = html.escape(url, quote=True)
    lead = "글자가 작게 보이면" if top else "참고자료 링크는 웹페이지에서 열립니다"
    pad = "14px 16px" if top else "4px 16px 28px"
    return (f'<tr><td align="center" style="padding:{pad};font-family:{FONT};font-size:11pt;line-height:1.5;color:{INK_MUTED};">'
            f'{lead} &middot; <a href="{u}" target="_blank" style="color:{ACCENT};font-weight:700;text-decoration:underline;">웹에서 보기</a></td></tr>')


def img_row(cid, w, alt, url):
    tag = (f'<img src="cid:{cid}" width="{w}" style="display:block;width:{w}px;max-width:100%;height:auto;border:0;" '
           f'alt="{html.escape(alt, quote=True)}">')
    if url:
        tag = f'<a href="{html.escape(url, quote=True)}" target="_blank">{tag}</a>'
    return f'<tr><td align="center" style="padding:0;">{tag}</td></tr>'


def wrap_mail(rows):
    return f"""<!DOCTYPE html>
<html lang="ko">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<style>body{{margin:0;padding:0;background:{CANVAS};}}table{{border-collapse:collapse;}}img{{border:0;}}</style>
</head>
<body style="margin:0;padding:0;background:{CANVAS};">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{CANVAS};">
<tr><td align="center" style="padding:20px 0;">
<table role="presentation" width="{EMAIL_WIDTH}" cellpadding="0" cellspacing="0" style="width:100%;max-width:{EMAIL_WIDTH}px;">
{rows}
</table>
</td></tr>
</table>
</body></html>"""


def png_part(path, cid):
    m = MIMEImage(path.read_bytes(), _subtype="png")
    m.add_header("Content-ID", f"<{cid}>")
    m.add_header("Content-Disposition", "inline", filename=f"{cid}.png")
    return m


def build_eml(a, out, to, cc):
    from PIL import Image
    cfg, url = settings(), web_url(a["id"])
    head, body = out / "email_head.png", out / "email_body.png"
    capture([(out / "email-head.html", head, 0), (out / "email-body.html", body, 60)])
    hi, bi = Image.open(head), Image.open(body)
    full = Image.new("RGB", (hi.width, hi.height + bi.height))
    full.paste(hi, (0, 0))
    full.paste(bi, (0, hi.height))
    full.save(out / "email_screenshot.png")  # 미리보기·검토용
    w = min(hi.width // 2, EMAIL_WIDTH)
    subject = cfg["subject_prefix"] + a["title"]
    rows = "\n".join([img_row("article_head", w, subject, url), web_link_row(url, True),
                      img_row("article_body", w, cfg["kicker"], url), web_link_row(url)])
    msg = MIMEMultipart("related")
    msg["Subject"], msg["From"], msg["To"] = subject, cfg["sender"], ", ".join(to)
    if cc:
        msg["Cc"] = ", ".join(cc)
    msg["X-Unsent"] = "1"  # Outlook이 받은 메일이 아니라 보낼 초안으로 연다
    msg.attach(MIMEText(wrap_mail(rows), "html", "utf-8"))
    msg.attach(png_part(head, "article_head"))
    msg.attach(png_part(body, "article_body"))
    (out / "newsletter.eml").write_bytes(msg.as_bytes())
    return out / "newsletter.eml"


# ---------- 사이트 (main web/site_export.py) ----------

def export_site(k, out):
    token_dir = SITE / settings()["web_path_token"]
    dest = token_dir / k
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    for f in out.iterdir():
        if f.is_file() and f.name not in SKIP:
            shutil.copy2(f, dest / f.name)
    SITE.mkdir(exist_ok=True)  # 사이트 루트는 빈 페이지 — 토큰 경로를 모르면 아무것도 찾을 수 없게
    (SITE / "index.html").write_text('<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8">'
                                     '<meta name="robots" content="noindex, nofollow"><title></title></head><body></body></html>\n', encoding="utf-8")
    (SITE / "robots.txt").write_text("User-agent: *\nDisallow: /\n", encoding="utf-8")
    entries = []
    for m in token_dir.glob("*/article.json"):
        x = json.loads(m.read_text(encoding="utf-8"))
        entries.append((x.get("pub_date", ""), m.parent.name, x))
    entries.sort(key=lambda t: (t[0], t[1]), reverse=True)
    e = html.escape
    cards = "\n".join(
        f'<a class="card" href="{e(quote(s))}/">'
        + (f'<img src="{e(quote(s))}/{e(x["hero_file"])}" alt="" loading="lazy">' if x.get("hero_file") else "")
        + f'<div class="card-body"><div class="card-meta">{e(x.get("pub_date", ""))}</div><h2>{e(x.get("title", s))}</h2>'
        f'<p>{e(x.get("teaser", ""))}</p></div></a>' for _, s, x in entries) or '<p class="empty">아직 발행된 글이 없습니다.</p>'
    (token_dir / "index.html").write_text(INDEX.replace("{{ kicker }}", e(settings()["kicker"])).replace("{{ cards }}", cards), encoding="utf-8")
    return dest


INDEX = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>{{ kicker }}</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable.min.css">
<style>
  :root { --accent:#0B6E4F; --canvas:#F7F8FA; --surface:#FFFFFF; --ink:#101114; --ink2:#3D4148; --muted:#6E7278; --line:#DFE1E5; }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--canvas); color:var(--ink); font-family:"Pretendard Variable",Pretendard,"Malgun Gothic",sans-serif; }
  header { max-width:760px; margin:0 auto; padding:20px 16px; font-weight:800; letter-spacing:0.1em; text-transform:uppercase; }
  main { max-width:760px; margin:0 auto; padding:0 16px 48px; display:grid; gap:16px; }
  .card { display:block; background:var(--surface); border:1px solid var(--line); border-radius:16px; overflow:hidden; color:inherit; text-decoration:none; }
  .card:hover { border-color:var(--accent); }
  .card img { display:block; width:100%; aspect-ratio:16/7; object-fit:cover; }
  .card-body { padding:20px 24px; }
  .card-meta { font-size:13px; color:var(--muted); }
  .card h2 { margin:6px 0 10px; font-size:20px; line-height:1.4; letter-spacing:-0.02em; word-break:keep-all; }
  .card p { margin:0; color:var(--ink2); font-size:15px; line-height:1.7; word-break:keep-all; }
  .empty { color:var(--muted); }
</style>
</head>
<body>
<header>{{ kicker }}</header>
<main>
{{ cards }}
</main>
</body>
</html>
"""


# ---------- 발행 ----------

def git(*args):
    r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode:
        raise SystemExit(f"git {' '.join(args)} 실패: {(r.stderr or r.stdout).strip()}")
    return r.stdout.strip()


def release(k, to, cc, push=True):
    a, out, info = build(k)
    print("1/4 웹 발행본 —", out.relative_to(ROOT).as_posix(), flush=True)
    eml = build_eml(a, out, to, cc)
    print("2/4 메일 —", eml.relative_to(ROOT).as_posix(), flush=True)
    dest = export_site(k, out)
    print("3/4 사이트 —", dest.relative_to(ROOT).as_posix(), flush=True)
    meta = json.loads(a["meta"].read_text(encoding="utf-8"))
    meta["published"] = {"date": a["pub_date"], "url": info["web_url"], "site": dest.relative_to(ROOT).as_posix(),
                         "eml": eml.relative_to(ROOT).as_posix(), "to": to, "cc": cc}
    a["meta"].write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    git("add", "--", "site", a["meta"].relative_to(ROOT).as_posix())
    if git("diff", "--cached", "--name-only"):
        git("commit", "-m", f"발행: {a['title']}", "--", "site", a["meta"].relative_to(ROOT).as_posix())
    if push:
        git("push", "origin", "HEAD")
        print("4/4 커밋·푸시 — Vercel이 site/를 배포", flush=True)
    else:
        print("4/4 커밋만 (--no-push)", flush=True)
    if not info["web_url"]:
        print("주의: config/publish.json web_base_url이 비어 있어 메일에 '웹에서 보기' 링크가 없습니다.", flush=True)
    print(json.dumps(meta["published"], ensure_ascii=False), flush=True)


def main():
    ap = argparse.ArgumentParser(description="확정 칼럼 발행")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("article")
    r = sub.add_parser("release")
    r.add_argument("article")
    r.add_argument("--to", required=True, help="쉼표 구분")
    r.add_argument("--cc", default="")
    r.add_argument("--no-push", action="store_true")
    args = ap.parse_args()
    split = lambda v: [x.strip() for x in v.split(",") if x.strip()]
    if args.cmd == "build":
        _, out, info = build(args.article)
        print(json.dumps({**info, "dir": out.relative_to(ROOT).as_posix()}, ensure_ascii=False))
    else:
        to = split(args.to)
        if not to:
            raise SystemExit("받는 사람이 없습니다.")
        release(args.article, to, split(args.cc), not args.no_push)


if __name__ == "__main__":
    sys.exit(main())

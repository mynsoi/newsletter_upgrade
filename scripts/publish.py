"""확정 칼럼 → 웹 발행(Vercel 정적 사이트) + 이미지 메일(.eml).

HTML 구조·디자인과 메일 방식은 main 브랜치(web/server.py · web/email_renderer.py · web/site_export.py)를 따른다.
- 웹: web/article.html + web/article.css (Offpiste식 1컬럼, Pine Green)
- 메일: 웹페이지의 메일 전용 변형(email.html)을 800px 폭으로 한 장 찍어 넣은 이미지 메일.
  보내지는 않는다 — .eml을 Outlook에서 열어 확인한 뒤 사람이 보낸다.
- 배포: site/<web_path_token>/<글>/ 로 복사하고 아카이브 목록을 다시 만든 뒤 커밋·푸시 → vercel.json이 site/를 배포.

사용:
  python3 -I scripts/publish.py build <글>                         # 미리보기만 — publish/<글>/ (git 밖)
  python3 -I scripts/publish.py release <글> --to a@x,b@x [--cc …] [--no-push]
  python3 -I scripts/publish.py unpublish <글…> [--no-push]          # 웹에서 내리기(아카이브 목록도 다시)
  python3 -I scripts/publish.py refresh [--no-push]                  # 이미 발행한 글에 조회수·좋아요 자리 붙이기(본문·발행일은 그대로)
조회수·좋아요(2026-11-20): 글·목록 페이지가 reader.js로 /api/reader(Vercel 함수 api/reader.py)를 부른다. 발행·내리기 때 발행 목록을
  Supabase site_articles 표에 맞춘다(scripts/reader_stats.py) — 표에 있는 글만 수치를 받는다. 메일에는 넣지 않는다.
설정: config/publish.json (web_base_url · web_path_token · 보내는 사람). 받는 사람은 git 밖 publish/recipients.json에만 남긴다(주소 공개 방지)
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
# email-head/-body·email_head/_body는 2026-11-25 이전(머리·본문 두 장) 파일 — 예전 미리보기 폴더에 남아 있어도 사이트로 복사하지 않게 둔다
SKIP = {"newsletter.eml", "email.html", "email-head.html", "email-body.html", "email_head.png", "email_body.png", "email_screenshot.png"}

# 조회수·좋아요 자리(web/reader.js가 채운다 — 수치를 받기 전에는 숨김). 메일 캡처용 변형에는 넣지 않는다
READER_BAR = '<div class="reader-bar" data-article="{id}" hidden></div>'
READER_SCRIPT = '<script src="reader.js" defer></script>'

# 디자인 토큰 — web/article.css와 같은 값
CANVAS = "#F7F8FA"
EMAIL_WIDTH = 800  # main은 600 — 데스크톱 Outlook에서 좁아 보여 넓힘(2026-10-20, 960은 넓다고 해 800). 캡처 CSS(article.css .email-capture)가 이 폭 기준


# 받는 사람 주소는 git에 올리지 않는다(2026-11-18 — 저장소가 Public이라 글 설정에 적으면 주소가 공개된다).
# 이 PC에만 두는 파일: publish/recipients.json (publish/는 .gitignore) — {"<글>": {"to": [...], "cc": [...]}, "_last": {...}}
RECIPIENTS = ROOT / "publish" / "recipients.json"


def recipients():
    try:
        return json.loads(RECIPIENTS.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_recipients(k, to, cc):
    """이 글에 쓴 받는 사람을 이 PC에만 적어 둔다 — 다시 발행할 때 화면에 채워 주고, 다른 글의 기본값(_last)으로도 쓴다."""
    r = recipients()
    r[k] = r["_last"] = {"to": to, "cc": cc}
    RECIPIENTS.parent.mkdir(parents=True, exist_ok=True)
    RECIPIENTS.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")


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
    return dict(re.findall(r"^(\w+):[ \t]*'?(.*?)'?[ \t]*$", m.group(1), re.M))  # [ \t]* — 빈 칸이 다음 줄을 값으로 읽지 않게


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
        if not blocks and re.match(r"\**가제\s*[:：]", b):  # 가제 줄은 발행본에 넣지 않는다(2026-10-23 — 가제를 붙이던 때 확정한 글)
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
        fm = front(src.read_text(encoding="utf-8")) if src.is_file() else {}
        # 참고자료에 원문 제목도(2026-10-22) — '제목 (사이트, 작성자, 날짜)'. 제목 끝의 ' | 사이트명'은 뗀다
        # src_title — 칼럼 제목(title)과 이름이 겹치면 칼럼 제목이 마지막 원문 제목으로 덮였다(2026-10-22 발행 미리보기 제목 버그)
        src_title = re.sub(r"\s+[|｜]\s+[^|｜]{1,40}$", "", fm.get("title", "")).strip()
        refs.append({"label": f"{src_title} ({label})" if src_title else label, "url": fm.get("url", "")})
    # 사내 자료는 원고에 썼어도 참고자료에 올리지 않는다(2026-10-29 사용자 — 발행본에 내부 자료 이름이 나가지 않게. 10/23엔 제목을 붙였었다)
    return {"id": k, "meta": mp, "title": title or meta.get("title", k), "blocks": blocks,
            "hero": (ROOT / hero).as_posix() if hero else "", "references": refs,
            # 발행일은 발행(다시 발행 포함)한 날 — 웹·아카이브·메일 모두(2026-11-26 사용자. 11/25에 처음 발행일 유지로 바꿨다가 되돌림)
            "confirmed": conf, "pub_date": date.today().isoformat(),
            # 제목 아래 안내 상자 — 글 메타에 notice가 있으면 그 값(빈 값이면 상자 없음), 없으면 config/publish.json의 notice(2026-11-12 사용자: 매 발행본 기본으로)
            "notice": meta["notice"] if "notice" in meta else settings().get("notice", ""),
            "footer": meta.get("footer")}  # 이 글만 바닥글을 바꿀 때(2026-10-29). 없으면 config/publish.json


# ---------- HTML ----------

def inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"==(.+?)==", r'<strong class="key">\1</strong>', s)  # 강조(굵게) — 작업실 편집기의 강조 버튼(2026-11-04)
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
    else:  # 머리 그림이 없으면 제목만 — 템플릿의 제목이 사라지지 않게(메일은 늘 이쪽, build 참고)
        hero = f'<div class="article-page title-only"><h1 class="plain-title">{e(a["title"])}</h1></div>'
    refs = ""
    if a["references"]:
        items = "\n".join(
            f'      <li><a href="{e(r["url"])}" target="_blank" rel="noopener">{e(r["label"])}</a></li>' if r["url"]
            else f"      <li>{e(r['label'])}</li>" for r in a["references"])
        refs = f'<section class="references">\n    <h3>참고자료</h3>\n    <ul>\n{items}\n    </ul>\n  </section>'
    notice = ""
    if a.get("notice"):
        lines = [x for x in a["notice"].split("\n") if x.strip()]  # '※'로 시작하는 줄은 작은 회색 글씨(담당자 등)
        # 왼쪽에 공지 아이콘(확성기, 2026-11-12) — 메일 캡처에도 그대로 찍히게 인라인 SVG
        icon = ('<svg class="notice-icon" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" '
                'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
                '<path d="M3 10.5v3a1 1 0 0 0 1 1h2.5L13 19V5L6.5 9.5H4a1 1 0 0 0-1 1z" fill="currentColor" fill-opacity=".15"/>'
                '<path d="M16.5 9a4 4 0 0 1 0 6M19 6.5a7.5 7.5 0 0 1 0 11"/></svg>')
        notice = '<aside class="notice">' + icon + '<div class="notice-text">' + "".join(
            f'<p class="notice-note">{inline(x)}</p>' if x.startswith("※") else f"<p>{inline(x)}</p>" for x in lines) + "</div></aside>"
    rep = {
        "{{ title }}": e(a["title"]), "{{ kicker }}": e(cfg["kicker"]), "{{ issue_label }}": e(a["pub_date"]),
        "{{ hero_html }}": hero, "{{ tldr_html }}": notice,
        "{{ body_html }}": "\n    ".join(body), "{{ references_html }}": refs, "{{ footer }}": a.get("footer") or cfg["footer"],
        "{{ body_class }}": body_class,
        "{{ reader_html }}": "" if body_class else READER_BAR.format(id=e(a["id"])),
        "{{ reader_script }}": "" if body_class else READER_SCRIPT,
    }
    page = (WEB / "article.html").read_text(encoding="utf-8")
    for key, v in rep.items():
        page = page.replace(key, v)
    return page


def build(k):
    """publish/<글>/ — 웹 발행본(index.html)과 메일 캡처용 변형(email.html), 그림, article.json"""
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
    shutil.copyfile(WEB / "reader.js", out / "reader.js")
    (out / "index.html").write_text(render(a, files), encoding="utf-8")
    # email.html — 작업실 미리보기이자 메일 캡처 원본. 한 장으로 찍는다(2026-11-25 사용자 — 예전엔 머리·본문 두 장이었다.
    # 사이에 '웹에서 보기' 줄을 넣으려던 구조인데 그 줄은 10/26에 없앴고, 머리 아래를 바짝 잘라 내다 제목 y 꼬리가 잘렸다)
    # 메일에는 머리 그림을 넣지 않는다 — 첫 화면에서 본문이 바로 보이게(팀장 의견, 2026-10-26).
    # 머리는 헤더 + 제목 글자만. 웹 발행본(index.html)·아카이브 썸네일은 머리 그림 그대로
    mail = {**a, "hero": ""}
    (out / "email.html").write_text(render(mail, files, "email-capture"), encoding="utf-8")
    info = {"id": k, "title": a["title"], "pub_date": a["pub_date"], "hero_file": files.get(a["hero"], ""),
            "teaser": teaser(b["text"] for b in a["blocks"] if b["type"] == "p"),
            "web_url": web_url(k)}  # 웹에도 올라가는 파일 — 내부 경로(columns/…)는 넣지 않는다
    (out / "article.json").write_text(json.dumps(info, ensure_ascii=False, indent=1), encoding="utf-8")
    return a, out, info


TEASER_LEN = 200  # 목록 카드는 2줄만 보여 준다(INDEX의 .card p) — 넓은 화면의 2줄(90자 안팎)을 넉넉히 채울 길이


def teaser(paragraphs):
    """목록 카드의 미리보기 글 — 첫 문단이 짧으면 다음 문단까지 이어 붙인다(2026-11-20: 첫 문단 길이대로라 카드마다 1줄·3줄로 달랐다).
    굵게·강조 표시는 떼고, 줄바꿈은 빈칸으로."""
    out = ""
    for t in paragraphs:
        t = re.sub(r"\*\*|==", "", t)
        out = (out + " " + " ".join(t.split())).strip()
        if len(out) >= TEASER_LEN:
            break
    return out[:TEASER_LEN]


def teaser_from_page(page):
    """발행된 index.html에서 본문 문단을 읽어 미리보기 글을 다시 만든다(refresh — 확정 원고를 다시 읽지 않고 발행된 그대로에서)."""
    m = re.search(r'<article class="article-body">(.*?)</article>', page, re.S)
    body = re.sub(r"<blockquote>.*?</blockquote>", "", m.group(1), flags=re.S) if m else ""
    return teaser(html.unescape(re.sub(r"<[^>]+>", "", x.replace("<br>", " "))) for x in re.findall(r"<p>(.*?)</p>", body, re.S))


# ---------- 메일 (main web/email_renderer.py 방법 B) ----------

def web_url(k):
    cfg = settings()
    base = (cfg.get("web_base_url") or "").strip().rstrip("/")
    return f"{base}/{cfg['web_path_token']}/{quote(k)}/" if base else ""


def trim_bottom(img, pad=60):
    """하단의 빈 영역(균일 색상 행)을 지우고 pad 픽셀만 남긴다."""
    w, h = img.size
    # 가로 모든 칸을 본다(2026-11-25) — 예전엔 w//30(2배율 1600px에서 53px) 간격이라 y·g 같은 가는 꼬리가 칸 사이에 끼면
    # 빈 줄로 보고 잘랐다(머리 캡처는 pad 0이라 제목 y 꼬리가 잘림). 아래에서 위로 보다 글자를 만나면 멈추므로 비용은 작다
    xs = list(range(10, w - 10))
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


def img_row(cid, w, alt, url):
    """메일 이미지 한 줄 — 누르면 웹페이지로 간다(이미지 안의 참고자료 링크는 눌리지 않으므로).
    2026-10-26부터 이미지 사이·아래의 '웹에서 보기' 글자 줄은 넣지 않는다 — 이미지 링크만."""
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
    shot = out / "email_screenshot.png"  # 메일에 넣는 한 장(작업실 검토에도 이 파일)
    capture([(out / "email.html", shot, 60)])
    w = min(Image.open(shot).width // 2, EMAIL_WIDTH)
    subject = cfg["subject_prefix"] + a["title"]
    rows = img_row("article", w, subject, url)
    msg = MIMEMultipart("related")
    msg["Subject"], msg["From"], msg["To"] = subject, cfg["sender"], ", ".join(to)
    if cc:
        msg["Cc"] = ", ".join(cc)
    msg["X-Unsent"] = "1"  # Outlook이 받은 메일이 아니라 보낼 초안으로 연다
    msg.attach(MIMEText(wrap_mail(rows), "html", "utf-8"))
    msg.attach(png_part(shot, "article"))
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
    build_index()
    return dest


def build_index():
    token_dir = SITE / settings()["web_path_token"]
    token_dir.mkdir(parents=True, exist_ok=True)
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
    shutil.copyfile(WEB / "reader.js", token_dir / "reader.js")  # 목록 카드의 조회·좋아요 수치
    cards = "\n".join(
        f'<a class="card" data-article="{e(s)}" href="{e(quote(s))}/">'
        + (f'<img src="{e(quote(s))}/{e(x["hero_file"])}" alt="" loading="lazy">' if x.get("hero_file") else "")
        + f'<div class="card-body"><div class="card-meta">{e(x.get("pub_date", ""))}</div><h2>{e(x.get("title", s))}</h2>'
        f'<p>{e(x.get("teaser", ""))}</p></div></a>' for _, s, x in entries) or '<p class="empty">아직 발행된 글이 없습니다.</p>'
    (token_dir / "index.html").write_text(INDEX.replace("{{ kicker }}", e(settings()["kicker"])).replace("{{ cards }}", cards), encoding="utf-8")


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
  .card p { margin:0; color:var(--ink2); font-size:15px; line-height:1.7; word-break:keep-all;
    display:-webkit-box; -webkit-box-orient:vertical; -webkit-line-clamp:2; line-clamp:2; overflow:hidden; }
  .empty { color:var(--muted); }
</style>
</head>
<body>
<header>{{ kicker }}</header>
<main>
{{ cards }}
</main>
<script src="reader.js" defer></script>
</body>
</html>
"""


# ---------- 발행 ----------

def push_branch():
    """운영 브랜치에 올린다 — 다른 PC·동료가 먼저 올렸으면 받아서(rebase) 다시(2026-10-26, wiki.push와 같은 방식)."""
    sys.path.insert(0, str(ROOT / "scripts"))
    import wiki as W
    if not W.push():
        raise SystemExit("git push 실패 — 발행 커밋은 이 PC에 남아 있습니다. git status로 확인한 뒤 다시 발행하세요")


def git(*args):
    r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode:
        raise SystemExit(f"git {' '.join(args)} 실패: {(r.stderr or r.stdout).strip()}")
    return r.stdout.strip()


def sync_reader():
    """발행 목록을 DB에 맞춘다(조회수·좋아요가 받을 글) — 닿지 못해도 발행은 막지 않고 알리기만 한다."""
    sys.path.insert(0, str(ROOT / "scripts"))
    import reader_stats as RS
    ok, msg = RS.sync()
    print(("조회수·좋아요 — " if ok else "주의: 조회수·좋아요 발행 목록을 DB에 맞추지 못했습니다 — ") + msg
          + ("" if ok else " (나중에: python -I scripts/reader_stats.py sync)"), flush=True)


def refresh(push=True):
    """이미 발행한 글에 조회수·좋아요 자리를 붙이고 목록(미리보기 글 포함)을 다시 만든다 — 본문·발행일·style.css는 건드리지 않는다(다시 발행하면 발행일이 그날로 바뀌므로).
    index.html에 자리와 스크립트 줄만 끼우고 reader.js를 새로 복사한다. 이미 붙은 글은 reader.js만 바뀐다."""
    token_dir = SITE / settings()["web_path_token"]
    for m in sorted(token_dir.glob("*/article.json")):
        d, k = m.parent, m.parent.name
        page = (d / "index.html").read_text(encoding="utf-8")
        if 'class="reader-bar"' not in page:
            bar = READER_BAR.format(id=html.escape(k))
            for mark in ('<section class="references">', "</main>"):  # 참고자료 위, 없으면 본문 끝
                if mark in page:
                    page = page.replace(mark, bar + "\n\n  " + mark, 1)
                    break
            else:
                raise SystemExit(f"자리를 찾지 못했습니다: {k}")
            page = page.replace("</body>", READER_SCRIPT + "\n</body>", 1)
            (d / "index.html").write_text(page, encoding="utf-8")
            print("붙임 —", k, flush=True)
        shutil.copyfile(WEB / "reader.js", d / "reader.js")
        info = json.loads(m.read_text(encoding="utf-8"))  # 목록 미리보기 글도 지금 방식으로(본문에서 다시)
        t = teaser_from_page(page)
        if t and t != info.get("teaser"):
            info["teaser"] = t
            m.write_text(json.dumps(info, ensure_ascii=False, indent=1), encoding="utf-8")
    build_index()
    sync_reader()
    git("add", "-A", "--", "site")
    if git("diff", "--cached", "--name-only", "--", "site"):
        git("commit", "-m", "발행본에 조회수·좋아요 자리", "--", "site")
    if push:
        push_branch()


def release(k, to, cc, push=True):
    a, out, info = build(k)
    print("1/4 웹 발행본 —", out.relative_to(ROOT).as_posix(), flush=True)
    eml = build_eml(a, out, to, cc)
    print("2/4 메일 —", eml.relative_to(ROOT).as_posix(), flush=True)
    dest = export_site(k, out)
    print("3/4 사이트 —", dest.relative_to(ROOT).as_posix(), flush=True)
    sync_reader()
    meta = json.loads(a["meta"].read_text(encoding="utf-8"))
    meta["published"] = {"date": a["pub_date"], "url": info["web_url"], "site": dest.relative_to(ROOT).as_posix(),
                         "eml": eml.relative_to(ROOT).as_posix()}  # 받는 사람은 여기 적지 않는다 — save_recipients
    save_recipients(k, to, cc)
    a["meta"].write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    mine = ["site", a["meta"].relative_to(ROOT).as_posix()]
    git("add", "--", *mine)
    if git("diff", "--cached", "--name-only", "--", *mine):
        # 작업실 자동 공유가 그 사이 이 파일들을 먼저 커밋했으면 커밋할 게 없어 실패한다(2026-11-03 발행 실패) — 남은 변경이 없으면 괜찮다
        r = subprocess.run(["git", "commit", "-m", f"발행: {a['title']}", "--", *mine], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode and git("status", "--porcelain", "--", *mine):
            raise SystemExit(f"git commit 실패: {(r.stderr or r.stdout).strip()}")
    if push:  # 인자 이름이 push라 함수는 push_branch — 같은 이름이면 bool을 부르다 죽는다(2026-10-26 발행 실패)
        push_branch()
        print("4/4 커밋·푸시 — Vercel이 site/를 배포", flush=True)
    else:
        print("4/4 커밋만 (--no-push)", flush=True)
    if not info["web_url"]:
        print("주의: config/publish.json web_base_url이 비어 있어 메일 이미지에 웹페이지 링크가 없습니다.", flush=True)
    print(json.dumps(meta["published"], ensure_ascii=False), flush=True)


def unpublish(ks, push=True):
    """웹에서 내린다 — site/<토큰>/<글>/을 지우고 아카이브 목록을 다시 만들고, 글 설정의 published를 지운다.
    이미 보낸 메일의 이미지 링크(웹페이지)는 끊긴다."""
    paths = ["site"]
    for k in ks:
        d = SITE / settings()["web_path_token"] / k
        if d.exists():
            shutil.rmtree(d)
        try:
            mp = meta_path(k)
        except SystemExit:  # 글은 이미 지웠고 웹에만 남은 경우
            continue
        meta = json.loads(mp.read_text(encoding="utf-8"))
        if meta.pop("published", None) is not None:
            mp.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
            paths.append(mp.relative_to(ROOT).as_posix())
        print("내림 —", k, flush=True)
    build_index()
    sync_reader()
    git("add", "-A", "--", *paths)
    if git("diff", "--cached", "--name-only", "--", *paths):
        git("commit", "-m", "웹에서 내림: " + ", ".join(ks), "--", *paths)
    if push:
        push_branch()


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
    u = sub.add_parser("unpublish")
    u.add_argument("article", nargs="+")
    u.add_argument("--no-push", action="store_true")
    f = sub.add_parser("refresh")
    f.add_argument("--no-push", action="store_true")
    args = ap.parse_args()
    split = lambda v: [x.strip() for x in v.split(",") if x.strip()]
    if args.cmd == "unpublish":
        return unpublish(args.article, not args.no_push)
    if args.cmd == "refresh":
        return refresh(not args.no_push)
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

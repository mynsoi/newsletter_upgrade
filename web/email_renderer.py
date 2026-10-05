"""
아티클 → Outlook 이메일 HTML 변환기

웹 아티클 HTML을 Outlook(Word 렌더엔진) 호환 테이블 레이아웃으로 변환한다.
- 히어로: 이미지 + 제목 오버레이 → 합성 PNG (CID 임베드)
- 본문: 인라인 스타일 테이블 레이아웃
- 섹션 이미지: 둥근 모서리 적용 PNG (CID 임베드)
"""
import io
import re
import html
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

from PIL import Image, ImageDraw, ImageFont
import markdown as md_lib

from segments import SEGMENT_LABELS, split_segment_blocks

# ── 디자인 토큰 ──
ACCENT = "#0B6E4F"
ACCENT_SOFT = "#DCEFE7"
CANVAS = "#F7F8FA"
SURFACE = "#FFFFFF"
INK = "#101114"
INK_SECONDARY = "#3D4148"
INK_MUTED = "#6E7278"
LINE = "#DFE1E5"
CONTENT_WIDTH = 760
PAD = 48
FONT = "Malgun Gothic, sans-serif"

FONT_DIR = Path(__file__).parent / "fonts"


def _round_corners(img: Image.Image, radius: int = 24) -> Image.Image:
    mask = Image.new("L", img.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([0, 0, img.size[0], img.size[1]], radius=radius, fill=255)
    result = img.copy()
    result.putalpha(mask)
    bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
    bg.paste(result, mask=result)
    return bg.convert("RGB")


def _crop_to_fill(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    w, h = img.size
    scale = max(target_w / w, target_h / h)
    new_w = int(w * scale)
    new_h = int(h * scale)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    return img.crop((left, top, left + target_w, top + target_h))


def _load_font(name: str, size: int) -> ImageFont.FreeTypeFont:
    candidates = [
        FONT_DIR / name,
        Path(f"C:/Windows/Fonts/{name}"),
    ]
    for p in candidates:
        if p.exists():
            return ImageFont.truetype(str(p), size)
    return ImageFont.load_default()


def _make_hero_image(hero_path: str, title: str, kicker: str = "Insight Weekly") -> bytes:
    img = Image.open(hero_path).convert("RGBA")

    target_w = CONTENT_WIDTH * 2
    target_h = int(target_w * 7 / 16)
    img = _crop_to_fill(img, target_w, target_h)
    w, h = img.size

    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for y in range(h):
        if y < h * 0.3:
            alpha = int(25 * (1 - y / (h * 0.3)))
        elif y > h * 0.5:
            alpha = int(180 * ((y - h * 0.5) / (h * 0.5)))
        else:
            alpha = 0
        draw.line([(0, y), (w, y)], fill=(10, 11, 14, alpha))

    img = Image.alpha_composite(img, overlay)
    draw = ImageDraw.Draw(img)

    font_title = _load_font("Pretendard-ExtraBold.otf", 72)
    font_kicker = _load_font("Pretendard-Bold.otf", 22)

    padding = 48
    max_text_w = w - padding * 2

    lines = _wrap_text(title, font_title, max_text_w, draw)
    line_h = 86
    y_title = h - 70 - len(lines) * line_h
    y_kicker = y_title - 36

    draw.text((padding, y_kicker), kicker.upper(), font=font_kicker,
              fill=(255, 255, 255, 200))
    for line in lines:
        draw.text((padding, y_title), line, font=font_title, fill=(255, 255, 255, 255))
        y_title += line_h

    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG", quality=95)
    return buf.getvalue()


def _wrap_text(text: str, font, max_width: int, draw) -> list[str]:
    lines = []
    current = ""
    for char in text:
        test = current + char
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] > max_width:
            if current:
                lines.append(current)
            current = char
        else:
            current = test
    if current:
        lines.append(current)
    return lines


def _image_to_cid_pair(img_bytes: bytes, cid_name: str) -> tuple[str, MIMEImage]:
    mime_img = MIMEImage(img_bytes, _subtype="png")
    mime_img.add_header("Content-ID", f"<{cid_name}>")
    mime_img.add_header("Content-Disposition", "inline", filename=f"{cid_name}.png")
    return f"cid:{cid_name}", mime_img


def render_email_html(article: dict, image_paths: dict, output_dir: Path) -> tuple[str, list[MIMEImage]]:
    embedded_images: list[MIMEImage] = []

    # ── 히어로 이미지 ──
    hero_src = image_paths.get("hero", "")
    hero_cid = ""
    if hero_src:
        hero_file = output_dir / hero_src if not Path(hero_src).is_absolute() else Path(hero_src)
        if hero_file.exists():
            hero_bytes = _make_hero_image(str(hero_file), article["title"])
            hero_cid, hero_mime = _image_to_cid_pair(hero_bytes, "hero")
            embedded_images.append(hero_mime)

    # ── 섹션 이미지 (16:9 crop) ──
    section_cids: dict[str, str] = {}
    image_positions = article.get("image_positions", {})
    body_img_w = CONTENT_WIDTH - PAD * 2
    for key, src in image_paths.items():
        if key == "hero":
            continue
        img_file = output_dir / src if not Path(src).is_absolute() else Path(src)
        if img_file.exists():
            img = Image.open(img_file).convert("RGB")
            render_w = body_img_w * 2
            render_h = int(render_w * 9 / 16)
            img = _crop_to_fill(img, render_w, render_h)
            img = _round_corners(img, radius=32)
            buf = io.BytesIO()
            img.save(buf, format="PNG", quality=90)
            cid, mime = _image_to_cid_pair(buf.getvalue(), key.replace("-", "_"))
            section_cids[key] = cid
            embedded_images.append(mime)

    # ── 본문 빌드 ──
    md_converter = md_lib.Markdown(extensions=["extra"])
    body_rows = []

    for i, sec in enumerate(article["sections"]):
        img_key = f"section-{i}"
        img_html = ""
        if img_key in section_cids:
            img_html = (
                f'<img src="{section_cids[img_key]}" '
                f'width="{body_img_w}" '
                f'style="display:block;border-radius:16px;" '
                f'alt="{sec["heading"]}">'
            )

        body_rows.append(
            f'<tr><td style="padding:32px 0 12px;font-size:13pt;font-weight:800;'
            f'line-height:1.36;letter-spacing:-0.025em;color:{INK};'
            f'font-family:{FONT};">'
            f'{sec["heading"]}</td></tr>'
        )

        raw_pos = image_positions.get(img_key)
        paragraphs = [p for p in sec["body"].split("\n\n") if p.strip()]

        if isinstance(raw_pos, int) and img_html and paragraphs:
            para_idx = max(0, min(raw_pos, len(paragraphs)))
            before = "\n\n".join(paragraphs[:para_idx])
            after = "\n\n".join(paragraphs[para_idx:])
            if before:
                body_rows.extend(_md_rows(before, md_converter))
            body_rows.append(f'<tr><td style="padding:20px 0;font-family:{FONT};font-size:11pt;">{img_html}</td></tr>')
            if after:
                body_rows.extend(_md_rows(after, md_converter))
        else:
            if img_html:
                body_rows.append(f'<tr><td style="padding:20px 0;font-family:{FONT};font-size:11pt;">{img_html}</td></tr>')
            body_rows.extend(_md_rows(sec["body"], md_converter))

    body_content = "\n".join(body_rows)

    # ── TL;DR (Outlook용 테이블 불렛) ──
    tldr_items = "".join(
        f'<tr>'
        f'<td style="padding:3px 8px 3px 0;font-size:11pt;color:{ACCENT};font-weight:700;'
        f'vertical-align:top;width:14px;font-family:{FONT};">&#8226;</td>'
        f'<td style="padding:3px 0;font-size:11pt;line-height:1.72;color:{INK_SECONDARY};'
        f'font-family:{FONT};">{pt}</td>'
        f'</tr>'
        for pt in article["tldr_points"]
    )

    # ── 태그 (#해시태그) ──
    tags = article.get("tags", ["AI & 업무"])
    tags_html = " ".join(
        f'<span style="font-size:10pt;font-weight:600;color:{ACCENT};'
        f'font-family:{FONT};margin-right:10px;">#{tag}</span>'
        for tag in tags
    )

    # ── 참고자료 ──
    ref_items = "".join(
        f'<tr><td style="font-size:9pt;line-height:1.7;color:{INK_MUTED};'
        f'padding:6px 0;border-bottom:1px solid {LINE};font-family:{FONT};">{ref}</td></tr>'
        for ref in article["references"]
    )

    issue_number = article.get("issue_number", "")
    issue_label = f"Issue #{issue_number}" if issue_number else article["pub_date"]

    hero_row = ""
    if hero_cid:
        hero_row = (
            f'<tr><td style="padding:0;font-family:{FONT};font-size:11pt;">'
            f'<img src="{hero_cid}" width="{CONTENT_WIDTH}" '
            f'style="display:block;width:{CONTENT_WIDTH}px;" alt="{article["title"]}">'
            f'</td></tr>'
        )

    # ── 최종 이메일 HTML ──
    email_html = f"""<!DOCTYPE html>
<html lang="ko" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<!--[if mso]>
<noscript>
<xml>
<o:OfficeDocumentSettings>
<o:PixelsPerInch>96</o:PixelsPerInch>
</o:OfficeDocumentSettings>
</xml>
</noscript>
<![endif]-->
<style>
  body {{ margin:0; padding:0; background:{CANVAS}; }}
  table {{ border-collapse:collapse; }}
  td {{ font-family:{FONT}; font-size:11pt; }}
  img {{ border:0; outline:none; text-decoration:none; }}
  p {{ margin:0 0 14px 0; font-size:11pt; line-height:1.82; color:{INK_SECONDARY}; font-family:{FONT}; }}
  strong {{ font-weight:700; color:{INK}; }}
</style>
<!--[if mso]>
<style>
  body, table, td, p, li, span, div {{ font-family:{FONT} !important; }}
</style>
<![endif]-->
</head>
<body style="margin:0;padding:0;background:{CANVAS};font-family:{FONT};">

<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{CANVAS};">
<tr><td align="center" style="padding:0;">

<table role="presentation" width="{CONTENT_WIDTH}" cellpadding="0" cellspacing="0">

<!-- 헤더 -->
<tr><td style="padding:0;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
  <tr>
    <td style="padding:16px 0;font-size:11pt;font-weight:700;letter-spacing:0.1em;color:{INK};font-family:Arial,sans-serif;">
      INSIGHT WEEKLY
    </td>
    <td align="right" style="padding:16px 0;font-size:8pt;font-weight:600;letter-spacing:0.06em;color:{INK_MUTED};font-family:Arial,sans-serif;">
      {issue_label}
    </td>
  </tr>
  </table>
</td></tr>

<!-- 히어로 -->
{hero_row}

<!-- 콘텐츠 (하나의 연속 흰색 박스) -->
<tr><td bgcolor="{SURFACE}" style="background:{SURFACE};padding:0;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0">

  <!-- 태그 -->
  <tr><td style="padding:24px {PAD}px 8px {PAD}px;">
    {tags_html}
  </td></tr>

  <!-- 저자·날짜 -->
  <tr><td style="padding:4px {PAD}px 20px {PAD}px;font-size:10pt;color:{INK_MUTED};font-family:{FONT};">
    <strong style="color:{INK_SECONDARY};">기업문화AX팀</strong>
    <span style="color:{LINE};margin:0 8px;">&middot;</span>
    {article["pub_date"]}
  </td></tr>

  <!-- 구분선 -->
  <tr><td style="padding:0 {PAD}px;"><hr style="border:none;border-top:1px solid {LINE};margin:0;"></td></tr>

  <!-- TL;DR -->
  <tr><td style="padding:24px {PAD}px;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
      bgcolor="{ACCENT_SOFT}" style="background:{ACCENT_SOFT};">
    <!--[if mso]><tr><td style="padding:20px 24px;"><![endif]-->
    <!--[if !mso]><!--><tr><td style="padding:20px 24px;border-radius:16px;"><!--<![endif]-->
      <div style="font-size:10pt;font-weight:700;letter-spacing:0.04em;color:{ACCENT};margin-bottom:10px;font-family:{FONT};">
        세 줄 요약
      </div>
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
        {tldr_items}
      </table>
    </td></tr>
    </table>
  </td></tr>

  <!-- 본문 -->
  <tr><td style="padding:0 {PAD}px 24px {PAD}px;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
      {body_content}
    </table>
  </td></tr>

  <!-- 참고자료 -->
  <tr><td style="padding:0 {PAD}px;">
    <hr style="border:none;border-top:1px solid {LINE};margin:0 0 24px 0;">
    <div style="font-size:10pt;font-weight:700;color:{INK_MUTED};margin-bottom:12px;font-family:{FONT};">참고자료</div>
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
      {ref_items}
    </table>
  </td></tr>

  <!-- 푸터 -->
  <tr><td style="padding:32px {PAD}px 40px {PAD}px;text-align:center;font-size:9pt;line-height:1.7;color:{INK_MUTED};border-top:1px solid {LINE};font-family:{FONT};">
    Insight Weekly &middot; 기업문화AX팀 발행<br>
    매주 목요일 발행합니다.
  </td></tr>

</table>
</td></tr>

</table>

</td></tr>
</table>
</body>
</html>"""

    return email_html, embedded_images


# 레이어 역할색 — article.css .layer-* 와 같은 값
LAYER_COLORS = {"exec": "#6B4FA0", "lead": ACCENT, "leader": ACCENT, "member": "#2F5D9E"}


def _md_rows(text: str, md_converter) -> list[str]:
    """본문 마크다운 → 표 행. 레이어 문단은 흰 바탕·역할색 좌측 테두리·라벨 박스로 감싼다."""
    rows = []
    for role, chunk in split_segment_blocks(text):
        inner = md_converter.convert(chunk)
        md_converter.reset()
        if not role:
            rows.append(_wrap_body_html(inner))
            continue
        color = LAYER_COLORS.get(role, ACCENT)
        label = SEGMENT_LABELS.get(role, role)
        rows.append(
            f'<tr><td style="padding:12px 0;">'
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" bgcolor="{SURFACE}" '
            f'style="background:{SURFACE};border:1px solid {LINE};border-left:4px solid {color};">'
            f'<tr><td style="padding:16px 20px 4px;font-family:{FONT};font-size:10pt;font-weight:700;'
            f'color:{color};">{label}</td></tr>'
            f'<tr><td style="padding:0 20px 4px;">'
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0">'
            f'{_wrap_body_html(inner)}</table></td></tr></table></td></tr>'
        )
    return rows


def _wrap_body_html(html: str) -> str:
    html = re.sub(
        r"<p>(.*?)</p>",
        rf'<p style="margin:0 0 14px 0;font-size:11pt;line-height:1.82;color:{INK_SECONDARY};'
        rf'font-family:{FONT};">\1</p>',
        html, flags=re.DOTALL
    )
    html = re.sub(
        r"<blockquote>(.*?)</blockquote>",
        rf'<table role="presentation" cellpadding="0" cellspacing="0" style="margin:14px 0;">'
        rf'<tr><td style="border-left:3px solid {ACCENT};padding-left:16px;font-size:11pt;'
        rf'line-height:1.75;color:{INK_SECONDARY};font-family:{FONT};">\1</td></tr></table>',
        html, flags=re.DOTALL
    )
    html = re.sub(r"<hr\s*/?>", "", html)
    return f'<tr><td style="padding:0;font-family:{FONT};font-size:11pt;">{html}</td></tr>'


def build_eml(subject: str, html_body: str, embedded_images: list[MIMEImage],
              recipients: list[str], cc: list[str] = None,
              sender: str = "Insight Weekly <noreply@example.com>") -> bytes:
    msg = MIMEMultipart("related")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    if cc:
        msg["Cc"] = ", ".join(cc)

    html_part = MIMEText(html_body, "html", "utf-8")
    msg.attach(html_part)

    for mime_img in embedded_images:
        msg.attach(mime_img)

    return msg.as_bytes()


# ── 방법 B: 전체 이미지 기반 이메일 ──
# 웹페이지를 메일 전용 변형(email-head.html · email-body.html, server.write_email_pages)으로
# 600px 폭에서 찍는다. 머리(헤더·히어로)와 본문을 따로 찍어 그 사이에 "웹에서 보기" 줄을 넣는다.

EMAIL_WIDTH = 600   # 폰 375px에서 ×0.625 — 캡처 CSS(article.css .email-capture)가 이 폭 기준
EMAIL_PAGES = ("email-head.html", "email-body.html")


def _trim_bottom(img: Image.Image, pad: int = 60) -> Image.Image:
    """하단의 빈 영역(균일 색상 행)을 제거하고 pad 픽셀만 남긴다."""
    w, h = img.size
    sample_xs = list(range(10, w - 10, max(1, w // 30)))
    crop_y = h
    for y in range(h - 1, -1, -1):
        pixels = [img.getpixel((x, y))[:3] for x in sample_xs]
        ref = pixels[0]
        is_uniform = all(
            abs(p[0] - ref[0]) <= 10 and
            abs(p[1] - ref[1]) <= 10 and
            abs(p[2] - ref[2]) <= 10
            for p in pixels
        )
        if not is_uniform:
            crop_y = min(y + 1 + pad, h)
            break
    if crop_y < h:
        img = img.crop((0, 0, w, crop_y))
    return img


def capture_article_screenshot(preview_url: str, output_path: Path,
                               width: int = EMAIL_WIDTH, pad: int = 60) -> Path:
    """프리뷰 페이지를 풀페이지 PNG 스크린샷(2배율)으로 캡처한다."""
    from html2image import Html2Image
    import tempfile

    tmp_dir = tempfile.mkdtemp()
    hti = Html2Image(
        browser_executable=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        output_path=tmp_dir,
        custom_flags=[
            "--no-sandbox",
            "--disable-gpu",
            "--hide-scrollbars",
            "--force-device-scale-factor=2",
            "--virtual-time-budget=8000",   # 웹폰트·이미지 로드 대기
        ],
    )

    fname = "capture.png"
    hti.screenshot(url=preview_url, save_as=fname, size=(width, 8000))

    raw = Image.open(Path(tmp_dir) / fname)
    raw = _trim_bottom(raw, pad=pad)
    raw.save(str(output_path), format="PNG", quality=95)
    return output_path


def _web_link_row(web_url: str, top: bool = False) -> str:
    """"웹에서 보기" 줄. 이미지 안의 참고자료 링크는 눌리지 않으므로 링크가 필요한 독자를
    웹페이지로 보낸다. top이면 제목 아래(본문 이미지 위)용 짧은 문구. web_url이 비면 빈 문자열."""
    if not web_url:
        return ""
    url = html.escape(web_url, quote=True)
    lead = "글자가 작게 보이면" if top else "참고자료 링크는 웹페이지에서 열립니다"
    pad = "14px 16px" if top else "4px 16px 28px"
    return (
        f'<tr><td align="center" style="padding:{pad};font-family:{FONT};font-size:11pt;'
        f'line-height:1.5;color:{INK_MUTED};">{lead} &middot; '
        f'<a href="{url}" target="_blank" style="color:{ACCENT};font-weight:700;'
        f'text-decoration:underline;">웹에서 보기</a></td></tr>'
    )


def _img_row(cid: str, display_w: int, alt: str, web_url: str) -> str:
    img = (f'<img src="cid:{cid}" width="{display_w}" '
           f'style="display:block;width:{display_w}px;max-width:100%;height:auto;border:0;" '
           f'alt="{html.escape(alt, quote=True)}">')
    if web_url:
        img = f'<a href="{html.escape(web_url, quote=True)}" target="_blank">{img}</a>'
    return f'<tr><td align="center" style="padding:0;">{img}</td></tr>'


def _wrap_mail(rows: str) -> str:
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


def _png_part(path: Path, cid: str) -> MIMEImage:
    mime_img = MIMEImage(path.read_bytes(), _subtype="png")
    mime_img.add_header("Content-ID", f"<{cid}>")
    mime_img.add_header("Content-Disposition", "inline", filename=f"{cid}.png")
    return mime_img


def build_image_eml(subject: str, preview_base: str, output_dir: Path,
                    recipients: list[str], cc: list[str] = None,
                    sender: str = "Insight Weekly <noreply@example.com>",
                    web_url: str = "") -> bytes:
    """메일 전용 변형 페이지 두 장을 캡처해 이미지 기반 .eml을 빌드한다 (--mode image).

    preview_base: email-head.html · email-body.html이 있는 디렉토리 URL(끝 슬래시 포함).
    web_url이 있으면 이미지를 그 주소로 링크하고 제목 아래·하단에 "웹에서 보기" 줄을 붙인다.
    두 장을 이은 전체 이미지(email_screenshot.png)도 남긴다 — 리허설·검토용.
    """
    head_png = output_dir / "email_head.png"
    body_png = output_dir / "email_body.png"
    capture_article_screenshot(preview_base + EMAIL_PAGES[0], head_png, pad=0)
    capture_article_screenshot(preview_base + EMAIL_PAGES[1], body_png)

    head_img, body_img = Image.open(head_png), Image.open(body_png)
    full = Image.new("RGB", (head_img.width, head_img.height + body_img.height))
    full.paste(head_img, (0, 0))
    full.paste(body_img, (0, head_img.height))
    full.save(output_dir / "email_screenshot.png", format="PNG")

    display_w = min(head_img.width // 2, EMAIL_WIDTH)
    rows = "\n".join([
        _img_row("article_head", display_w, subject, web_url),
        _web_link_row(web_url, top=True),
        _img_row("article_body", display_w, "Insight Weekly", web_url),
        _web_link_row(web_url),
    ])
    parts = [_png_part(head_png, "article_head"), _png_part(body_png, "article_body")]
    return build_eml(subject, _wrap_mail(rows), parts, recipients, cc, sender)


def build_teaser_eml(subject: str, article: dict, output_dir: Path,
                     recipients: list[str], cc: list[str] = None,
                     sender: str = "Insight Weekly <noreply@example.com>",
                     web_url: str = "") -> bytes:
    """폴백(--mode teaser): 대표 이미지 + 제목 + 세 줄 요약(텍스트) + 웹 링크 버튼.

    본문을 이미지로 넣지 않아 폰에서도 글자가 기기 글꼴 크기로 보인다. 전문은 웹에서 읽는다.
    """
    if not web_url:
        raise ValueError("teaser 메일은 웹 주소가 있어야 합니다 — settings.yaml web_base_url을 채우세요.")
    e = html.escape
    url = e(web_url, quote=True)
    parts: list[MIMEImage] = []
    issue = article.get("issue_number", "")
    issue_html = (f'<span style="float:right;font-size:9pt;color:{INK_MUTED};letter-spacing:0.06em;">'
                  f'Issue #{e(str(issue))}</span>') if issue else ""
    rows = [
        f'<tr><td style="padding:0 16px 14px;font-family:Arial,sans-serif;font-size:11pt;'
        f'font-weight:700;letter-spacing:0.1em;color:{INK};">INSIGHT WEEKLY{issue_html}</td></tr>'
    ]
    hero_file = article.get("hero_file", "")
    if hero_file and (output_dir / hero_file).exists():
        hero = _crop_to_fill(Image.open(output_dir / hero_file).convert("RGB"),
                             EMAIL_WIDTH * 2, int(EMAIL_WIDTH * 2 * 9 / 16))
        buf = io.BytesIO()
        hero.save(buf, format="PNG")
        cid, mime = _image_to_cid_pair(buf.getvalue(), "hero")
        parts.append(mime)
        rows.append(f'<tr><td style="padding:0;"><a href="{url}" target="_blank">'
                    f'<img src="{cid}" width="{EMAIL_WIDTH}" alt="" style="display:block;'
                    f'width:{EMAIL_WIDTH}px;max-width:100%;height:auto;border:0;"></a></td></tr>')
    bullets = "".join(
        f'<tr><td style="padding:4px 10px 4px 0;vertical-align:top;color:{ACCENT};font-weight:700;'
        f'font-family:{FONT};font-size:12pt;">&#8226;</td><td style="padding:4px 0;font-family:{FONT};'
        f'font-size:12pt;line-height:1.6;color:{INK_SECONDARY};word-break:keep-all;">{e(pt)}</td></tr>'
        for pt in article.get("tldr_points", [])
    )
    rows.append(
        f'<tr><td bgcolor="{SURFACE}" style="background:{SURFACE};padding:24px 24px 28px;">'
        f'<div style="font-family:{FONT};font-size:17pt;font-weight:800;line-height:1.35;color:{INK};word-break:keep-all;'
        f'margin-bottom:6px;">{e(article["title"])}</div>'
        f'<div style="font-family:{FONT};font-size:10pt;color:{INK_MUTED};margin-bottom:18px;">'
        f'기업문화AX팀 &middot; {e(article.get("pub_date", ""))}</div>'
        f'<div style="font-family:{FONT};font-size:10pt;font-weight:700;color:{ACCENT};margin-bottom:6px;">'
        f'세 줄 요약</div>'
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0">{bullets}</table>'
        f'<table role="presentation" cellpadding="0" cellspacing="0" style="margin-top:22px;"><tr>'
        f'<td bgcolor="{ACCENT}" style="background:{ACCENT};padding:12px 22px;">'
        f'<a href="{url}" target="_blank" style="font-family:{FONT};font-size:12pt;font-weight:700;'
        f'color:#FFFFFF;text-decoration:none;">웹에서 전문 보기 &rarr;</a></td></tr></table>'
        f'</td></tr>'
    )
    rows.append(f'<tr><td style="padding:24px 16px 32px;text-align:center;font-family:{FONT};font-size:9pt;'
                f'line-height:1.7;color:{INK_MUTED};">Insight Weekly &middot; 기업문화AX팀 발행<br>'
                f'매주 목요일 발행합니다.</td></tr>')
    return build_eml(subject, _wrap_mail("\n".join(rows)), parts, recipients, cc, sender)


def main(argv=None) -> None:
    """python web/email_renderer.py <slug> --to a@x,b@x [--cc ...] [--mode image|teaser]

    output/<slug>/(발행 도구 결과)로 .eml을 만든다. 리허설 결과에 따라 당일 teaser로 바꿔 보낼 수 있다.
    """
    import argparse
    import json
    import server
    from site_export import article_web_url

    ap = argparse.ArgumentParser(description="발행물 → .eml")
    ap.add_argument("slug")
    ap.add_argument("--mode", choices=("image", "teaser"), default="image")
    ap.add_argument("--to", required=True, help="쉼표 구분")
    ap.add_argument("--cc", default="")
    ap.add_argument("--out", help="저장 경로 (기본 output/<slug>/newsletter[-teaser].eml)")
    args = ap.parse_args(argv)

    out_dir = server.OUTPUT_DIR / args.slug
    article = json.loads((out_dir / "article.json").read_text(encoding="utf-8"))
    subject = f"[Insight Weekly] {article['title']}"

    def split(v):
        return [x.strip() for x in v.split(",") if x.strip()]

    web_url = article_web_url(args.slug)
    if not web_url:
        print("경고: settings.yaml web_base_url이 비어 있어 '웹에서 보기' 링크가 빠집니다.")
    if args.mode == "teaser":
        eml = build_teaser_eml(subject, article, out_dir, split(args.to), split(args.cc), web_url=web_url)
    else:
        server.write_email_pages(article, out_dir)
        eml = build_image_eml(subject, out_dir.as_uri() + "/", out_dir, split(args.to),
                              split(args.cc), web_url=web_url)
    dest = Path(args.out) if args.out else out_dir / (
        "newsletter-teaser.eml" if args.mode == "teaser" else "newsletter.eml")
    dest.write_bytes(eml)
    print(dest)


if __name__ == "__main__":
    main()

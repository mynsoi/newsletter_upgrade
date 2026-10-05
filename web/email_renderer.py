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
                html = md_converter.convert(before)
                md_converter.reset()
                body_rows.append(_wrap_body_html(html))
            body_rows.append(f'<tr><td style="padding:20px 0;font-family:{FONT};font-size:11pt;">{img_html}</td></tr>')
            if after:
                html = md_converter.convert(after)
                md_converter.reset()
                body_rows.append(_wrap_body_html(html))
        else:
            if img_html:
                body_rows.append(f'<tr><td style="padding:20px 0;font-family:{FONT};font-size:11pt;">{img_html}</td></tr>')
            html = md_converter.convert(sec["body"])
            md_converter.reset()
            body_rows.append(_wrap_body_html(html))

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

def _trim_bottom(img: Image.Image) -> Image.Image:
    """하단의 빈 영역(균일 색상 행)을 제거한다."""
    w, h = img.size
    sample_xs = list(range(10, w - 10, max(1, w // 30)))
    crop_y = h
    for y in range(h - 1, max(0, h - 10000), -1):
        pixels = [img.getpixel((x, y))[:3] for x in sample_xs]
        ref = pixels[0]
        is_uniform = all(
            abs(p[0] - ref[0]) <= 10 and
            abs(p[1] - ref[1]) <= 10 and
            abs(p[2] - ref[2]) <= 10
            for p in pixels
        )
        if not is_uniform:
            crop_y = min(y + 60, h)
            break
    if crop_y < h:
        img = img.crop((0, 0, w, crop_y))
    return img


def capture_article_screenshot(preview_url: str, output_path: Path,
                               width: int = 760) -> Path:
    """프리뷰 페이지를 풀페이지 PNG 스크린샷으로 캡처한다."""
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
        ],
    )

    fname = "article_full.png"
    hti.screenshot(url=preview_url, save_as=fname, size=(width, 8000))

    raw = Image.open(Path(tmp_dir) / fname)
    raw = _trim_bottom(raw)
    raw.save(str(output_path), format="PNG", quality=95)
    return output_path


def _web_link_row(web_url: str) -> str:
    """이미지 메일 하단 "웹에서 보기" 줄. 이미지 안의 참고자료 링크는 눌리지 않으므로
    링크가 필요한 독자를 웹페이지로 보낸다. web_url이 비면 빈 문자열."""
    if not web_url:
        return ""
    url = html.escape(web_url, quote=True)
    return (
        f'<tr><td align="center" style="padding:4px 0 28px;font-family:{FONT};font-size:10pt;'
        f'color:{INK_MUTED};">참고자료 링크는 웹페이지에서 열립니다 &middot; '
        f'<a href="{url}" target="_blank" style="color:{ACCENT};font-weight:700;'
        f'text-decoration:underline;">웹에서 보기</a></td></tr>'
    )


def build_image_eml(subject: str, preview_url: str, output_dir: Path,
                    recipients: list[str], cc: list[str] = None,
                    sender: str = "Insight Weekly <noreply@example.com>",
                    web_url: str = "") -> bytes:
    """프리뷰 페이지를 스크린샷으로 캡처하여 이미지 기반 .eml을 빌드한다.

    web_url이 있으면 본문 이미지를 그 주소로 링크하고 하단에 "웹에서 보기" 줄을 붙인다.
    """
    screenshot_path = output_dir / "email_screenshot.png"
    capture_article_screenshot(preview_url, screenshot_path)

    full_img = Image.open(screenshot_path)
    display_w = min(full_img.width // 2, CONTENT_WIDTH)

    buf = io.BytesIO()
    full_img.save(buf, format="PNG", quality=95)
    mime_img = MIMEImage(buf.getvalue(), _subtype="png")
    mime_img.add_header("Content-ID", "<article_full>")
    mime_img.add_header("Content-Disposition", "inline", filename="article.png")

    img_open, img_close = "", ""
    if web_url:
        img_open = f'<a href="{html.escape(web_url, quote=True)}" target="_blank">'
        img_close = "</a>"

    body = f"""<!DOCTYPE html>
<html lang="ko">
<head><meta charset="utf-8">
<style>body{{margin:0;padding:0;background:{CANVAS};}}table{{border-collapse:collapse;}}img{{border:0;}}</style>
</head>
<body style="margin:0;padding:0;background:{CANVAS};">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{CANVAS};">
<tr><td align="center" style="padding:20px 0;">
{img_open}<img src="cid:article_full" width="{display_w}"
  style="display:block;width:{display_w}px;max-width:100%;height:auto;border:0;" alt="Insight Weekly">{img_close}
</td></tr>
{_web_link_row(web_url)}
</table>
</body></html>"""

    return build_eml(subject, body, [mime_img], recipients, cc, sender)

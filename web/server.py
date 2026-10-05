"""
아티클 발행 도구 — Flask 로컬 서버

.md 업로드 → 파싱 → DALL-E 3 이미지 생성 → 이미지 선택 → 정적 HTML 생성
"""
import os
import re
import json
import shutil
import base64
import tempfile
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from flask import Flask, request, jsonify, send_from_directory, send_file
import markdown as md_lib
import openai

from segments import (
    SEGMENT_COMMENT_RE, SEGMENT_LABELS, SEGMENT_MARK_PREFIX,
    split_segment_blocks, strip_segment_marks,
)

# ── .env 로드 ──
def _load_dotenv():
    """ROOT/.env 파일이 있으면 환경변수로 로드한다."""
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

_load_dotenv()

# ── 경로 ──
ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = WEB_DIR / "templates"
STATIC_DIR = WEB_DIR / "static"
OUTPUT_DIR = ROOT / "output"

app = Flask(__name__)

# ── OpenAI 클라이언트 ──
_client = None

def get_openai_client(api_key: str = None):
    global _client
    key = api_key or os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("API 키가 설정되지 않았습니다.")
    if api_key:
        return openai.OpenAI(api_key=api_key)
    if _client is None:
        _client = openai.OpenAI(api_key=key)
    return _client


# ══════════════════════════════════════════════════════════════
# 마크다운 파싱
# ══════════════════════════════════════════════════════════════

def parse_article_md(text: str) -> dict:
    """아티클 .md를 파싱하여 구조화된 데이터를 반환한다."""
    lines = text.split("\n")

    # 제목 (첫 번째 # 헤더)
    title = ""
    for line in lines:
        if line.startswith("# ") and not line.startswith("## "):
            title = line[2:].strip()
            break

    # 메타 주석에서 slug, 발행일 추출
    slug = ""
    pub_date = ""
    slug_match = re.search(r"slug:\s*([\w-]+)", text)
    if slug_match:
        slug = slug_match.group(1)

    pub_date, warnings = _read_pub_date(text)

    # 레이어 표시(<!-- segment: X -->)는 주석 제거 전에 본문 표지로 바꿔 둔다 — 렌더러가 박스로 감싼다
    text = SEGMENT_COMMENT_RE.sub(lambda m: f"{SEGMENT_MARK_PREFIX}{m.group(1)}]]", text)

    # claims 주석 제거
    clean_text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)

    # TL;DR / 세 줄 요약 추출
    tldr_points = []
    tldr_match = re.search(
        r"\*\*(?:TL;DR|세 줄 요약)\*\*\s*\n((?:\s*-\s+.+\n?)+)", clean_text
    )
    if tldr_match:
        for line in tldr_match.group(1).strip().split("\n"):
            item = re.sub(r"^\s*-\s+", "", line).strip()
            if item:
                tldr_points.append(item)

    # 도입 문단 (TL;DR과 첫 ## 사이)
    intro = ""
    if tldr_match:
        tldr_end = tldr_match.end()
        first_h2 = clean_text.find("\n## ", tldr_end)
        if first_h2 != -1:
            intro = clean_text[tldr_end:first_h2].strip()
            intro = re.sub(r"<!--.*?-->", "", intro, flags=re.DOTALL).strip()

    # 본문 섹션 (## 헤더별 분할)
    sections = []
    body_start = clean_text.find("\n## ")
    if body_start == -1:
        body_text = clean_text
    else:
        body_text = clean_text[body_start:]

    # 참고자료 분리
    references = []
    ref_split = re.split(r"\n## 참고자료\s*\n", body_text, maxsplit=1)
    if len(ref_split) == 2:
        body_text = ref_split[0]
        for line in ref_split[1].strip().split("\n"):
            item = re.sub(r"^\s*-\s+", "", line).strip()
            if item:
                references.append(item)

    # 섹션 파싱
    section_splits = re.split(r"\n(?=## )", body_text)
    for part in section_splits:
        part = part.strip()
        if not part:
            continue
        heading_match = re.match(r"^## (.+)", part)
        if heading_match:
            heading = heading_match.group(1).strip()
            body = part[heading_match.end():].strip()
            sections.append({"heading": heading, "body": body})

    tags = _extract_tags(clean_text, sections)

    return {
        "title": title,
        "slug": slug or _slugify(title),
        "pub_date": pub_date,
        "warnings": warnings,
        "tldr_points": tldr_points,
        "intro": intro,
        "sections": sections,
        "references": references,
        "tags": tags,
    }


PUB_DATE_RE = re.compile(r"발행 승인:\s*(\d{4}-\d{2}-\d{2})")


def _read_pub_date(text: str) -> tuple[str, list[str]]:
    """머리말(세 줄 요약·첫 소제목 앞)의 주석에서 `발행 승인: YYYY-MM-DD`를 읽는다.

    본문에 같은 문구가 있어도 잡히지 않도록 머리말 주석만 본다. 없으면 오늘 날짜 + 경고.
    """
    head_end = len(text)
    for marker in ("**세 줄 요약**", "**TL;DR**", "\n## "):
        i = text.find(marker)
        if i != -1:
            head_end = min(head_end, i)
    for comment in re.findall(r"<!--(.*?)-->", text[:head_end], flags=re.DOTALL):
        m = PUB_DATE_RE.search(comment)
        if m:
            return m.group(1), []
    today = datetime.now().strftime("%Y-%m-%d")
    return today, [
        f"머리말에 '<!-- 발행 승인: YYYY-MM-DD -->'가 없어 발행일을 오늘({today})로 넣었습니다. "
        "승인 기록을 확인하세요."
    ]


def _slugify(text: str) -> str:
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[\s]+", "-", text).strip("-").lower()[:60]


_TAG_KEYWORDS = {
    "AI 생산성": ["생산성", "productivity", "효율", "시간 절감"],
    "AI 도구": ["도구", "tool", "코파일럿", "copilot", "챗봇", "chatbot"],
    "조직 변화": ["조직 변화", "변화 관리", "change management", "전환"],
    "리더십": ["리더", "leader", "경영", "management", "매니저"],
    "협업": ["협업", "collaboration", "팀워크", "소통"],
    "조직 문화": ["문화", "culture", "심리적 안전", "psychological safety"],
    "인재 관리": ["인재", "talent", "채용", "hiring", "온보딩"],
    "자동화": ["자동화", "automation", "워크플로", "workflow"],
    "데이터·분석": ["데이터", "data", "분석", "analytics", "측정"],
    "의사결정": ["의사결정", "decision", "판단", "거버넌스"],
    "교육·성장": ["교육", "학습", "learning", "스킬", "skill", "역량"],
    "디지털 전환": ["디지털 전환", "DX", "digital transformation"],
    "보상·평가": ["보상", "평가", "성과", "KPI", "performance"],
    "조직 역량": ["흡수역량", "역량", "capability", "absorptive"],
}


def _extract_tags(text: str, sections: list) -> list:
    """본문과 소제목에서 키워드 매칭으로 태그를 추출한다."""
    combined = text.lower()
    for sec in sections:
        combined += " " + sec["heading"].lower()

    matched = []
    for tag, keywords in _TAG_KEYWORDS.items():
        if any(kw.lower() in combined for kw in keywords):
            matched.append(tag)
    return matched[:5] if matched else ["AI & 업무"]


# ══════════════════════════════════════════════════════════════
# HTML 렌더링
# ══════════════════════════════════════════════════════════════

def _render_md_blocks(text: str, md_converter) -> str:
    out = []
    for role, chunk in split_segment_blocks(text):
        inner = md_converter.convert(chunk)
        md_converter.reset()
        if role:
            label = SEGMENT_LABELS.get(role, role)
            out.append(
                f'<aside class="layer layer-{role}">'
                f'<div class="layer-label">{label}</div>{inner}</aside>'
            )
        else:
            out.append(inner)
    return "\n".join(out)


def render_article_html(article: dict, image_paths: dict, body_class: str = "") -> str:
    """Jinja2 없이 순수 문자열로 아티클 HTML을 렌더링한다.

    body_class: 메일 캡처용 변형(email-capture …) — 웹 발행본은 비워 둔다.
    """
    template_path = TEMPLATES_DIR / "article.html"
    template = template_path.read_text(encoding="utf-8")

    # 태그
    tags = article.get("tags", ["AI & 업무"])
    tags_html = "\n      ".join(
        f'<span class="tag">{tag}</span>' for tag in tags
    )

    # 호수 (issue_number)
    issue_number = article.get("issue_number", "")
    issue_label = f"Issue #{issue_number}" if issue_number else article["pub_date"]

    # TL;DR
    tldr_items = "\n".join(
        f"      <li>{pt}</li>" for pt in article["tldr_points"]
    )

    # 본문 HTML
    md_converter = md_lib.Markdown(extensions=["extra"])
    image_positions = article.get("image_positions", {})
    body_parts = []

    # 도입 문단 (TL;DR과 첫 소제목 사이)
    intro = article.get("intro", "")
    if intro:
        body_parts.append(f'<div class="intro">{md_converter.convert(intro)}</div>')
        md_converter.reset()

    for i, sec in enumerate(article["sections"]):
        img_key = f"section-{i}"
        img_tag = ""
        if img_key in image_paths:
            img_tag = (
                f'<img class="section-image" src="{image_paths[img_key]}" '
                f'alt="{sec["heading"]}">'
            )

        body_parts.append(f'<h2>{sec["heading"]}</h2>')

        raw_pos = image_positions.get(img_key)
        paragraphs = [p for p in sec["body"].split("\n\n") if p.strip()]

        if isinstance(raw_pos, int) and img_tag and paragraphs:
            para_idx = max(0, min(raw_pos, len(paragraphs)))
            before = "\n\n".join(paragraphs[:para_idx])
            after = "\n\n".join(paragraphs[para_idx:])
            if before:
                body_parts.append(_render_md_blocks(before, md_converter))
            body_parts.append(img_tag)
            if after:
                body_parts.append(_render_md_blocks(after, md_converter))
        else:
            if img_tag:
                body_parts.append(img_tag)
            body_parts.append(_render_md_blocks(sec["body"], md_converter))

    body_html = "\n".join(body_parts)

    # 참고자료
    ref_items = "\n".join(
        f"      <li>{ref}</li>" for ref in article["references"]
    )

    # 히어로 이미지
    hero_img = image_paths.get("hero", "")

    # 템플릿 치환
    html = template
    replacements = {
        "{{ title }}": article["title"],
        "{{ issue_label }}": issue_label,
        "{{ hero_image }}": hero_img,
        "{{ kicker }}": "Insight Weekly",
        "{% for tag in tags %}\n      <span class=\"tag\">{{ tag }}</span>\n      {% endfor %}": tags_html,
        "{{ author }}": "기업문화AX팀",
        "{{ pub_date }}": article["pub_date"],
        "{% for point in tldr_points %}\n      <li>{{ point }}</li>\n      {% endfor %}": tldr_items,
        "{{ body_html }}": body_html,
        "{{ body_class }}": body_class,
        "{% for ref in references %}\n      <li>{{ ref }}</li>\n      {% endfor %}": ref_items,
    }
    for key, val in replacements.items():
        html = html.replace(key, val)

    return html


# ══════════════════════════════════════════════════════════════
# API 라우트
# ══════════════════════════════════════════════════════════════

@app.route("/")
def index():
    return send_file(TEMPLATES_DIR / "publish.html")


@app.route("/style.css")
def article_css():
    return send_from_directory(STATIC_DIR, "article.css")


@app.route("/api/parse", methods=["POST"])
def api_parse():
    """업로드된 .md 파일을 파싱한다."""
    if "file" not in request.files:
        return jsonify({"error": "파일이 없습니다."}), 400

    file = request.files["file"]
    text = file.read().decode("utf-8")
    try:
        result = parse_article_md(text)
        # 원본 텍스트도 보관 (나중에 HTML 변환 시 필요)
        result["_raw"] = text
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"파싱 실패: {e}"}), 500


_IMAGE_STYLES = [
    {
        "label": "일러스트 A",
        "prefix": "Clean flat-style business illustration. Warm color palette — orange, amber, coral tones. Simple friendly figures, modern workplace setting.",
        "suffix": "Do NOT include any text, words, letters, numbers, labels, or captions anywhere in the image.",
    },
    {
        "label": "일러스트 B",
        "prefix": "Clean flat-style business illustration. Cool color palette — navy, teal, slate blue tones. Simple friendly figures, modern workplace setting.",
        "suffix": "Do NOT include any text, words, letters, numbers, labels, or captions anywhere in the image.",
    },
    {
        "label": "포토",
        "prefix": "ONE single editorial photograph — not a collage, not a grid, not multiple frames. Professional stock photo of a real workplace moment. Never show a direct frontal face. Real office with natural window light or warm indoor lighting. Shallow depth of field, soft bokeh. Muted warm tones. High-resolution photojournalistic quality — Harvard Business Review or Fast Company cover.",
        "suffix": "Do NOT include any text, words, letters, numbers, labels, or watermarks. Never show a direct frontal face — use back views, silhouettes, side profiles, or hand close-ups only.",
    },
]


_COMPOSITION_HINTS = {
    "일러스트 A": [
        "Wide establishing shot showing a full scene with multiple figures.",
        "Close-up focused on one or two characters interacting.",
        "Bird's-eye overhead view looking down at a workspace.",
        "Split or contrasting composition showing before/after or two sides.",
        "One character in foreground with activity in background.",
        "Isometric angled view of an office or meeting environment.",
    ],
    "일러스트 B": [
        "One character in foreground with activity in background.",
        "Isometric angled view of an office or meeting environment.",
        "Wide establishing shot showing a full scene with multiple figures.",
        "Close-up focused on one or two characters interacting.",
        "Split or contrasting composition showing before/after or two sides.",
        "Bird's-eye overhead view looking down at a workspace.",
    ],
    "포토": [
        "Tight close-up of hands or objects on a desk.",
        "One person seen from behind, looking out a window or at a screen.",
        "Over-the-shoulder shot of a team collaborating around a table.",
        "Wide environmental shot of an empty or sparsely occupied office space.",
        "Side-profile silhouette against bright window light.",
        "Bird's-eye flat-lay of work items arranged on a surface.",
    ],
}


def _build_scene_prompt(heading: str, body: str, style: dict, is_hero: bool, section_index: int = 0) -> str:
    body_snippet = re.sub(r"\s+", " ", strip_segment_marks(body or ""))[:400]
    if is_hero:
        scene = f"Wide panoramic scene for a newsletter cover. Topic: {heading}."
    else:
        scene = f"Scene illustrating: {heading}."
    if body_snippet:
        scene += f" Context: {body_snippet}"
    hints = _COMPOSITION_HINTS.get(style["label"], [])
    composition = hints[section_index % len(hints)] if hints else ""
    if composition and not is_hero:
        scene += f" Composition: {composition}"
    return f"{style['prefix']} {scene} {style['suffix']}"


def _generate_one(client, prompt: str, size: str, quality: str, key: str, idx: int, tmp_dir: Path):
    import sys
    print(f"  [{key}] 후보 {idx+1}/3 생성 시작...", flush=True)
    response = client.images.generate(
        model="gpt-image-2.5-flare",
        prompt=prompt,
        size=size,
        quality=quality,
        n=1,
    )
    img_data = base64.b64decode(response.data[0].b64_json)
    print(f"  [{key}] 후보 {idx+1}/3 완료 ({len(img_data)} bytes)", flush=True)
    filename = f"{key}_candidate_{idx}.png"
    filepath = tmp_dir / filename
    filepath.write_bytes(img_data)
    return f"/tmp-images/{filename}"


@app.route("/api/generate-images", methods=["POST"])
def api_generate_images():
    """스타일별 후보 3장을 병렬 생성한다."""
    data = request.json
    heading = data.get("heading", "")
    body = data.get("body", "")
    prompt_override = data.get("prompt", "")
    is_hero = data.get("is_hero", False)
    key = data.get("key", "unknown")
    section_index = data.get("section_index", 0)
    style_index = data.get("style_index")  # None이면 전체, 0/1/2이면 해당 스타일만
    user_api_key = request.headers.get("X-OpenAI-Key", "").strip()

    size = "1536x1024"
    quality = "medium"
    tmp_dir = Path(tempfile.gettempdir()) / "newsletter_images"
    tmp_dir.mkdir(exist_ok=True)

    env_key = os.environ.get("OPENAI_API_KEY", "")
    has_key = user_api_key or env_key
    use_placeholder = not has_key
    print(f"  [이미지 생성] key={key}, 모드={'DALL-E' if has_key else '플레이스홀더'}, 크기={size}, 화질={quality}", flush=True)

    if use_placeholder:
        images = [f"https://picsum.photos/seed/{key}{i}/1536/1024" for i in range(3)]
        labels = [s["label"] for s in _IMAGE_STYLES]
        return jsonify({"images": images, "labels": labels, "key": key})

    try:
        client = get_openai_client(user_api_key or None)
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 400

    # 단일 스타일 재생성
    if style_index is not None:
        style = _IMAGE_STYLES[style_index]
        if prompt_override:
            p = f"{style['prefix']} {prompt_override} {style['suffix']}"
        else:
            p = _build_scene_prompt(heading, body, style, is_hero, section_index)
        try:
            url = _generate_one(client, p, size, quality, key, style_index, tmp_dir)
            return jsonify({"image": url, "style_index": style_index, "label": style["label"], "key": key})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    prompts = []
    for i, style in enumerate(_IMAGE_STYLES):
        if prompt_override:
            p = f"{style['prefix']} {prompt_override} {style['suffix']}"
        else:
            p = _build_scene_prompt(heading, body, style, is_hero, section_index)
        prompts.append(p)

    images = [None, None, None]
    errors = []

    def gen(idx):
        return idx, _generate_one(client, prompts[idx], size, quality, key, idx, tmp_dir)

    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(gen, i) for i in range(3)]
        for future in futures:
            try:
                idx, url = future.result()
                images[idx] = url
            except openai.AuthenticationError:
                errors.append("API 키가 유효하지 않습니다.")
            except openai.RateLimitError:
                errors.append("API 요청 한도 초과입니다.")
            except Exception as e:
                errors.append(str(e))

    if errors and not any(images):
        return jsonify({"error": errors[0]}), 500

    labels = [s["label"] for s in _IMAGE_STYLES]
    result_images = [img or f"https://picsum.photos/seed/{key}{i}/1536/1024"
                     for i, img in enumerate(images)]
    return jsonify({"images": result_images, "labels": labels, "key": key})


@app.route("/tmp-images/<filename>")
def serve_tmp_image(filename):
    tmp_dir = Path(tempfile.gettempdir()) / "newsletter_images"
    return send_from_directory(tmp_dir, filename)


@app.route("/api/publish", methods=["POST"])
def api_publish():
    """선택된 이미지와 아티클 데이터로 정적 HTML을 생성한다."""
    data = request.json
    article = data.get("article", {})
    selected = data.get("selected_images", {})
    slug = article.get("slug", "untitled")

    # 출력 디렉토리
    out_dir = OUTPUT_DIR / slug
    out_dir.mkdir(parents=True, exist_ok=True)

    # 선택된 이미지를 output 폴더로 복사
    tmp_dir = Path(tempfile.gettempdir()) / "newsletter_images"
    image_paths = {}
    for key, url in selected.items():
        if url.startswith("http"):
            image_paths[key] = url
        else:
            src_filename = url.split("/")[-1]
            src_path = tmp_dir / src_filename
            dest_name = f"{key}.png"
            dest_path = out_dir / dest_name
            if src_path.exists():
                shutil.copy2(src_path, dest_path)
                image_paths[key] = dest_name
            elif dest_path.exists():
                image_paths[key] = dest_name

    # CSS 복사
    css_src = STATIC_DIR / "article.css"
    css_dest = out_dir / "style.css"
    shutil.copy2(css_src, css_dest)

    # HTML 렌더링
    html = render_article_html(article, image_paths)
    html_path = out_dir / "index.html"
    html_path.write_text(html, encoding="utf-8")

    # 아카이브 카드 썸네일용 (web/site_export.py)
    hero_file = image_paths.get("hero", "")
    article["hero_file"] = "" if hero_file.startswith("http") else hero_file
    # 메일 변형 페이지를 나중에 다시 그릴 때 쓴다 (write_email_pages)
    article["image_paths"] = image_paths

    article_json_path = out_dir / "article.json"
    article_json_path.write_text(json.dumps(article, ensure_ascii=False, indent=2), encoding="utf-8")

    # 임시 이미지 정리
    for f in tmp_dir.glob("*.png"):
        f.unlink(missing_ok=True)

    return jsonify({
        "output_path": str(out_dir.relative_to(ROOT)),
        "preview_url": f"/preview/{slug}/",
    })


def write_email_pages(article: dict, out_dir: Path) -> None:
    """메일 캡처용 변형 페이지(email-head.html · email-body.html)를 발행 폴더에 쓴다.

    웹 발행본(index.html)과 같은 내용에 .email-capture CSS(600px·본문 20px·링크 장식 제거)를
    입힌다. 머리와 본문을 나눠 찍어 그 사이에 "웹에서 보기" 줄을 넣기 위해 두 장이다.
    """
    image_paths = article.get("image_paths") or (
        {"hero": article["hero_file"]} if article.get("hero_file") else {})
    shutil.copy2(STATIC_DIR / "article.css", out_dir / "style.css")
    for name, part in (("email-head.html", "head"), ("email-body.html", "body")):
        page = render_article_html(article, image_paths,
                                   body_class=f"email-capture email-part-{part}")
        (out_dir / name).write_text(page, encoding="utf-8")


@app.route("/api/send-email", methods=["POST"])
def api_send_email():
    """발행된 아티클을 .eml 파일로 생성하여 다운로드한다.

    mode: "image"(기본 — 웹페이지 전문 이미지) | "teaser"(대표 이미지 + 세 줄 요약 + 웹 링크, 폴백)
    """
    from email_renderer import build_image_eml, build_teaser_eml
    from site_export import article_web_url

    data = request.json
    slug = data.get("slug", "")
    recipients = data.get("recipients", [])
    cc = data.get("cc", [])
    mode = data.get("mode", "image")

    if not slug:
        return jsonify({"error": "slug가 필요합니다."}), 400
    if not recipients:
        return jsonify({"error": "수신자가 필요합니다."}), 400

    out_dir = OUTPUT_DIR / slug
    if not out_dir.exists():
        return jsonify({"error": f"발행물을 찾을 수 없습니다: {slug}"}), 404

    article_json = out_dir / "article.json"
    if not article_json.exists():
        return jsonify({"error": "article.json을 찾을 수 없습니다."}), 404

    article = json.loads(article_json.read_text(encoding="utf-8"))
    subject = f"[Insight Weekly] {article['title']}"
    web_url = article_web_url(slug)

    try:
        if mode == "teaser":
            eml_bytes = build_teaser_eml(subject, article, out_dir, recipients, cc, web_url=web_url)
            name = "newsletter-teaser.eml"
        else:
            write_email_pages(article, out_dir)
            preview_base = f"http://localhost:5001/preview/{slug}/"
            eml_bytes = build_image_eml(subject, preview_base, out_dir, recipients, cc,
                                        web_url=web_url)
            name = "newsletter.eml"

        eml_path = out_dir / name
        eml_path.write_bytes(eml_bytes)

        return send_file(eml_path, as_attachment=True, download_name=name,
                         mimetype="message/rfc822")
    except Exception as e:
        return jsonify({"error": f"이메일 생성 실패: {str(e)}"}), 500


@app.route("/preview/<slug>/")
def preview(slug):
    out_dir = OUTPUT_DIR / slug
    return send_file(out_dir / "index.html")


@app.route("/preview/<slug>/<path:filename>")
def preview_static(slug, filename):
    out_dir = OUTPUT_DIR / slug
    return send_from_directory(out_dir, filename)


# ══════════════════════════════════════════════════════════════
# 메인
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    OUTPUT_DIR.mkdir(exist_ok=True)
    print(f"  아티클 발행 도구 서버")
    print(f"  http://localhost:5001")
    print(f"  출력 디렉토리: {OUTPUT_DIR}")
    app.run(host="127.0.0.1", port=5001, debug=True)

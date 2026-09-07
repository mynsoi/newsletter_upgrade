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

    date_match = re.search(r"발행 승인:\s*(\d{4}-\d{2}-\d{2})", text)
    if date_match:
        pub_date = date_match.group(1)
    if not pub_date:
        pub_date = datetime.now().strftime("%Y-%m-%d")

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
        "tldr_points": tldr_points,
        "sections": sections,
        "references": references,
        "tags": tags,
    }


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

def render_article_html(article: dict, image_paths: dict) -> str:
    """Jinja2 없이 순수 문자열로 아티클 HTML을 렌더링한다."""
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
                body_parts.append(md_converter.convert(before))
                md_converter.reset()
            body_parts.append(img_tag)
            if after:
                body_parts.append(md_converter.convert(after))
                md_converter.reset()
        else:
            if img_tag:
                body_parts.append(img_tag)
            body_parts.append(md_converter.convert(sec["body"]))
            md_converter.reset()

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
        "label": "일러스트",
        "prefix": "Clean flat-style business illustration. Warm color palette, simple friendly figures, modern workplace setting.",
        "suffix": "Do NOT include any text, words, letters, numbers, labels, or captions anywhere in the image.",
    },
    {
        "label": "포토",
        "prefix": "ONE single editorial photograph — not a collage, not a grid, not multiple frames. Professional stock photo of a real workplace moment. Choose ONE composition that best fits the topic: a close-up of hands shaking, one person at a desk seen from behind, a team huddled over a laptop shot over-the-shoulder, hands gesturing mid-conversation, or two colleagues talking in side profile. Never show a direct frontal face. Real office with natural window light or warm indoor lighting. Shallow depth of field, soft bokeh. Muted warm tones. High-resolution photojournalistic quality — Harvard Business Review or Fast Company cover.",
        "suffix": "Do NOT include any text, words, letters, numbers, labels, or watermarks. Never show a direct frontal face — use back views, silhouettes, side profiles, or hand close-ups only.",
    },
    {
        "label": "컨셉 아트",
        "prefix": "Stylized 3D rendered scene — not a single isolated icon, but a small environment or arrangement that tells a story. Pick ONE key object from the topic and place it in context with surrounding objects that give it meaning: a glowing sticky note among dozens of faded ones on a wall, an office chair in a sunlit room by a window, one open box glowing among rows of closed identical boxes, a lit desk lamp on one desk in a dark open-plan office, a compass on a cluttered table of maps. The hero object stands out through warm golden light or color while the surroundings stay muted cool-gray. Smooth stylized 3D materials, soft rounded edges, clay-render aesthetic. Cinematic composition with depth — foreground/background layers, shallow depth of field. No human figures.",
        "suffix": "Do NOT include any text, words, letters, numbers, labels, or captions anywhere in the image. Do NOT include any people, faces, hands, or human figures.",
    },
]


def _build_scene_prompt(heading: str, body: str, style: dict, is_hero: bool) -> str:
    body_snippet = re.sub(r"\s+", " ", body or "")[:400]
    if is_hero:
        scene = f"Wide panoramic scene for a newsletter cover. Topic: {heading}."
    else:
        scene = f"Scene illustrating: {heading}."
    if body_snippet:
        scene += f" Context: {body_snippet}"
    return f"{style['prefix']} {scene} {style['suffix']}"


def _generate_one(client, prompt: str, size: str, quality: str, key: str, idx: int, tmp_dir: Path):
    import sys
    print(f"  [{key}] 후보 {idx+1}/3 생성 시작...", flush=True)
    response = client.images.generate(
        model="gpt-image-1",
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

    prompts = []
    for i, style in enumerate(_IMAGE_STYLES):
        if prompt_override:
            p = f"{style['prefix']} {prompt_override} {style['suffix']}"
        else:
            p = _build_scene_prompt(heading, body, style, is_hero)
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
            # 외부 URL(플레이스홀더 모드) — URL 그대로 사용
            image_paths[key] = url
        else:
            src_filename = url.split("/")[-1]
            src_path = tmp_dir / src_filename
            if src_path.exists():
                dest_name = f"{key}.png"
                dest_path = out_dir / dest_name
                shutil.copy2(src_path, dest_path)
                image_paths[key] = dest_name

    # CSS 복사
    css_src = STATIC_DIR / "article.css"
    css_dest = out_dir / "style.css"
    shutil.copy2(css_src, css_dest)

    # HTML 렌더링
    html = render_article_html(article, image_paths)
    html_path = out_dir / "index.html"
    html_path.write_text(html, encoding="utf-8")

    # 임시 이미지 정리
    for f in tmp_dir.glob("*.png"):
        f.unlink(missing_ok=True)

    return jsonify({
        "output_path": str(out_dir.relative_to(ROOT)),
        "preview_url": f"/preview/{slug}/",
    })


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

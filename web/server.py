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

from flask import Flask, request, jsonify, send_from_directory, send_file
import markdown as md_lib
import openai

# ── 경로 ──
ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = WEB_DIR / "templates"
STATIC_DIR = WEB_DIR / "static"
OUTPUT_DIR = ROOT / "output"

app = Flask(__name__)

# ── OpenAI 클라이언트 ──
_client = None

def get_openai_client():
    global _client
    if _client is None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
        _client = openai.OpenAI(api_key=api_key)
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

    # 세 줄 요약 (TL;DR) 추출 — **세 줄 요약** 아래 목록
    tldr_points = []
    tldr_match = re.search(
        r"\*\*세 줄 요약\*\*\s*\n((?:\s*-\s+.+\n?)+)", clean_text
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

    return {
        "title": title,
        "slug": slug or _slugify(title),
        "pub_date": pub_date,
        "tldr_points": tldr_points,
        "sections": sections,
        "references": references,
    }


def _slugify(text: str) -> str:
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[\s]+", "-", text).strip("-").lower()[:60]


# ══════════════════════════════════════════════════════════════
# HTML 렌더링
# ══════════════════════════════════════════════════════════════

def render_article_html(article: dict, image_paths: dict) -> str:
    """Jinja2 없이 순수 문자열로 아티클 HTML을 렌더링한다."""
    template_path = TEMPLATES_DIR / "article.html"
    template = template_path.read_text(encoding="utf-8")

    # 태그 (slug에서 추출하거나 기본값)
    tags_html = '<span class="tag">AI &amp; 조직</span>'

    # TL;DR
    tldr_items = "\n".join(
        f"      <li>{pt}</li>" for pt in article["tldr_points"]
    )

    # 본문 HTML
    md_converter = md_lib.Markdown(extensions=["extra"])
    body_parts = []
    for i, sec in enumerate(article["sections"]):
        body_parts.append(f'<h2>{sec["heading"]}</h2>')
        img_key = f"section-{i}"
        if img_key in image_paths:
            body_parts.append(
                f'<img class="section-image" src="{image_paths[img_key]}" '
                f'alt="{sec["heading"]}">'
            )
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
        "{{ issue_label }}": article["pub_date"],
        "{{ hero_image }}": hero_img,
        "{{ kicker }}": "Insight Weekly",
        "{% for tag in tags %}\n      <span class=\"tag\">{{ tag }}</span>\n      {% endfor %}": tags_html,
        "{{ author }}": "기업문화팀",
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


@app.route("/api/generate-images", methods=["POST"])
def api_generate_images():
    """DALL-E 3로 이미지 후보 3장을 생성한다."""
    data = request.json
    prompt = data.get("prompt", "")
    is_hero = data.get("is_hero", False)
    key = data.get("key", "unknown")

    if not prompt:
        return jsonify({"error": "프롬프트가 비어 있습니다."}), 400

    size = "1792x1024" if is_hero else "1024x1024"

    images = []
    tmp_dir = Path(tempfile.gettempdir()) / "newsletter_images"
    tmp_dir.mkdir(exist_ok=True)

    # 플레이스홀더 모드: OPENAI_API_KEY가 없으면 picsum 이미지 사용
    use_placeholder = not os.environ.get("OPENAI_API_KEY")

    for i in range(3):
        if use_placeholder:
            w, h = (1792, 1024) if is_hero else (1024, 1024)
            images.append(
                f"https://picsum.photos/seed/{key}{i}/{w}/{h}"
            )
        else:
            try:
                client = get_openai_client()
                response = client.images.generate(
                    model="dall-e-3",
                    prompt=prompt,
                    size=size,
                    quality="standard",
                    n=1,
                    response_format="b64_json",
                )
                img_data = base64.b64decode(response.data[0].b64_json)
                filename = f"{key}_candidate_{i}.png"
                filepath = tmp_dir / filename
                filepath.write_bytes(img_data)
                images.append(f"/tmp-images/{filename}")
            except Exception as e:
                return jsonify({"error": f"이미지 생성 실패 (후보 {i+1}): {e}"}), 500

    return jsonify({"images": images, "key": key})


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
